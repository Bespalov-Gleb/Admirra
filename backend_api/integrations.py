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
    
    if integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
        # Priority 1: Get counters from selected campaigns via CounterIds
        if campaign_ids:
            campaign_ids_list = [cid.strip() for cid in campaign_ids.split(',') if cid.strip()]
            
            campaigns_from_db = db.query(models.Campaign).filter(
                models.Campaign.integration_id == integration_id,
                models.Campaign.id.in_([uuid.UUID(cid) for cid in campaign_ids_list if len(cid) == 36])
            ).all()
            
            external_ids = [str(c.external_id) for c in campaigns_from_db if c.external_id and str(c.external_id).isdigit()]
            
            if external_ids:
                from automation.yandex_direct import YandexDirectAPI
                direct_api = YandexDirectAPI(access_token, client_login=target_account)
                
                campaign_counters_map = await direct_api.get_campaign_counters(external_ids)
                
                # Collect all unique counter IDs
                # CRITICAL: Use different variable name to avoid overwriting counters_list
                all_counter_ids = set()
                for counter_ids_from_campaign in campaign_counters_map.values():
                    for cid in counter_ids_from_campaign:
                        all_counter_ids.add(str(cid))
                
                if all_counter_ids:
                    # Fetch counter details from Metrika API
                    from automation.yandex_metrica import YandexMetricaAPI
                    metrica_api = YandexMetricaAPI(access_token)
                    
                    # Get all accessible counters to match with IDs
                    try:
                        all_counters = await metrica_api.get_counters()
                        
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
                        
                        logger.info(f"📊 Found {len(counters_list)} counters from {len(all_counter_ids)} CounterIds for campaigns")
                    except Exception as e:
                        logger.error(f"Failed to fetch counter details from Metrika: {e}")
        
        # Priority 2: Fallback to profile-based counters
        if not counters_list and target_account:
            from automation.yandex_metrica import YandexMetricaAPI
            metrica_api = YandexMetricaAPI(access_token, client_login=target_account)
            
            try:
                counters = await metrica_api.get_counters()
                
                # Filter by owner_login if possible
                for counter in counters:
                    owner_login = counter.get('owner_login', '')
                    # Normalize for comparison
                    def normalize_login(login):
                        return login.lower().replace('.', '').replace('-', '') if login else ''
                    
                    if normalize_login(owner_login) == normalize_login(target_account) or not owner_login:
                        counters_list.append({
                            "id": str(counter.get('id')),
                            "name": counter.get('name', 'Unknown'),
                            "site": counter.get('site', ''),
                            "owner_login": owner_login,
                            "source": "profile"  # Indicates this counter came from profile
                        })
            except Exception as e:
                logger.error(f"Failed to fetch profile counters: {e}")
                # If 403, try without profile filter
                if "403" in str(e) or "access_denied" in str(e).lower():
                    try:
                        fallback_api = YandexMetricaAPI(access_token)
                        counters = await fallback_api.get_counters()
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
        
        if integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
            from automation.yandex_metrica import YandexMetricaAPI
            metrica_api = YandexMetricaAPI(access_token)
            
            all_goals = []
            from sqlalchemy import func
            
            for counter_id in counter_ids_list:
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
                    
                    if include_stats:
                        # Try DB first
                        db_goal = db.query(models.MetrikaGoals).filter(
                            models.MetrikaGoals.integration_id == integration_id,
                            models.MetrikaGoals.goal_id == goal_id,
                            models.MetrikaGoals.date >= datetime.strptime(date_from, "%Y-%m-%d").date(),
                            models.MetrikaGoals.date <= datetime.strptime(date_to, "%Y-%m-%d").date()
                        ).first()
                        
                        if db_goal:
                            goal_data["conversions"] = int(db_goal.conversion_count or 0)
                            goal_data["conversion_rate"] = float(db_goal.conversion_rate or 0.0)
                        else:
                            # Fallback to API
                            try:
                                stats = await metrica_api.get_goals_stats(
                                    counter_id, date_from, date_to,
                                    metrics="ym:s:anyGoalConversionRate,ym:s:sumGoalReachesAny"
                                )
                                if stats and len(stats) > 0:
                                    total_reaches = sum(row.get('metrics', [0, 0])[1] for row in stats)
                                    total_cr = sum(row.get('metrics', [0, 0])[0] for row in stats)
                                    avg_cr = total_cr / len(stats) if stats else 0.0
                                    goal_data["conversions"] = int(total_reaches)
                                    goal_data["conversion_rate"] = float(avg_cr)
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
                                        goal_metric = f"ym:s:goal{goal_id}reaches"
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
                                            goal_metric = f"ym:s:goal{goal_id}reaches"
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
                                                goal_metric = f"ym:s:goal{goal_id}reaches"
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
                                # Get goal stats directly from Metrika API
                                goal_metric = f"ym:s:goal{goal['id']}reaches"
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
    
    # 1. Обновляем поля самой интеграции
    for key, value in integration_in.items():
        if hasattr(integration, key):
            # Special handling for JSON fields if they come as lists/dicts
            if key == 'selected_goals' and (isinstance(value, list) or isinstance(value, dict)):
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
    db.commit()
    db.refresh(integration)
    
    # Verify the value was actually saved
    logger.info(f"After commit and refresh: agency_client_login={integration.agency_client_login}, account_id={integration.account_id}")
    
    # OPTIMIZATION: Sync statistics only when integration is finalized (is_active=True)
    # This happens on step 6 (summary) when user completes the integration wizard
    if integration_in.get("is_active") is True:
        from datetime import datetime, timedelta
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)  # Sync last 30 days
            date_from = start_date.strftime("%Y-%m-%d")
            date_to = end_date.strftime("%Y-%m-%d")
            
            logger.info(f"🔄 Finalizing integration {integration_id}: syncing stats ({date_from} to {date_to})")
            await sync_integration(db, integration, date_from, date_to)
            db.commit()
            logger.info(f"✅ Statistics synced for finalized integration {integration_id}")
        except Exception as e:
            # Don't fail the whole request if sync fails - user can retry later
            logger.error(f"❌ Statistics sync failed for finalized integration {integration_id}: {e}")
            log_event("backend", f"Statistics sync failed: {str(e)}")
    
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
        # Каждая интеграция ДОЛЖНА быть привязана к одному конкретному профилю Яндекс.Директа.
        # В UI пользователь выбирает профиль на шаге 2, и его логин мы храним в integration.account_id.
        # Здесь не угадываем «личный» логин и не используем устаревший agency_client_login —
        # всегда работаем строго через account_id.
        selected_profile = integration.account_id if integration.account_id and integration.account_id.lower() != "unknown" else None
        if not selected_profile:
            logger.error(f"❌ discover_campaigns: integration {integration_id} has no account_id (profile login). Cannot fetch campaigns correctly.")
            raise HTTPException(status_code=400, detail="Для интеграции не задан логин рекламного профиля (account_id). Пере настройте интеграцию.")
        
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
    
    # OPTIMIZATION: Statistics sync removed from discover_campaigns
    # Statistics will be synced only when integration is finalized (on step 6)
    
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
    Remove an integration by its ID and all related data.
    This includes campaigns, statistics, keywords, groups, and goals.
    """
    integration = db.query(models.Integration).join(models.Client).filter(
        models.Integration.id == integration_id,
        models.Client.owner_id == current_user.id
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
        
    # Get all campaigns for this integration to clean up related data
    campaigns = db.query(models.Campaign).filter(
        models.Campaign.integration_id == integration_id
    ).all()
    
    campaign_names = [campaign.name for campaign in campaigns]
    client_id = integration.client_id
    
    # Delete statistics and related data that are linked by campaign_name
    # (These don't have foreign keys, so CASCADE won't work)
    if campaign_names:
        # Delete YandexKeywords by campaign_name
        deleted_keywords = db.query(models.YandexKeywords).filter(
            models.YandexKeywords.client_id == client_id,
            models.YandexKeywords.campaign_name.in_(campaign_names)
        ).delete(synchronize_session=False)
        
        # Delete YandexGroups by campaign_name
        deleted_groups = db.query(models.YandexGroups).filter(
            models.YandexGroups.client_id == client_id,
            models.YandexGroups.campaign_name.in_(campaign_names)
        ).delete(synchronize_session=False)
        
        logger.info(f"🗑️ Deleted {deleted_keywords} YandexKeywords and {deleted_groups} YandexGroups for integration {integration_id}")
    
    # MetrikaGoals will be deleted automatically via CASCADE (has foreign key)
    # Campaigns will be deleted automatically via CASCADE (has foreign key)
    # YandexStats and VKStats will be deleted automatically via CASCADE when campaigns are deleted
    
    # Delete the integration (this will cascade delete campaigns and metrika_goals)
    db.delete(integration)
    db.commit()
    
    # CRITICAL: Clear dashboard cache to ensure fresh data after integration deletion
    # This prevents stale cached data from the deleted integration from appearing
    from backend_api.cache_service import CacheService
    CacheService.clear()
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
