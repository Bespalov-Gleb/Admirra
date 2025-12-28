from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from core.database import get_db
from core import models, schemas, security
from datetime import datetime, timedelta
from typing import List, Optional
import uuid

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/summary", response_model=schemas.StatsSummary)
def get_summary(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[uuid.UUID] = None,
    platform: Optional[str] = "all", # 'yandex', 'vk', 'all'
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get aggregated statistics (Expenses, Impressions, Clicks, Leads, CPC, CPA) for a specified period.
    Default period is last 14 days if start_date is not provided.
    """
    # Convert string dates to date objects if provided
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()
    
    # Get effective client IDs (either filtered or all owned)
    if client_id:
        client = db.query(models.Client).filter_by(id=client_id, owner_id=current_user.id).first()
        if not client:
            return {
                "expenses": 0, "impressions": 0, "clicks": 0, "leads": 0, "cpc": 0, "cpa": 0
            }
        effective_client_ids = [client_id]
    else:
        effective_client_ids = [c.id for c in db.query(models.Client).filter_by(owner_id=current_user.id).all()]
    
    if not effective_client_ids:
        return {
            "expenses": 0, "impressions": 0, "clicks": 0, "leads": 0, "cpc": 0, "cpa": 0
        }

    # Aggregate Yandex Stats
    yandex_query = db.query(
        func.sum(models.YandexStats.cost).label("total_cost"),
        func.sum(models.YandexStats.impressions).label("total_impressions"),
        func.sum(models.YandexStats.clicks).label("total_clicks"),
        func.sum(models.YandexStats.conversions).label("total_conversions")
    ).filter(models.YandexStats.client_id.in_(effective_client_ids))

    # Aggregate VK Stats
    vk_query = db.query(
        func.sum(models.VKStats.cost).label("total_cost"),
        func.sum(models.VKStats.impressions).label("total_impressions"),
        func.sum(models.VKStats.clicks).label("total_clicks"),
        func.sum(models.VKStats.conversions).label("total_conversions")
    ).filter(models.VKStats.client_id.in_(effective_client_ids))

    if d_start:
        yandex_query = yandex_query.filter(models.YandexStats.date >= d_start)
        vk_query = vk_query.filter(models.VKStats.date >= d_start)
    if d_end:
        yandex_query = yandex_query.filter(models.YandexStats.date <= d_end)
        vk_query = vk_query.filter(models.VKStats.date <= d_end)

    yandex_summary = yandex_query.first() if platform in ["all", "yandex"] else None
    vk_summary = vk_query.first() if platform in ["all", "vk"] else None

    # Sum up everything
    total_costs = float((yandex_summary.total_cost if yandex_summary else 0) or 0) + \
                  float((vk_summary.total_cost if vk_summary else 0) or 0)
    total_impressions = int((yandex_summary.total_impressions if yandex_summary else 0) or 0) + \
                        int((vk_summary.total_impressions if vk_summary else 0) or 0)
    total_clicks = int((yandex_summary.total_clicks if yandex_summary else 0) or 0) + \
                   int((vk_summary.total_clicks if vk_summary else 0) or 0)
    total_conversions = int((yandex_summary.total_conversions if yandex_summary else 0) or 0) + \
                        int((vk_summary.total_conversions if vk_summary else 0) or 0)

    cpc = total_costs / total_clicks if total_clicks > 0 else 0
    cpa = total_costs / total_conversions if total_conversions > 0 else 0

    return {
        "expenses": round(total_costs, 2),
        "impressions": total_impressions,
        "clicks": total_clicks,
        "leads": total_conversions,
        "cpc": round(cpc, 2),
        "cpa": round(cpa, 2)
    }

@router.get("/dynamics", response_model=schemas.DynamicsStat)
def get_dynamics(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[uuid.UUID] = None,
    platform: Optional[str] = "all",
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get daily dynamics of costs and clicks for the dashboard chart.
    """
    if client_id:
        client = db.query(models.Client).filter_by(id=client_id, owner_id=current_user.id).first()
        if not client:
            return {"labels": [], "costs": [], "clicks": []}
        effective_client_ids = [client_id]
    else:
        effective_client_ids = [c.id for c in db.query(models.Client).filter_by(owner_id=current_user.id).all()]
    
    # Defaults
    if end_date:
        d_end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        d_end = datetime.utcnow().date()

    if start_date:
        d_start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        d_start = d_end - timedelta(days=13)
    
    yandex_stats = db.query(
        models.YandexStats.date,
        func.sum(models.YandexStats.cost).label("cost"),
        func.sum(models.YandexStats.clicks).label("clicks")
    ).filter(
        models.YandexStats.client_id.in_(effective_client_ids),
        models.YandexStats.date >= d_start,
        models.YandexStats.date <= d_end
    ).group_by(models.YandexStats.date).all()

    vk_stats = db.query(
        models.VKStats.date,
        func.sum(models.VKStats.cost).label("cost"),
        func.sum(models.VKStats.clicks).label("clicks")
    ).filter(
        models.VKStats.client_id.in_(effective_client_ids),
        models.VKStats.date >= d_start,
        models.VKStats.date <= d_end
    ).group_by(models.VKStats.date).all()

    # Calculate number of days
    delta = d_end - d_start
    labels = []
    costs_data = []
    clicks_data = []

    for i in range(delta.days + 1):
        d = d_start + timedelta(days=i)
        labels.append(d.strftime("%d %b"))
        
        y_stat = next((s for s in yandex_stats if s.date == d), None) if platform in ["all", "yandex"] else None
        v_stat = next((s for s in vk_stats if s.date == d), None) if platform in ["all", "vk"] else None
        
        day_cost = float((y_stat.cost if y_stat else 0) + (v_stat.cost if v_stat else 0))
        day_clicks = int((y_stat.clicks if y_stat else 0) + (v_stat.clicks if v_stat else 0))
        
        costs_data.append(round(day_cost, 2))
        clicks_data.append(day_clicks)

    return {
        "labels": labels,
        "costs": costs_data,
        "clicks": clicks_data
    }

@router.get("/campaigns", response_model=List[schemas.CampaignStat])
def get_campaign_stats(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[uuid.UUID] = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics grouped by campaign for the specified period.
    """
    if client_id:
        client = db.query(models.Client).filter_by(id=client_id, owner_id=current_user.id).first()
        if not client: return []
        effective_client_ids = [client_id]
    else:
        effective_client_ids = [c.id for c in db.query(models.Client).filter_by(owner_id=current_user.id).all()]

    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()

    query = db.query(
        models.YandexStats.campaign_name,
        func.sum(models.YandexStats.impressions).label("impressions"),
        func.sum(models.YandexStats.clicks).label("clicks"),
        func.sum(models.YandexStats.cost).label("cost"),
        func.sum(models.YandexStats.conversions).label("conversions")
    ).filter(models.YandexStats.client_id.in_(effective_client_ids))

    if d_start:
        query = query.filter(models.YandexStats.date >= d_start)
    if d_end:
        query = query.filter(models.YandexStats.date <= d_end)

    results = query.group_by(models.YandexStats.campaign_name).all()

    campaigns = []
    for r in results:
        cost = float(r.cost or 0)
        clicks = int(r.clicks or 0)
        convs = int(r.conversions or 0)
        campaigns.append({
            "name": r.campaign_name,
            "impressions": int(r.impressions or 0),
            "clicks": clicks,
            "cost": round(cost, 2),
            "conversions": convs,
            "cpc": round(cost / clicks, 2) if clicks > 0 else 0,
            "cpa": round(cost / convs, 2) if convs > 0 else 0
        })

    return campaigns

@router.get("/keywords", response_model=List[schemas.KeywordStat])
def get_keyword_stats(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[uuid.UUID] = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed statistics by keyword.
    """
    if client_id:
        client = db.query(models.Client).filter_by(id=client_id, owner_id=current_user.id).first()
        if not client: return []
        effective_client_ids = [client_id]
    else:
        effective_client_ids = [c.id for c in db.query(models.Client).filter_by(owner_id=current_user.id).all()]
        
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()

    query = db.query(
        models.YandexKeywords.keyword,
        models.YandexKeywords.campaign_name,
        func.sum(models.YandexKeywords.impressions).label("impressions"),
        func.sum(models.YandexKeywords.clicks).label("clicks"),
        func.sum(models.YandexKeywords.cost).label("cost"),
        func.sum(models.YandexKeywords.conversions).label("conversions")
    ).filter(models.YandexKeywords.client_id.in_(effective_client_ids))

    if d_start:
        query = query.filter(models.YandexKeywords.date >= d_start)
    if d_end:
        query = query.filter(models.YandexKeywords.date <= d_end)

    results = query.group_by(models.YandexKeywords.keyword, models.YandexKeywords.campaign_name).all()

    keywords = []
    for r in results:
        cost = float(r.cost or 0)
        clicks = int(r.clicks or 0)
        convs = int(r.conversions or 0)
        keywords.append({
            "keyword": r.keyword,
            "campaign_name": r.campaign_name,
            "impressions": int(r.impressions or 0),
            "clicks": clicks,
            "cost": round(cost, 2),
            "conversions": convs,
            "cpc": round(cost / clicks, 2) if clicks > 0 else 0,
            "cpa": round(cost / convs, 2) if convs > 0 else 0
        })

    return keywords

@router.get("/groups", response_model=List[schemas.GroupStat])
def get_group_stats(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[uuid.UUID] = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed statistics by ad group.
    """
    if client_id:
        client = db.query(models.Client).filter_by(id=client_id, owner_id=current_user.id).first()
        if not client: return []
        effective_client_ids = [client_id]
    else:
        effective_client_ids = [c.id for c in db.query(models.Client).filter_by(owner_id=current_user.id).all()]

    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()

    query = db.query(
        models.YandexGroups.group_name,
        models.YandexGroups.campaign_name,
        func.sum(models.YandexGroups.impressions).label("impressions"),
        func.sum(models.YandexGroups.clicks).label("clicks"),
        func.sum(models.YandexGroups.cost).label("cost"),
        func.sum(models.YandexGroups.conversions).label("conversions")
    ).filter(models.YandexGroups.client_id.in_(effective_client_ids))

    if d_start:
        query = query.filter(models.YandexGroups.date >= d_start)
    if d_end:
        query = query.filter(models.YandexGroups.date <= d_end)

    results = query.group_by(models.YandexGroups.group_name, models.YandexGroups.campaign_name).all()

    groups = []
    for r in results:
        cost = float(r.cost or 0)
        clicks = int(r.clicks or 0)
        convs = int(r.conversions or 0)
        groups.append({
            "name": r.group_name,
            "campaign_name": r.campaign_name,
            "impressions": int(r.impressions or 0),
            "clicks": clicks,
            "cost": round(cost, 2),
            "conversions": convs,
            "cpc": round(cost / clicks, 2) if clicks > 0 else 0,
            "cpa": round(cost / convs, 2) if convs > 0 else 0
        })

    return groups

@router.get("/top-clients", response_model=List[schemas.TopClient])
def get_top_clients(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get top projects by total expenses.
    """
    clients = db.query(models.Client).filter_by(owner_id=current_user.id).all()
    results = []
    total_all = 0
    
    for client in clients:
        y_cost = db.query(func.sum(models.YandexStats.cost)).filter_by(client_id=client.id).scalar() or 0
        v_cost = db.query(func.sum(models.VKStats.cost)).filter_by(client_id=client.id).scalar() or 0
        total = float(y_cost) + float(v_cost)
        if total > 0:
            results.append({"name": client.name, "expenses": total})
            total_all += total
            
    # Sort and calculate percentage
    results.sort(key=lambda x: x["expenses"], reverse=True)
    results = results[:5] # Top 5
    
    for r in results:
        r["percentage"] = round((r["expenses"] / total_all) * 100, 1) if total_all > 0 else 0
        r["expenses"] = round(r["expenses"], 2)
        
    return results

@router.get("/goals", response_model=List[schemas.GoalStat])
def get_goals(
    client_id: Optional[uuid.UUID] = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get Metrika goals for the current client.
    """
    if client_id:
        effective_client_ids = [client_id]
    else:
        effective_client_ids = [c.id for c in db.query(models.Client).filter_by(owner_id=current_user.id).all()]
    
    if not effective_client_ids:
        return []

    # Get goals from MetrikaGoals
    goals = db.query(
        models.MetrikaGoals.goal_name,
        func.sum(models.MetrikaGoals.conversion_count).label("count")
    ).filter(models.MetrikaGoals.client_id.in_(effective_client_ids)).group_by(models.MetrikaGoals.goal_name).all()

    # In a real app, trend would be calculated by comparing periods. 
    # For now, we return a mock/calculated trend.
    return [
        {
            "name": g.goal_name,
            "count": int(g.count or 0),
            "trend": 15.6 # Simplified for now
        } for g in goals
    ]

@router.get("/integrations", response_model=List[schemas.IntegrationStatus])
def get_integrations_status(
    client_id: Optional[uuid.UUID] = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get connection status of various platforms.
    """
    if client_id:
        client = db.query(models.Client).filter_by(id=client_id, owner_id=current_user.id).first()
        if not client: return []
        effective_client_ids = [client_id]
    else:
        # If no client_id, we check if there are ANY integrations for this user's clients
        effective_client_ids = [c.id for c in db.query(models.Client).filter_by(owner_id=current_user.id).all()]

    connected_platforms = db.query(models.Integration.platform).filter(
        models.Integration.client_id.in_(effective_client_ids)
    ).distinct().all()
    
    connected_list = [p[0].value for p in connected_platforms]
    
    all_platforms = ["yandex_direct", "vk_ads", "google_ads", "facebook_ads", "instagram", "telegram"]
    
    return [
        {
            "platform": p,
            "is_connected": p in connected_list
        } for p in all_platforms
    ]
