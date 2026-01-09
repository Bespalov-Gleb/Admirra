from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.database import get_db
from core import models, schemas, security
from typing import List, Optional
import uuid

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

@router.get("/", response_model=List[schemas.CampaignResponse])
def get_campaigns(
    integration_id: Optional[uuid.UUID] = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    List campaigns for a specific integration or all campaigns owned by the user.
    """
    query = db.query(models.Campaign).join(models.Integration).join(models.Client).filter(
        models.Client.owner_id == current_user.id
    )
    
    if integration_id:
        query = query.filter(models.Campaign.integration_id == integration_id)
        
    return query.all()

@router.patch("/{campaign_id}", response_model=schemas.CampaignResponse)
def update_campaign(
    campaign_id: uuid.UUID,
    campaign_update: schemas.CampaignUpdate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update campaign name, status, or move it to another client (project).
    """
    campaign = db.query(models.Campaign).join(models.Integration).join(models.Client).filter(
        models.Campaign.id == campaign_id,
        models.Client.owner_id == current_user.id
    ).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    if campaign_update.name is not None:
        campaign.name = campaign_update.name
    if campaign_update.is_active is not None:
        campaign.is_active = campaign_update.is_active
        
    if campaign_update.client_id is not None:
        # Check if the target client belongs to the user
        target_client = db.query(models.Client).filter_by(id=campaign_update.client_id, owner_id=current_user.id).first()
        if not target_client:
            raise HTTPException(status_code=403, detail="Target client not found or access denied")
        
        # We need an integration for the target client on the same platform
        current_integration = db.query(models.Integration).filter_by(id=campaign.integration_id).first()
        target_integration = db.query(models.Integration).filter_by(
            client_id=target_client.id, 
            platform=current_integration.platform
        ).first()
        
        if not target_integration:
              # Ideally we'd move it or create a placeholder integration, but for now we require an integration
              raise HTTPException(status_code=400, detail="Target project does not have an integration for this platform")
        
        campaign.integration_id = target_integration.id

    db.commit()
    db.refresh(campaign)
    return campaign

