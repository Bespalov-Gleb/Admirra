from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from core.database import get_db, SessionLocal
from core import models, schemas, security
from automation.yandex_direct import YandexDirectAPI
from automation.yandex_metrica import YandexMetricaAPI
from automation.vk_ads import (
    VKAdsAPI,
    exchange_vk_agency_client_credentials_for_integration,
    vk_campaigns_error_needs_agency_client_retry,
)
from automation.mytarget import MyTargetAPI
from automation.avito_ads import AvitoAdsAPI
from automation.avito_integration_helpers import (
    build_avito_api_from_integration as _build_avito_api_from_integration,
    get_metrika_integration_for_client as _get_metrika_integration_for_client,
    metrika_profile_login as _metrika_profile_login,
)
from typing import List, Optional
import uuid
import httpx
import logging
import asyncio
from datetime import datetime, timedelta, timezone
import os
import json
from core.logging_utils import log_event
from backend_api.sync_jobs import enqueue_sync_job, ensure_sync_worker_started
from backend_api.services.project_settings import is_project_paused
from core.config import get_config
from backend_api.services.history import log_history_event
from backend_api.services.subscription import SubscriptionService
from core.campaign_status import apply_platform_status

cfg = get_config()

# Yandex Direct Credentials
YANDEX_CLIENT_ID = cfg.oauth.yandex_client_id
YANDEX_CLIENT_SECRET = cfg.oauth.yandex_client_secret
YANDEX_AUTH_URL = cfg.oauth.yandex_auth_url
YANDEX_TOKEN_URL = cfg.oauth.yandex_token_url

# VK Ads Credentials (Authorization Code Grant)
# Документация: https://ads.vk.com/doc/api/info/Авторизация%20в%20API#AuthorizationCodeGrant
VK_CLIENT_ID = cfg.oauth.vk_client_id
VK_CLIENT_SECRET = cfg.oauth.vk_client_secret
# Authorization Code Grant для VK Ads API
# Auth URL: https://ads.vk.com/hq/settings/access?action=oauth2
# Token URL: https://ads.vk.com/api/v2/oauth2/token.json
VK_ADS_AUTH_URL = "https://ads.vk.com/hq/settings/access"
VK_ADS_TOKEN_URL = "https://ads.vk.com/api/v2/oauth2/token.json"
# Права OAuth (параметр scope, через запятую) — только из документации VK Ads API, раздел «Scopes — права доступа».
# Рекламодатель: read_ads, read_payments, create_ads.
# Агентство / представительство: create_clients, read_clients, create_agency_payments.
# Менеджер: read_manager_clients, edit_manager_clients, read_payments.
# Поле required_permission в JSON ошибки API (например view_campaigns) — внутренний код метода, не имя в scope.
VK_ADS_OAUTH_SCOPE = cfg.oauth.vk_ads_oauth_scope

# myTarget Credentials (Authorization Code Grant)
# Для песочницы используем target-sandbox.my.com
# Для боевого окружения - target.my.com или target.vk.ru
MYTARGET_CLIENT_ID = cfg.oauth.mytarget_client_id
MYTARGET_CLIENT_SECRET = cfg.oauth.mytarget_client_secret
MYTARGET_AUTH_URL = cfg.oauth.mytarget_auth_url
MYTARGET_TOKEN_URL = cfg.oauth.mytarget_token_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["Integrations"])


def _resolve_avito_credentials(
    *,
    user: Optional[models.User] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
) -> tuple[str, Optional[str], Optional[str]]:
    if (client_id or "").strip() and (client_secret or "").strip():
        return "client_credentials", (client_id or "").strip(), (client_secret or "").strip()

    def _secret(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        try:
            return security.decrypt_token(value)
        except Exception:
            return value

    user_client_id = _secret(getattr(user, "avito_client_id", None)) if user else None
    user_client_secret = _secret(getattr(user, "avito_client_secret", None)) if user else None
    if user_client_id and user_client_secret:
        return "client_credentials", user_client_id.strip(), user_client_secret.strip()

    env_client_id = (os.getenv("AVITO_CLIENT_ID") or "").strip()
    env_client_secret = (os.getenv("AVITO_CLIENT_SECRET") or "").strip()
    if env_client_id and env_client_secret:
        return "client_credentials", env_client_id, env_client_secret

    if not (client_id or "").strip() or not (client_secret or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Avito API credentials не настроены. Добавьте AVITO_CLIENT_ID и AVITO_CLIENT_SECRET на сервере.",
        )
    return "client_credentials", (client_id or "").strip(), (client_secret or "").strip()


@router.post("/remote-log")
async def remote_log(payload: dict):
    """
    Endpoint for frontend to send logs.
    """
    message = payload.get("message", "No message")
    data = payload.get("data")
    log_event("frontend", message, data)
    return {"status": "ok"}

@router.get("/", response_model=List[schemas.IntegrationResponse])
def get_integrations(
    client_id: Optional[str] = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all active integrations (Yandex, VK, etc.) across all clients owned by the user.
    Optional client_id filters to a specific project.
    """
    q = db.query(models.Integration).join(models.Client).filter(
        models.Client.owner_id == current_user.id
    )
    if client_id:
        try:
            from uuid import UUID
            u = UUID(client_id)
            q = q.filter(models.Integration.client_id == u)
        except ValueError:
            pass
    return q.all()

@router.get("/yandex/auth-url")
def get_yandex_auth_url(redirect_uri: str):
    """
    Generate Yandex OAuth authorization URL with dynamic redirect_uri.
    Required scopes for Yandex Direct API:
    - direct:api - access to Yandex Direct API
    - metrika:read - access to Yandex Metrika (for goals)
    """
    # Yandex Direct + Metrika (чтение целей; офлайн-конверсии — отдельный scope, пока убран)
    scope = "direct:api metrika:read"
    return {
        "url": f"{YANDEX_AUTH_URL}?response_type=code&client_id={YANDEX_CLIENT_ID}&redirect_uri={redirect_uri}&scope={scope}"
    }

@router.get("/vk/auth-url")
def get_vk_auth_url(redirect_uri: str):
    """
    Возвращает OAuth URL для авторизации в VK Ads API.
    
    Использует Authorization Code Grant согласно документации VK Ads API:
    https://ads.vk.com/doc/api/info/Авторизация%20в%20API#AuthorizationCodeGrant
    
    Правильный URL: https://ads.vk.com/hq/settings/access?action=oauth2
    
    Параметры:
    - client_id: ID приложения VK Ads
    - redirect_uri: URL для callback после авторизации (должен быть зарегистрирован в настройках приложения)
    - scope: VK_ADS_OAUTH_SCOPE (см. доку: рекламодатель read_ads,read_payments,create_ads; агентство/менеджер — свои наборы)
    - response_type: code
    - state: CSRF защита
    
    Убедитесь, что в настройках приложения VK Ads:
    1. Redirect URL указан точно: {redirect_uri}
    2. Приложение имеет доступ к Authorization Code Grant (предоставляется по запросу)
    3. В кабинете приложения VK включены нужные доступы к API; при 403 на ad_plans — переподключить OAuth и проверить scope в ответе token.json
    """
    import secrets
    import base64
    import hashlib
    
    logger.info(f"🔗 VK Ads OAuth URL requested:")
    logger.info(f"   Client ID: {VK_CLIENT_ID}")
    logger.info(f"   Redirect URI: {redirect_uri}")
    
    # Генерируем state для CSRF защиты
    state = secrets.token_urlsafe(32)
    
    # Scope — официальный список (Authorization Code Grant), строка через запятую.
    # Рекламодатель: read_ads (статистика и РК), read_payments (транзакции и баланс),
    #   create_ads (РК, баннеры, аудитории, ставки, статус, таргетинги и т.п.).
    # Агентство / представительство: create_clients, read_clients, create_agency_payments.
    # Менеджер: read_manager_clients, edit_manager_clients, read_payments.
    scope = VK_ADS_OAUTH_SCOPE
    
    # Формируем OAuth URL для VK Ads API согласно документации
    # Документация: https://ads.vk.com/doc/api/info/Авторизация%20в%20API#AuthorizationCodeGrant
    # Правильный URL: https://ads.vk.com/hq/settings/access?action=oauth2
    # ВАЖНО: redirect_uri должен быть URL-encoded
    from urllib.parse import quote
    
    encoded_redirect_uri = quote(redirect_uri, safe='')
    encoded_scope = quote(scope, safe='')
    
    auth_url = (
        f"https://ads.vk.com/hq/settings/access"
        f"?action=oauth2"
        f"&response_type=code"
        f"&client_id={VK_CLIENT_ID}"
        f"&state={state}"
        f"&scope={encoded_scope}"
        f"&redirect_uri={encoded_redirect_uri}"
    )
    
    logger.info(f"   Generated VK Ads OAuth URL: {auth_url}")
    logger.info(f"   Full OAuth parameters:")
    logger.info(f"     - client_id: {VK_CLIENT_ID}")
    logger.info(f"     - redirect_uri: {redirect_uri}")
    logger.info(f"     - scope: {scope}")
    logger.info(f"     - state: {state}")
    
    return {
        "url": auth_url,
        "client_id": VK_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": scope
    }

@router.get("/mytarget/auth-url")
def get_mytarget_auth_url(redirect_uri: str):
    """
    Возвращает OAuth URL для авторизации в myTarget API.
    
    Использует Authorization Code Grant согласно документации myTarget API.
    Для песочницы: https://target-sandbox.my.com
    Для боевого окружения: https://target.my.com или https://target.vk.ru
    
    Параметры:
    - client_id: ID приложения myTarget
    - redirect_uri: URL для callback после авторизации (должен быть зарегистрирован в настройках приложения)
    - response_type: code
    - state: CSRF защита
    
    Убедитесь, что в настройках приложения myTarget:
    1. Redirect URL указан точно: {redirect_uri}
    2. Приложение имеет доступ к Authorization Code Grant (предоставляется по запросу)
    3. Зарегистрировано в песочнице: https://target-sandbox.my.com
    """
    import secrets
    
    if not MYTARGET_CLIENT_ID:
        raise HTTPException(
            status_code=500, 
            detail="MYTARGET_CLIENT_ID не настроен. Укажите его в переменных окружения."
        )
    
    logger.info(f"🔗 myTarget OAuth URL requested:")
    logger.info(f"   Client ID: {MYTARGET_CLIENT_ID}")
    logger.info(f"   Redirect URI: {redirect_uri}")
    
    # Генерируем state для CSRF защиты
    state = secrets.token_urlsafe(32)
    
    # Формируем OAuth URL для myTarget API
    # Документация: https://target.vk.ru/help/advertisers/api_authorization/ru
    from urllib.parse import quote
    
    encoded_redirect_uri = quote(redirect_uri, safe='')
    
    auth_url = (
        f"{MYTARGET_AUTH_URL}"
        f"?response_type=code"
        f"&client_id={MYTARGET_CLIENT_ID}"
        f"&state={state}"
        f"&redirect_uri={encoded_redirect_uri}"
    )
    
    logger.info(f"   Generated myTarget OAuth URL: {auth_url}")
    logger.info(f"   Full OAuth parameters:")
    logger.info(f"     - client_id: {MYTARGET_CLIENT_ID}")
    logger.info(f"     - redirect_uri: {redirect_uri}")
    logger.info(f"     - state: {state}")
    
    return {
        "url": auth_url,
        "client_id": MYTARGET_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "state": state
    }

from fastapi import BackgroundTasks

async def run_sync_in_background_async(integration_id: uuid.UUID, days: int = 7):
    """
    Асинхронная функция для фоновой синхронизации.
    Создает отдельную сессию БД и выполняет синхронизацию без блокировки основного потока.
    
    CRITICAL: При первой синхронизации (NEVER статус) автоматически использует 90 дней
    для загрузки исторических данных целей Метрики.
    """
    db = SessionLocal()
    try:
        integration = db.query(models.Integration).filter(models.Integration.id == integration_id).first()
        if integration:
            try:
                end_date = datetime.now().date()
                
                # CRITICAL: For first sync (NEVER status) or if no goals data exists, use 90 days
                # This ensures we have historical data for goals in the dashboard
                is_first_sync = integration.sync_status == models.IntegrationSyncStatus.NEVER
                if is_first_sync and integration.platform == models.IntegrationPlatform.YANDEX_METRIKA:
                    # Check if we have any goals data
                    has_goals_data = db.query(models.MetrikaGoals).filter(
                        models.MetrikaGoals.integration_id == integration_id
                    ).first() is not None
                    
                    if not has_goals_data:
                        # First sync: use 90 days for historical data
                        actual_days = 90
                        logger.info(f"🔄 First sync detected for integration {integration_id}: using 90 days for historical goals data")
                    else:
                        actual_days = days
                else:
                    actual_days = days
                
                start_date = end_date - timedelta(days=actual_days - 1)  # -1 because we include today
                date_from = start_date.strftime("%Y-%m-%d")
                date_to = end_date.strftime("%Y-%m-%d")
                
                logger.info(f"🔄 Background sync started for integration {integration_id} ({date_from} to {date_to}, {actual_days} days)")
                await sync_integration(db, integration, date_from, date_to)
                db.commit()
                logger.info(f"✅ Background sync completed for integration {integration_id}")
            except Exception as e:
                logger.error(f"❌ Background sync failed for {integration_id}: {e}")
                db.rollback()
        else:
            logger.warning(f"Integration {integration_id} not found for background sync")
    finally:
        db.close()

def run_sync_in_background(integration_id: uuid.UUID, days: int = 7):
    """
    Синхронная обертка для BackgroundTasks (FastAPI BackgroundTasks требует синхронную функцию).
    Запускает асинхронную синхронизацию в отдельном event loop.
    """
    enqueue_sync_job(integration_id, days)

@router.post("/yandex/exchange")
async def exchange_yandex_token(
    payload: dict, # Expecting {"code": "...", "redirect_uri": "...", "client_name": "..."}
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Exchange authorization code for access token.
    """
    SubscriptionService.require_active_subscription(db, current_user)

    auth_code = payload.get("code")
    redirect_uri = payload.get("redirect_uri") # Must match the one used in auth-url
    client_name_input = payload.get("client_name")
    client_id_input = payload.get("client_id")  # NEW: If provided, link to existing client
    platform_input = (payload.get("platform") or "YANDEX_DIRECT").strip().upper()
    if platform_input not in {"YANDEX_DIRECT", "YANDEX_METRIKA"}:
        raise HTTPException(status_code=400, detail="platform должен быть YANDEX_DIRECT или YANDEX_METRIKA")
    target_platform = (
        models.IntegrationPlatform.YANDEX_METRIKA
        if platform_input == "YANDEX_METRIKA"
        else models.IntegrationPlatform.YANDEX_DIRECT
    )

    if not auth_code or not redirect_uri:
        log_event("backend", "Failed to exchange Yandex token: missing code or redirect_uri")
        raise HTTPException(status_code=400, detail="Missing code or redirect_uri")

    log_event("backend", f"Exchanging Yandex code for client_name: {client_name_input}, client_id: {client_id_input}, platform: {platform_input}")

    # 1. Exchange code for token
    async with httpx.AsyncClient() as client:
        # Yandex requires the same redirect_uri in the token request for strict validation
        response = await client.post(YANDEX_TOKEN_URL, data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": YANDEX_CLIENT_ID,
            "client_secret": YANDEX_CLIENT_SECRET,
            "redirect_uri": redirect_uri  # Required for strict validation - must match exactly
        })
        
        if response.status_code != 200:
            logger.error(f"Yandex Token Exchange Failed: {response.text}")
            raise HTTPException(status_code=400, detail="Failed to exchange token with Yandex")
            
        token_data = response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        
        # 2. Get User Info from Yandex Passport
        yandex_login = None
        yandex_user_id = None
        
        try:
            auth_headers = {"Authorization": f"OAuth {access_token}"}
            user_info_resp = await client.get("https://login.yandex.ru/info?format=json", headers=auth_headers)
            if user_info_resp.status_code == 200:
                user_info = user_info_resp.json()
                yandex_login = user_info.get("login")
                yandex_user_id = user_info.get("id")
        except Exception as e:
            logger.error(f"Failed to fetch Yandex user info: {e}")

        # Determine Client Name
        # If client_name is provided from frontend, use it. Otherwise fallback to login or generic.
        if client_name_input:
             client_name = client_name_input
        elif yandex_login:
             if target_platform == models.IntegrationPlatform.YANDEX_METRIKA:
                 client_name = f"Yandex Metrika ({yandex_login})"
             else:
                 client_name = f"Yandex Direct ({yandex_login})"
        else:
             client_name = "Yandex Metrika Main" if target_platform == models.IntegrationPlatform.YANDEX_METRIKA else "Yandex Direct Main"
        
        # 3. Create/Get Client
        # CRITICAL FIX: If client_id is provided from frontend, use EXISTING client by ID
        # This ensures integration is linked to the correct project, not found by name collision
        if client_id_input:
            try:
                import uuid as uuid_lib
                client_uuid = uuid_lib.UUID(client_id_input)
                client = db.query(models.Client).filter(
                    models.Client.id == client_uuid,
                    models.Client.owner_id == current_user.id
                ).first()
                
                if not client:
                    log_event("backend", f"Client ID {client_id_input} not found or not owned by user", level="error")
                    raise HTTPException(status_code=404, detail=f"Project (Client) not found")
                    
                log_event("backend", f"Using existing client: {client.name} (ID: {client.id})")
            except ValueError:
                log_event("backend", f"Invalid client_id format: {client_id_input}", level="error")
                raise HTTPException(status_code=400, detail="Invalid project ID format")
        else:
            # Legacy flow: search by name (will create duplicates if name matches)
            client = db.query(models.Client).filter(
                models.Client.owner_id == current_user.id,
                models.Client.name == client_name
            ).first()
            
            if not client:
                SubscriptionService.ensure_can_create_project(db, current_user)
                client = models.Client(
                    owner_id=current_user.id,
                    name=client_name
                )
                db.add(client)
                db.flush()
                log_event("backend", f"Created new client: {client.name} (ID: {client.id})")

        # 4. Save Integration
        db_integration = db.query(models.Integration).filter(
            models.Integration.client_id == client.id,
            models.Integration.platform == target_platform
        ).first()

        encrypted_access = security.encrypt_token(access_token)
        encrypted_refresh = security.encrypt_token(refresh_token) if refresh_token else None

        # Store Yandex Login as account_id for display
        final_account_id = yandex_login if yandex_login else "Unknown"
        # Store User ID as platform_client_id (optional, but good for reference)
        encrypted_platform_id = security.encrypt_token(yandex_user_id) if yandex_user_id else None

        if db_integration:
            db_integration.access_token = encrypted_access
            db_integration.refresh_token = encrypted_refresh
            db_integration.account_id = final_account_id
            db_integration.platform_client_id = encrypted_platform_id
            db_integration.sync_status = models.IntegrationSyncStatus.NEVER
        else:
            SubscriptionService.ensure_can_create_cabinet(db, current_user)
            db_integration = models.Integration(
                client_id=client.id,
                platform=target_platform,
                access_token=encrypted_access,
                refresh_token=encrypted_refresh,
                account_id=final_account_id,
                platform_client_id=encrypted_platform_id,
                sync_status=models.IntegrationSyncStatus.NEVER
            )
            db.add(db_integration)
        
        db.commit()
        db.refresh(db_integration)
        
        # SILENT AUTOMATION: Removed auto_discover_agency_bg to allow user selection
        # Instead, we check if it's an agency account and return it
        is_agency = False
        try:
             agency_clients = await get_agency_clients(access_token)
             if agency_clients:
                 is_agency = True
        except:
             pass

        return {
            "status": "success", 
            "integration_id": str(db_integration.id), 
            "access_token": access_token,
            "is_agency": is_agency
        }

@router.post("/vk/exchange")
async def exchange_vk_token_oauth(
    payload: dict, # Expecting {"access_token": "...", "refresh_token": "...", "code": "...", "redirect_uri": "...", "client_name": "..."}
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Обменивает authorization code на токен VK Ads API и сохраняет его.
    
    Использует Authorization Code Grant согласно документации VK Ads API:
    https://ads.vk.com/doc/api/info/Авторизация%20в%20API#AuthorizationCodeGrant
    
    Endpoint: POST https://ads.vk.com/api/v2/oauth2/token.json
    Параметры: grant_type=authorization_code, code={code}, client_id={client_id}
    
    Примечание: client_secret НЕ требуется для Authorization Code Grant в VK Ads API.
    """
    # Проверяем, есть ли уже готовый токен от VKID.Auth.exchangeCode
    SubscriptionService.require_active_subscription(db, current_user)

    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    expires_in = payload.get("expires_in")
    
    redirect_uri = payload.get("redirect_uri")
    client_name_input = payload.get("client_name")
    client_id_input = payload.get("client_id")
    
    # Проверяем, есть ли код авторизации для обмена через VK Ads API
    auth_code = payload.get("code")
    device_id = payload.get("device_id")
    
    # Initialize vk_user_id (will be extracted from token_data if available)
    vk_user_id = None
    
    # Если есть код авторизации, обмениваем его на токен через VK Ads API
    # Документация: https://ads.vk.com/doc/api/info/Авторизация%20в%20API#AuthorizationCodeGrant
    if auth_code:
        logger.info(f"🔄 Exchanging VK Ads authorization code for token...")
        logger.info(f"   Code: {auth_code[:20]}... (truncated)")
        
        async with httpx.AsyncClient() as client:
            try:
                # Согласно документации VK Ads API, для Authorization Code Grant нужны:
                # grant_type, code, client_id (client_secret НЕ требуется для этого flow)
                # redirect_uri рекомендуется передавать для совместимости, если он был указан при запросе авторизации
                token_payload = {
                    "grant_type": "authorization_code",
                    "code": auth_code,
                    "client_id": VK_CLIENT_ID
                }
                # Добавляем redirect_uri, если он был передан (для совместимости)
                if redirect_uri:
                    token_payload["redirect_uri"] = redirect_uri
                
                logger.info(f"   Using VK Ads token endpoint: {VK_ADS_TOKEN_URL}")
                logger.info(f"   Token payload: grant_type=authorization_code, code={auth_code[:20]}..., client_id={VK_CLIENT_ID}")
                response = await client.post(VK_ADS_TOKEN_URL, data=token_payload, timeout=30.0)
                
                logger.info(f"📡 VK Ads Token Exchange Response: {response.status_code}")
                logger.info(f"   Response headers: {dict(response.headers)}")
                
                if response.status_code != 200:
                    logger.error(f"❌ VK Ads Token Exchange Failed: {response.status_code}")
                    logger.error(f"   Response text: {response.text[:500]}")
                    try:
                        error_json = response.json()
                        logger.error(f"   Error JSON: {error_json}")
                        
                        # Специальная обработка ошибки token_limit_exceeded
                        if error_json.get("error") == "token_limit_exceeded":
                            error_description = error_json.get("error_description", "")
                            user_id = error_json.get("user_id", "N/A")
                            logger.error(f"⚠️ VK Ads Token Limit Exceeded for user_id: {user_id}")
                            logger.error(f"   Client ID: {VK_CLIENT_ID}")
                            logger.error(f"   Description: {error_description}")
                            
                            raise HTTPException(
                                status_code=400,
                                detail=(
                                    f"Достигнут лимит активных токенов доступа для вашего приложения VK Ads.\n\n"
                                    f"Решение:\n"
                                    f"1. Напишите в поддержку VK Ads: ads_api@vk.team\n"
                                    f"2. Укажите ваш Client ID: {VK_CLIENT_ID}\n"
                                    f"3. Запросите увеличение лимита или отзыв старых токенов\n\n"
                                    f"Также проверьте настройки приложения VK Ads и отзовите неиспользуемые токены."
                                )
                            )
                    except HTTPException:
                        raise
                    except:
                        pass
                    raise HTTPException(status_code=400, detail=f"Failed to exchange code: {response.text[:200]}")
                
                token_data = response.json()
                access_token = token_data.get("access_token")
                refresh_token = token_data.get("refresh_token")
                expires_in = token_data.get("expires_in")
                vk_user_id = token_data.get("user_id")  # VK Ads user_id for token revocation
                
                if not access_token:
                    raise HTTPException(status_code=500, detail="VK Ads API не вернул access_token")
                
                logger.info(f"✅ VK Ads token received successfully")
                logger.info(f"   Access token received: {bool(access_token)}")
                logger.info(f"   Refresh token received: {bool(refresh_token)}")
                logger.info(f"   Expires in: {expires_in or 'N/A'} seconds")
                logger.info(f"   User ID: {vk_user_id or 'N/A'}")
                # Фактические права токена (если нет read_ads — будет 403 view_campaigns на ad_plans)
                logger.info(f"   Scope в ответе token.json: {token_data.get('scope')!r}")
            except Exception as exchange_err:
                logger.error(f"❌ Failed to exchange code: {exchange_err}")
                raise HTTPException(status_code=400, detail=f"Не удалось обменять код на токен: {str(exchange_err)}")
    elif access_token:
        # Fallback: если токен уже есть (от старого flow), используем его
        logger.info(f"✅ Received token from frontend (legacy flow)")
        logger.info(f"   Access token received: {bool(access_token)}")
        logger.info(f"   Refresh token received: {bool(refresh_token)}")
        logger.info(f"   Expires in: {expires_in or 'N/A'} seconds")
    else:
        # Если нет ни кода, ни токена - ошибка
        raise HTTPException(status_code=400, detail="Either authorization code or access_token is required")
    
    if not access_token:
        raise HTTPException(status_code=400, detail="Access token is required")
    
    # vk_user_id is already initialized above and extracted from token_data if code exchange was used
    # If token comes directly (legacy flow), vk_user_id will remain None
    # Try to auto-detect Account ID (Cabinet) using the token
    vk_account_id = None
    try:
        async with httpx.AsyncClient() as client:
            # Method 1: Try /api/v2/ad_accounts.json (may return 404 for some accounts)
            acc_response = await client.get(
                "https://ads.vk.com/api/v2/ad_accounts.json", 
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0
            )
            if acc_response.status_code == 200:
                acc_data = acc_response.json()
                logger.info(f"📡 VK Ads ad_accounts.json response: {acc_data}")
                items = acc_data.get("items", [])
                logger.info(f"📋 Found {len(items)} account(s) in response")
                if items:
                    # Log all items for debugging
                    for idx, item in enumerate(items):
                        logger.info(f"   Account #{idx}: id={item.get('id')}, name={item.get('name')}, status={item.get('status')}")
                    
                    raw_id = items[0].get("id")
                    raw_id_str = str(raw_id)
                    logger.info(f"🔵 Raw VK Account ID from API: '{raw_id_str}' (type: {type(raw_id)})")
                    
                    # CRITICAL: Normalize account_id format
                    # VK Ads API may return ID in format "vkads_592676405@vk@8493881"
                    # We need to extract the numeric part "592676405"
                    import re
                    if '@vk@' in raw_id_str or raw_id_str.startswith('vkads_'):
                        # Extract numeric ID from format "vkads_592676405@vk@8493881"
                        match = re.search(r'vkads_(\d+)', raw_id_str)
                        if not match:
                            # Fallback: extract first numeric sequence
                            match = re.search(r'(\d+)', raw_id_str)
                        
                        if match:
                            vk_account_id = match.group(1)
                            logger.info(f"✅ Normalized VK Account ID: '{raw_id_str}' -> '{vk_account_id}'")
                        else:
                            logger.error(f"❌ Could not extract numeric ID from: '{raw_id_str}'")
                            vk_account_id = raw_id_str  # Fallback to original
                    elif raw_id_str.isdigit():
                        # Already in correct format
                        vk_account_id = raw_id_str
                        logger.info(f"✅ VK Account ID is already numeric: '{vk_account_id}'")
                    else:
                        # Try to extract any numeric sequence
                        match = re.search(r'(\d+)', raw_id_str)
                        if match:
                            vk_account_id = match.group(1)
                            logger.warning(f"⚠️ Extracted numeric ID from non-standard format: '{raw_id_str}' -> '{vk_account_id}'")
                        else:
                            logger.warning(f"⚠️ VK Account ID '{raw_id_str}' is not numeric, using as-is")
                            vk_account_id = raw_id_str
                    
                    logger.info(f"Final VK Account ID: {vk_account_id}")
            elif acc_response.status_code == 404:
                # Method 2: If ad_accounts.json returns 404, try to get account_id from campaigns
                logger.info(f"⚠️ /api/v2/ad_accounts.json returned 404, trying alternative method...")
                campaigns_response = await client.get(
                    "https://ads.vk.com/api/v2/ad_plans.json",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"limit": 1},  # Get just one campaign to extract account_id
                    timeout=10.0
                )
                if campaigns_response.status_code == 200:
                    campaigns_data = campaigns_response.json()
                    items = campaigns_data.get("items", [])
                    if items:
                        # Try to get account_id from campaign data
                        campaign = items[0]
                        # Some VK Ads API responses include account_id in campaign data
                        if "account_id" in campaign:
                            vk_account_id = str(campaign["account_id"])
                            logger.info(f"✅ Got account_id from campaign data: {vk_account_id}")
                        elif "client_id" in campaign:
                            vk_account_id = str(campaign["client_id"])
                            logger.info(f"✅ Got account_id from campaign client_id: {vk_account_id}")
                        else:
                            logger.warning(f"⚠️ Campaign data doesn't contain account_id or client_id: {campaign.keys()}")
                else:
                    logger.warning(f"⚠️ Failed to fetch campaigns for account_id detection: {campaigns_response.status_code}")
            else:
                logger.warning(f"Failed to auto-detect VK Account ID: {acc_response.status_code} - {acc_response.text[:200]}")
    except Exception as e:
        logger.warning(f"Failed to auto-detect VK Account ID: {e}")
    
    # If still no account_id, we'll proceed without it - VK Ads API can work without explicit account_id
    # The account_id will be determined from the token's scope
    if not vk_account_id:
        logger.info(f"ℹ️ VK Account ID not detected. Integration will work with token's default account.")

    # Determine Client Name
    client_name = client_name_input or "VK Ads Project"
    
    # Create/Get Client
    # CRITICAL FIX: If client_id is provided from frontend, use EXISTING client by ID
    if client_id_input:
        try:
            import uuid as uuid_lib
            client_uuid = uuid_lib.UUID(client_id_input)
            db_client = db.query(models.Client).filter(
                models.Client.id == client_uuid,
                models.Client.owner_id == current_user.id
            ).first()
            
            if not db_client:
                logger.error(f"Client ID {client_id_input} not found or not owned by user")
                raise HTTPException(status_code=404, detail=f"Project (Client) not found")
            
            logger.info(f"Using existing client: {db_client.name} (ID: {db_client.id})")
        except ValueError:
            logger.error(f"Invalid client_id format: {client_id_input}")
            raise HTTPException(status_code=400, detail="Invalid project ID format")
    else:
        # Legacy flow: search by name
        db_client = db.query(models.Client).filter(
            models.Client.owner_id == current_user.id,
            models.Client.name == client_name
        ).first()
        
        if not db_client:
            SubscriptionService.ensure_can_create_project(db, current_user)
            db_client = models.Client(owner_id=current_user.id, name=client_name)
            db.add(db_client)
            db.flush()
            logger.info(f"Created new client: {db_client.name} (ID: {db_client.id})")

    # Save Integration
    # CRITICAL: For VK Ads, check if there's already an integration with the same account_id for this user
    # This prevents creating duplicate integrations for the same VK Ads account, which would consume token slots
    # and lead to token_limit_exceeded errors
    db_integration = None
    
    if vk_account_id:
        # First, try to find existing integration with the same account_id for this user
        # (across all clients owned by this user)
        existing_integration = db.query(models.Integration).join(
            models.Client
        ).filter(
            models.Client.owner_id == current_user.id,
            models.Integration.platform == models.IntegrationPlatform.VK_ADS,
            models.Integration.account_id == vk_account_id
        ).first()
        
        if existing_integration:
            logger.info(f"✅ Found existing VK Ads integration with account_id={vk_account_id} for user {current_user.id}")
            logger.info(f"   Existing integration ID: {existing_integration.id}, Client: {existing_integration.client.name}")
            logger.info(f"   New client: {db_client.name}")
            
            # CRITICAL: If existing integration belongs to a different client, we have two options:
            # 1. Use existing integration and update its token (reuse token)
            # 2. Create new integration for new client (but this wastes token slots)
            # We choose option 1: reuse existing integration and update token
            # This prevents token_limit_exceeded errors
            logger.info(f"🔄 Reusing existing VK Ads integration {existing_integration.id} for account_id={vk_account_id}")
            logger.info(f"   Updating token and linking to new client: {db_client.name}")
            
            db_integration = existing_integration
            # Update token and client_id
            encrypted_access = security.encrypt_token(access_token)
            encrypted_refresh = security.encrypt_token(refresh_token) if refresh_token else None
            db_integration.access_token = encrypted_access
            db_integration.refresh_token = encrypted_refresh
            db_integration.client_id = db_client.id  # Link to new client
            db_integration.account_id = vk_account_id
            if vk_user_id:
                db_integration.vk_user_id = vk_user_id
            db_integration.sync_status = models.IntegrationSyncStatus.NEVER
        else:
            # No existing integration with this account_id, check for integration in this specific client
            db_integration = db.query(models.Integration).filter(
                models.Integration.client_id == db_client.id,
                models.Integration.platform == models.IntegrationPlatform.VK_ADS
            ).first()
            
            if db_integration:
                # Update existing integration for this client
                encrypted_access = security.encrypt_token(access_token)
                encrypted_refresh = security.encrypt_token(refresh_token) if refresh_token else None
                db_integration.access_token = encrypted_access
                db_integration.refresh_token = encrypted_refresh
                db_integration.account_id = vk_account_id
                if vk_user_id:
                    db_integration.vk_user_id = vk_user_id
                db_integration.sync_status = models.IntegrationSyncStatus.NEVER
            else:
                # Create new integration
                SubscriptionService.ensure_can_create_cabinet(db, current_user)
                encrypted_access = security.encrypt_token(access_token)
                encrypted_refresh = security.encrypt_token(refresh_token) if refresh_token else None
                db_integration = models.Integration(
                    client_id=db_client.id,
                    platform=models.IntegrationPlatform.VK_ADS,
                    access_token=encrypted_access,
                    refresh_token=encrypted_refresh,
                    account_id=vk_account_id,
                    vk_user_id=vk_user_id,
                    sync_status=models.IntegrationSyncStatus.NEVER
                )
                db.add(db_integration)
    else:
        # No account_id detected, use client-specific check (legacy behavior)
        db_integration = db.query(models.Integration).filter(
            models.Integration.client_id == db_client.id,
            models.Integration.platform == models.IntegrationPlatform.VK_ADS
        ).first()

        encrypted_access = security.encrypt_token(access_token)
        encrypted_refresh = security.encrypt_token(refresh_token) if refresh_token else None
        
        if db_integration:
            db_integration.access_token = encrypted_access
            db_integration.refresh_token = encrypted_refresh
            db_integration.account_id = vk_account_id
            if vk_user_id:
                db_integration.vk_user_id = vk_user_id
            db_integration.sync_status = models.IntegrationSyncStatus.NEVER
        else:
            SubscriptionService.ensure_can_create_cabinet(db, current_user)
            db_integration = models.Integration(
                client_id=db_client.id,
                platform=models.IntegrationPlatform.VK_ADS,
                access_token=encrypted_access,
                refresh_token=encrypted_refresh,
                account_id=vk_account_id,
                vk_user_id=vk_user_id,
                sync_status=models.IntegrationSyncStatus.NEVER
            )
            db.add(db_integration)
    
    db.commit()
    db.refresh(db_integration)
    
    # Trigger background sync
    background_tasks.add_task(run_sync_in_background, db_integration.id)
    
    return {
        "status": "success", 
        "integration_id": str(db_integration.id),
        "is_agency": False # VK usually doesn't have the same agency structure as Yandex in this flow
    }

@router.post("/mytarget/exchange")
async def exchange_mytarget_token(
    payload: dict, # Expecting {"code": "...", "redirect_uri": "...", "client_name": "...", "client_id": "..."}
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Обменивает authorization code на токен myTarget API и сохраняет его.
    
    Использует Authorization Code Grant согласно документации myTarget API:
    https://target.vk.ru/help/advertisers/api_authorization/ru
    
    Endpoint: POST https://target-sandbox.my.com/api/v2/oauth2/token.json (для песочницы)
    Параметры: grant_type=authorization_code, code={code}, client_id={client_id}, client_secret={client_secret}, redirect_uri={redirect_uri}
    """
    SubscriptionService.require_active_subscription(db, current_user)

    if not MYTARGET_CLIENT_ID or not MYTARGET_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="MYTARGET_CLIENT_ID и MYTARGET_CLIENT_SECRET должны быть настроены в переменных окружения."
        )
    
    auth_code = payload.get("code")
    redirect_uri = payload.get("redirect_uri")
    client_name_input = payload.get("client_name")
    client_id_input = payload.get("client_id")
    
    if not auth_code or not redirect_uri:
        log_event("backend", "Failed to exchange myTarget token: missing code or redirect_uri")
        raise HTTPException(status_code=400, detail="Missing code or redirect_uri")
    
    log_event("backend", f"Exchanging myTarget code for client_name: {client_name_input}, client_id: {client_id_input}")
    
    # 1. Exchange code for token
    async with httpx.AsyncClient() as client:
        # myTarget требует client_secret для Authorization Code Grant
        token_payload = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": MYTARGET_CLIENT_ID,
            "client_secret": MYTARGET_CLIENT_SECRET,
            "redirect_uri": redirect_uri  # Должен совпадать с тем, что использовался в auth-url
        }
        
        logger.info(f"🔄 Exchanging myTarget authorization code for token...")
        logger.info(f"   Using token endpoint: {MYTARGET_TOKEN_URL}")
        logger.info(f"   Code: {auth_code[:20]}... (truncated)")
        
        response = await client.post(MYTARGET_TOKEN_URL, data=token_payload, timeout=30.0)
        
        if response.status_code != 200:
            logger.error(f"❌ myTarget Token Exchange Failed: {response.status_code}")
            logger.error(f"   Response text: {response.text[:500]}")
            try:
                error_json = response.json()
                logger.error(f"   Error JSON: {error_json}")
            except:
                pass
            raise HTTPException(status_code=400, detail=f"Failed to exchange token with myTarget: {response.text[:200]}")
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in")
        
        if not access_token:
            raise HTTPException(status_code=500, detail="myTarget API не вернул access_token")
        
        logger.info(f"✅ myTarget token received successfully")
        logger.info(f"   Access token received: {bool(access_token)}")
        logger.info(f"   Refresh token received: {bool(refresh_token)}")
        logger.info(f"   Expires in: {expires_in or 'N/A'} seconds")
    
    # 2. Try to get user info / account info from myTarget API
    mytarget_account_id = None
    try:
        async with httpx.AsyncClient() as client:
            # Попытка получить информацию об аккаунте
            # Документация myTarget API может отличаться, используем стандартный endpoint
            acc_response = await client.get(
                "https://target-sandbox.my.com/api/v2/user.json",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0
            )
            if acc_response.status_code == 200:
                acc_data = acc_response.json()
                # Структура ответа может отличаться, адаптируем под реальный API
                mytarget_account_id = acc_data.get("id") or acc_data.get("user_id") or acc_data.get("account_id")
                if mytarget_account_id:
                    mytarget_account_id = str(mytarget_account_id)
                    logger.info(f"Auto-detected myTarget Account ID: {mytarget_account_id}")
            else:
                logger.warning(f"Failed to auto-detect myTarget Account ID: {acc_response.status_code} - {acc_response.text[:200]}")
    except Exception as e:
        logger.warning(f"Failed to auto-detect myTarget Account ID: {e}")
    
    # 3. Determine Client Name
    client_name = client_name_input or "myTarget Project"
    
    # 4. Create/Get Client
    if client_id_input:
        try:
            import uuid as uuid_lib
            client_uuid = uuid_lib.UUID(client_id_input)
            db_client = db.query(models.Client).filter(
                models.Client.id == client_uuid,
                models.Client.owner_id == current_user.id
            ).first()
            
            if not db_client:
                logger.error(f"Client ID {client_id_input} not found or not owned by user")
                raise HTTPException(status_code=404, detail=f"Project (Client) not found")
            
            log_event("backend", f"Using existing client: {db_client.name} (ID: {db_client.id})")
        except ValueError:
            log_event("backend", f"Invalid client_id format: {client_id_input}", level="error")
            raise HTTPException(status_code=400, detail="Invalid project ID format")
    else:
        # Legacy flow: search by name
        db_client = db.query(models.Client).filter(
            models.Client.owner_id == current_user.id,
            models.Client.name == client_name
        ).first()
        
        if not db_client:
            SubscriptionService.ensure_can_create_project(db, current_user)
            db_client = models.Client(owner_id=current_user.id, name=client_name)
            db.add(db_client)
            db.flush()
            log_event("backend", f"Created new client: {db_client.name} (ID: {db_client.id})")
    
    # 5. Save Integration
    db_integration = db.query(models.Integration).filter(
        models.Integration.client_id == db_client.id,
        models.Integration.platform == models.IntegrationPlatform.MYTARGET
    ).first()
    
    encrypted_access = security.encrypt_token(access_token)
    encrypted_refresh = security.encrypt_token(refresh_token) if refresh_token else None
    
    if db_integration:
        db_integration.access_token = encrypted_access
        db_integration.refresh_token = encrypted_refresh
        db_integration.account_id = mytarget_account_id
        db_integration.sync_status = models.IntegrationSyncStatus.NEVER
    else:
        SubscriptionService.ensure_can_create_cabinet(db, current_user)
        db_integration = models.Integration(
            client_id=db_client.id,
            platform=models.IntegrationPlatform.MYTARGET,
            access_token=encrypted_access,
            refresh_token=encrypted_refresh,
            account_id=mytarget_account_id,
            sync_status=models.IntegrationSyncStatus.NEVER
        )
        db.add(db_integration)
    
    db.commit()
    db.refresh(db_integration)
    
    # 6. Trigger background sync
    background_tasks.add_task(run_sync_in_background, db_integration.id)
    
    return {
        "status": "success",
        "integration_id": str(db_integration.id),
        "is_agency": False
    }

@router.post("/avito/connect")
async def connect_avito_ads(
    payload: dict,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    SubscriptionService.require_active_subscription(db, current_user)

    client_id_raw = payload.get("client_id")
    client_name_input = (payload.get("client_name") or "").strip()
    db_client = None
    if client_id_raw:
        try:
            client_uuid = uuid.UUID(str(client_id_raw))
        except Exception:
            raise HTTPException(status_code=400, detail="Некорректный client_id")
        db_client = db.query(models.Client).filter(
            models.Client.id == client_uuid,
            models.Client.owner_id == current_user.id,
        ).first()
        if not db_client:
            raise HTTPException(status_code=404, detail="Проект не найден")
    elif client_name_input:
        db_client = models.Client(owner_id=current_user.id, name=client_name_input)
        db.add(db_client)
        db.flush()
    else:
        raise HTTPException(
            status_code=400,
            detail="Укажите проект (client_id) или название нового проекта (client_name)",
        )

    avito_account_id = (
        payload.get("avito_account_id")
        or payload.get("account_id")
    )
    if avito_account_id is not None:
        avito_account_id = str(avito_account_id).strip()
    if not avito_account_id or not str(avito_account_id).isdigit():
        raise HTTPException(
            status_code=400,
            detail="avito_account_id обязателен (числовой ID рекламного аккаунта из кабинета Avito Рекламы)",
        )

    raw_avito_client_id = payload.get("avito_client_id") or payload.get("client_id_value")
    raw_avito_client_secret = payload.get("avito_client_secret") or payload.get("client_secret_value")

    credential_type, avito_client_id, avito_client_secret = _resolve_avito_credentials(
        user=current_user,
        client_id=raw_avito_client_id,
        client_secret=raw_avito_client_secret,
    )

    avito_api = AvitoAdsAPI(
        credential_type=credential_type,
        client_id=avito_client_id,
        client_secret=avito_client_secret,
        account_id=avito_account_id,
    )
    await avito_api.validate_credentials(avito_account_id)
    profiles = await avito_api.get_profiles_or_accounts(avito_account_id)
    profile_match = next(
        (p for p in profiles if str(p.get("id")) == str(avito_account_id)),
        profiles[0] if profiles else None,
    )
    inferred_account_id = str(avito_account_id)
    inferred_account_name = (
        payload.get("account_name")
        or (profile_match.get("name") if profile_match else None)
        or f"Avito {avito_account_id}"
    )

    db_integration = db.query(models.Integration).filter(
        models.Integration.client_id == db_client.id,
        models.Integration.platform == models.IntegrationPlatform.AVITO_ADS,
    ).first()

    encrypted_client_id = security.encrypt_token(avito_client_id) if avito_client_id else None
    encrypted_client_secret = security.encrypt_token(avito_client_secret) if avito_client_secret else None

    if db_integration:
        db_integration.access_token = ""
        db_integration.refresh_token = None
        db_integration.platform_client_id = encrypted_client_id
        db_integration.platform_client_secret = encrypted_client_secret
        db_integration.account_id = str(inferred_account_id) if inferred_account_id else None
        db_integration.account_name = inferred_account_name or credential_type
        db_integration.sync_status = models.IntegrationSyncStatus.NEVER
        db_integration.error_message = None
    else:
        db_integration = models.Integration(
            client_id=db_client.id,
            platform=models.IntegrationPlatform.AVITO_ADS,
            access_token="",
            refresh_token=None,
            platform_client_id=encrypted_client_id,
            platform_client_secret=encrypted_client_secret,
            account_id=str(inferred_account_id) if inferred_account_id else None,
            account_name=inferred_account_name or credential_type,
            sync_status=models.IntegrationSyncStatus.NEVER,
        )
        db.add(db_integration)

    db.commit()
    db.refresh(db_integration)
    return {
        "status": "success",
        "integration_id": str(db_integration.id),
        "client_id": str(db_client.id),
        "account_id": db_integration.account_id,
        "account_name": db_integration.account_name,
    }


from .services import IntegrationService

@router.post("/", response_model=schemas.IntegrationResponse, status_code=status.HTTP_201_CREATED)
async def create_integration(
    integration: schemas.IntegrationCreate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create or update an integration manually. 
    """
    # Проверка активности подписки перед созданием интеграции
    SubscriptionService.require_active_subscription(db, current_user)

    # 1. Automate VK Ads token exchange if credentials provided
    access_token = integration.access_token
    refresh_token = integration.refresh_token

    if integration.platform == models.IntegrationPlatform.VK_ADS and integration.client_id and integration.client_secret:
        vk_data = await IntegrationService.exchange_vk_token(
            integration.client_id, 
            integration.client_secret
        )
        access_token = vk_data["access_token"]
        refresh_token = vk_data["refresh_token"]

    if not access_token:
        raise HTTPException(status_code=400, detail="Access token is required for this platform")

    # 2. Check if client exists or create one
    client = db.query(models.Client).filter(
        models.Client.owner_id == current_user.id,
        models.Client.name == integration.client_name
    ).first()
    
    if not client:
        SubscriptionService.ensure_can_create_project(db, current_user)
        client = models.Client(
            owner_id=current_user.id,
            name=integration.client_name
        )
        db.add(client)
        db.flush() # Get ID

    # 3. Check if integration already exists for this client and platform
    db_integration = db.query(models.Integration).filter(
        models.Integration.client_id == client.id,
        models.Integration.platform == integration.platform
    ).first()

    # Encrypt tokens and credentials before saving
    encrypted_access = security.encrypt_token(access_token)
    encrypted_refresh = security.encrypt_token(refresh_token) if refresh_token else None
    encrypted_platform_client_id = security.encrypt_token(integration.client_id) if integration.client_id else None
    encrypted_platform_client_secret = security.encrypt_token(integration.client_secret) if integration.client_secret else None

    # NEW: Automatically fetch Yandex login if account_id is missing
    final_account_id = integration.account_id
    if integration.platform == models.IntegrationPlatform.YANDEX_DIRECT and (not final_account_id or final_account_id.lower() == "unknown"):
        log_event("backend", "Triggering Yandex auto-detection for account_id")
        try:
            async with httpx.AsyncClient() as client_http:
                auth_headers = {"Authorization": f"OAuth {access_token}"}
                user_info_resp = await client_http.get("https://login.yandex.ru/info?format=json", headers=auth_headers, timeout=10.0)
                if user_info_resp.status_code == 200:
                    user_info = user_info_resp.json()
                    final_account_id = user_info.get("login")
                    log_event("backend", f"Auto-detected Yandex login: {final_account_id}")
                else:
                    log_event("backend", f"Yandex Passport failed: {user_info_resp.status_code} - {user_info_resp.text}")
        except Exception as e:
            logger.error(f"Failed to auto-detect Yandex login: {e}")
            log_event("backend", f"Exception during Yandex auto-detection: {str(e)}")

    if db_integration:
        db_integration.access_token = encrypted_access
        db_integration.refresh_token = encrypted_refresh
        db_integration.platform_client_id = encrypted_platform_client_id
        db_integration.platform_client_secret = encrypted_platform_client_secret
        db_integration.account_id = final_account_id # ENSURE UPDATED
        db_integration.sync_status = models.IntegrationSyncStatus.NEVER
        log_history_event(
            db,
            actor=current_user,
            event_type="integration",
            action="integration_updated",
            description=f"Обновлена интеграция {integration.platform.value}",
            client_id=client.id,
            target_type="integration",
            target_id=str(db_integration.id),
            meta={"platform": integration.platform.value},
        )
        db.commit()
        db.refresh(db_integration)
        return db_integration

    SubscriptionService.ensure_can_create_cabinet(db, current_user)
    new_integration = models.Integration(
        client_id=client.id,
        platform=integration.platform,
        access_token=encrypted_access,
        refresh_token=encrypted_refresh,
        platform_client_id=encrypted_platform_client_id,
        platform_client_secret=encrypted_platform_client_secret,
        account_id=final_account_id,
        sync_status=models.IntegrationSyncStatus.NEVER
    )
    db.add(new_integration)
    log_history_event(
        db,
        actor=current_user,
        event_type="integration",
        action="integration_created",
        description=f"Создана интеграция {integration.platform.value}",
        client_id=client.id,
        target_type="integration",
        meta={"platform": integration.platform.value},
    )
    db.commit()
    db.refresh(new_integration)
    return new_integration

from automation.sync import sync_integration
from datetime import datetime, timedelta

@router.post("/{integration_id}/sync")
async def trigger_sync(
    integration_id: uuid.UUID,
    request_data: schemas.SyncRequest = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger data synchronization for a specific integration.
    Синхронизация выполняется в фоне, чтобы не блокировать запрос.
    
    CRITICAL: Используем run_sync_in_background, которая запускает синхронизацию
    в отдельном потоке с новым event loop, чтобы не блокировать основной event loop FastAPI.
    """
    days = request_data.days if request_data else 7
    force_full = bool(request_data.force_full) if request_data else False
    integration = db.query(models.Integration).join(models.Client).filter(
        models.Integration.id == integration_id,
        models.Client.owner_id == current_user.id
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    if is_project_paused(integration.client):
        raise HTTPException(status_code=409, detail="Проект на паузе. Возобновите проект, чтобы запустить синхронизацию.")
    
    job_id = enqueue_sync_job(integration_id, days, force_full=force_full)
    log_history_event(
        db,
        actor=current_user,
        event_type="integration",
        action="sync_started",
        description=f"Запущена синхронизация интеграции {integration.platform.value}",
        client_id=integration.client_id,
        target_type="integration",
        target_id=str(integration.id),
        meta={"days": days, "force_full": force_full, "job_id": str(job_id)},
    )
    db.commit()
    
    return {
        "status": "queued", 
        "message": f"Sync queued for last {days} days. Processing in background...",
        "job_id": str(job_id),
    }


@router.post("/sync/jobs")
async def create_sync_job(
    payload: dict = Body(...),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    integration_id = payload.get("integration_id")
    days = int(payload.get("days", 7))
    if not integration_id:
        raise HTTPException(status_code=400, detail="integration_id is required")
    try:
        iid = uuid.UUID(integration_id)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid integration_id")

    integration = db.query(models.Integration).join(models.Client).filter(
        models.Integration.id == iid,
        models.Client.owner_id == current_user.id,
    ).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    if is_project_paused(integration.client):
        raise HTTPException(status_code=409, detail="Проект на паузе. Возобновите проект, чтобы запустить синхронизацию.")

    force_full = bool(payload.get("force_full", False))
    job_id = enqueue_sync_job(iid, days, force_full=force_full)
    log_history_event(
        db,
        actor=current_user,
        event_type="integration",
        action="sync_started",
        description=f"Запущена синхронизация интеграции {integration.platform.value}",
        client_id=integration.client_id,
        target_type="integration",
        target_id=str(integration.id),
        meta={"days": days, "force_full": force_full, "job_id": str(job_id)},
    )
    db.commit()
    return {"status": "queued", "job_id": str(job_id)}


@router.get("/sync/jobs/{job_id}")
async def get_sync_job(
    job_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    job = db.query(models.SyncJob).join(models.Integration).join(models.Client).filter(
        models.SyncJob.id == job_id,
        models.Client.owner_id == current_user.id,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Sync job not found")
    return {
        "id": str(job.id),
        "integration_id": str(job.integration_id),
        "status": job.status.value if job.status else None,
        "stage": job.stage,
        "progress": job.progress,
        "attempt": job.attempt,
        "error": job.error,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


@router.get("/{integration_id}/sync-status")
async def get_integration_sync_status(
    integration_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    integration = db.query(models.Integration).join(models.Client).filter(
        models.Integration.id == integration_id,
        models.Client.owner_id == current_user.id,
    ).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    job = db.query(models.SyncJob).filter(
        models.SyncJob.integration_id == integration_id
    ).order_by(models.SyncJob.created_at.desc()).first()
    if not job:
        return {"integration_id": str(integration_id), "job": None}
    return {
        "integration_id": str(integration_id),
        "job": {
            "id": str(job.id),
            "status": job.status.value if job.status else None,
            "stage": job.stage,
            "progress": job.progress,
            "error": job.error,
            "updated_at": job.updated_at,
        },
    }

@router.get("/{integration_id}", response_model=schemas.IntegrationResponse)
def get_integration(
    integration_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific integration by ID.
    """
    from sqlalchemy.orm import joinedload
    
    integration = db.query(models.Integration).options(
        joinedload(models.Integration.client)
    ).join(models.Client).filter(
        models.Integration.id == integration_id,
        models.Client.owner_id == current_user.id
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
        
    return integration

@router.get("/{integration_id}/profiles")
async def get_integration_profiles(
    integration_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetch available profiles/accounts for this integration.
    For Yandex Agency, returns list of sub-clients.
    """
    integration = db.query(models.Integration).join(models.Client).filter(
        models.Integration.id == integration_id,
        models.Client.owner_id == current_user.id
    ).first()
    
    if not integration:
        log_event("get_integration_profiles", f"Integration {integration_id} not found for user {current_user.id}", level="warning")
        raise HTTPException(status_code=404, detail="Integration not found")

    log_event("get_integration_profiles", f"User {current_user.id} requesting profiles for integration {integration_id}")

    access_token = security.decrypt_token(integration.access_token)
    
    if integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
        log_event("yandex", f"fetching profiles for integration {integration_id}")
        try:
            profiles = []
            seen_logins = set()

            # ARCHITECTURE: One Yandex account (email) can have access to multiple advertising profiles
            # 1. Personal advertising account
            # 2. Agency clients (if this is an agency account)
            # 3. Managed accounts (accounts where user has Editor/Manager role)

            # 1. Always include the personal account itself
            # Get personal advertising account login via Clients.get API
            # CRITICAL: Clients.get returns the Login field which is the advertising account login (username)
            # This is the format needed for Client-Login header
            personal_login = None
            clients_info = []
            try:
                direct_api = YandexDirectAPI(access_token)
                clients_info = await direct_api.get_clients() or []
                logger.info(f"🔵 Clients.get returned {len(clients_info) if clients_info else 0} client(s)")
                if clients_info:
                    # Clients.get returns the account's own login in the Login field
                    # This is the advertising account username, not email
                    personal_login = clients_info[0].get("Login")
                    logger.info(f"🔵 Clients.get Login field: '{personal_login}'")
                    logger.info(f"🔵 Clients.get full response: {json.dumps(clients_info[0], indent=2, ensure_ascii=False)}")
            except Exception as clients_err:
                logger.warning(f"Could not get personal account login via Clients.get: {clients_err}")
            
            # Fallback to account_id if Clients.get fails or returns nothing
            # NOTE: account_id is usually the Yandex email/login, which may not be the advertising account login
            if not personal_login:
                personal_login = integration.account_id
                logger.warning(f"⚠️ Using account_id as fallback for personal login: {personal_login} (this may not be the correct advertising account login)")
            
            if personal_login and personal_login.lower() != "unknown":
                personal_info = clients_info[0].get("ClientInfo", "") if clients_info else ""
                personal_name = personal_info if personal_info else f"Личный аккаунт ({personal_login})"
                profiles.append({"login": personal_login, "name": personal_name, "type": "personal"})
                seen_logins.add(personal_login.lower())
                logger.info(f"✅ Added personal profile: {personal_login} ({personal_name})")

            # 2. Try to get agency clients (if this account is an agency)
            try:
                agency_clients = await get_agency_clients(access_token)
                logger.info(f"🔵 AgencyClients.get returned {len(agency_clients)} clients")
                for ac in agency_clients:
                    login = ac.get("login")
                    logger.info(f"🔵 Agency client: login='{login}', name='{ac.get('name', 'N/A')}'")
                    if login and login.lower() not in seen_logins:
                        profiles.append(ac)
                        seen_logins.add(login.lower())
                        logger.info(f"✅ Added agency client: {login}")
                    else:
                        logger.warning(f"⚠️ Skipped agency client (duplicate or empty login): {login}")
            except Exception as agency_err:
                logger.warning(f"No agency clients found or error: {agency_err}")

            # 3. Try to get managed logins (accounts with shared access)
            # For each managed login, fetch ClientInfo (human-readable cabinet name) via Clients.get
            try:
                direct_api = YandexDirectAPI(access_token)
                clients_info_managed = await direct_api.get_clients() or []
                managed_logins_to_fetch = []
                for c_info in clients_info_managed:
                    managed = c_info.get("ManagedLogins", [])
                    for m_login in managed:
                        if m_login and m_login.lower() not in seen_logins:
                            managed_logins_to_fetch.append(m_login)
                            seen_logins.add(m_login.lower())

                # Fetch ClientInfo for each managed login (human-readable cabinet name)
                for m_login in managed_logins_to_fetch:
                    info = await direct_api.get_client_info_for_login(m_login)
                    cabinet_name = info.get("ClientInfo", "").strip() if info else ""
                    display_name = cabinet_name if cabinet_name else f"Доступный аккаунт ({m_login})"
                    profiles.append({
                        "login": m_login,
                        "name": display_name,
                        "type": "managed"
                    })
                    logger.info(f"Added managed login: {m_login} ({display_name})")
            except Exception as managed_err:
                logger.warning(f"Error fetching managed logins: {managed_err}")

            # Fallback if nothing found
            if not profiles:
                display_id = integration.account_id or "Unknown"
                profiles = [{"login": display_id, "name": f"Личный аккаунт ({display_id})"}]
            
            logger.info(f"TOTAL profiles found for integration {integration_id}: {len(profiles)} - {[p['login'] for p in profiles]}")
            log_event("yandex", f"received {len(profiles)} profiles from yandex")
            return profiles
        except Exception as e:
            log_event("yandex", f"error fetching profiles: {str(e)}", level="error")
            return [{"login": integration.account_id, "name": f"Аккаунт ({integration.account_id})"}]
    
    elif integration.platform == models.IntegrationPlatform.VK_ADS:
        log_event("vk", f"fetching profiles for integration {integration_id}")
        try:
            from automation.vk_ads import VKAdsAPI
            vk_api = VKAdsAPI(access_token, integration.account_id)
            
            # Получаем все доступные профили (личные аккаунты + agency клиенты)
            vk_profiles = await vk_api.get_profiles()
            
            # Преобразуем в формат, совместимый с Yandex (используем id как login)
            profiles = []
            for vk_profile in vk_profiles:
                profile_id = vk_profile.get("id")
                profile_name = vk_profile.get("name", f"Аккаунт {profile_id}")
                profile_type = vk_profile.get("type", "personal")
                
                # Используем id как login для совместимости с существующей логикой
                profiles.append({
                    "id": profile_id,  # VK использует ID, а не login
                    "login": profile_id,  # Для совместимости с Yandex форматом
                    "name": profile_name,
                    "type": profile_type
                })
                logger.info(f"✅ Added VK profile: {profile_id} ({profile_name})")
            
            # Fallback если ничего не найдено
            if not profiles and integration.account_id:
                profiles.append({
                    "id": str(integration.account_id),
                    "login": str(integration.account_id),
                    "name": f"Аккаунт ({integration.account_id})",
                    "type": "personal"
                })
                logger.info(f"✅ Added fallback VK profile: {integration.account_id}")
            
            logger.info(f"TOTAL VK profiles found for integration {integration_id}: {len(profiles)} - {[p['id'] for p in profiles]}")
            log_event("vk", f"received {len(profiles)} profiles from vk")
            return profiles
        except Exception as e:
            log_event("vk", f"error fetching VK profiles: {str(e)}", level="error")
            # Fallback на account_id если есть
            if integration.account_id:
                return [{
                    "id": str(integration.account_id),
                    "login": str(integration.account_id),
                    "name": f"Аккаунт ({integration.account_id})"
                }]
            return []
    
    elif integration.platform == models.IntegrationPlatform.AVITO_ADS:
        if not integration.account_id:
            return []
        try:
            avito_api = _build_avito_api_from_integration(integration)
            profiles = await avito_api.get_profiles_or_accounts(integration.account_id)
            if profiles:
                return [
                    {
                        "id": str(p.get("id") or ""),
                        "login": str(p.get("id") or ""),
                        "name": p.get("name") or p.get("title") or f"Аккаунт {p.get('id')}",
                        "type": p.get("type") or "avito_account",
                    }
                    for p in profiles
                    if p.get("id") is not None
                ]
        except Exception as e:
            logger.warning(f"Avito profiles fetch failed: {e}")
        return [{
            "id": str(integration.account_id),
            "login": str(integration.account_id),
            "name": integration.account_name or f"Аккаунт ({integration.account_id})",
            "type": "avito_account",
        }]

    log_event("get_integration_profiles", f"No specific profile fetching logic for platform {integration.platform}", level="info")
    return []

@router.get("/{integration_id}/counters")
async def get_integration_counters(
    integration_id: uuid.UUID,
    account_id: Optional[str] = None,
    campaign_ids: Optional[str] = None,  # Comma-separated list of campaign IDs
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get Metrika counters for selected campaigns or profile.
    Priority: Campaign CounterIds -> Profile counters from Metrika API.
    """
    integration = db.query(models.Integration).join(models.Client).filter(
        models.Integration.id == integration_id,
        models.Client.owner_id == current_user.id
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    access_token = security.decrypt_token(integration.access_token)
    
    # Determine target_account for profile filtering
    if account_id:
        target_account = account_id
    elif integration.agency_client_login and integration.agency_client_login.lower() != "unknown":
        target_account = integration.agency_client_login
    else:
        target_account = integration.account_id
    
    counters_list = []
    
    # VK Ads doesn't use Yandex Metrika counters
    if integration.platform == models.IntegrationPlatform.VK_ADS:
        logger.info(f"ℹ️ VK Ads integration - Metrika counters are not applicable. Returning empty list.")
        return {"counters": []}

    # Avito Ads: counters come from a linked YANDEX_METRIKA integration
    if integration.platform == models.IntegrationPlatform.AVITO_ADS:
        metrika_src = _get_metrika_integration_for_client(db, integration.client_id)
        if not metrika_src:
            return {"counters": [], "warning": "Подключите Яндекс Метрику (OAuth) для выбора счётчиков лидов"}
        access_token = security.decrypt_token(metrika_src.access_token)
        target_account = _metrika_profile_login(metrika_src)

    if integration.platform in (
        models.IntegrationPlatform.YANDEX_DIRECT,
        models.IntegrationPlatform.AVITO_ADS,
    ):
        # Priority 1: Get counters from selected campaigns via CounterIds
        logger.info(f"🔵 Priority 1: Attempting to get counters from campaigns. campaign_ids={campaign_ids}")
        if campaign_ids and integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
            campaign_ids_list = [cid.strip() for cid in campaign_ids.split(',') if cid.strip()]
            logger.info(f"🔵 Parsed {len(campaign_ids_list)} campaign IDs: {campaign_ids_list}")
            
            campaigns_from_db = db.query(models.Campaign).filter(
                models.Campaign.integration_id == integration_id,
                models.Campaign.id.in_([uuid.UUID(cid) for cid in campaign_ids_list if len(cid) == 36])
            ).all()
            
            logger.info(f"🔵 Found {len(campaigns_from_db)} campaigns in DB")
            
            external_ids = [str(c.external_id) for c in campaigns_from_db if c.external_id and str(c.external_id).isdigit()]
            logger.info(f"🔵 Extracted {len(external_ids)} external IDs: {external_ids}")
            
            if external_ids:
                from automation.yandex_direct import YandexDirectAPI
                direct_api = YandexDirectAPI(access_token, client_login=target_account)
                
                logger.info(f"🔵 Calling get_campaign_counters for {len(external_ids)} campaigns...")
                campaign_counters_map = await direct_api.get_campaign_counters(external_ids)
                logger.info(f"🔵 get_campaign_counters returned: {campaign_counters_map}")
                
                # Collect all unique counter IDs
                # CRITICAL: Use different variable name to avoid overwriting counters_list
                all_counter_ids = set()
                for counter_ids_from_campaign in campaign_counters_map.values():
                    for cid in counter_ids_from_campaign:
                        all_counter_ids.add(str(cid))
                
                logger.info(f"🔵 Collected {len(all_counter_ids)} unique counter IDs: {all_counter_ids}")
                
                if all_counter_ids:
                    # Fetch counter details from Metrika API
                    from automation.yandex_metrica import YandexMetricaAPI
                    metrica_api = YandexMetricaAPI(access_token)
                    
                    # Get all accessible counters to match with IDs
                    try:
                        all_counters = await metrica_api.get_counters()
                        logger.info(f"🔵 Metrika API returned {len(all_counters)} total counters")
                        
                        # Filter to only counters that match our CounterIds
                        for counter in all_counters:
                            counter_id_str = str(counter.get('id', ''))
                            if counter_id_str in all_counter_ids:
                                counter_name = counter.get('name', '')
                                if not counter_name:
                                    logger.warning(f"⚠️ Counter {counter_id_str} has no name in Metrika API response")
                                counters_list.append({
                                    "id": counter_id_str,
                                    "name": counter_name or f"Счетчик {counter_id_str}",
                                    "site": counter.get('site', ''),
                                    "owner_login": counter.get('owner_login', ''),
                                    "source": "campaign"  # Indicates this counter came from campaign CounterIds
                                })
                        
                        logger.info(f"✅ Priority 1 SUCCESS: Found {len(counters_list)} counters from {len(all_counter_ids)} CounterIds for campaigns")
                    except Exception as e:
                        logger.error(f"❌ Priority 1 FAILED: Failed to fetch counter details from Metrika: {e}")
                else:
                    logger.warning(f"⚠️ Priority 1: No CounterIds found in campaigns. campaign_counters_map={campaign_counters_map}")
            else:
                logger.warning(f"⚠️ Priority 1: No valid external_ids extracted from campaigns")
        else:
            logger.warning(f"⚠️ Priority 1: No campaign_ids provided in request")
        
        # Priority 2: Fallback to profile-based counters
        # Use fallback if no counters found from campaigns (either no campaign_ids or no CounterIds in campaigns)
        if not counters_list and target_account:
            logger.info(f"🔵 Priority 2: No counters from campaigns, falling back to profile-based counters")
            from automation.yandex_metrica import YandexMetricaAPI
            metrica_api = YandexMetricaAPI(access_token, client_login=target_account)
            
            try:
                counters = await metrica_api.get_counters()
                logger.info(f"📊 Metrika API returned {len(counters)} counters for profile '{target_account}'")
                
                # CRITICAL: If campaign_ids were provided but no CounterIds found,
                # return ALL counters without filtering by owner_login
                # This is because campaigns might not have CounterIds configured, but user still needs to select counters
                if campaign_ids:
                    logger.warning(f"⚠️ Campaigns don't have CounterIds, returning ALL {len(counters)} accessible counters")
                    for counter in counters:
                        counters_list.append({
                            "id": str(counter.get('id')),
                            "name": counter.get('name', 'Unknown'),
                            "site": counter.get('site', ''),
                            "owner_login": counter.get('owner_login', ''),
                            "source": "profile_fallback_all"  # Indicates all counters returned because campaigns have no CounterIds
                        })
                else:
                    # Normalize for comparison
                    def normalize_login(login):
                        return login.lower().replace('.', '').replace('-', '') if login else ''
                    
                    target_normalized = normalize_login(target_account)
                    matched_counters = []
                    unmatched_counters = []
                    
                    # Filter by owner_login if possible
                    for counter in counters:
                        owner_login = counter.get('owner_login', '')
                        owner_normalized = normalize_login(owner_login)
                        
                        # Match if owner matches target OR if no owner_login (trusted counter)
                        matches = normalize_login(owner_login) == target_normalized or not owner_login
                        
                        counter_data = {
                            "id": str(counter.get('id')),
                            "name": counter.get('name', 'Unknown'),
                            "site": counter.get('site', ''),
                            "owner_login": owner_login,
                            "source": "profile"  # Indicates this counter came from profile
                        }
                        
                        if matches:
                            matched_counters.append(counter_data)
                            logger.info(f"✅ Included counter '{counter.get('name', 'Unknown')}' (ID: {counter.get('id')}, owner: {owner_login}, normalized: {owner_normalized}, expected: {target_account}, normalized: {target_normalized})")
                        else:
                            unmatched_counters.append(counter_data)
                            logger.info(f"❌ Excluded counter '{counter.get('name', 'Unknown')}' (ID: {counter.get('id')}, owner: {owner_login}, normalized: {owner_normalized}, expected: {target_account}, normalized: {target_normalized})")
                    
                    # If no matched counters but we have unmatched ones, return all with a warning
                    if not matched_counters and unmatched_counters:
                        logger.warning(f"⚠️ No counters matched profile '{target_account}' after filtering")
                        logger.warning(f"⚠️ Returning all {len(unmatched_counters)} accessible counters (user can manually select)")
                        counters_list = unmatched_counters
                    else:
                        counters_list = matched_counters
                        if unmatched_counters:
                            logger.info(f"📊 Filtered to {len(matched_counters)} counters for profile '{target_account}' (excluded {len(unmatched_counters)} counters from other profiles)")
            except Exception as e:
                logger.error(f"Failed to fetch profile counters: {e}")
                # If 403, try without profile filter
                if "403" in str(e) or "access_denied" in str(e).lower():
                    logger.warning(f"⚠️ Metrika API returned 403 for profile '{target_account}'. Trying fallback without profile filter...")
                    try:
                        fallback_api = YandexMetricaAPI(access_token)
                        counters = await fallback_api.get_counters()
                        logger.info(f"📊 Fallback API returned {len(counters)} counters (no profile filter)")
                        for counter in counters:
                            counters_list.append({
                                "id": str(counter.get('id')),
                                "name": counter.get('name', 'Unknown'),
                                "site": counter.get('site', ''),
                                "owner_login": counter.get('owner_login', ''),
                                "source": "profile_fallback"
                            })
                    except Exception as fallback_err:
                        logger.error(f"Fallback counter fetch also failed: {fallback_err}")
    
    logger.info(f"✅ Returning {len(counters_list)} counters for integration {integration_id}")
    return {"counters": counters_list}

@router.get("/{integration_id}/goal-names")
def get_goal_names(
    integration_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    integration = db.query(models.Integration).join(models.Client).filter(
        models.Integration.id == integration_id,
        models.Client.owner_id == current_user.id,
    ).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    from sqlalchemy import func as sa_func
    rows = (
        db.query(
            models.MetrikaGoals.goal_id,
            sa_func.max(models.MetrikaGoals.goal_name).label("goal_name"),
        )
        .filter(
            models.MetrikaGoals.integration_id == integration_id,
            models.MetrikaGoals.goal_id != "all",
            models.MetrikaGoals.goal_name.isnot(None),
        )
        .group_by(models.MetrikaGoals.goal_id)
        .all()
    )
    return {str(r.goal_id): r.goal_name for r in rows if r.goal_name}


@router.get("/{integration_id}/goals")
async def get_integration_goals(
    integration_id: uuid.UUID,
    account_id: Optional[str] = None,
    campaign_ids: Optional[str] = None,  # Comma-separated list of campaign IDs
    counter_ids: Optional[str] = None,  # NEW: Comma-separated list of counter IDs
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    with_stats: bool = True,  # NEW: позволяем отключать тяжёлый расчёт конверсий
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetch available goals (Metrica) for selected campaigns.
    CRITICAL: If campaign_ids is provided, returns goals only for those campaigns.
    Otherwise falls back to profile-based goal fetching (legacy behavior).
    """
    integration = db.query(models.Integration).join(models.Client).filter(
        models.Integration.id == integration_id,
        models.Client.owner_id == current_user.id
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    # CRITICAL: Refresh integration from DB to ensure we have the latest agency_client_login
    # This is important because the profile might have been updated just before this call
    db.refresh(integration)

    # Use the token from integration
    access_token = security.decrypt_token(integration.access_token)
    # Флаг, надо ли вообще считать конверсии (DB + Metrika API).
    include_stats = bool(date_from and date_to and with_stats)
    
    # VK Ads doesn't use Yandex Metrika goals
    if integration.platform == models.IntegrationPlatform.VK_ADS:
        logger.info(f"ℹ️ VK Ads integration - Yandex Metrika goals are not applicable. Returning empty list.")
        return []

    # Avito Ads: goals come from a linked YANDEX_METRIKA integration
    if integration.platform == models.IntegrationPlatform.AVITO_ADS:
        metrika_src = _get_metrika_integration_for_client(db, integration.client_id)
        if not metrika_src:
            return []
        access_token = security.decrypt_token(metrika_src.access_token)
        target_account = _metrika_profile_login(metrika_src)
    else:
        # Determine target_account for profile filtering (used in both paths)
        if account_id:
            target_account = account_id
            logger.info(f"Using account_id from query param: {target_account}")
        elif integration.agency_client_login and integration.agency_client_login.lower() != "unknown":
            target_account = integration.agency_client_login
            logger.info(f"Using agency_client_login (selected profile): {target_account}")
        else:
            target_account = None
            logger.info(f"No profile selected, not filtering Metrika counters (will show all accessible)")
    
    # CRITICAL: Priority order for goal fetching:
    # 1. If counter_ids provided, fetch goals ONLY from those counters (highest priority)
    # 2. If campaign_ids provided, get CounterIds from campaigns, then fetch goals
    # 3. Fallback to profile-based goal fetching
    
    # Priority 1: Fetch goals from selected counters
    if counter_ids:
        counter_ids_list = [cid.strip() for cid in counter_ids.split(',') if cid.strip()]
        
        if integration.platform in (
            models.IntegrationPlatform.YANDEX_DIRECT,
            models.IntegrationPlatform.AVITO_ADS,
        ):
            from automation.yandex_metrica import YandexMetricaAPI
            metrica_api = YandexMetricaAPI(access_token)
            
            all_goals = []
            from sqlalchemy import func
            
            # Получаем цели для всех счетчиков параллельно
            goals_tasks = [metrica_api.get_counter_goals(counter_id) for counter_id in counter_ids_list]
            goals_results = await asyncio.gather(*goals_tasks, return_exceptions=True)
            
            # Обрабатываем результаты
            for counter_id, goals_result in zip(counter_ids_list, goals_results):
                if isinstance(goals_result, Exception):
                    logger.error(f"Failed to fetch goals for counter {counter_id}: {goals_result}")
                    continue
                
                goals = goals_result
                for goal in goals:
                    goal_id = str(goal["id"])
                    goal_name = goal.get("name", f"Goal {goal_id}")
                    goal_data = {
                        "id": goal_id,
                        "name": f"{goal_name}",
                        "type": goal.get("type", "Unknown"),
                        "counter_id": counter_id,
                        "conversions": 0,
                        "conversion_rate": 0.0
                    }
                    
                    if include_stats:
                        # CRITICAL: Always try DB first - no API calls unless data is missing
                        from sqlalchemy import func
                        db_stats = db.query(
                            func.sum(models.MetrikaGoals.conversion_count).label("total_conversions")
                        ).filter(
                            models.MetrikaGoals.integration_id == integration_id,
                            models.MetrikaGoals.goal_id == goal_id,
                            models.MetrikaGoals.date >= datetime.strptime(date_from, "%Y-%m-%d").date(),
                            models.MetrikaGoals.date <= datetime.strptime(date_to, "%Y-%m-%d").date()
                        ).first()
                        
                        if db_stats and db_stats.total_conversions is not None:
                            goal_data["conversions"] = int(db_stats.total_conversions or 0)
                            # Calculate conversion rate from DB if we have clicks data
                            # For now, set to 0 if not available - we can calculate from YandexStats later
                            goal_data["conversion_rate"] = 0.0
                        else:
                            # No data in DB - only then fetch from API (should be rare after initial sync)
                            logger.info(f"No DB data for goal {goal_id}, fetching from API (should only happen on first load)")
                            try:
                                from automation.request_queue import get_request_queue
                                queue = await get_request_queue()
                                # CRITICAL: Use visits (целевые визиты) instead of reaches
                                stats = await queue.enqueue('metrica', metrica_api.get_goals_stats,
                                    counter_id, date_from, date_to,
                                    metrics=f"ym:s:goal{goal_id}visits"
                                )
                                if stats and len(stats) > 0:
                                    total_visits = sum(int(row.get('metrics', [0])[0]) for row in stats if row.get('metrics'))
                                    goal_data["conversions"] = int(total_visits)
                                    goal_data["conversion_rate"] = 0.0
                            except Exception as stats_err:
                                logger.debug(f"Could not fetch stats for goal {goal_id} from counter {counter_id}: {stats_err}")
                    
                    all_goals.append(goal_data)
            
            logger.info(f"✅ Returning {len(all_goals)} goals from {len(counter_ids_list)} selected counters")
            return all_goals
    
    # Priority 2: If campaign_ids provided, get goals по выбранным кампаниям, а не по всему профилю
    if campaign_ids:
        campaign_ids_list = [cid.strip() for cid in campaign_ids.split(',') if cid.strip()]
        
        if integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
            campaigns_from_db = db.query(models.Campaign).filter(
                models.Campaign.integration_id == integration_id,
                models.Campaign.id.in_([uuid.UUID(cid) for cid in campaign_ids_list if len(cid) == 36])
            ).all()
            
            external_ids = [str(c.external_id) for c in campaigns_from_db if c.external_id and str(c.external_id).isdigit()]
            
            # 1) Новый основной путь: Кампания → CounterIds → цели Метрики
            if external_ids:
                from automation.yandex_direct import YandexDirectAPI
                direct_api = YandexDirectAPI(access_token, client_login=target_account)
                
                campaign_counters_map = await direct_api.get_campaign_counters(external_ids)
                logger.info(f"get_campaign_counters returned: {campaign_counters_map}")
                
                all_counter_ids = set()
                for counters_list in campaign_counters_map.values():
                    for cid in counters_list:
                        all_counter_ids.add(str(cid))
                
                logger.info(f"Extracted {len(all_counter_ids)} unique counter IDs: {list(all_counter_ids)}")
                
                if all_counter_ids:
                    from automation.yandex_metrica import YandexMetricaAPI
                    # Важно: здесь НЕ фильтруем по owner_login, работаем ровно с теми счётчиками,
                    # которые вернул Direct для выбранных кампаний.
                    metrica_api = YandexMetricaAPI(access_token)
                    
                    all_goals = []
                    from sqlalchemy import func
                    
                    for counter_id in all_counter_ids:
                        try:
                            goals = await metrica_api.get_counter_goals(counter_id)
                        except Exception as goals_err:
                            logger.error(f"Failed to fetch goals for counter {counter_id}: {goals_err}")
                            continue
                        
                        for goal in goals:
                            goal_id = str(goal["id"])
                            goal_name = goal.get("name", f"Goal {goal_id}")
                            goal_data = {
                                "id": goal_id,
                                "name": f"{goal_name}",
                                "type": goal.get("type", "Unknown"),
                                "counter_id": counter_id,
                                "conversions": 0,
                                "conversion_rate": 0.0
                            }
                            
                            # Если включён расчёт статистики — подтягиваем конверсии (DB + fallback в API)
                            if include_stats:
                                stats = db.query(
                                    func.sum(models.MetrikaGoals.conversion_count).label("total_conversions")
                                ).filter(
                                    models.MetrikaGoals.goal_id == goal_id,
                                    models.MetrikaGoals.integration_id == integration_id,
                                    models.MetrikaGoals.date >= date_from,
                                    models.MetrikaGoals.date <= date_to
                                ).first()
                                
                                if not stats or not stats.total_conversions:
                                    try:
                                        # CRITICAL: Use visits (целевые визиты) instead of reaches
                                        goal_metric = f"ym:s:goal{goal_id}visits"
                                        goals_stats = await metrica_api.get_goals_stats(
                                            counter_id,
                                            date_from,
                                            date_to,
                                            metrics=goal_metric
                                        )
                                        
                                        total_conversions_from_api = 0
                                        for day_data in goals_stats:
                                            if len(day_data.get("metrics", [])) > 0:
                                                total_conversions_from_api += int(day_data["metrics"][0] or 0)
                                        
                                        if total_conversions_from_api > 0:
                                            goal_data["conversions"] = total_conversions_from_api
                                            
                                            total_clicks = db.query(
                                                func.sum(models.YandexStats.clicks)
                                            ).join(
                                                models.Campaign
                                            ).filter(
                                                models.Campaign.integration_id == integration_id,
                                                models.Campaign.external_id.in_(external_ids),
                                                models.YandexStats.date >= date_from,
                                                models.YandexStats.date <= date_to
                                            ).scalar() or 0
                                            
                                            if total_clicks > 0:
                                                goal_data["conversion_rate"] = round(
                                                    (goal_data["conversions"] / total_clicks) * 100, 2
                                                )
                                    except Exception as api_err:
                                        logger.warning(f"⚠️ Failed to fetch goal stats from Metrika API for goal_id={goal_id}: {api_err}")
                                elif stats and stats.total_conversions:
                                    goal_data["conversions"] = int(stats.total_conversions)
                                    
                                    total_clicks = db.query(
                                        func.sum(models.YandexStats.clicks)
                                    ).join(
                                        models.Campaign
                                    ).filter(
                                        models.Campaign.integration_id == integration_id,
                                        models.Campaign.external_id.in_(external_ids),
                                        models.YandexStats.date >= date_from,
                                        models.YandexStats.date <= date_to
                                    ).scalar() or 0
                                    
                                    if total_clicks > 0:
                                        goal_data["conversion_rate"] = round(
                                            (goal_data["conversions"] / total_clicks) * 100, 2
                                        )
                            
                            all_goals.append(goal_data)
                    
                    return all_goals
            
            # 2) Fallback: если не удалось получить CounterIds, пробуем старую логику PriorityGoals
            campaign_goals_map = {}
            if external_ids:
                from automation.yandex_direct import YandexDirectAPI
                direct_api = YandexDirectAPI(access_token, client_login=target_account)
                campaign_goals_map = await direct_api.get_campaign_goals(external_ids)
            
            if campaign_goals_map:
                all_goal_ids = set()
                goal_id_to_name = {}
                for campaign_id, goals in campaign_goals_map.items():
                    for goal in goals:
                        goal_id = goal["goal_id"]
                        all_goal_ids.add(goal_id)
                        if "goal_name" in goal:
                            goal_id_to_name[goal_id] = goal["goal_name"]
                
                from automation.yandex_metrica import YandexMetricaAPI
                metrica_api = YandexMetricaAPI(access_token, client_login=target_account)
                
                try:
                    counters = await metrica_api.get_counters()
                    
                    all_goals = []
                    from sqlalchemy import func
                    
                    for counter in counters:
                        counter_id = str(counter["id"])
                        counter_name = counter.get("name", "Unknown")
                        try:
                            goals = await metrica_api.get_counter_goals(counter_id)
                            for goal in goals:
                                goal_id = str(goal["id"])
                                if goal_id not in all_goal_ids:
                                    continue
                                
                                goal_name_from_campaign = goal_id_to_name.get(goal_id, goal["name"])
                                goal_data = {
                                    "id": goal_id,
                                    "name": f"{goal_name_from_campaign} ({counter_name})",
                                    "type": goal.get("type", "Unknown"),
                                    "counter_id": counter_id,
                                    "conversions": 0,
                                    "conversion_rate": 0.0
                                }
                                
                                if include_stats:
                                    stats = db.query(
                                        func.sum(models.MetrikaGoals.conversion_count).label("total_conversions")
                                    ).filter(
                                        models.MetrikaGoals.goal_id == goal_id,
                                        models.MetrikaGoals.integration_id == integration_id,
                                        models.MetrikaGoals.date >= date_from,
                                        models.MetrikaGoals.date <= date_to
                                    ).first()
                                    
                                    if not stats or not stats.total_conversions:
                                        try:
                                            # CRITICAL: Use visits (целевые визиты) instead of reaches
                                            goal_metric = f"ym:s:goal{goal_id}visits"
                                            goals_stats = await metrica_api.get_goals_stats(
                                                counter_id,
                                                date_from,
                                                date_to,
                                                metrics=goal_metric
                                            )
                                            
                                            total_conversions_from_api = 0
                                            for day_data in goals_stats:
                                                if len(day_data.get("metrics", [])) > 0:
                                                    total_conversions_from_api += int(day_data["metrics"][0] or 0)
                                            
                                            if total_conversions_from_api > 0:
                                                goal_data["conversions"] = total_conversions_from_api
                                                
                                                total_clicks = db.query(
                                                    func.sum(models.YandexStats.clicks)
                                                ).join(
                                                    models.Campaign
                                                ).filter(
                                                    models.Campaign.integration_id == integration_id,
                                                    models.Campaign.external_id.in_(external_ids),
                                                    models.YandexStats.date >= date_from,
                                                    models.YandexStats.date <= date_to
                                                ).scalar() or 0
                                                
                                                if total_clicks > 0:
                                                    goal_data["conversion_rate"] = round(
                                                        (goal_data["conversions"] / total_clicks) * 100, 2
                                                    )
                                        except Exception as api_err:
                                            logger.warning(f"⚠️ (fallback) Failed to fetch goal stats from Metrika API for goal_id={goal_id}: {api_err}")
                                    elif stats and stats.total_conversions:
                                        goal_data["conversions"] = int(stats.total_conversions)
                                        
                                        total_clicks = db.query(
                                            func.sum(models.YandexStats.clicks)
                                        ).join(
                                            models.Campaign
                                        ).filter(
                                            models.Campaign.integration_id == integration_id,
                                            models.Campaign.external_id.in_(external_ids),
                                            models.YandexStats.date >= date_from,
                                            models.YandexStats.date <= date_to
                                        ).scalar() or 0
                                        
                                        if total_clicks > 0:
                                            goal_data["conversion_rate"] = round(
                                                (goal_data["conversions"] / total_clicks) * 100, 2
                                            )
                                
                                all_goals.append(goal_data)
                        except Exception as goals_err:
                            logger.error(f"(fallback) Failed to fetch goals for counter {counter_id}: {goals_err}")
                    
                    logger.info(f"✅ (fallback PriorityGoals) Returning {len(all_goals)} goals from {len(campaign_ids_list)} selected campaigns")
                    return all_goals
                except Exception as e:
                    logger.error(f"(fallback PriorityGoals) Error fetching goals from Metrika: {e}")
            
            # 3) Fallback через домены: Кампания → домены сайтов → счётчики Метрики с теми же доменами → цели
            logger.info("Trying domain-based matching: campaign domains → Metrika counters → goals")
            try:
                # Получаем домены выбранных кампаний
                campaign_domains = await direct_api.get_campaign_domains(external_ids)
                logger.info(f"Extracted {len(campaign_domains)} unique domains from campaigns: {list(campaign_domains)}")
                
                if campaign_domains:
                    from automation.yandex_metrica import YandexMetricaAPI
                    metrica_api = YandexMetricaAPI(access_token)
                    
                    # Получаем все доступные счётчики
                    all_counters = await metrica_api.get_counters()
                    logger.info(f"Got {len(all_counters)} counters from Metrika for domain matching")
                    
                    # Фильтруем счётчики по доменам
                    matching_counters = []
                    for counter in all_counters:
                        counter_site = counter.get("site", "")
                        if not counter_site:
                            continue
                        
                        counter_domain = YandexMetricaAPI.normalize_domain(counter_site)
                        if counter_domain in campaign_domains:
                            matching_counters.append(counter)
                            logger.info(f"Counter '{counter.get('name')}' (ID: {counter.get('id')}, site: {counter_site}) matches campaign domain '{counter_domain}'")
                    
                    if matching_counters:
                        logger.info(f"Found {len(matching_counters)} counters matching campaign domains")
                        
                        all_goals = []
                        from sqlalchemy import func
                        
                        for counter in matching_counters:
                            counter_id = str(counter["id"])
                            counter_name = counter.get("name", "Unknown")
                            
                            try:
                                goals = await metrica_api.get_counter_goals(counter_id)
                                for goal in goals:
                                    goal_id = str(goal["id"])
                                    goal_name = goal.get("name", f"Goal {goal_id}")
                                    goal_data = {
                                        "id": goal_id,
                                        "name": f"{goal_name}",
                                        "type": goal.get("type", "Unknown"),
                                        "counter_id": counter_id,
                                        "conversions": 0,
                                        "conversion_rate": 0.0
                                    }
                                    
                                    if include_stats:
                                        stats = db.query(
                                            func.sum(models.MetrikaGoals.conversion_count).label("total_conversions")
                                        ).filter(
                                            models.MetrikaGoals.goal_id == goal_id,
                                            models.MetrikaGoals.integration_id == integration_id,
                                            models.MetrikaGoals.date >= date_from,
                                            models.MetrikaGoals.date <= date_to
                                        ).first()
                                        
                                        if not stats or not stats.total_conversions:
                                            try:
                                                # CRITICAL: Use visits (целевые визиты) instead of reaches
                                                goal_metric = f"ym:s:goal{goal_id}visits"
                                                goals_stats = await metrica_api.get_goals_stats(
                                                    counter_id,
                                                    date_from,
                                                    date_to,
                                                    metrics=goal_metric
                                                )
                                                
                                                total_conversions_from_api = 0
                                                for day_data in goals_stats:
                                                    if len(day_data.get("metrics", [])) > 0:
                                                        total_conversions_from_api += int(day_data["metrics"][0] or 0)
                                                
                                                if total_conversions_from_api > 0:
                                                    goal_data["conversions"] = total_conversions_from_api
                                                    
                                                    total_clicks = db.query(
                                                        func.sum(models.YandexStats.clicks)
                                                    ).join(
                                                        models.Campaign
                                                    ).filter(
                                                        models.Campaign.integration_id == integration_id,
                                                        models.Campaign.external_id.in_(external_ids),
                                                        models.YandexStats.date >= date_from,
                                                        models.YandexStats.date <= date_to
                                                    ).scalar() or 0
                                                    
                                                    if total_clicks > 0:
                                                        goal_data["conversion_rate"] = round(
                                                            (goal_data["conversions"] / total_clicks) * 100, 2
                                                        )
                                            except Exception as api_err:
                                                logger.warning(f"⚠️ (domain fallback) Failed to fetch goal stats for goal_id={goal_id}: {api_err}")
                                        elif stats and stats.total_conversions:
                                            goal_data["conversions"] = int(stats.total_conversions)
                                            
                                            total_clicks = db.query(
                                                func.sum(models.YandexStats.clicks)
                                            ).join(
                                                models.Campaign
                                            ).filter(
                                                models.Campaign.integration_id == integration_id,
                                                models.Campaign.external_id.in_(external_ids),
                                                models.YandexStats.date >= date_from,
                                                models.YandexStats.date <= date_to
                                            ).scalar() or 0
                                            
                                            if total_clicks > 0:
                                                goal_data["conversion_rate"] = round(
                                                    (goal_data["conversions"] / total_clicks) * 100, 2
                                                )
                                    
                                    all_goals.append(goal_data)
                            except Exception as goals_err:
                                logger.error(f"(domain fallback) Failed to fetch goals for counter {counter_id}: {goals_err}")
                        
                        if all_goals:
                            logger.info(f"✅ (domain fallback) Returning {len(all_goals)} goals from {len(matching_counters)} matching counters")
                            return all_goals
                        else:
                            logger.warning("(domain fallback) No goals found in matching counters")
                    else:
                        logger.warning(f"(domain fallback) No counters match campaign domains {list(campaign_domains)}")
                else:
                    logger.warning("(domain fallback) Could not extract domains from campaigns")
            except Exception as domain_err:
                logger.error(f"(domain fallback) Error in domain-based matching: {domain_err}")
            
            logger.info("⚠️ Neither CounterIds, PriorityGoals, nor domain matching worked, falling back to profile-wide goals")
    
    # LEGACY PATH: If no campaign_ids provided, use profile-based goal fetching
    
    # CRITICAL: Import YandexMetricaAPI here (before use in fallback path)
    from automation.yandex_metrica import YandexMetricaAPI
    
    # CRITICAL: Try to get the correct Metrika owner_login format for the selected profile
    # Direct API uses one format (e.g., "sintez-digital"), Metrika may use another (e.g., "Sintez.digital")
    # We'll try to get the actual login format from Direct API
    metrika_owner_login = target_account  # Default to target_account
    if target_account and integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
        try:
            from automation.yandex_direct import YandexDirectAPI
            direct_api = YandexDirectAPI(access_token, client_login=target_account)
            clients_info = await direct_api.get_clients()
            if clients_info:
                # Get the Login field which is the actual advertising account login
                actual_login = clients_info[0].get("Login")
                if actual_login:
                    metrika_owner_login = actual_login
        except Exception as e:
            pass
    
    # IMPORTANT: Try to get counters with profile filter first, but fallback to all if 403
    # Some profiles may not have direct access in Metrika API (403 Forbidden)
    # In that case, we get all accessible counters and filter by owner_login later
    metrica_api = YandexMetricaAPI(access_token, client_login=target_account)
    
    try:
        try:
            counters = await metrica_api.get_counters()
        except Exception as api_err:
            error_str = str(api_err)
            if "403" in error_str or "access_denied" in error_str.lower():
                fallback_api = YandexMetricaAPI(access_token)
                try:
                    counters = await fallback_api.get_counters()
                    metrica_api = fallback_api
                except Exception:
                    return []
            else:
                return []

        if not counters:
            return []
            
        # CRITICAL: Save all counters before filtering (for fallback if filtering returns 0)
        all_counters_before_filter = counters.copy()
        
        # CRITICAL: Filter counters by the selected profile (target_account)
        # One Yandex account can have access to counters from multiple advertising profiles
        # We need to show only counters that belong to the selected profile
        warning_message = None
        if target_account:
            # Helper function to normalize login for comparison
            # Metrika owner_login can have different format than Direct agency_client_login
            # Examples: "Sintez.digital" vs "sintez-digital"
            # Strategy: normalize both by removing dots/dashes and comparing alphanumeric parts
            def normalize_login(login: str) -> str:
                """Normalize login for comparison: lowercase, remove dots/dashes, keep only alphanumeric"""
                if not login:
                    return ""
                # Convert to lowercase and remove all dots, dashes, underscores
                normalized = login.lower().strip()
                # Remove common separators to compare core parts
                normalized = normalized.replace('.', '').replace('-', '').replace('_', '')
                return normalized
            
            # Use both target_account and metrika_owner_login for matching
            # This handles cases where formats differ between Direct and Metrika
            target_logins = [target_account, metrika_owner_login]
            if target_account != metrika_owner_login:
                target_logins = list(set([target_account, metrika_owner_login]))  # Remove duplicates
            
            target_normalized = normalize_login(target_account)
            metrika_normalized = normalize_login(metrika_owner_login)
            
            filtered_counters = []
            for counter in counters:
                owner_login = counter.get('owner_login', '')
                owner_normalized = normalize_login(owner_login)
                
                matches = (
                    owner_login.lower() == target_account.lower() or
                    owner_login.lower() == metrika_owner_login.lower() or
                    owner_normalized == target_normalized or
                    owner_normalized == metrika_normalized or
                    target_normalized in owner_normalized or
                    owner_normalized in target_normalized
                )
                
                if matches:
                    filtered_counters.append(counter)
            
            if filtered_counters:
                counters = filtered_counters
            else:
                counters = all_counters_before_filter
                warning_message = "Метрики для этого профиля не найдены. Пожалуйста, выберите нужные метрики из доступных"

        all_goals = []
        for counter in counters:
            counter_id = str(counter['id'])
            counter_name = counter.get('name', 'Unknown')
            owner_login = counter.get('owner_login', 'N/A')
            
            # CRITICAL: Only double-check counter if we're NOT showing all counters (no warning_message)
            # If warning_message is set, we're showing all counters intentionally, so skip this check
            if target_account and not warning_message:
                def normalize_login_check(login: str) -> str:
                    """Normalize login for comparison: lowercase, remove dots/dashes, keep only alphanumeric"""
                    if not login:
                        return ""
                    normalized = login.lower().strip()
                    normalized = normalized.replace('.', '').replace('-', '').replace('_', '')
                    return normalized
                
                owner_normalized = normalize_login_check(owner_login)
                target_normalized = normalize_login_check(target_account)
                metrika_normalized = normalize_login_check(metrika_owner_login)
                
                # Use same matching logic as filtering
                matches = (
                    owner_login.lower() == target_account.lower() or
                    owner_login.lower() == metrika_owner_login.lower() or
                    owner_normalized == target_normalized or
                    owner_normalized == metrika_normalized or
                    target_normalized in owner_normalized or
                    owner_normalized in target_normalized
                )
                
                if not matches:
                    logger.warning(f"⚠️ Skipping counter '{counter_name}' (ID: {counter_id}) - owner_login '{owner_login}' (normalized: '{owner_normalized}') doesn't match selected profile '{target_account}' (normalized: '{target_normalized}')")
                    continue
            
            try:
                goals = await metrica_api.get_counter_goals(counter_id)
                for goal in goals:
                    goal_data = {
                        "id": str(goal['id']),
                        "name": f"{goal['name']} ({counter_name})",
                        "type": goal.get('type', 'Unknown'),
                        "counter_id": counter_id,
                        "conversions": 0,
                        "conversion_rate": 0.0
                    }
                    
                    # If stats requested, fetch from DB / Metrika API
                    if include_stats:
                        from sqlalchemy import func
                        # CRITICAL: MetrikaGoals stores data with goal_id="all" for aggregated goals
                        # But we need to find data for specific goal_id
                        # Strategy: Try to find by specific goal_id first, if not found, try "all"
                        stats = db.query(
                            func.sum(models.MetrikaGoals.conversion_count).label('total_conversions')
                        ).filter(
                            models.MetrikaGoals.goal_id == str(goal['id']),
                            models.MetrikaGoals.integration_id == integration_id,  # CRITICAL: Filter by integration, not client
                            models.MetrikaGoals.date >= date_from,
                            models.MetrikaGoals.date <= date_to
                        ).first()
                        
                        # If no stats found for specific goal_id, try "all" (aggregated)
                        if not stats or not stats.total_conversions:
                            logger.debug(f"📊 No stats found for goal_id={goal['id']}, trying 'all' for integration {integration_id}")
                            stats = db.query(
                                func.sum(models.MetrikaGoals.conversion_count).label('total_conversions')
                            ).filter(
                                models.MetrikaGoals.goal_id == "all",
                                models.MetrikaGoals.integration_id == integration_id,
                                models.MetrikaGoals.date >= date_from,
                                models.MetrikaGoals.date <= date_to
                            ).first()
                        
                        if not stats or not stats.total_conversions:
                            try:
                                # CRITICAL: Use visits (целевые визиты) instead of reaches
                                goal_metric = f"ym:s:goal{goal['id']}visits"
                                goals_stats = await metrica_api.get_goals_stats(
                                    counter_id,
                                    date_from,
                                    date_to,
                                    metrics=goal_metric
                                )
                                
                                # Sum up conversions from all days
                                total_conversions_from_api = 0
                                for day_data in goals_stats:
                                    if len(day_data.get('metrics', [])) > 0:
                                        total_conversions_from_api += int(day_data['metrics'][0] or 0)
                                
                                if total_conversions_from_api > 0:
                                    goal_data["conversions"] = total_conversions_from_api
                                    
                                    # Calculate conversion rate based on campaign clicks
                                    total_clicks = db.query(
                                        func.sum(models.YandexStats.clicks)
                                    ).join(
                                        models.Campaign
                                    ).filter(
                                        models.Campaign.integration_id == integration_id,
                                        models.YandexStats.date >= date_from,
                                        models.YandexStats.date <= date_to
                                    ).scalar() or 0
                                    
                                    if total_clicks > 0:
                                        goal_data["conversion_rate"] = round((goal_data["conversions"] / total_clicks) * 100, 2)
                            except Exception as api_err:
                                logger.warning(f"⚠️ Failed to fetch goal stats from Metrika API for goal_id={goal['id']}: {api_err}")
                        elif stats and stats.total_conversions:
                            goal_data["conversions"] = int(stats.total_conversions)
                            
                            # Calculate conversion rate based on campaign clicks
                            total_clicks = db.query(
                                func.sum(models.YandexStats.clicks)
                            ).join(
                                models.Campaign
                            ).filter(
                                models.Campaign.integration_id == integration_id,
                                models.YandexStats.date >= date_from,
                                models.YandexStats.date <= date_to
                            ).scalar() or 0
                            
                            if total_clicks > 0:
                                goal_data["conversion_rate"] = round((goal_data["conversions"] / total_clicks) * 100, 2)
                    
                    all_goals.append(goal_data)
            except Exception as goals_err:
                logger.error(f"Failed to fetch goals for counter {counter_id}: {goals_err}")
        
        # CRITICAL: If warning_message is set, return goals with warning
        # Frontend should display the warning message to user
        if warning_message:
            # Return as dict with goals and warning_message
            return {
                "goals": all_goals,
                "warning_message": warning_message
            }
        
        return all_goals
    except Exception as e:
        logger.error(f"Error fetching real Metrica goals: {e}")
        return []

@router.patch("/{integration_id}", response_model=schemas.IntegrationResponse)
async def update_integration(
    integration_id: uuid.UUID,
    integration_in: dict = Body(...),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update integration settings (auto_sync, sync_interval, etc.).
    """
    integration = db.query(models.Integration).join(models.Client).filter(
        models.Integration.id == integration_id,
        models.Client.owner_id == current_user.id
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    logger.info(f"Updating integration {integration_id} with data: {integration_in}")
    logger.info(f"Before update: agency_client_login={integration.agency_client_login}, account_id={integration.account_id}")
    
    # CRITICAL: For VK Ads, validate and normalize account_id format
    # VK Ads account_id should be a simple numeric string (e.g., "592676405")
    # If it comes in format like "vkads_592676405@vk@8493881", extract the numeric part
    if integration.platform == models.IntegrationPlatform.VK_ADS:
        if 'account_id' in integration_in and integration_in['account_id']:
            account_id_raw = str(integration_in['account_id'])
            logger.info(f"🔵 VK Ads account_id received: '{account_id_raw}'")
            
            # Check if it's in wrong format (vkads_XXX@vk@YYY)
            if '@vk@' in account_id_raw or account_id_raw.startswith('vkads_'):
                # Extract numeric ID - try to find the main account ID
                # Format might be: "vkads_592676405@vk@8493881" -> extract "592676405"
                import re
                # Try to extract numeric ID after "vkads_" or before "@vk@"
                match = re.search(r'vkads_(\d+)', account_id_raw)
                if not match:
                    match = re.search(r'(\d+)', account_id_raw)  # Fallback: any numeric sequence
                
                if match:
                    normalized_id = match.group(1)
                    logger.warning(f"⚠️ VK Ads account_id in wrong format '{account_id_raw}', normalized to '{normalized_id}'")
                    integration_in['account_id'] = normalized_id
                    if 'agency_client_login' in integration_in:
                        integration_in['agency_client_login'] = normalized_id
                else:
                    logger.error(f"❌ Could not extract numeric ID from VK account_id: '{account_id_raw}'")
                    raise HTTPException(status_code=400, detail=f"Неверный формат account_id для VK Ads: {account_id_raw}. Ожидается числовой ID (например, '592676405').")
            else:
                # Already in correct format, but ensure it's numeric
                if not account_id_raw.isdigit():
                    logger.warning(f"⚠️ VK Ads account_id '{account_id_raw}' is not purely numeric, but using as-is")
    
    # 1. Обновляем поля самой интеграции
    for key, value in integration_in.items():
        if hasattr(integration, key):
            # Special handling for JSON fields if they come as lists/dicts
            if key == 'selected_goals' and (isinstance(value, list) or isinstance(value, dict)):
                value = json.dumps(value)
            elif key == 'selected_counters' and (isinstance(value, list) or isinstance(value, dict)):
                value = json.dumps(value)
            setattr(integration, key, value)
            logger.info(f"Set {key} = {value}")

    # 2. Обновляем признак активности кампаний по selected_campaign_ids / all_campaigns
    try:
        selected_campaign_ids = integration_in.get("selected_campaign_ids")
        all_campaigns_flag = integration_in.get("all_campaigns")
        if selected_campaign_ids is not None or all_campaigns_flag is not None:
            from uuid import UUID as _UUID
            # Приводим к множеству UUID для быстрых проверок
            selected_set = set()
            if isinstance(selected_campaign_ids, list):
                for cid in selected_campaign_ids:
                    try:
                        selected_set.add(_UUID(str(cid)))
                    except Exception:
                        logger.warning(f"Invalid campaign id in selected_campaign_ids: {cid}")
            # Получаем все кампании этой интеграции
            campaigns_q = db.query(models.Campaign).filter(
                models.Campaign.integration_id == integration.id
            )
            for campaign in campaigns_q:
                if all_campaigns_flag:
                    # Пользователь выбрал "все кампании" — помечаем все как активные
                    campaign.is_active = True
                else:
                    # Активны только явно выбранные кампании
                    campaign.is_active = campaign.id in selected_set
            logger.info(
                f"Updated campaigns is_active for integration {integration_id}: "
                f"all_campaigns={all_campaigns_flag}, selected_count={len(selected_set)}"
            )
    except Exception as camp_err:
        logger.error(f"Failed to update campaigns is_active for integration {integration_id}: {camp_err}")
    
    # CRITICAL: For Yandex Direct, ensure agency_client_login is set when account_id is updated
    if integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
        if 'account_id' in integration_in and integration_in['account_id']:
            # Auto-set agency_client_login if not explicitly provided
            if 'agency_client_login' not in integration_in:
                integration.agency_client_login = integration_in['account_id']
                logger.info(f"Auto-set agency_client_login to {integration_in['account_id']} for integration {integration_id}")
        # Also ensure agency_client_login is set if explicitly provided
        if 'agency_client_login' in integration_in:
            integration.agency_client_login = integration_in['agency_client_login']
            logger.info(f"Explicitly set agency_client_login to {integration_in['agency_client_login']} for integration {integration_id}")
    
    logger.info(f"After update (before commit): agency_client_login={integration.agency_client_login}, account_id={integration.account_id}")
    
    log_event("backend", f"updated integration {integration_id}", integration_in)
    log_history_event(
        db,
        actor=current_user,
        event_type="integration",
        action="integration_settings_changed",
        description=f"Изменены настройки интеграции {integration.platform.value}",
        client_id=integration.client_id,
        target_type="integration",
        target_id=str(integration.id),
        meta={"fields": sorted([str(k) for k in integration_in.keys()])},
    )
    db.commit()
    db.refresh(integration)
    
    # Verify the value was actually saved
    logger.info(f"After commit and refresh: agency_client_login={integration.agency_client_login}, account_id={integration.account_id}")
    
    # OPTIMIZATION: Sync statistics only when integration is finalized (is_active=True)
    # This happens on step 6 (summary) when user completes the integration wizard
    # CRITICAL: Sync выполняется в фоне, чтобы не блокировать запрос
    if integration_in.get("is_active") is True:
        # CRITICAL: Используем run_sync_in_background, которая запускает синхронизацию
        # в отдельном потоке с новым event loop, чтобы не блокировать основной event loop FastAPI.
        run_sync_in_background(integration_id, 30)
        logger.info(f"🔄 Finalizing integration {integration_id}: queued background sync for 30 days")
    
    return integration


def _vk_persist_token_json_to_integration(
    integration: models.Integration, db: Session, token_data: dict
) -> None:
    """Сохранить ответ token.json (access / refresh / expires_in) в интеграции."""
    integration.access_token = security.encrypt_token(token_data["access_token"])
    rt = token_data.get("refresh_token")
    if rt:
        integration.refresh_token = security.encrypt_token(rt)
    exp_in = token_data.get("expires_in")
    if exp_in is not None:
        try:
            integration.expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=int(exp_in)
            )
        except (TypeError, ValueError):
            pass
    db.add(integration)
    db.commit()
    db.refresh(integration)


@router.post("/{integration_id}/discover-campaigns")
async def discover_campaigns(
    integration_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetch campaign list from platform and save/update in DB as inactive.
    """
    integration = db.query(models.Integration).join(models.Client).filter(
        models.Integration.id == integration_id,
        models.Client.owner_id == current_user.id
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    # CRITICAL: Refresh integration from DB to ensure we have the latest account_id and agency_client_login
    # This is important because the profile might have been updated just before this call
    db.refresh(integration)
    
    # DEBUG: Log current state of integration
    logger.info(f"🔵 discover_campaigns: integration {integration_id} state:")
    logger.info(f"   account_id: '{integration.account_id}'")
    logger.info(f"   agency_client_login: '{integration.agency_client_login}'")
    logger.info(f"   platform: {integration.platform}")
    
    # CRITICAL: For VK Ads, ensure account_id is set before fetching campaigns
    # If account_id is not set, campaigns will be fetched from all accessible cabinets
    if integration.platform == models.IntegrationPlatform.VK_ADS:
        if not integration.account_id or integration.account_id.lower() == "unknown":
            logger.warning(f"⚠️ VK Ads: No cabinet selected (account_id is None or 'unknown'). Campaigns will be fetched from all accessible cabinets.")
        else:
            logger.info(f"✅ VK Ads: Cabinet selected (account_id: {integration.account_id}). Campaigns will be filtered by this cabinet.")
    
    # CRITICAL: If profile is selected, delete campaigns from other profiles
    # This prevents "RSY - Hot_3" type campaigns from appearing
    if integration.agency_client_login and integration.agency_client_login.lower() != "unknown":
        # Get valid campaign IDs from API for the selected profile
        # We'll delete campaigns that don't match after we get the list
        logger.info(f"🔍 Profile selected: {integration.agency_client_login}. Will clean up campaigns from other profiles after discovery.")
        
    log_event("backend", f"discovering campaigns for integration {integration_id}")
    access_token = security.decrypt_token(integration.access_token)
    discovered_campaigns = []
    
    if integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
        # CRITICAL: Use the SAME profile selection as sync — agency_client_login first, then account_id.
        # Sync uses agency_client_login for Reports API; if discover-campaigns used only account_id,
        # we'd get campaigns for a different profile and stats would be skipped (not in DB).
        selected_profile = None
        if integration.agency_client_login and integration.agency_client_login.lower() not in ["unknown", "none", ""]:
            selected_profile = integration.agency_client_login
        elif integration.account_id and integration.account_id.lower() != "unknown":
            selected_profile = integration.account_id
        if not selected_profile:
            logger.error(f"❌ discover_campaigns: integration {integration_id} has no profile (agency_client_login or account_id). Cannot fetch campaigns correctly.")
            raise HTTPException(status_code=400, detail="Для интеграции не задан логин рекламного профиля. Пере настройте интеграцию и выберите профиль.")
        
        use_client_login = selected_profile
        logger.info(
            f"Fetching campaigns for integration {integration_id}, "
            f"using profile (account_id)='{selected_profile}', "
            f"agency_client_login='{integration.agency_client_login}', "
            f"Client-Login header='{use_client_login}'"
        )
        
        # Жёстко фильтруем кампании по выбранному профилю через Client-Login
        api = YandexDirectAPI(access_token, client_login=use_client_login)
        logger.info(f"🔵 About to call api.get_campaigns() with Client-Login: '{use_client_login}'")
        try:
            discovered_campaigns = await api.get_campaigns()
            logger.info(f"🔵 api.get_campaigns() returned {len(discovered_campaigns)} campaigns")
            if discovered_campaigns:
                logger.info(f"🔵 First few campaign names: {[c.get('name') for c in discovered_campaigns[:5]]}")
                logger.info(f"🔵 First few campaign IDs: {[c.get('id') for c in discovered_campaigns[:5]]}")
        except Exception as e:
            message = str(e)
            # Специальная обработка популярных ошибок API
            # error_code 513: "Ваш логин не подключен к Яндекс.Директу"
            if 'error_code\": 513' in message or 'не подключен к Яндекс.Директу' in message:
                logger.warning(f"Yandex Direct not connected for this login (integration {integration_id}): {message}")
                raise HTTPException(
                    status_code=400,
                    detail="Для этого аккаунта Яндекс.Директ не подключён. "
                           "Зайдите в Яндекс.Директ под этой почтой и создайте хотя бы одну кампанию."
                )
            # error_code 3228: API only available in Direct Pro mode
            if 'error_code\": 3228' in message or 'Директ Про' in message:
                logger.warning(f"Yandex API available only in Direct Pro for this login (integration {integration_id}): {message}")
                raise HTTPException(
                    status_code=400,
                    detail="API Яндекс.Директ доступен только в режиме «Директ Про» для этого аккаунта. "
                           "Переключите интерфейс на «Директ Про» в настройках Яндекс.Директа."
                )
            
            # Все остальные ошибки пробрасываем как 502, чтобы фронт показал общий текст
            logger.error(f"Unexpected Yandex Direct error while discovering campaigns: {message}")
            raise HTTPException(
                status_code=502,
                detail="Не удалось получить кампании из Яндекс.Директ. Попробуйте ещё раз позже."
            )
        
        logger.info(f"🔵 ========== DISCOVER CAMPAIGNS RESULTS ==========")
        logger.info(f"🔵 API returned {len(discovered_campaigns)} campaigns from Yandex Direct API")
        logger.info(f"🔵 Using Client-Login: '{use_client_login}'")
        logger.info(f"🔵 Integration agency_client_login: '{integration.agency_client_login}'")
        logger.info(f"🔵 Integration account_id: '{integration.account_id}'")
        
        if discovered_campaigns:
            logger.info(f"🔵 ALL Campaign names from API: {[c.get('name') for c in discovered_campaigns]}")
            logger.info(f"🔵 ALL Campaign IDs from API: {[c.get('id') for c in discovered_campaigns]}")
            logger.info(f"🔵 ALL Campaign states from API: {[c.get('state', 'N/A') for c in discovered_campaigns]}")
            
            # Log each campaign in detail
            for idx, c in enumerate(discovered_campaigns):
                logger.info(f"🔵 Campaign [{idx+1}]: ID={c.get('id')}, Name='{c.get('name')}', State={c.get('state', 'N/A')}, Status={c.get('status', 'N/A')}, Type={c.get('type', 'N/A')}")
        else:
            logger.warning(f"🔵 ⚠️ NO CAMPAIGNS RETURNED FROM API!")
        
        # CRITICAL: Check for missing campaigns
        # Expected campaigns from screenshot: "ADS", "Landing", "elka152.ru - Алекс новая", "elka152.ru - Александр", "Основа основ"
        expected_campaign_names = ["ADS", "Landing", "elka152.ru - Алекс новая", "elka152.ru - Александр", "Основа основ"]
        found_campaign_names = [c.get('name') for c in discovered_campaigns]
        missing_campaigns = [name for name in expected_campaign_names if name not in found_campaign_names]
        if missing_campaigns:
            logger.error(f"❌ ========== MISSING CAMPAIGNS DETECTED ==========")
            logger.error(f"❌ MISSING CAMPAIGNS: {missing_campaigns}")
            logger.error(f"❌ Expected {len(expected_campaign_names)} campaigns, but got {len(discovered_campaigns)}")
            logger.error(f"❌ Found campaigns: {found_campaign_names}")
            logger.error(f"❌ This might indicate that:")
            logger.error(f"❌   1. Campaigns.get API is not returning all campaigns")
            logger.error(f"❌   2. Reports API is not finding missing campaigns (even with 5-year range)")
            logger.error(f"❌   3. Missing campaigns belong to a different profile")
            logger.error(f"❌   4. Missing campaigns are in a state that API filters out")
        else:
            logger.info(f"✅ All expected campaigns found!")
        
        logger.info(f"🔵 ==============================================")
        
        # Check for specific campaigns
        campaign_names_lower = [c.get('name', '').lower() for c in discovered_campaigns]
        if any('кси' in name or 'ksi' in name for name in campaign_names_lower):
            logger.info(f"✅ Found 'кси' campaign in API response!")
        else:
            logger.warning(f"❌ 'кси' campaign NOT found in API response!")
        
        # Check for "ADS" and "Landing" campaigns
        if any('ads' in name.lower() for name in campaign_names_lower):
            logger.info(f"✅ Found 'ADS' campaign in API response!")
        else:
            logger.warning(f"❌ 'ADS' campaign NOT found in API response!")
        
        if any('landing' in name.lower() for name in campaign_names_lower):
            logger.info(f"✅ Found 'Landing' campaign in API response!")
        else:
            logger.warning(f"❌ 'Landing' campaign NOT found in API response!")
        
        log_event("yandex", f"discovered {len(discovered_campaigns)} campaigns")
    elif integration.platform == models.IntegrationPlatform.VK_ADS:
        # CRITICAL: Для VK Ads используем account_id (выбранный кабинет) для фильтрации кампаний
        # Согласно документации VK Ads API, параметр client_id используется для фильтрации кампаний по кабинету
        selected_cabinet_id = integration.account_id if integration.account_id and integration.account_id.lower() != "unknown" else None
        
        if selected_cabinet_id:
            logger.info(f"🔵 VK Ads: Using selected cabinet (account_id) for filtering campaigns: {selected_cabinet_id}")
        else:
            logger.warning(f"⚠️ VK Ads: No cabinet selected (account_id is None or 'unknown'). Will fetch campaigns from all accessible cabinets.")
        
        campaigns_ok = False
        try:
            api = VKAdsAPI(access_token, account_id=selected_cabinet_id)
            discovered_campaigns = await api.get_campaigns()
            campaigns_ok = True
        except HTTPException:
            raise
        except Exception as e:
            err = e
            if vk_campaigns_error_needs_agency_client_retry(err) and VK_CLIENT_SECRET:
                logger.info(
                    "VK Ads discover_campaigns: повтор через agency_client_credentials (integration=%s)",
                    integration_id,
                )
                td = await exchange_vk_agency_client_credentials_for_integration(
                    client_id=VK_CLIENT_ID,
                    client_secret=VK_CLIENT_SECRET,
                    agency_access_token=access_token,
                    agency_client_login=integration.agency_client_login,
                    account_id=integration.account_id,
                )
                if td:
                        _vk_persist_token_json_to_integration(integration, db, td)
                        access_token = security.decrypt_token(integration.access_token)
                        api = VKAdsAPI(access_token, account_id=selected_cabinet_id)
                        try:
                            discovered_campaigns = await api.get_campaigns()
                            campaigns_ok = True
                        except Exception as e2:
                            err = e2
            if not campaigns_ok:
                msg = str(err)[:500]
                logger.exception(
                    f"VK Ads discover_campaigns failed (integration {integration_id}): {msg}"
                )
                if "view_campaigns" in msg or (
                    "access_denied" in msg and "403" in msg
                ):
                    raise HTTPException(
                        status_code=403,
                        detail=(
                            "VK Реклама отклонила запрос к списку кампаний (в ответе API: право view_campaigns). "
                            "Обычно это значит, что в токене нет нужных OAuth-прав (часто read_ads) или приложение "
                            "в кабинете VK не одобрено для этих методов. Отключите интеграцию и подключите снова, "
                            "разрешив все запрошенные доступы; проверьте поле scope в ответе token.json и документацию "
                            "VK Ads API. При указании scope вручную используйте только имена из документации, не "
                            "подставляйте required_permission из текста ошибки без проверки."
                        ),
                    )
                raise HTTPException(
                    status_code=502,
                    detail=f"Не удалось получить кампании из VK Рекламы: {msg}",
                )
        
        if selected_cabinet_id:
            logger.info(f"✅ VK Ads: Discovered {len(discovered_campaigns)} campaigns for cabinet {selected_cabinet_id}")
        else:
            logger.info(f"✅ VK Ads: Discovered {len(discovered_campaigns)} campaigns (no cabinet filter applied)")
        
        log_event("vk", f"discovered {len(discovered_campaigns)} campaigns")

    elif integration.platform == models.IntegrationPlatform.AVITO_ADS:
        try:
            avito_api = _build_avito_api_from_integration(integration)
            discovered_campaigns = await avito_api.get_campaigns(integration.account_id)
            logger.info(f"✅ Avito Ads: discovered {len(discovered_campaigns)} campaigns for account {integration.account_id}")
        except Exception as e:
            logger.exception(f"Avito Ads discover_campaigns failed (integration {integration_id}): {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Не удалось получить кампании из Avito Рекламы: {str(e)[:300]}",
            )
        log_event("avito", f"discovered {len(discovered_campaigns)} campaigns")

    # Save to DB
    logger.info(f"💾 Saving {len(discovered_campaigns)} campaigns to database for integration {integration_id}")
    saved_count = 0
    updated_count = 0
    for dc in discovered_campaigns:
        campaign = db.query(models.Campaign).filter_by(
            integration_id=integration.id,
            external_id=str(dc["id"])
        ).first()
        
        incoming_name = dc.get("name")
        if not campaign:
            campaign = models.Campaign(
                integration_id=integration.id,
                external_id=str(dc["id"]),
                name=incoming_name or f"Campaign {dc.get('id')}",
                is_active=False # Discovery creates them as inactive by default
            )
            db.add(campaign)
            saved_count += 1
            logger.info(f"   💾 Created new campaign: ID={dc['id']}, Name='{dc['name']}'")
        else:
            # Не затираем нормальное имя пустыми/плейсхолдерами
            if incoming_name and not str(incoming_name).startswith("Campaign "):
                campaign.name = incoming_name
            updated_count += 1
            logger.info(f"   💾 Updated existing campaign: ID={dc['id']}, Name='{dc['name']}'")
        apply_platform_status(campaign, dc)
            
    db.commit()
    logger.info(f"💾 Saved {saved_count} new campaigns, updated {updated_count} existing campaigns")
    
    # CRITICAL: Clean up campaigns from other profiles if profile is selected
    # Delete campaigns that weren't returned by API (they belong to other profiles)
    # Use same profile check as discover: agency_client_login or account_id
    has_valid_profile = (
        (integration.agency_client_login and integration.agency_client_login.lower() not in ["unknown", "none", ""])
        or (integration.account_id and integration.account_id.lower() != "unknown")
    )
    if has_valid_profile and discovered_campaigns and len(discovered_campaigns) > 0:
        discovered_external_ids = {str(dc["id"]) for dc in discovered_campaigns}
        all_db_campaigns = db.query(models.Campaign).filter_by(integration_id=integration.id).all()
        
        # Check if any existing campaigns match discovered campaigns
        # If none match, it might mean profile changed OR API returned wrong data
        existing_external_ids = {str(c.external_id) for c in all_db_campaigns}
        matching_count = len(existing_external_ids & discovered_external_ids)
        
        deleted_count = 0
        campaigns_to_delete = []
        profile_log = integration.agency_client_login or integration.account_id or "?"
        for db_campaign in all_db_campaigns:
            if str(db_campaign.external_id) not in discovered_external_ids:
                campaigns_to_delete.append(db_campaign)
                logger.warning(f"🗑️ Will delete campaign '{db_campaign.name}' (ID: {db_campaign.external_id}) - not in API response for profile {profile_log}")
        
        # CRITICAL: Only delete if:
        # 1. We have campaigns to delete
        # 2. We discovered some campaigns (not empty)
        # 3. At least SOME discovered campaigns match existing ones (profile didn't completely change)
        # OR if NONE match but we have discovered campaigns (profile definitely changed)
        if campaigns_to_delete:
            logger.info(f"🔵 Found {len(campaigns_to_delete)} campaigns to delete (not in API response for profile {profile_log})")
            logger.info(f"🔵 Discovered {len(discovered_campaigns)} campaigns for profile {profile_log}")
            logger.info(f"🔵 Matching campaigns: {matching_count} out of {len(existing_external_ids)} existing")
            
            # Only delete if we're confident this is a profile change (no matches) OR if we have some matches (partial overlap)
            # This prevents deleting when API returns wrong data due to errors
            if matching_count == 0 and len(discovered_campaigns) > 0:
                # Profile completely changed - safe to delete old campaigns
                logger.info(f"🔵 Profile changed completely (0 matches) - deleting {len(campaigns_to_delete)} old campaigns")
                for db_campaign in campaigns_to_delete:
                    db.delete(db_campaign)
                    deleted_count += 1
            elif matching_count > 0:
                # Partial overlap - some campaigns match, some don't
                # This is normal when profile changes or when some campaigns are archived
                logger.info(f"🔵 Partial overlap ({matching_count} matches) - deleting {len(campaigns_to_delete)} campaigns not in current profile")
                for db_campaign in campaigns_to_delete:
                    db.delete(db_campaign)
                    deleted_count += 1
            else:
                logger.warning(f"⚠️ Skipping campaign deletion: no matches and discovered_campaigns might be wrong")
            
            if deleted_count > 0:
                db.commit()
                logger.info(f"🗑️ Deleted {deleted_count} campaigns from other profiles")
        else:
            logger.info(f"🔵 No campaigns to delete - all campaigns match discovered campaigns for profile {profile_log}")
    else:
        if not has_valid_profile:
            logger.info(f"🔵 Skipping campaign deletion: no valid profile (agency_client_login or account_id) selected")
        elif not discovered_campaigns or len(discovered_campaigns) == 0:
            logger.warning(f"⚠️ Skipping campaign deletion: discovered_campaigns is empty (might be API error or wrong profile)")
    
    # OPTIMIZATION: Statistics sync removed from discover_campaigns
    # Statistics will be synced only when integration is finalized (on step 6)
    
    # Return all campaigns for this integration as dictionaries
    # CRITICAL: Use discovered_campaigns data (from API) to get state and type
    # Create a map of external_id -> campaign data from API
    discovered_map = {str(dc["id"]): dc for dc in discovered_campaigns}
    
    # Возвращаем ВСЕ кампании (включая архивные/остановленные и исторические имена).
    all_campaigns = db.query(models.Campaign).filter_by(integration_id=integration.id).all()

    filtered_campaigns = []
    for campaign in all_campaigns:
        # Get state from discovered_campaigns (API data)
        api_campaign = discovered_map.get(str(campaign.external_id))
        
        # Build campaign dict with data from API if available
        # Map state values to match frontend expectations
        campaign_state = api_campaign.get("state", "UNKNOWN") if api_campaign else "UNKNOWN"
        if campaign_state == "UNKNOWN" and api_campaign:
            # VK часто возвращает status (active/deleted/blocked) без поля state.
            raw_status = str(api_campaign.get("status") or "").lower()
            if raw_status == "active":
                campaign_state = "ON"
            elif raw_status == "deleted":
                campaign_state = "ARCHIVED"
            elif raw_status == "blocked":
                campaign_state = "SUSPENDED"
        # IMPORTANT: Keep ARCHIVED state as-is for filtering
        # Map state: OFF -> SUSPENDED for frontend (OFF means paused/stopped)
        # But keep ARCHIVED, ENDED, ON, SUSPENDED as-is
        if campaign_state == "OFF":
            campaign_state = "SUSPENDED"  # Frontend uses SUSPENDED for paused campaigns
        # ARCHIVED campaigns should be returned with state="ARCHIVED" so filter can find them
        
        # Get type and ensure it matches frontend expectations
        campaign_type = api_campaign.get("type", "UNKNOWN") if api_campaign else "UNKNOWN"
        # Type values from API should match: TEXT_CAMPAIGN, DYNAMIC_TEXT_CAMPAIGN, MOBILE_APP_CAMPAIGN, SMART_CAMPAIGN
        
        campaign_dict = {
            "id": str(campaign.id),
            "external_id": campaign.external_id,
            "name": campaign.name,
            "status": campaign.platform_status or (api_campaign.get("status", "UNKNOWN") if api_campaign else "UNKNOWN"),
            "state": campaign_state,  # Mapped state for frontend filtering
            "platform_state": campaign.platform_state,
            "display_status": campaign.display_status or "unknown",
            "type": campaign_type  # Campaign type for filtering
        }
        
        filtered_campaigns.append(campaign_dict)
    
    logger.info(f"✅ Returning {len(filtered_campaigns)} campaigns (ALL from DB for integration)")
    return filtered_campaigns

@router.get("/{integration_id}/campaigns-stats")
async def get_campaigns_stats(
    integration_id: uuid.UUID,
    date_from: str = None,
    date_to: str = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get aggregated statistics for campaigns in the integration.
    Used by the wizard to show real stats in the campaign selection step.
    """
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    integration = db.query(models.Integration).join(models.Client).filter(
        models.Integration.id == integration_id,
        models.Client.owner_id == current_user.id
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    # Default date range: last 30 days
    if not date_from or not date_to:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        date_from = start_date.strftime("%Y-%m-%d")
        date_to = end_date.strftime("%Y-%m-%d")
    
    # CRITICAL: Convert string dates to date objects for proper SQL comparison
    date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
    date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
    logger.info(f"📊 Querying stats for date range: {date_from_obj} to {date_to_obj} (from strings: {date_from} to {date_to})")
    
    campaigns_stats = []
    
    if integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
        # Aggregate YandexStats by campaign_id
        stats_query = db.query(
            models.Campaign.id,
            models.Campaign.external_id,
            models.Campaign.name,
            func.sum(models.YandexStats.impressions).label('impressions'),
            func.sum(models.YandexStats.clicks).label('clicks'),
            func.sum(models.YandexStats.cost).label('cost'),
            func.sum(models.YandexStats.conversions).label('conversions')
        ).join(
            models.YandexStats, models.Campaign.id == models.YandexStats.campaign_id
        ).filter(
            models.Campaign.integration_id == integration_id,
            models.YandexStats.date >= date_from_obj,  # Use date object, not string
            models.YandexStats.date <= date_to_obj     # Use date object, not string
        ).group_by(
            models.Campaign.id, models.Campaign.external_id, models.Campaign.name
        ).all()
        
        logger.info(f"📊 SQL query returned {len(stats_query)} campaigns with stats")
        
        for stat in stats_query:
            stat_id_str = str(stat.id)  # Convert UUID to string
            logger.info(f"   Campaign '{stat.name}' (ID: {stat_id_str}): impressions={stat.impressions}, clicks={stat.clicks}, cost={stat.cost}")
            campaigns_stats.append({
                "id": stat_id_str,  # Use string ID to match discover-campaigns format
                "external_id": stat.external_id,
                "name": stat.name,
                "impressions": int(stat.impressions or 0),
                "clicks": int(stat.clicks or 0),
                "cost": float(stat.cost or 0),
                "conversions": int(stat.conversions or 0)
            })
        
        logger.info(f"📊 Created campaigns_stats list with {len(campaigns_stats)} entries. IDs: {[cs['id'] for cs in campaigns_stats]}")
    
    elif integration.platform == models.IntegrationPlatform.VK_ADS:
        # Aggregate VKStats by campaign_id
        stats_query = db.query(
            models.Campaign.id,
            models.Campaign.external_id,
            models.Campaign.name,
            func.sum(models.VKStats.impressions).label('impressions'),
            func.sum(models.VKStats.clicks).label('clicks'),
            func.sum(models.VKStats.cost).label('cost'),
            func.sum(models.VKStats.conversions).label('conversions')
        ).join(
            models.VKStats, models.Campaign.id == models.VKStats.campaign_id
        ).filter(
            models.Campaign.integration_id == integration_id,
            models.VKStats.date >= date_from_obj,  # Use date object, not string
            models.VKStats.date <= date_to_obj     # Use date object, not string
        ).group_by(
            models.Campaign.id, models.Campaign.external_id, models.Campaign.name
        ).all()
        
        for stat in stats_query:
            campaigns_stats.append({
                "id": str(stat.id),  # Convert UUID to string to match discover-campaigns format
                "external_id": stat.external_id,
                "name": stat.name,
                "impressions": int(stat.impressions or 0),
                "clicks": int(stat.clicks or 0),
                "cost": float(stat.cost or 0),
                "conversions": int(stat.conversions or 0)
            })

    elif integration.platform == models.IntegrationPlatform.AVITO_ADS:
        stats_query = db.query(
            models.Campaign.id,
            models.Campaign.external_id,
            models.Campaign.name,
            func.sum(models.AvitoStats.impressions).label('impressions'),
            func.sum(models.AvitoStats.clicks).label('clicks'),
            func.sum(models.AvitoStats.cost).label('cost'),
        ).join(
            models.AvitoStats, models.Campaign.id == models.AvitoStats.campaign_id
        ).filter(
            models.Campaign.integration_id == integration_id,
            models.AvitoStats.date >= date_from_obj,
            models.AvitoStats.date <= date_to_obj
        ).group_by(
            models.Campaign.id, models.Campaign.external_id, models.Campaign.name
        ).all()

        for stat in stats_query:
            campaigns_stats.append({
                "id": str(stat.id),
                "external_id": stat.external_id,
                "name": stat.name,
                "impressions": int(stat.impressions or 0),
                "clicks": int(stat.clicks or 0),
                "cost": float(stat.cost or 0),
                "conversions": 0,
            })

    # Also include campaigns without stats (newly discovered)
    # CRITICAL: Filter out campaigns that don't belong to this profile
    # Get list of valid campaign IDs from the most recent discover-campaigns call
    all_campaigns = db.query(models.Campaign).filter_by(integration_id=integration.id).all()
    logger.info(f"📋 Total campaigns in DB for this integration: {len(all_campaigns)}")
    stats_model = models.YandexStats
    if integration.platform == models.IntegrationPlatform.VK_ADS:
        stats_model = models.VKStats
    elif integration.platform == models.IntegrationPlatform.AVITO_ADS:
        stats_model = models.AvitoStats
    
    # Filter out template/invalid campaigns
    template_names = ["campaignname", "test campaign", "тест", "test", "шаблон", "template"]
    valid_campaigns = []
    for campaign in all_campaigns:
        campaign_name_lower = campaign.name.lower().strip()
        # Skip template campaigns
        if campaign_name_lower in template_names or campaign_name_lower == "campaignname":
            logger.info(f"   ⏭️ Skipping template campaign in stats: ID={campaign.external_id}, Name='{campaign.name}'")
            continue
        # Skip campaigns with invalid external_id
        if not campaign.external_id or not str(campaign.external_id).isdigit():
            logger.info(f"   ⏭️ Skipping invalid campaign ID in stats: ID={campaign.external_id}, Name='{campaign.name}'")
            continue
        valid_campaigns.append(campaign)
    
    # CRITICAL: Convert campaign IDs to strings for comparison
    # campaigns_stats contains "id" as strings (UUID converted to string)
    existing_ids = {cs["id"] for cs in campaigns_stats}
    
    for campaign in valid_campaigns:
        campaign_id_str = str(campaign.id)  # Convert UUID to string for comparison
        if campaign_id_str not in existing_ids:
            # Check if this campaign has ANY stats records (for debugging)
            stats_count = db.query(stats_model).filter(
                stats_model.campaign_id == campaign.id
            ).count()
            stats_in_range = db.query(stats_model).filter(
                stats_model.campaign_id == campaign.id,
                stats_model.date >= date_from_obj,
                stats_model.date <= date_to_obj
            ).count()
            logger.info(
                "   Campaign '%s' (ID: %s): has %s total %s records, %s in date range %s to %s",
                campaign.name,
                campaign_id_str,
                stats_count,
                stats_model.__name__,
                stats_in_range,
                date_from_obj,
                date_to_obj,
            )
            
            campaigns_stats.append({
                "id": campaign_id_str,  # Use string ID to match discover-campaigns format
                "external_id": campaign.external_id,
                "name": campaign.name,
                "impressions": 0,
                "clicks": 0,
                "cost": 0,
                "conversions": 0
            })
    
    log_event("backend", f"returned stats for {len(campaigns_stats)} campaigns")
    logger.info(f"✅ Returning {len(campaigns_stats)} campaigns total (with and without stats)")
    return campaigns_stats

@router.get("/{integration_id}/test-connection")
async def test_integration_connection(
    integration_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Test if the integration tokens are still valid and have access.
    """
    integration = db.query(models.Integration).join(models.Client).filter(
        models.Integration.id == integration_id,
        models.Client.owner_id == current_user.id
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
        
    access_token = security.decrypt_token(integration.access_token)
    status_info = {"status": "success", "platform": integration.platform, "details": []}
    
    try:
        if integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
            # Test Direct API
            direct_api = YandexDirectAPI(access_token)
            try:
                # Simple check: fetch campaign IDs only
                await direct_api.get_campaigns()
                status_info["details"].append("Yandex Direct: OK")
            except Exception as e:
                status_info["status"] = "failed"
                status_info["details"].append(f"Yandex Direct: {str(e)}")
            
            # Test Metrica API
            metrica_api = YandexMetricaAPI(access_token)
            try:
                await metrica_api.get_counters()
                status_info["details"].append("Yandex Metrica: OK")
            except Exception as e:
                # Metrica failure might not mean total failure if Direct works
                status_info["details"].append(f"Yandex Metrica: {str(e)}")
                if status_info["status"] == "success": # If Direct worked, we might still mark as partial success or warning
                     status_info["status"] = "warning"

        elif integration.platform == models.IntegrationPlatform.VK_ADS:
             # Test VK API
             from automation.vk_ads import VKAdsAPI
             vk_api = VKAdsAPI(access_token, integration.account_id)
             try:
                 await vk_api.get_campaigns()
                 status_info["details"].append("VK Ads: OK")
             except Exception as e:
                 status_info["status"] = "failed"
                 status_info["details"].append(f"VK Ads: {str(e)}")

        elif integration.platform == models.IntegrationPlatform.AVITO_ADS:
             try:
                 avito_api = _build_avito_api_from_integration(integration)
                 await avito_api.validate_credentials(integration.account_id)
                 status_info["details"].append("Avito Ads: OK")
             except Exception as e:
                 status_info["status"] = "failed"
                 status_info["details"].append(f"Avito Ads: {str(e)}")

        # Update integration status in DB
        integration.last_sync_at = datetime.utcnow()
        if status_info["status"] == "failed":
            integration.sync_status = models.IntegrationSyncStatus.FAILED
            integration.error_message = "; ".join(status_info["details"])
            log_history_event(
                db,
                actor=current_user,
                event_type="integration",
                action="sync_failed",
                description=f"Синхронизация интеграции {integration.platform.value} завершилась с ошибкой",
                client_id=integration.client_id,
                target_type="integration",
                target_id=str(integration.id),
                meta={"details": status_info["details"]},
            )
        else:
            integration.sync_status = models.IntegrationSyncStatus.SUCCESS
            integration.error_message = None
            log_history_event(
                db,
                actor=current_user,
                event_type="integration",
                action="sync_finished",
                description=f"Синхронизация интеграции {integration.platform.value} завершена успешно",
                client_id=integration.client_id,
                target_type="integration",
                target_id=str(integration.id),
            )
            
        db.commit()
        return status_info

    except Exception as e:
        logger.error(f"Health check failed for {integration_id}: {e}")
        return {"status": "error", "message": str(e)}

@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(
    integration_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove an integration by its ID and all related data.
    This includes campaigns, statistics, keywords, groups, and goals.
    
    CRITICAL: For VK Ads integrations, attempts to revoke the access token
    before deletion to free up token slots and prevent token_limit_exceeded errors.
    """
    integration = db.query(models.Integration).join(models.Client).filter(
        models.Integration.id == integration_id,
        models.Client.owner_id == current_user.id
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    # CRITICAL: For VK Ads, revoke the token before deletion to free up token slots
    if integration.platform == models.IntegrationPlatform.VK_ADS:
        logger.info(f"🔄 Attempting to revoke VK Ads token before deleting integration {integration_id}...")
        try:
            access_token = None
            refresh_token = None
            
            # Получаем токены из интеграции (они зашифрованы)
            if integration.access_token:
                try:
                    access_token = security.decrypt_token(integration.access_token)
                except Exception as decrypt_err:
                    logger.warning(f"⚠️ Could not decrypt access_token for revocation: {decrypt_err}")
            
            if integration.refresh_token:
                try:
                    refresh_token = security.decrypt_token(integration.refresh_token)
                except Exception as decrypt_err:
                    logger.warning(f"⚠️ Could not decrypt refresh_token for revocation: {decrypt_err}")
            
            # Определяем user_id для отзыва токена
            user_id_for_revoke = integration.vk_user_id
            
            # ИСПРАВЛЕНИЕ: Если vk_user_id не установлен, пробуем использовать agency_client_login
            if not user_id_for_revoke and integration.agency_client_login:
                user_id_for_revoke = integration.agency_client_login
                logger.info(f"   vk_user_id not set, using agency_client_login for revocation: {user_id_for_revoke}")
            
            # Если все еще нет user_id, пробуем извлечь из токена
            if not user_id_for_revoke and access_token:
                try:
                    logger.info(f"   Attempting to extract user_id from access_token...")
                    async with httpx.AsyncClient() as client:
                        # Пробуем получить user info через VK Ads API
                        user_info_response = await client.get(
                            "https://ads.vk.com/api/v2/statistics/users/summary.json",
                            headers={"Authorization": f"Bearer {access_token}"},
                            timeout=10.0
                        )
                        if user_info_response.status_code == 200:
                            user_data = user_info_response.json()
                            items = user_data.get("items", [])
                            if items:
                                raw_id = items[0].get("id")
                                if raw_id:
                                    import re
                                    # Извлекаем user_id из формата "vkads_USERID@vk@..."
                                    match = re.search(r'vkads_(\d+)|@(\w+)@agency_client', str(raw_id))
                                    if match:
                                        user_id_for_revoke = match.group(1) or str(raw_id)
                                        logger.info(f"   ✅ Extracted user_id from token: {user_id_for_revoke}")
                                    else:
                                        user_id_for_revoke = str(raw_id)
                                        logger.info(f"   ✅ Using raw ID from token: {user_id_for_revoke}")
                except Exception as extract_err:
                    logger.debug(f"   Could not extract user_id from token: {extract_err}")
            
            # Пытаемся отозвать токен согласно официальной документации VK Ads API
            # POST /api/v2/oauth2/token/delete.json
            # Параметры: client_id, client_secret, username или user_id
            from backend_api.services import IntegrationService
            revoked = await IntegrationService.revoke_vk_token(
                access_token=access_token,
                refresh_token=refresh_token,
                client_id=VK_CLIENT_ID,
                client_secret=VK_CLIENT_SECRET,
                user_id=user_id_for_revoke  # VK Ads user_id/username for token revocation
            )
            
            if revoked:
                logger.info(f"✅ VK Ads token revoked successfully for integration {integration_id}")
            else:
                logger.warning(f"⚠️ Could not revoke VK Ads token for integration {integration_id}, but continuing with deletion")
                
        except Exception as revoke_err:
            # Не прерываем удаление интеграции, даже если отзыв токена не удался
            logger.error(f"❌ Error revoking VK Ads token for integration {integration_id}: {revoke_err}")
            logger.info(f"   Continuing with integration deletion despite token revocation error")
        
    # Get all campaigns for this integration to clean up related data
    campaigns = db.query(models.Campaign).filter(
        models.Campaign.integration_id == integration_id
    ).all()
    
    campaign_ids = [c.id for c in campaigns]
    campaign_names = [c.name for c in campaigns]
    client_id = integration.client_id
    
    # CRITICAL: Explicitly delete VKStats and YandexStats by campaign_id.
    # Не полагаемся на CASCADE — у пользователя могут быть проблемы с миграциями/БД.
    # Без явного удаления данные остаются и дашборд показывает некорректную статистику.
    if campaign_ids:
        deleted_vk = db.query(models.VKStats).filter(
            models.VKStats.campaign_id.in_(campaign_ids)
        ).delete(synchronize_session=False)
        deleted_yandex = db.query(models.YandexStats).filter(
            models.YandexStats.campaign_id.in_(campaign_ids)
        ).delete(synchronize_session=False)
        logger.info(f"🗑️ Deleted {deleted_vk} VKStats and {deleted_yandex} YandexStats for integration {integration_id}")
    
    # Orphan VKStats (campaign_id IS NULL) — могли остаться при старых синхронизациях.
    # Удаляем для VK-интеграций, т.к. они не участвуют в CASCADE.
    if integration.platform == models.IntegrationPlatform.VK_ADS:
        deleted_orphans = db.query(models.VKStats).filter(
            models.VKStats.client_id == client_id,
            models.VKStats.campaign_id.is_(None)
        ).delete(synchronize_session=False)
        if deleted_orphans:
            logger.info(f"🗑️ Deleted {deleted_orphans} orphan VKStats (campaign_id=NULL) for client {client_id}")
    
    # Delete statistics linked by campaign_name (no FKs)
    if campaign_names:
        deleted_keywords = db.query(models.YandexKeywords).filter(
            models.YandexKeywords.client_id == client_id,
            models.YandexKeywords.campaign_name.in_(campaign_names)
        ).delete(synchronize_session=False)
        deleted_groups = db.query(models.YandexGroups).filter(
            models.YandexGroups.client_id == client_id,
            models.YandexGroups.campaign_name.in_(campaign_names)
        ).delete(synchronize_session=False)
        logger.info(f"🗑️ Deleted {deleted_keywords} YandexKeywords and {deleted_groups} YandexGroups for integration {integration_id}")
    
    deleted_goals = db.query(models.MetrikaGoals).filter(
        models.MetrikaGoals.integration_id == integration_id
    ).delete(synchronize_session=False)
    if deleted_goals:
        logger.info(f"🗑️ Deleted {deleted_goals} MetrikaGoals for integration {integration_id}")

    # Campaigns — CASCADE при удалении integration, но статистика выше уже удалена явно.
    
    # Delete the integration (this will cascade delete campaigns and metrika_goals)
    log_history_event(
        db,
        actor=current_user,
        event_type="integration",
        action="integration_deleted",
        description=f"Удалена интеграция {integration.platform.value}",
        client_id=integration.client_id,
        target_type="integration",
        target_id=str(integration.id),
        meta={"platform": integration.platform.value},
    )
    db.delete(integration)
    db.commit()
    
    # CRITICAL: Clear dashboard cache to ensure fresh data after integration deletion
    # This prevents stale cached data from the deleted integration from appearing
    from backend_api.cache_service import CacheService
    CacheService.invalidate_client(str(integration.client_id))
    logger.info(f"🗑️ Cleared dashboard cache after deleting integration {integration_id}")
    
    logger.info(f"✅ Deleted integration {integration_id} and all related data")
    return None

async def get_agency_clients(access_token: str) -> List[dict]:
    """
    Fetch list of sub-clients from Yandex Agency Account using AgencyClients service.
    """
    url = "https://api.direct.yandex.com/json/v5/agencyclients"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept-Language": "ru"
    }
    
    # Request all clients
    payload = {
        "method": "get",
        "params": {
            "SelectionCriteria": {
                "Archived": "NO" # Only active clients
            },
            "FieldNames": ["Login", "ClientInfo", "RepresentedBy"],
            "Page": {
                "Limit": 10000 
            }
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if "result" in data and "Clients" in data["result"]:
                    return [
                        {
                            "login": c["Login"],
                            "name": c.get("ClientInfo", c["Login"]).strip() or c["Login"],
                            "fio": c.get("RepresentedBy", {}).get("Agency", ""),
                            "type": "agency_client"
                        }
                        for c in data["result"]["Clients"]
                    ]
            else:
                logger.error(f"AgencyClients Error: {response.text}")
        except Exception as e:
            logger.error(f"Failed to fetch agency clients: {e}")
            
    return []

@router.get("/yandex/agency-clients")
async def list_agency_clients(
    access_token: str, 
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Proxy endpoint to get clients from Yandex for the current token (before saving integration).
    """
    clients = await get_agency_clients(access_token)
    return clients

async def import_yandex_clients(db: Session, user_id: uuid.UUID, access_token: str, clients_to_import: List[dict]):
    """
    Core logic to import Yandex clients into the database.
    """
    imported_count = 0
    tasks = []
    for client_data in clients_to_import:
        login = client_data.get("login")
        
        # 0. Check if this client already exists for this user to avoid duplicates
        existing = db.query(models.Integration).join(models.Client).filter(
            models.Client.owner_id == user_id,
            models.Integration.platform == models.IntegrationPlatform.YANDEX_DIRECT,
            models.Integration.agency_client_login == login
        ).first()
        
        if existing:
            continue

        # 1. Create Client (Project)
        new_client = models.Client(
            owner_id=user_id,
            name=client_data.get("name") or login,
            description=f"Auto-imported from Yandex Agency (Login: {login})"
        )
        db.add(new_client)
        db.commit()
        db.refresh(new_client)
        
        # 2. Create Integration
        encrypted_access = security.encrypt_token(access_token)
        
        new_integration = models.Integration(
            client_id=new_client.id,
            platform=models.IntegrationPlatform.YANDEX_DIRECT,
            access_token=encrypted_access,
            is_agency=True,
            agency_client_login=login,
            sync_status=models.IntegrationSyncStatus.PENDING,
            last_sync_at=datetime.utcnow()
        )
        db.add(new_integration)
        db.commit()
        
        # 3. Trigger initial sync в фоне (не блокируем запрос)
        # CRITICAL: Используем run_sync_in_background, которая запускает синхронизацию
        # в отдельном потоке с новым event loop, чтобы не блокировать основной event loop FastAPI.
        run_sync_in_background(new_integration.id, 7)
        imported_count += 1
    
    # НЕ ждем завершения синхронизации - она выполняется в фоне
    return imported_count

async def run_sync_in_background_async(integration_id: uuid.UUID, days: int = 7):
    """
    Асинхронная функция для фоновой синхронизации.
    Создает отдельную сессию БД и выполняет синхронизацию без блокировки основного потока.
    """
    db = SessionLocal()
    try:
        integration = db.query(models.Integration).filter(models.Integration.id == integration_id).first()
        if integration:
            try:
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=days)
                date_from = start_date.strftime("%Y-%m-%d")
                date_to = end_date.strftime("%Y-%m-%d")
                
                logger.info(f"🔄 Background sync started for integration {integration_id} ({date_from} to {date_to})")
                await sync_integration(db, integration, date_from, date_to)
                db.commit()
                logger.info(f"✅ Background sync completed for integration {integration_id}")
            except Exception as e:
                logger.error(f"❌ Background sync failed for integration {integration_id}: {e}")
                db.rollback()
        else:
            logger.warning(f"Integration {integration_id} not found for background sync")
    finally:
        db.close()


@router.post("/batch-import")
async def batch_import_integrations(
    payload: dict = Body(...),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Import multiple clients from Yandex Agency account manually.
    """
    access_token = payload.get("access_token")
    clients_to_import = payload.get("clients", [])
    
    if not access_token or not clients_to_import:
        raise HTTPException(status_code=400, detail="Missing access_token or clients list")
        
    count = await import_yandex_clients(db, current_user.id, access_token, clients_to_import)
    return {"message": f"Successfully imported {count} projects", "count": count}
