from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from core.database import get_db, SessionLocal
from core import models, schemas, security
from typing import List
import uuid
import httpx
import logging
import asyncio
from datetime import datetime, timedelta
import os

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
    """
    return {
        "url": f"{YANDEX_AUTH_URL}?response_type=code&client_id={YANDEX_CLIENT_ID}&redirect_uri={redirect_uri}"
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
        raise HTTPException(status_code=400, detail="Authorization code and redirect_uri are required")

    # 1. Exchange code for token
    async with httpx.AsyncClient() as client:
        # Yandex requires the same redirect_uri in the token request
        response = await client.post(YANDEX_TOKEN_URL, data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": YANDEX_CLIENT_ID,
            "client_secret": YANDEX_CLIENT_SECRET,
            # "redirect_uri": redirect_uri # Yandex docs say this is optional for token exchange but good practice if strictly checked
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

    if db_integration:
        db_integration.access_token = encrypted_access
        db_integration.refresh_token = encrypted_refresh
        db_integration.platform_client_id = encrypted_platform_client_id
        db_integration.platform_client_secret = encrypted_platform_client_secret
        db_integration.account_id = integration.account_id
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
        account_id=integration.account_id,
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
        raise HTTPException(status_code=404, detail="Integration not found")

    access_token = security.decrypt_token(integration.access_token)
    
    if integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
        try:
            profiles = await get_agency_clients(access_token)
            if profiles:
                return profiles
        except Exception as e:
            logger.error(f"Error fetching Yandex agency clients: {e}")
        
        # Fallback to single account if not an agency or no sub-clients
        return [{"login": integration.account_id, "name": integration.account_id}]

@router.get("/{integration_id}/goals")
async def get_integration_goals(
    integration_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetch available goals (Metrica) for this integration.
    """
    integration = db.query(models.Integration).join(models.Client).filter(
        models.Integration.id == integration_id,
        models.Client.owner_id == current_user.id
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    # For now, return a placeholder or implement Metrica fetching
    # In a real scenario, we'd find the Metrica counter ID linked to this Direct account
    # or let user input it.
    
    # Stub for UI development
    return [
        {"id": "500481744", "name": "Автоцель: переход в мессенджер"},
        {"id": "530485499", "name": "Целевая страница"},
        {"id": "900465557", "name": "Переход в корзину"},
        {"id": "900455915", "name": "Оформление заказа"},
        {"id": "500481741", "name": "Клик по номеру"},
        {"id": "90481745", "name": "Страница формы"}
    ]

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
        
    for key, value in integration_in.items():
        if hasattr(integration, key):
            # Special handling for JSON fields if they come as lists/dicts
            if key == 'selected_goals' and isinstance(value, list):
                import json
                value = json.dumps(value)
            setattr(integration, key, value)
            
    db.commit()
    db.refresh(integration)
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
        
    access_token = security.decrypt_token(integration.access_token)
    discovered_campaigns = []
    
    if integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
        api = YandexDirectAPI(access_token, integration.agency_client_login)
        discovered_campaigns = await api.get_campaigns()
    elif integration.platform == models.IntegrationPlatform.VK_ADS:
        api = VKAdsAPI(access_token, integration.account_id)
        discovered_campaigns = await api.get_campaigns()
        
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
    
    # Return all campaigns for this integration
    return db.query(models.Campaign).filter_by(integration_id=integration.id).all()

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
