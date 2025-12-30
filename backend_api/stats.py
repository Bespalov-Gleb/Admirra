from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from core.database import get_db
from core import models, schemas, security
from datetime import datetime, timedelta
from typing import List, Optional
import uuid
from backend_api.stats_service import StatsService

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
    """
    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, client_id)
    if not effective_client_ids:
        return {"expenses": 0, "impressions": 0, "clicks": 0, "leads": 0, "cpc": 0, "cpa": 0}

    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()
    
    return StatsService.aggregate_summary(db, effective_client_ids, d_start, d_end, platform)

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
    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, client_id)
    if not effective_client_ids:
        return {"labels": [], "costs": [], "clicks": []}
    
    # Defaults
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else d_end - timedelta(days=13)
    
    yandex_stats = db.query(
        models.YandexStats.date,
        func.sum(models.YandexStats.cost).label("cost"),
        func.sum(models.YandexStats.clicks).label("clicks"),
        func.sum(models.YandexStats.impressions).label("impressions"),
        func.sum(models.YandexStats.conversions).label("leads")
    ).filter(
        models.YandexStats.client_id.in_(effective_client_ids),
        models.YandexStats.date >= d_start,
        models.YandexStats.date <= d_end
    ).group_by(models.YandexStats.date).all()

    vk_stats = db.query(
        models.VKStats.date,
        func.sum(models.VKStats.cost).label("cost"),
        func.sum(models.VKStats.clicks).label("clicks"),
        func.sum(models.VKStats.impressions).label("impressions"),
        func.sum(models.VKStats.conversions).label("leads")
    ).filter(
        models.VKStats.client_id.in_(effective_client_ids),
        models.VKStats.date >= d_start,
        models.VKStats.date <= d_end
    ).group_by(models.VKStats.date).all()

    labels = []
    costs_data = []
    clicks_data = []
    impressions_data = []
    leads_data = []
    cpc_data = []
    cpa_data = []

    for i in range((d_end - d_start).days + 1):
        d = d_start + timedelta(days=i)
        labels.append(d.strftime("%d %b"))
        
        y_stat = next((s for s in yandex_stats if s.date == d), None) if platform in ["all", "yandex"] else None
        v_stat = next((s for s in vk_stats if s.date == d), None) if platform in ["all", "vk"] else None
        
        day_cost = float((y_stat.cost if y_stat else 0) + (v_stat.cost if v_stat else 0))
        day_clicks = int((y_stat.clicks if y_stat else 0) + (v_stat.clicks if v_stat else 0))
        day_impressions = int((y_stat.impressions if y_stat else 0) + (v_stat.impressions if v_stat else 0))
        day_leads = int((y_stat.leads if y_stat else 0) + (v_stat.leads if v_stat else 0))
        
        costs_data.append(round(day_cost, 2))
        clicks_data.append(day_clicks)
        impressions_data.append(day_impressions)
        leads_data.append(day_leads)
        
        cpc_val = round(day_cost / day_clicks, 2) if day_clicks > 0 else 0
        cpa_val = round(day_cost / day_leads, 2) if day_leads > 0 else 0
        
        cpc_data.append(cpc_val)
        cpa_data.append(cpa_val)

    return {
        "labels": labels, 
        "costs": costs_data, 
        "clicks": clicks_data,
        "impressions": impressions_data,
        "leads": leads_data,
        "cpc": cpc_data,
        "cpa": cpa_data
    }

@router.get("/campaigns", response_model=List[schemas.CampaignStat])
def get_campaign_stats(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[uuid.UUID] = None,
    platform: Optional[str] = "all",
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics grouped by campaign for the specified period.
    """
    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, client_id)
    if not effective_client_ids: return []

    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()

    return StatsService.get_campaign_stats(db, effective_client_ids, d_start, d_end, platform)

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
    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, client_id)
    if not effective_client_ids: return []
        
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

    if d_start: query = query.filter(models.YandexKeywords.date >= d_start)
    if d_end: query = query.filter(models.YandexKeywords.date <= d_end)

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
    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, client_id)
    if not effective_client_ids: return []

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

    if d_start: query = query.filter(models.YandexGroups.date >= d_start)
    if d_end: query = query.filter(models.YandexGroups.date <= d_end)

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
    user_clients = db.query(models.Client.id, models.Client.name).filter_by(owner_id=current_user.id).all()
    if not user_clients: return []
        
    client_map = {c.id: c.name for c in user_clients}
    client_ids = list(client_map.keys())

    yandex_costs = db.query(models.YandexStats.client_id, func.sum(models.YandexStats.cost).label("total_cost")).filter(models.YandexStats.client_id.in_(client_ids)).group_by(models.YandexStats.client_id).all()
    vk_costs = db.query(models.VKStats.client_id, func.sum(models.VKStats.cost).label("total_cost")).filter(models.VKStats.client_id.in_(client_ids)).group_by(models.VKStats.client_id).all()

    expenses_map = {cid: 0 for cid in client_ids}
    for cid, cost in yandex_costs: expenses_map[cid] += float(cost or 0)
    for cid, cost in vk_costs: expenses_map[cid] += float(cost or 0)

    results = []
    total_all = 0
    for cid, total in expenses_map.items():
        if total > 0:
            results.append({"name": client_map[cid], "expenses": total})
            total_all += total

    results.sort(key=lambda x: x["expenses"], reverse=True)
    results = results[:5]
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
    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, client_id)
    if not effective_client_ids: return []

    goals = db.query(
        models.MetrikaGoals.goal_name,
        func.sum(models.MetrikaGoals.conversion_count).label("count")
    ).filter(models.MetrikaGoals.client_id.in_(effective_client_ids)).group_by(models.MetrikaGoals.goal_name).all()

    return [{"name": g.goal_name, "count": int(g.count or 0), "trend": 15.6} for g in goals]

@router.get("/integrations", response_model=List[schemas.IntegrationStatus])
def get_integrations_status(
    client_id: Optional[uuid.UUID] = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, client_id)
    if not effective_client_ids: return []

    connected_platforms = db.query(models.Integration.platform).filter(models.Integration.client_id.in_(effective_client_ids)).distinct().all()
    connected_list = [p[0].value for p in connected_platforms]
    all_platforms = ["yandex_direct", "vk_ads", "google_ads", "facebook_ads", "instagram", "telegram"]
    
    return [{"platform": p, "is_connected": p in connected_list} for p in all_platforms]
