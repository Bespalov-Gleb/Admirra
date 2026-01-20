from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from core.database import get_db, SessionLocal
from core import models, schemas, security
from automation.yandex_direct import YandexDirectAPI
from automation.yandex_metrica import YandexMetricaAPI
from automation.vk_ads import VKAdsAPI
from typing import List, Optional
import uuid
import httpx
import logging
import asyncio
from datetime import datetime, timedelta
import os
import json
from core.logging_utils import log_event

# Yandex Direct Credentials
YANDEX_CLIENT_ID = os.getenv("YANDEX_CLIENT_ID", "e2a052c8cac54caeb9b1b05a593be932")
YANDEX_CLIENT_SECRET = os.getenv("YANDEX_CLIENT_SECRET", "a3ff5920d00e4ee7b8a8019e33cdaaf0")
YANDEX_AUTH_URL = "https://oauth.yandex.ru/authorize"
YANDEX_TOKEN_URL = "https://oauth.yandex.ru/token"

# VK Ads Credentials (OAuth 2.0 flow)
VK_CLIENT_ID = os.getenv("VK_CLIENT_ID", "54416403")
VK_CLIENT_SECRET = os.getenv("VK_CLIENT_SECRET", "8oAosCbGdjPM3CP8HCXe")
VK_AUTH_URL = "https://ads.vk.com/oauth2/authorize"
VK_TOKEN_URL = "https://ads.vk.com/api/v2/oauth2/token.json"

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["Integrations"])

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
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all active integrations (Yandex, VK, etc.) across all clients owned by the user.
    """
    # Get all integrations for clients owned by the current user
    return db.query(models.Integration).join(models.Client).filter(
        models.Client.owner_id == current_user.id
    ).all()

@router.get("/yandex/auth-url")
def get_yandex_auth_url(redirect_uri: str):
    """
    Generate Yandex OAuth authorization URL with dynamic redirect_uri.
    Required scopes for Yandex Direct API:
    - direct:api - access to Yandex Direct API
    - metrika:read - access to Yandex Metrika (for goals)
    """
    # Yandex Direct requires specific scopes
    scope = "direct:api metrika:read"
    return {
        "url": f"{YANDEX_AUTH_URL}?response_type=code&client_id={YANDEX_CLIENT_ID}&redirect_uri={redirect_uri}&scope={scope}"
    }

@router.get("/vk/auth-url")
def get_vk_auth_url(redirect_uri: str):
    """
    Generate VK Ads OAuth authorization URL.
    """
    # Scope for VK Ads v2: ads, offline (for long-lived access)
    scope = "ads,offline"
    return {
        "url": f"{VK_AUTH_URL}?response_type=code&client_id={VK_CLIENT_ID}&redirect_uri={redirect_uri}&scope={scope}"
    }

from fastapi import BackgroundTasks

def run_sync_in_background(integration_id: uuid.UUID, days: int = 7):
    # Create a new session for the background task
    db = SessionLocal()
    try:
        integration = db.query(models.Integration).filter(models.Integration.id == integration_id).first()
        if integration:
            try:
                # We need to run the async sync function in a sync context or use asyncio.run
                # Since we are in a background task (which runs in a thread pool), we can use asyncio.run
                end = datetime.now().date()
                start = end - timedelta(days=days)
                asyncio.run(sync_integration(db, integration, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
                db.commit()
            except Exception as e:
                logger.error(f"Background sync failed for {integration_id}: {e}")
    finally:
        db.close()

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
    auth_code = payload.get("code")
    redirect_uri = payload.get("redirect_uri") # Must match the one used in auth-url
    client_name_input = payload.get("client_name")
    client_id_input = payload.get("client_id")  # NEW: If provided, link to existing client
    
    if not auth_code or not redirect_uri:
        log_event("backend", "Failed to exchange Yandex token: missing code or redirect_uri")
        raise HTTPException(status_code=400, detail="Missing code or redirect_uri")
    
    log_event("backend", f"Exchanging Yandex code for client_name: {client_name_input}, client_id: {client_id_input}")

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
             client_name = f"Yandex Direct ({yandex_login})"
        else:
             client_name = "Yandex Direct Main"
        
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
            models.Integration.platform == models.IntegrationPlatform.YANDEX_DIRECT
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
            db_integration = models.Integration(
                client_id=client.id,
                platform=models.IntegrationPlatform.YANDEX_DIRECT,
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
    payload: dict, # Expecting {"code": "...", "redirect_uri": "...", "client_name": "..."}
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Exchange authorization code for VK Ads access token.
    """
    auth_code = payload.get("code")
    redirect_uri = payload.get("redirect_uri")
    client_name_input = payload.get("client_name")
    client_id_input = payload.get("client_id")  # NEW: If provided, link to existing client
    
    if not auth_code or not redirect_uri:
        raise HTTPException(status_code=400, detail="Authorization code and redirect_uri are required")

    async with httpx.AsyncClient() as client:
        response = await client.post(VK_TOKEN_URL, data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": VK_CLIENT_ID,
            "client_secret": VK_CLIENT_SECRET,
            "redirect_uri": redirect_uri
        })
        
        if response.status_code != 200:
            logger.error(f"VK Token Exchange Failed: {response.text}")
            raise HTTPException(status_code=400, detail="Failed to exchange token with VK Ads")
            
        token_data = response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        
        # Try to auto-detect Account ID (Cabinet)
        vk_account_id = None
        try:
            acc_response = await client.get(
                "https://ads.vk.com/api/v2/ad_accounts.json", 
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if acc_response.status_code == 200:
                acc_data = acc_response.json()
                items = acc_data.get("items", [])
                if items:
                    vk_account_id = str(items[0].get("id"))
                    logger.info(f"Auto-detected VK Account ID: {vk_account_id}")
        except Exception as e:
            logger.error(f"Failed to auto-detect VK Account ID: {e}")

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
                db_client = models.Client(owner_id=current_user.id, name=client_name)
                db.add(db_client)
                db.flush()
                logger.info(f"Created new client: {db_client.name} (ID: {db_client.id})")

        # Save Integration
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
            db_integration.sync_status = models.IntegrationSyncStatus.NEVER
        else:
            db_integration = models.Integration(
                client_id=db_client.id,
                platform=models.IntegrationPlatform.VK_ADS,
                access_token=encrypted_access,
                refresh_token=encrypted_refresh,
                account_id=vk_account_id,
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
        db.commit()
        db.refresh(db_integration)
        return db_integration

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
    """
    days = request_data.days if request_data else 7
    integration = db.query(models.Integration).join(models.Client).filter(
        models.Integration.id == integration_id,
        models.Client.owner_id == current_user.id
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
        
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    date_from = start_date.strftime("%Y-%m-%d")
    date_to = end_date.strftime("%Y-%m-%d")

    try:
        await sync_integration(db, integration, date_from, date_to)
        db.commit()
        return {"status": "success", "message": f"Synced last {days} days"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

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
            try:
                direct_api = YandexDirectAPI(access_token)
                clients_info = await direct_api.get_clients()
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
                profiles.append({"login": personal_login, "name": f"Личный аккаунт ({personal_login})"})
                seen_logins.add(personal_login.lower())
                logger.info(f"✅ Added personal profile: {personal_login}")

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
            try:
                direct_api = YandexDirectAPI(access_token)
                clients_info = await direct_api.get_clients()
                for c_info in clients_info:
                    # Get logins where this user has management access
                    managed = c_info.get("ManagedLogins", [])
                    for m_login in managed:
                        if m_login and m_login.lower() not in seen_logins:
                            profiles.append({
                                "login": m_login,
                                "name": f"Доступный аккаунт ({m_login})"
                            })
                            seen_logins.add(m_login.lower())
                            logger.info(f"Added managed login: {m_login}")
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
    
    log_event("get_integration_profiles", f"No specific profile fetching logic for platform {integration.platform}", level="info")
    return [] # Return empty list for other platforms or if no specific logic

@router.get("/{integration_id}/goals")
async def get_integration_goals(
    integration_id: uuid.UUID,
    account_id: Optional[str] = None,
    campaign_ids: Optional[str] = None,  # Comma-separated list of campaign IDs
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
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
    
    # CRITICAL: If campaign_ids provided, get goals from campaigns, not from profile
    if campaign_ids:
        campaign_ids_list = [cid.strip() for cid in campaign_ids.split(',') if cid.strip()]
        logger.info(f"📊 Getting goals for {len(campaign_ids_list)} selected campaigns: {campaign_ids_list}")
        
        if integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
            # CRITICAL: campaign_ids from frontend are UUIDs from DB, not external_id
            # We need to get external_id (numeric) from DB to query Yandex API
            campaigns_from_db = db.query(models.Campaign).filter(
                models.Campaign.integration_id == integration_id,
                models.Campaign.id.in_([uuid.UUID(cid) for cid in campaign_ids_list if len(cid) == 36])
            ).all()
            
            # Get external_ids (numeric IDs from Yandex Direct)
            external_ids = [str(c.external_id) for c in campaigns_from_db if c.external_id and str(c.external_id).isdigit()]
            logger.info(f"📊 Converted {len(campaign_ids_list)} UUIDs to {len(external_ids)} external_ids: {external_ids}")
            
            if external_ids:
                from automation.yandex_direct import YandexDirectAPI
                direct_api = YandexDirectAPI(access_token, client_login=target_account)
                
                # Try to get PriorityGoals from campaigns (works only for Direct Pro)
                # NOTE: This will return empty due to API limitations, triggering fallback
                campaign_goals_map = await direct_api.get_campaign_goals(external_ids)
            
            if campaign_goals_map:
                # Successfully got goals from campaigns - collect unique goal IDs
                all_goal_ids = set()
                for campaign_id, goals in campaign_goals_map.items():
                    for goal in goals:
                        all_goal_ids.add(goal["goal_id"])
                
                logger.info(f"📊 Found {len(all_goal_ids)} unique goal IDs from campaigns: {all_goal_ids}")
                
                # Now get full goal details from Metrika API
                # We need to find which counters contain these goals
                from automation.yandex_metrica import YandexMetricaAPI
                metrica_api = YandexMetricaAPI(access_token, client_login=target_account)
                
                try:
                    counters = await metrica_api.get_counters()
                    # Filter counters by profile (same logic as before)
                    if target_account:
                        def normalize_login(login: str) -> str:
                            if not login:
                                return ""
                            normalized = login.lower().strip()
                            normalized = normalized.replace('.', '').replace('-', '').replace('_', '')
                            return normalized
                        
                        target_normalized = normalize_login(target_account)
                        filtered_counters = []
                        for counter in counters:
                            owner_login = counter.get('owner_login', '')
                            owner_normalized = normalize_login(owner_login)
                            if (owner_login.lower() == target_account.lower() or
                                owner_normalized == target_normalized):
                                filtered_counters.append(counter)
                        counters = filtered_counters
                    
                    # Get goals from counters and filter by goal IDs from campaigns
                    all_goals = []
                    for counter in counters:
                        counter_id = str(counter['id'])
                        counter_name = counter.get('name', 'Unknown')
                        try:
                            goals = await metrica_api.get_counter_goals(counter_id)
                            for goal in goals:
                                goal_id = str(goal['id'])
                                # Only include goals that are used in selected campaigns
                                if goal_id in all_goal_ids:
                                    goal_data = {
                                        "id": goal_id,
                                        "name": f"{goal['name']} ({counter_name})",
                                        "type": goal.get('type', 'Unknown'),
                                        "counter_id": counter_id,
                                        "conversions": 0,
                                        "conversion_rate": 0.0
                                    }
                                    
                                    # Get stats if date range provided
                                    if date_from and date_to:
                                        from sqlalchemy import func
                                        stats = db.query(
                                            func.sum(models.MetrikaGoals.conversion_count).label('total_conversions')
                                        ).filter(
                                            models.MetrikaGoals.goal_id == goal_id,
                                            models.MetrikaGoals.integration_id == integration_id,
                                            models.MetrikaGoals.date >= date_from,
                                            models.MetrikaGoals.date <= date_to
                                        ).first()
                                        
                                        if stats and stats.total_conversions:
                                            goal_data["conversions"] = int(stats.total_conversions)
                                            
                                            total_clicks = db.query(
                                                func.sum(models.YandexStats.clicks)
                                            ).join(
                                                models.Campaign
                                            ).filter(
                                                models.Campaign.integration_id == integration_id,
                                                models.Campaign.external_id.in_(campaign_ids_list),
                                                models.YandexStats.date >= date_from,
                                                models.YandexStats.date <= date_to
                                            ).scalar() or 0
                                            
                                            if total_clicks > 0:
                                                goal_data["conversion_rate"] = round((goal_data["conversions"] / total_clicks) * 100, 2)
                                    
                                    all_goals.append(goal_data)
                        except Exception as goals_err:
                            logger.error(f"Failed to fetch goals for counter {counter_id}: {goals_err}")
                    
                    logger.info(f"✅ Returning {len(all_goals)} goals from {len(campaign_ids_list)} selected campaigns")
                    return all_goals
                except Exception as e:
                    logger.error(f"Error fetching goals from Metrika: {e}")
                    # Fall through to fallback method
            
            # FALLBACK: If Direct Pro not available or no PriorityGoals found
            # Get all goals from profile's counters (works for accounts without Direct Pro)
            logger.info(f"⚠️ Direct Pro not available or no PriorityGoals. Using fallback: getting all goals from profile")
            # Continue with existing profile-based logic below
    
    # LEGACY PATH: If no campaign_ids provided, use profile-based goal fetching
    # This maintains backward compatibility
    logger.info(f"📊 Getting goals from profile (campaign_ids not provided or fallback used)")
    logger.info(f"Fetching goals for integration {integration_id}, target_account: {target_account} (query account_id={account_id}, integration.agency_client_login={integration.agency_client_login}, integration.account_id={integration.account_id})")
    
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
                    logger.info(f"📊 Got actual login format from Direct API: '{actual_login}' (was: '{target_account}')")
        except Exception as e:
            logger.warning(f"Could not get actual login format from Direct API: {e}, using target_account as-is")
    
    # IMPORTANT: Pass client_login to filter Metrika counters by the selected profile
    # This is needed when one Yandex account has access to multiple advertising profiles
    metrica_api = YandexMetricaAPI(access_token, client_login=target_account)
    
    try:
        log_event("yandex", f"fetching goals for integration {integration_id}, account: {target_account}")
        
        # Robust goal fetching with fallback
        try:
            counters = await metrica_api.get_counters()
        except Exception as api_err:
            logger.warning(f"Metrica counters fetch failed for {target_account}: {api_err}. Trying wildcard fetch.")
            # Fallback: try without login parameter
            fallback_api = YandexMetricaAPI(access_token) # No login
            try:
                counters = await fallback_api.get_counters()
                metrica_api = fallback_api # Use successful API for subsequent calls
            except Exception as fallback_err:
                logger.error(f"Fallback Metrica fetch also failed: {fallback_err}")
                return []

        if not counters:
            log_event("yandex", "No Metrica counters found or access denied")
            return []
            
        log_event("yandex", f"found {len(counters)} counters (before filtering)", [c.get('name') for c in counters])
        logger.info(f"📊 Found {len(counters)} counters before filtering for profile '{target_account}'")
        
        # CRITICAL: Filter counters by the selected profile (target_account)
        # One Yandex account can have access to counters from multiple advertising profiles
        # We need to show only counters that belong to the selected profile
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
            logger.info(f"📊 Comparing with target_account='{target_account}' (normalized: '{target_normalized}') and metrika_owner_login='{metrika_owner_login}' (normalized: '{metrika_normalized}')")
            
            # Try to filter by owner_login matching the selected profile
            filtered_counters = []
            excluded_counters = []
            
            for counter in counters:
                owner_login = counter.get('owner_login', '')
                owner_normalized = normalize_login(owner_login)
                counter_name = counter.get('name', 'Unknown')
                counter_id = counter.get('id', 'N/A')
                
                # Try multiple matching strategies:
                # 1. Exact match with target_account (case-insensitive)
                # 2. Exact match with metrika_owner_login (case-insensitive)
                # 3. Normalized match (without separators)
                # 4. Partial match (one contains the other)
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
                    logger.info(f"  ✅ Included counter '{counter_name}' (ID: {counter_id}, owner: {owner_login}, normalized: {owner_normalized})")
                else:
                    excluded_counters.append(f"{counter_name} (owner: {owner_login})")
                    logger.info(f"  ❌ Excluded counter '{counter_name}' (ID: {counter_id}, owner: {owner_login}, normalized: {owner_normalized}, expected: {target_account}, normalized: {target_normalized})")
            
            # CRITICAL: Only use filtered counters if we found matches
            # If no matches, it means either:
            # 1. The profile doesn't have its own counters (uses delegate access)
            # 2. The owner_login doesn't match (different account structure)
            # In this case, we should NOT show all counters - they belong to other profiles!
            if filtered_counters:
                counters = filtered_counters
                logger.info(f"✅ Filtered to {len(counters)} counters for profile '{target_account}' (excluded {len(excluded_counters)} counters from other profiles)")
            else:
                logger.warning(f"⚠️ No counters with owner_login='{target_account}'. This profile may not have its own Metrika counters.")
                logger.warning(f"⚠️ Excluded {len(excluded_counters)} counters from other profiles: {excluded_counters[:5]}")
                # CRITICAL: Return empty list instead of showing all counters
                # This prevents showing metrics from other profiles
                counters = []
                logger.info(f"📊 Returning 0 counters (strict filtering by profile)")
        
        log_event("yandex", f"found {len(counters)} counters (after filtering)", [c.get('name') for c in counters])
        logger.info(f"📊 Returning {len(counters)} counters after filtering for profile '{target_account}'")

        all_goals = []
        for counter in counters:
            counter_id = str(counter['id'])
            counter_name = counter.get('name', 'Unknown')
            owner_login = counter.get('owner_login', 'N/A')
            
            # CRITICAL: Double-check that counter belongs to selected profile
            # Use the same normalization logic as in filtering above
            if target_account:
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
                # Use metrica_api which might be the fallback one
                goals = await metrica_api.get_counter_goals(counter_id)
                logger.info(f"📊 Counter '{counter_name}' (ID: {counter_id}, owner: {owner_login}) has {len(goals)} goals")
                log_event("yandex", f"counter {counter_id} ({counter_name}) has {len(goals)} goals")
                for goal in goals:
                    goal_data = {
                        "id": str(goal['id']),
                        "name": f"{goal['name']} ({counter_name})",
                        "type": goal.get('type', 'Unknown'),
                        "counter_id": counter_id,
                        "conversions": 0,
                        "conversion_rate": 0.0
                    }
                    
                    # If date range provided, fetch stats from DB
                    if date_from and date_to:
                        from sqlalchemy import func
                        stats = db.query(
                            func.sum(models.MetrikaGoals.conversion_count).label('total_conversions')
                        ).filter(
                            models.MetrikaGoals.goal_id == str(goal['id']),
                            models.MetrikaGoals.integration_id == integration_id,  # CRITICAL: Filter by integration, not client
                            models.MetrikaGoals.date >= date_from,
                            models.MetrikaGoals.date <= date_to
                        ).first()
                        
                        if stats and stats.total_conversions:
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
    
    for key, value in integration_in.items():
        if hasattr(integration, key):
            # Special handling for JSON fields if they come as lists/dicts
            if key == 'selected_goals' and (isinstance(value, list) or isinstance(value, dict)):
                value = json.dumps(value)
            setattr(integration, key, value)
            logger.info(f"Set {key} = {value}")
    
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
    db.commit()
    db.refresh(integration)
    
    # Verify the value was actually saved
    logger.info(f"After commit and refresh: agency_client_login={integration.agency_client_login}, account_id={integration.account_id}")
    
    return integration

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
    
    # CRITICAL: Refresh integration from DB to ensure we have the latest agency_client_login
    # This is important because the profile might have been updated just before this call
    db.refresh(integration)
    
    # DEBUG: Log current state of integration
    logger.info(f"🔵 discover_campaigns: integration {integration_id} state:")
    logger.info(f"   account_id: '{integration.account_id}'")
    logger.info(f"   agency_client_login: '{integration.agency_client_login}'")
    logger.info(f"   platform: {integration.platform}")
    
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
        # Each token = 1 Yandex account (email), but не каждый аккаунт имеет Яндекс.Директ
        # CRITICAL: Use selected profile (agency_client_login takes priority over account_id)
        # This ensures we only get campaigns from the selected profile, not all accessible profiles
        # agency_client_login is set when user selects a profile on step 2
        # CRITICAL: Determine which profile to use and whether to pass Client-Login
        # agency_client_login is set when user selects a profile on step 2
        # If not set, we need to determine the personal account login
        selected_profile = integration.agency_client_login if integration.agency_client_login and integration.agency_client_login.lower() != "unknown" else None
        
        # Get personal account login to compare
        personal_advertising_login = None
        if not selected_profile:
            # No profile selected, try to get personal account login
            try:
                temp_api = YandexDirectAPI(access_token)
                clients_info = await temp_api.get_clients()
                if clients_info:
                    personal_advertising_login = clients_info[0].get("Login")
                    selected_profile = personal_advertising_login
                    logger.info(f"Using personal advertising account login: {personal_advertising_login}")
            except Exception as e:
                logger.warning(f"Could not determine personal advertising login: {e}")
                selected_profile = integration.account_id
        
        # IMPORTANT: Only pass Client-Login if agency_client_login is explicitly set
        # This means user selected a specific profile (not the default personal account)
        use_client_login = None
        if integration.agency_client_login and integration.agency_client_login.lower() != "unknown":
            # User explicitly selected a profile - use Client-Login to filter by that profile
            use_client_login = integration.agency_client_login
            logger.info(f"Using Client-Login={use_client_login} (user selected profile: {integration.agency_client_login})")
        else:
            # No profile explicitly selected - don't use Client-Login (will return campaigns for token owner)
            logger.info(f"Not using Client-Login (no profile explicitly selected, agency_client_login={integration.agency_client_login})")
        
        logger.info(f"Fetching campaigns for integration {integration_id}, selected_profile={selected_profile}, agency_client_login={integration.agency_client_login}, using Client-Login={use_client_login}")
        
        # Pass client_login to filter campaigns by selected profile
        # If no profile selected or it's the personal account, API will return campaigns for the token owner
        api = YandexDirectAPI(access_token, client_login=use_client_login)
        try:
            discovered_campaigns = await api.get_campaigns()
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
        
        logger.info(f"🔵 API returned {len(discovered_campaigns)} campaigns from Yandex Direct API")
        logger.info(f"🔵 Using Client-Login: '{use_client_login}'")
        logger.info(f"🔵 Integration agency_client_login: '{integration.agency_client_login}'")
        logger.info(f"🔵 Integration account_id: '{integration.account_id}'")
        logger.info(f"🔵 Campaign names from API: {[c.get('name') for c in discovered_campaigns]}")
        logger.info(f"🔵 Campaign IDs from API: {[c.get('id') for c in discovered_campaigns]}")
        logger.info(f"🔵 Campaign states from API: {[c.get('state', 'N/A') for c in discovered_campaigns]}")
        
        # Check for specific campaigns
        campaign_names_lower = [c.get('name', '').lower() for c in discovered_campaigns]
        if any('кси' in name or 'ksi' in name for name in campaign_names_lower):
            logger.info(f"✅ Found 'кси' campaign in API response!")
        else:
            logger.warning(f"❌ 'кси' campaign NOT found in API response!")
            logger.warning(f"❌ Expected 3 campaigns for profile '{use_client_login}', but got {len(discovered_campaigns)}")
            logger.warning(f"❌ This might indicate that Client-Login header is not filtering correctly")
        
        log_event("yandex", f"discovered {len(discovered_campaigns)} campaigns")
    elif integration.platform == models.IntegrationPlatform.VK_ADS:
        api = VKAdsAPI(access_token, integration.account_id)
        discovered_campaigns = await api.get_campaigns()
        log_event("vk", f"discovered {len(discovered_campaigns)} campaigns")
        
    # Save to DB
    logger.info(f"💾 Saving {len(discovered_campaigns)} campaigns to database for integration {integration_id}")
    saved_count = 0
    updated_count = 0
    for dc in discovered_campaigns:
        campaign = db.query(models.Campaign).filter_by(
            integration_id=integration.id,
            external_id=str(dc["id"])
        ).first()
        
        if not campaign:
            campaign = models.Campaign(
                integration_id=integration.id,
                external_id=str(dc["id"]),
                name=dc["name"],
                is_active=False # Discovery creates them as inactive by default
            )
            db.add(campaign)
            saved_count += 1
            logger.info(f"   💾 Created new campaign: ID={dc['id']}, Name='{dc['name']}'")
        else:
            campaign.name = dc["name"]
            updated_count += 1
            logger.info(f"   💾 Updated existing campaign: ID={dc['id']}, Name='{dc['name']}'")
            
    db.commit()
    logger.info(f"💾 Saved {saved_count} new campaigns, updated {updated_count} existing campaigns")
    
    # CRITICAL: Clean up campaigns from other profiles if profile is selected
    # Delete campaigns that weren't returned by API (they belong to other profiles)
    if integration.agency_client_login and integration.agency_client_login.lower() != "unknown":
        discovered_external_ids = {str(dc["id"]) for dc in discovered_campaigns}
        all_db_campaigns = db.query(models.Campaign).filter_by(integration_id=integration.id).all()
        
        deleted_count = 0
        for db_campaign in all_db_campaigns:
            if str(db_campaign.external_id) not in discovered_external_ids:
                logger.warning(f"🗑️ Deleting campaign '{db_campaign.name}' (ID: {db_campaign.external_id}) - not in API response for profile {integration.agency_client_login}")
                db.delete(db_campaign)
                deleted_count += 1
        
        if deleted_count > 0:
            db.commit()
            logger.info(f"🗑️ Deleted {deleted_count} campaigns from other profiles")
    
    # IMPORTANT: After discovering campaigns, immediately sync stats for last 7 days
    # so user can see real data in the wizard
    from datetime import datetime, timedelta
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        date_from = start_date.strftime("%Y-%m-%d")
        date_to = end_date.strftime("%Y-%m-%d")
        
        logger.info(f"🔄 Auto-syncing stats for integration {integration_id} ({date_from} to {date_to})")
        await sync_integration(db, integration, date_from, date_to)
        logger.info(f"✅ Auto-sync completed for integration {integration_id}")
    except Exception as e:
        # Don't fail the whole request if sync fails - user can retry later
        logger.error(f"❌ Auto-sync failed for integration {integration_id}: {e}")
        log_event("backend", f"Auto-sync failed: {str(e)}")
    
    # Return all campaigns for this integration as dictionaries
    # CRITICAL: Use discovered_campaigns data (from API) to get state and type
    # Create a map of external_id -> campaign data from API
    discovered_map = {str(dc["id"]): dc for dc in discovered_campaigns}
    
    # Filter out template/test campaigns (like "CampaignName", "Test Campaign", etc.)
    all_campaigns = db.query(models.Campaign).filter_by(integration_id=integration.id).all()
    
    # Filter out template campaigns and campaigns from other profiles
    template_names = ["campaignname", "test campaign", "тест", "test", "шаблон", "template"]
    filtered_campaigns = []
    for campaign in all_campaigns:
        campaign_name_lower = campaign.name.lower().strip()
        # Skip if name is a template/test name
        if campaign_name_lower in template_names or campaign_name_lower == "campaignname":
            logger.info(f"   ⏭️ Skipping template campaign: ID={campaign.external_id}, Name='{campaign.name}'")
            continue
        
        # CRITICAL: Filter out campaigns that don't match the selected profile
        # If external_id is not numeric (like "CampaignId"), it's invalid
        if not campaign.external_id or not str(campaign.external_id).isdigit():
            logger.info(f"   ⏭️ Skipping invalid campaign ID: ID={campaign.external_id}, Name='{campaign.name}'")
            continue
        
        # Get state from discovered_campaigns (API data)
        api_campaign = discovered_map.get(str(campaign.external_id))
        
        # Build campaign dict with data from API if available
        # Map state values to match frontend expectations
        campaign_state = api_campaign.get("state", "UNKNOWN") if api_campaign else "UNKNOWN"
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
            "status": api_campaign.get("status", "UNKNOWN") if api_campaign else "UNKNOWN",
            "state": campaign_state,  # Mapped state for frontend filtering
            "type": campaign_type  # Campaign type for filtering
        }
        
        filtered_campaigns.append(campaign_dict)
    
    logger.info(f"✅ Returning {len(filtered_campaigns)} campaigns (filtered out {len(all_campaigns) - len(filtered_campaigns)} template/archived campaigns)")
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
    
    # Also include campaigns without stats (newly discovered)
    # CRITICAL: Filter out campaigns that don't belong to this profile
    # Get list of valid campaign IDs from the most recent discover-campaigns call
    all_campaigns = db.query(models.Campaign).filter_by(integration_id=integration.id).all()
    logger.info(f"📋 Total campaigns in DB for this integration: {len(all_campaigns)}")
    
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
            stats_count = db.query(models.YandexStats).filter(
                models.YandexStats.campaign_id == campaign.id
            ).count()
            stats_in_range = db.query(models.YandexStats).filter(
                models.YandexStats.campaign_id == campaign.id,
                models.YandexStats.date >= date_from_obj,
                models.YandexStats.date <= date_to_obj
            ).count()
            logger.info(f"   Campaign '{campaign.name}' (ID: {campaign_id_str}): has {stats_count} total YandexStats records, {stats_in_range} in date range {date_from_obj} to {date_to_obj}")
            
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

        # Update integration status in DB
        integration.last_sync_at = datetime.utcnow()
        if status_info["status"] == "failed":
            integration.sync_status = models.IntegrationSyncStatus.FAILED
            integration.error_message = "; ".join(status_info["details"])
        else:
            integration.sync_status = models.IntegrationSyncStatus.SUCCESS
            integration.error_message = None
            
        db.commit()
        return status_info

    except Exception as e:
        logger.error(f"Health check failed for {integration_id}: {e}")
        return {"status": "error", "message": str(e)}

@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_integration(
    integration_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove an integration by its ID.
    """
    integration = db.query(models.Integration).join(models.Client).filter(
        models.Integration.id == integration_id,
        models.Client.owner_id == current_user.id
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
        
    db.delete(integration)
    db.commit()
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
                            "name": f"{c['ClientInfo']} ({c['Login']})",
                            "fio": c.get("RepresentedBy", {}).get("Agency", "")
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
        
        # 3. Trigger initial sync
        tasks.append(run_sync_in_background_async(new_integration.id))
        imported_count += 1
    
    if tasks:
        await asyncio.gather(*tasks)
    return imported_count

async def run_sync_in_background_async(integration_id: uuid.UUID):
    # Helper to run sync without needing background_tasks object
    # In a real app we'd use Celery, here we just use asyncio.create_task
    db = SessionLocal()
    try:
        integration = db.query(models.Integration).filter(models.Integration.id == integration_id).first()
        if integration:
            end = datetime.now().date()
            start = end - timedelta(days=7)
            await sync_integration(db, integration, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
            db.commit()
    except Exception as e:
        logger.error(f"Async bg sync failed for {integration_id}: {e}")
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
