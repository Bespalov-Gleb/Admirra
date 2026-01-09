import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.database import get_db
from core import models, schemas, security
from datetime import datetime, timedelta
from typing import List

from backend_api.stats_service import StatsService

router = APIRouter(prefix="/clients", tags=["Clients"])

@router.get("/stats", response_model=List[schemas.ClientResponse])
def get_clients_with_stats(
    start_date: str = None,
    end_date: str = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all clients with aggregated statistics for a specified period.
    """
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()
    # Default to 7 days if no start_date provided
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else d_end - timedelta(days=6)
    
    user_clients = db.query(models.Client).filter(models.Client.owner_id == current_user.id).all()
    
    results = []
    for client in user_clients:
        # Get dynamic summary with trends for each client
        summary_data = StatsService.aggregate_summary(db, [client.id], d_start, d_end)
        client.summary = summary_data
        results.append(client)
        
    return results

@router.get("/", response_model=List[schemas.ClientResponse])
def get_clients(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all clients owned by the current user.
    """
    return db.query(models.Client).filter(models.Client.owner_id == current_user.id).all()

@router.post("/", response_model=schemas.ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    client_in: schemas.ClientCreate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new client.
    """
    new_client = models.Client(
        owner_id=current_user.id,
        **client_in.dict()
    )
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    return new_client

@router.get("/{client_id}", response_model=schemas.ClientResponse)
def get_client(
    client_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get specific client details.
    """
    client = db.query(models.Client).filter(
        models.Client.id == client_id,
        models.Client.owner_id == current_user.id
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@router.put("/{client_id}", response_model=schemas.ClientResponse)
def update_client(
    client_id: uuid.UUID,
    client_in: schemas.ClientUpdate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update client information.
    """
    client = db.query(models.Client).filter(
        models.Client.id == client_id,
        models.Client.owner_id == current_user.id
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    update_data = client_in.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(client, key, value)
    
    db.commit()
    db.refresh(client)
    return client

@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a client. All related integrations and stats will be affected (based on DB constraints).
    """
    client = db.query(models.Client).filter(
        models.Client.id == client_id,
        models.Client.owner_id == current_user.id
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    db.delete(client)
    db.commit()
    return None
