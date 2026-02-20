from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from core.database import get_db
from core import models, schemas, security
from typing import List, Optional, Dict
import uuid

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

@router.get("/", response_model=List[schemas.CampaignResponse])
def get_campaigns(
    integration_id: Optional[uuid.UUID] = None,
    client_id: Optional[uuid.UUID] = None,
    platform: Optional[str] = None,  # Filter by platform (yandex_direct, vk_ads, etc.)
    goal_action_ids: Optional[List[str]] = Query(None),  # VK Ads goal/action filter
    only_active: bool = False,       # NEW: show only campaigns выбранные в интеграции (is_active=True)
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    List campaigns for a specific integration, client, or all campaigns owned by the user.
    Can filter by:
      - platform (yandex_direct, vk_ads, etc.)
      - only_active=True: только кампании, которые пользователь выбрал при настройке интеграции (is_active=True).
    """
    query = db.query(models.Campaign).join(models.Integration).join(models.Client).filter(
        models.Client.owner_id == current_user.id
    )
    
    if integration_id:
        query = query.filter(models.Campaign.integration_id == integration_id)
    if client_id:
        query = query.filter(models.Integration.client_id == client_id)
        # CRITICAL: При выборе проекта показывать только кампании из интеграций,
        # где пользователь включил хотя бы одну кампанию (is_active). Иначе подтягиваются
        # кампании из других профилей/аккаунтов того же клиента.
        if only_active:
            active_integration_ids = db.query(models.Campaign.integration_id).join(
                models.Integration
            ).filter(
                models.Integration.client_id == client_id,
                models.Campaign.is_active.is_(True)
            ).distinct().all()
            aid_list = [r[0] for r in active_integration_ids if r[0]]
            if aid_list:
                query = query.filter(models.Campaign.integration_id.in_(aid_list))
            # Если у клиента ровно 1 интеграция — всегда фильтровать по ней
            elif not integration_id:
                client_integrations = db.query(models.Integration.id).filter(
                    models.Integration.client_id == client_id
                ).distinct().all()
                ci_list = [r[0] for r in client_integrations if r[0]]
                if len(ci_list) == 1:
                    query = query.filter(models.Campaign.integration_id == ci_list[0])
    if platform:
        # Map frontend platform names to backend enum values
        platform_map = {
            'yandex': models.IntegrationPlatform.YANDEX_DIRECT,
            'vk': models.IntegrationPlatform.VK_ADS
        }
        target_platform = platform_map.get(platform.lower())
        if target_platform:
            query = query.filter(models.Integration.platform == target_platform)
    if goal_action_ids:
        query = query.filter(models.Campaign.vk_goal_action_id.in_(goal_action_ids))
    if only_active:
        # В дашбордах мы хотим видеть только кампании, которые пользователь отметил в интеграции
        query = query.filter(models.Campaign.is_active == True)
        
    return query.all()

@router.get("/vk-goal-actions", response_model=List[schemas.VkGoalAction])
def get_vk_goal_actions(
    client_id: Optional[uuid.UUID] = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(
        models.Campaign.vk_goal_action_id,
        models.Campaign.vk_goal_action_name
    ).join(models.Integration).join(models.Client).filter(
        models.Client.owner_id == current_user.id,
        models.Integration.platform == models.IntegrationPlatform.VK_ADS,
        or_(
            models.Campaign.vk_goal_action_id.isnot(None),
            models.Campaign.vk_goal_action_name.isnot(None)
        )
    )

    if client_id:
        query = query.filter(models.Integration.client_id == client_id)

    from automation.vk_goal_action_mapping import get_vk_goal_action_name_ru

    actions = {}
    for goal_id, goal_name in query.distinct().all():
        action_id = goal_id or goal_name
        action_name = goal_name or goal_id
        if action_id and action_name and action_id not in actions:
            # Переводим на русский (для кодов VK: traffic → Трафик и т.д.)
            actions[action_id] = get_vk_goal_action_name_ru(action_id) or get_vk_goal_action_name_ru(action_name) or action_name

    return [
        {"id": action_id, "name": action_name}
        for action_id, action_name in sorted(actions.items(), key=lambda x: (x[1] or "").lower())
    ]

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

@router.put("/bulk-update")
def bulk_update_campaigns(
    updates: List[Dict],
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update multiple campaigns in one request.
    Expected format: [{"id": "...", "is_active": true}, ...]
    """
    if not updates:
        return {"status": "success", "updated_count": 0}
        
    # Get IDs for authorization check
    update_ids = [uuid.UUID(str(u["id"])) for u in updates]
    
    # Check all requested campaigns exist and belong to the user
    campaigns = db.query(models.Campaign).join(models.Integration).join(models.Client).filter(
        models.Campaign.id.in_(update_ids),
        models.Client.owner_id == current_user.id
    ).all()
    
    if len(campaigns) != len(update_ids):
        raise HTTPException(status_code=403, detail="Some campaigns not found or access denied")
        
    # Map for easy access
    campaign_map = {c.id: c for c in campaigns}
    
    for update in updates:
        uid = uuid.UUID(str(update["id"]))
        c = campaign_map[uid]
        if "is_active" in update:
            c.is_active = update["is_active"]
        if "name" in update:
            c.name = update["name"]
            
    db.commit()
    return {"status": "success", "updated_count": len(campaigns)}

