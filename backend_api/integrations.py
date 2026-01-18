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
    
    if not auth_code or not redirect_uri:
        log_event("backend", "Failed to exchange Yandex token: missing code or redirect_uri")
        raise HTTPException(status_code=400, detail="Missing code or redirect_uri")
    
    log_event("backend", f"Exchanging Yandex code for client_name: {client_name_input}")

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
        db_client = db.query(models.Client).filter(
            models.Client.owner_id == current_user.id,
            models.Client.name == client_name
        ).first()
        
        if not db_client:
            db_client = models.Client(owner_id=current_user.id, name=client_name)
            db.add(db_client)
            db.flush()

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
    integration = db.query(models.Integration).join(models.Client).filter(
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

            # 1. Always include the personal account itself
            personal_login = integration.account_id
            if personal_login and personal_login.lower() != "unknown":
                profiles.append({"login": personal_login, "name": f"Личный аккаунт ({personal_login})"})
                seen_logins.add(personal_login.lower())

            # 2. Try to get agency clients
            agency_clients = await get_agency_clients(access_token)
            for ac in agency_clients:
                login = ac.get("login")
                if login and login.lower() not in seen_logins:
                    profiles.append(ac)
                    seen_logins.add(login.lower())

            # 3. Try to get managed logins (shared access / "Editor" role)
            try:
                direct_api = YandexDirectAPI(access_token)
                clients_info = await direct_api.get_clients()
                for c_info in clients_info:
                    managed = c_info.get("ManagedLogins", [])
                    for m_login in managed:
                        if m_login and m_login.lower() not in seen_logins:
                            profiles.append({
                                "login": m_login,
                                "name": f"Доступный аккаунт ({m_login})"
                            })
                            seen_logins.add(m_login.lower())
            except Exception as e:
                logger.error(f"Error fetching managed logins: {e}")

            # Fallback if nothing found
            if not profiles:
                display_id = integration.account_id or "Unknown"
                profiles = [{"login": display_id, "name": f"Личный аккаунт ({display_id})"}]
            
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
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetch available goals (Metrica) for this integration.
    If date_from and date_to are provided, also fetch goal statistics.
    """
    integration = db.query(models.Integration).join(models.Client).filter(
        models.Integration.id == integration_id,
        models.Client.owner_id == current_user.id
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Use the token from integration
    access_token = security.decrypt_token(integration.access_token)
    target_account = account_id or integration.account_id
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
            
        log_event("yandex", f"found {len(counters)} counters", [c.get('name') for c in counters])

        all_goals = []
        for counter in counters:
            counter_id = str(counter['id'])
            counter_name = counter.get('name', 'Unknown')
            try:
                # Use metrica_api which might be the fallback one
                goals = await metrica_api.get_counter_goals(counter_id)
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
                            models.MetrikaGoals.client_id == integration.client_id,
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
        
    log_event("backend", f"discovering campaigns for integration {integration_id}")
    access_token = security.decrypt_token(integration.access_token)
    discovered_campaigns = []
    
    if integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
        # CRITICAL: Ensure profile is selected before fetching campaigns
        client_login = integration.agency_client_login
        logger.info(f"Integration {integration_id}: agency_client_login = {client_login}, account_id = {integration.account_id}")
        
        if not client_login:
            client_login = integration.account_id
            logger.warning(f"Integration {integration_id}: No agency_client_login, falling back to account_id: {client_login}")
            
        if not client_login or client_login.lower() == "unknown":
            raise HTTPException(
                status_code=400, 
                detail="Профиль не выбран. Пожалуйста, выберите профиль на предыдущем шаге."
            )
        
        logger.info(f"Fetching campaigns for Yandex Direct integration {integration_id} with Client-Login: {client_login}")
        logger.info(f"DEBUG: Integration DB state - agency_client_login='{integration.agency_client_login}', account_id='{integration.account_id}'")
        
        # CRITICAL: Check if this is an agency account
        try:
            test_agency_clients = await get_agency_clients(access_token)
            logger.info(f"🔍 Token type check: AgencyClients API returned {len(test_agency_clients)} clients")
            if len(test_agency_clients) > 0:
                logger.info(f"   ✅ This is an AGENCY token")
                logger.info(f"   📋 Agency clients: {[c.get('login') for c in test_agency_clients[:5]]}")
            else:
                logger.warning(f"   ⚠️  This is a PERSONAL token (AgencyClients returned 0 clients)")
                logger.warning(f"   ❌ Client-Login header will be IGNORED by Yandex API!")
        except Exception as e:
            logger.warning(f"   ⚠️  Failed to check agency status: {e}")
            logger.warning(f"   This may be a PERSONAL token. Client-Login header may not work!")
        
        api = YandexDirectAPI(access_token, client_login)
        discovered_campaigns = await api.get_campaigns()
        logger.info(f"DEBUG: API returned {len(discovered_campaigns)} campaigns. First 3 IDs: {[c.get('id') for c in discovered_campaigns[:3]]}")
        logger.info(f"DEBUG: Campaign names: {[(c.get('id'), c.get('name')) for c in discovered_campaigns]}")
        log_event("yandex", f"discovered {len(discovered_campaigns)} campaigns for profile {client_login}")
    elif integration.platform == models.IntegrationPlatform.VK_ADS:
        api = VKAdsAPI(access_token, integration.account_id)
        discovered_campaigns = await api.get_campaigns()
        log_event("vk", f"discovered {len(discovered_campaigns)} campaigns")
        
    # Save to DB
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
        else:
            campaign.name = dc["name"]
            
    db.commit()
    
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
        log_event("backend", f"Auto-sync failed: {str(e)}", level="error")
    
    # Return all campaigns for this integration
    return db.query(models.Campaign).filter_by(integration_id=integration.id).all()

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
            models.YandexStats.date >= date_from,
            models.YandexStats.date <= date_to
        ).group_by(
            models.Campaign.id, models.Campaign.external_id, models.Campaign.name
        ).all()
        
        for stat in stats_query:
            campaigns_stats.append({
                "id": stat.id,
                "external_id": stat.external_id,
                "name": stat.name,
                "impressions": int(stat.impressions or 0),
                "clicks": int(stat.clicks or 0),
                "cost": float(stat.cost or 0),
                "conversions": int(stat.conversions or 0)
            })
    
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
            models.VKStats.date >= date_from,
            models.VKStats.date <= date_to
        ).group_by(
            models.Campaign.id, models.Campaign.external_id, models.Campaign.name
        ).all()
        
        for stat in stats_query:
            campaigns_stats.append({
                "id": stat.id,
                "external_id": stat.external_id,
                "name": stat.name,
                "impressions": int(stat.impressions or 0),
                "clicks": int(stat.clicks or 0),
                "cost": float(stat.cost or 0),
                "conversions": int(stat.conversions or 0)
            })
    
    # Also include campaigns without stats (newly discovered)
    all_campaigns = db.query(models.Campaign).filter_by(integration_id=integration.id).all()
    existing_ids = {cs["id"] for cs in campaigns_stats}
    
    for campaign in all_campaigns:
        if campaign.id not in existing_ids:
            campaigns_stats.append({
                "id": campaign.id,
                "external_id": campaign.external_id,
                "name": campaign.name,
                "impressions": 0,
                "clicks": 0,
                "cost": 0,
                "conversions": 0
            })
    
    log_event("backend", f"returned stats for {len(campaigns_stats)} campaigns")
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
            direct_api = YandexDirectAPI(access_token, integration.agency_client_login)
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
