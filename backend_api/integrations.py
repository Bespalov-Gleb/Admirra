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

# Yandex Direct Credentials (NEW VERSION - Supports Auto Auth, but pending API Access)
YANDEX_CLIENT_ID = "e2a052c8cac54caeb9b1b05a593be932"
YANDEX_CLIENT_SECRET = "a3ff5920d00e4ee7b8a8019e33cdaaf0"
YANDEX_AUTH_URL = "https://oauth.yandex.ru/authorize"
YANDEX_TOKEN_URL = "https://oauth.yandex.ru/token"

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
        
        # Trigger background sync
        background_tasks.add_task(run_sync_in_background, db_integration.id)
        
        return {"status": "success", "integration_id": str(db_integration.id), "access_token": access_token}

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

@router.post("/batch-import")
async def batch_import_integrations(
    payload: dict = Body(...),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Import multiple clients from Yandex Agency account.
    Payload: { "access_token": "...", "clients": [ { "login": "...", "name": "..." } ] }
    """
    access_token = payload.get("access_token")
    clients_to_import = payload.get("clients", [])
    
    if not access_token or not clients_to_import:
        raise HTTPException(status_code=400, detail="Missing access_token or clients list")
        
    imported_count = 0
    
    for client_data in clients_to_import:
        # 1. Create Client (Project)
        new_client = models.Client(
            owner_id=current_user.id,
            name=client_data.get("name") or client_data.get("login"),
            description=f"Imported from Yandex (Login: {client_data.get('login')})"
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
            agency_client_login=client_data.get("login"),
            sync_status=models.IntegrationSyncStatus.PENDING,
            last_sync_at=datetime.utcnow()
        )
        db.add(new_integration)
        db.commit()
        
        # 3. Trigger initial sync
        asyncio.create_task(run_sync_in_background(new_integration.id))
        imported_count += 1
        
    return {"message": f"Successfully imported {imported_count} projects", "count": imported_count}
