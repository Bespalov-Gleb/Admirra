from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from core.database import get_db
from core import models, schemas, security
from datetime import datetime, timedelta, date
from typing import List, Optional
import uuid
from backend_api.stats_service import StatsService
from .cache_service import cache_response
import csv
import io
from fastapi.responses import StreamingResponse
import logging
import asyncio
from automation.sync import sync_integration

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

def check_data_availability(
    db: Session,
    client_ids: List[uuid.UUID],
    d_start: date,
    d_end: date,
    platform: str = "all",
    campaign_ids: Optional[List[uuid.UUID]] = None
) -> bool:
    """
    Проверяет наличие данных в БД за указанный период.
    Возвращает True, если данные есть, False - если данных нет или период выходит за рамки сохраненных данных.
    """
    try:
        # Проверяем наличие данных для Yandex Direct
        if platform in ["all", "yandex"]:
            y_query = db.query(func.count(models.YandexStats.id)).join(
                models.Campaign, models.YandexStats.campaign_id == models.Campaign.id
            ).filter(
                models.YandexStats.client_id.in_(client_ids),
                models.YandexStats.date >= d_start,
                models.YandexStats.date <= d_end
            )
            if campaign_ids:
                y_query = y_query.filter(models.Campaign.id.in_(campaign_ids))
            y_count = y_query.scalar() or 0
            
            if y_count > 0:
                # Проверяем, что данные покрывают весь запрошенный период
                # Проверяем минимальную и максимальную даты в БД
                y_date_range = db.query(
                    func.min(models.YandexStats.date).label('min_date'),
                    func.max(models.YandexStats.date).label('max_date')
                ).join(
                    models.Campaign, models.YandexStats.campaign_id == models.Campaign.id
                ).filter(
                    models.YandexStats.client_id.in_(client_ids),
                    models.YandexStats.date >= d_start,
                    models.YandexStats.date <= d_end
                )
                if campaign_ids:
                    y_date_range = y_date_range.filter(models.Campaign.id.in_(campaign_ids))
                date_range = y_date_range.first()
                
                if date_range and date_range.min_date and date_range.max_date:
                    # Если минимальная дата в БД больше запрошенной начальной даты - данных не хватает
                    if date_range.min_date > d_start:
                        logger.info(f"⚠️ Data gap detected: DB min_date={date_range.min_date}, requested start={d_start}")
                        return False
                    # Если максимальная дата в БД меньше запрошенной конечной даты - данных не хватает
                    if date_range.max_date < d_end:
                        logger.info(f"⚠️ Data gap detected: DB max_date={date_range.max_date}, requested end={d_end}")
                        return False
                    return True
        
        # Проверяем наличие данных для VK Ads
        if platform in ["all", "vk"]:
            v_query = db.query(func.count(models.VKStats.id)).join(
                models.Campaign, models.VKStats.campaign_id == models.Campaign.id
            ).filter(
                models.VKStats.client_id.in_(client_ids),
                models.VKStats.date >= d_start,
                models.VKStats.date <= d_end
            )
            if campaign_ids:
                v_query = v_query.filter(models.Campaign.id.in_(campaign_ids))
            v_count = v_query.scalar() or 0
            
            if v_count > 0:
                # Проверяем, что данные покрывают весь запрошенный период
                v_date_range = db.query(
                    func.min(models.VKStats.date).label('min_date'),
                    func.max(models.VKStats.date).label('max_date')
                ).join(
                    models.Campaign, models.VKStats.campaign_id == models.Campaign.id
                ).filter(
                    models.VKStats.client_id.in_(client_ids),
                    models.VKStats.date >= d_start,
                    models.VKStats.date <= d_end
                )
                if campaign_ids:
                    v_date_range = v_date_range.filter(models.Campaign.id.in_(campaign_ids))
                date_range = v_date_range.first()
                
                if date_range and date_range.min_date and date_range.max_date:
                    if date_range.min_date > d_start:
                        logger.info(f"⚠️ VK Data gap detected: DB min_date={date_range.min_date}, requested start={d_start}")
                        return False
                    if date_range.max_date < d_end:
                        logger.info(f"⚠️ VK Data gap detected: DB max_date={date_range.max_date}, requested end={d_end}")
                        return False
                    return True
        
        # Если для выбранной платформы нет данных - возвращаем False
        return False
    except Exception as e:
        logger.error(f"Error checking data availability: {e}")
        return False

async def sync_integration_background(
    integration_id: uuid.UUID,
    date_from_str: str,
    date_to_str: str
):
    """
    Асинхронная функция для синхронизации интеграции в фоне.
    Создает новую сессию БД для фоновой задачи.
    """
    from core.database import SessionLocal
    
    db = SessionLocal()
    try:
        integration = db.query(models.Integration).filter(
            models.Integration.id == integration_id
        ).first()
        
        if not integration:
            logger.warning(f"Integration {integration_id} not found for background sync")
            return
        
        logger.info(f"🔄 Background sync started for integration {integration.id} ({integration.platform}) for period {date_from_str} to {date_to_str}")
        
        await sync_integration(db, integration, date_from_str, date_to_str)
        db.commit()
        
        logger.info(f"✅ Background sync completed for integration {integration.id}")
        
        # Очищаем кеш дашборда после синхронизации
        from backend_api.cache_service import CacheService
        CacheService.clear()
        logger.info(f"🗑️ Cleared dashboard cache after sync for integration {integration.id}")
        
    except Exception as e:
        logger.error(f"❌ Error in background sync for integration {integration_id}: {e}")
        db.rollback()
    finally:
        db.close()

def ensure_data_synced_async(
    db: Session,
    client_ids: List[uuid.UUID],
    d_start: date,
    d_end: date,
    platform: str = "all",
    campaign_ids: Optional[List[uuid.UUID]] = None
):
    """
    Проверяет наличие данных в БД за указанный период и запускает синхронизацию в фоне, если данных нет.
    НЕ БЛОКИРУЕТ запрос - синхронизация выполняется асинхронно.
    """
    # Проверяем наличие данных
    has_data = check_data_availability(db, client_ids, d_start, d_end, platform, campaign_ids)
    
    if has_data:
        logger.info(f"✅ Data available in DB for period {d_start} to {d_end}")
        return
    
    logger.info(f"⚠️ Data not available in DB for period {d_start} to {d_end}. Starting background sync...")
    
    # Получаем все интеграции для этих клиентов
    integrations = db.query(models.Integration).filter(
        models.Integration.client_id.in_(client_ids)
    ).all()
    
    if not integrations:
        logger.warning(f"No integrations found for client_ids: {client_ids}")
        return
    
    # Фильтруем интеграции по платформе
    if platform == "yandex":
        integrations = [i for i in integrations if i.platform == models.IntegrationPlatform.YANDEX_DIRECT]
    elif platform == "vk":
        integrations = [i for i in integrations if i.platform == models.IntegrationPlatform.VK_ADS]
    elif platform == "all":
        # Для "all" синхронизируем все платформы
        integrations = [i for i in integrations if i.platform in [
            models.IntegrationPlatform.YANDEX_DIRECT,
            models.IntegrationPlatform.VK_ADS
        ]]
    
    if not integrations:
        logger.warning(f"No integrations found for platform: {platform}")
        return
    
    # Если указаны campaign_ids, фильтруем интеграции по этим кампаниям
    if campaign_ids:
        campaign_integrations = db.query(models.Campaign.integration_id).filter(
            models.Campaign.id.in_(campaign_ids)
        ).distinct().all()
        integration_ids = [ci[0] for ci in campaign_integrations if ci[0]]
        integrations = [i for i in integrations if i.id in integration_ids]
    
    # Запускаем синхронизацию для каждой интеграции в фоне (не ждем завершения)
    date_from_str = d_start.strftime("%Y-%m-%d")
    date_to_str = d_end.strftime("%Y-%m-%d")
    
    for integration in integrations:
        try:
            # Запускаем синхронизацию в фоне через asyncio.create_task
            # Это не блокирует текущий запрос
            asyncio.create_task(
                sync_integration_background(integration.id, date_from_str, date_to_str)
            )
            logger.info(f"📤 Background sync task created for integration {integration.id}")
        except Exception as e:
            logger.error(f"❌ Error creating background sync task for integration {integration.id}: {e}")

@router.get("/summary", response_model=schemas.StatsSummary)
@cache_response(ttl=900)
async def get_summary(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[str] = Query(None),
    campaign_ids: Optional[List[str]] = Query(None),
    platform: Optional[str] = "all", # 'yandex', 'vk', 'all'
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get aggregated statistics (Expenses, Impressions, Clicks, Leads, CPC, CPA) for a specified period.
    """
    # Safe UUID conversion
    u_client_id = None
    if client_id and client_id.strip():
        try: u_client_id = uuid.UUID(client_id)
        except: pass
    
    u_campaign_ids = None
    if campaign_ids:
        u_campaign_ids = []
        for cid in campaign_ids:
            if cid and cid.strip():
                try: u_campaign_ids.append(uuid.UUID(cid))
                except: pass
        if not u_campaign_ids: u_campaign_ids = None

    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not effective_client_ids:
        return {"expenses": 0, "impressions": 0, "clicks": 0, "leads": 0, "cpc": 0, "cpa": 0, "balance": 0, "currency": "RUB", "trends": None}

    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else d_end - timedelta(days=13)
    
    # CRITICAL: Проверяем наличие данных и запускаем синхронизацию в фоне, если нужно
    # Синхронизация выполняется асинхронно и не блокирует запрос
    ensure_data_synced_async(db, effective_client_ids, d_start, d_end, platform, u_campaign_ids)
    
    print(f"DEBUG: get_summary - campaign_ids: {campaign_ids}, u_campaign_ids: {u_campaign_ids}")
    return StatsService.aggregate_summary(db, effective_client_ids, d_start, d_end, platform, u_campaign_ids)

@router.get("/dynamics", response_model=schemas.DynamicsStat)
@cache_response(ttl=900)
async def get_dynamics(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[str] = Query(None),
    campaign_ids: Optional[List[str]] = Query(None),
    platform: Optional[str] = "all",
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get daily dynamics of costs and clicks for the dashboard chart.
    """
    # Safe UUID conversion
    u_client_id = None
    if client_id and client_id.strip():
        try: u_client_id = uuid.UUID(client_id)
        except: pass
    
    u_campaign_ids = None
    if campaign_ids:
        u_campaign_ids = []
        for cid in campaign_ids:
            if cid and cid.strip():
                try: u_campaign_ids.append(uuid.UUID(cid))
                except: pass
        if not u_campaign_ids: u_campaign_ids = None

    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not effective_client_ids:
        return {
            "labels": [], 
            "costs": [], 
            "clicks": [],
            "impressions": [],
            "leads": [],
            "cpc": [],
            "cpa": []
        }
    
    print(f"DEBUG: get_dynamics - campaign_ids: {campaign_ids}, u_campaign_ids: {u_campaign_ids}")
    
    # Defaults
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else d_end - timedelta(days=13)
    
    # CRITICAL: Проверяем наличие данных и запускаем синхронизацию в фоне, если нужно
    # Синхронизация выполняется асинхронно и не блокирует запрос
    ensure_data_synced_async(db, effective_client_ids, d_start, d_end, platform, u_campaign_ids)

    y_stats = db.query(
        models.YandexStats.date,
        func.sum(models.YandexStats.cost).label("cost"),
        func.sum(models.YandexStats.clicks).label("clicks"),
        func.sum(models.YandexStats.impressions).label("impressions"),
        func.sum(models.YandexStats.conversions).label("leads")
    ).join(models.Campaign, models.YandexStats.campaign_id == models.Campaign.id).filter(
        models.YandexStats.client_id.in_(effective_client_ids),
        # CRITICAL: Removed is_active filter - statistics should be shown for all campaigns
        # is_active is a user selection flag, not a data filtering flag
        models.YandexStats.date >= d_start,
        models.YandexStats.date <= d_end
    )
    if u_campaign_ids:
        y_stats = y_stats.filter(models.Campaign.id.in_(u_campaign_ids))
        # CRITICAL: Also filter by integration_id when campaigns are selected
        campaign_integrations = db.query(models.Campaign.integration_id).filter(
            models.Campaign.id.in_(u_campaign_ids)
        ).distinct().all()
        integration_ids = [ci[0] for ci in campaign_integrations if ci[0]]
        if integration_ids:
            y_stats = y_stats.filter(models.Campaign.integration_id.in_(integration_ids))
    else:
        # CRITICAL: When no campaigns selected, filter by all integrations of the client
        # This prevents mixing data from different profiles/integrations
        if len(effective_client_ids) == 1:
            client_integrations = db.query(models.Integration.id).filter(
                models.Integration.client_id.in_(effective_client_ids)
            ).distinct().all()
            integration_ids = [ci[0] for ci in client_integrations if ci[0]]
            if integration_ids:
                y_stats = y_stats.filter(models.Campaign.integration_id.in_(integration_ids))
    y_stats = y_stats.group_by(models.YandexStats.date).all()

    v_stats = db.query(
        models.VKStats.date,
        func.sum(models.VKStats.cost).label("cost"),
        func.sum(models.VKStats.clicks).label("clicks"),
        func.sum(models.VKStats.impressions).label("impressions"),
        func.sum(models.VKStats.conversions).label("leads")
    ).join(models.Campaign, models.VKStats.campaign_id == models.Campaign.id).filter(
        models.VKStats.client_id.in_(effective_client_ids),
        # CRITICAL: Removed is_active filter - statistics should be shown for all campaigns
        # is_active is a user selection flag, not a data filtering flag
        models.VKStats.date >= d_start,
        models.VKStats.date <= d_end
    )
    if u_campaign_ids:
        v_stats = v_stats.filter(models.Campaign.id.in_(u_campaign_ids))
        # CRITICAL: Also filter by integration_id when campaigns are selected
        campaign_integrations = db.query(models.Campaign.integration_id).filter(
            models.Campaign.id.in_(u_campaign_ids)
        ).distinct().all()
        integration_ids = [ci[0] for ci in campaign_integrations if ci[0]]
        if integration_ids:
            v_stats = v_stats.filter(models.Campaign.integration_id.in_(integration_ids))
    else:
        # CRITICAL: When no campaigns selected, filter by all integrations of the client
        # This prevents mixing data from different profiles/integrations
        if len(effective_client_ids) == 1:
            client_integrations = db.query(models.Integration.id).filter(
                models.Integration.client_id.in_(effective_client_ids)
            ).distinct().all()
            integration_ids = [ci[0] for ci in client_integrations if ci[0]]
            if integration_ids:
                v_stats = v_stats.filter(models.Campaign.integration_id.in_(integration_ids))
    v_stats = v_stats.group_by(models.VKStats.date).all()

    # Metrica Goals dynamics
    # CRITICAL: Get integration_ids for filtering MetrikaGoals
    m_integration_ids = None
    if u_campaign_ids:
        # Get integration_ids from selected campaigns
        campaign_integrations = db.query(models.Campaign.integration_id).filter(
            models.Campaign.id.in_(u_campaign_ids)
        ).distinct().all()
        m_integration_ids = [ci[0] for ci in campaign_integrations if ci[0]]
    elif len(effective_client_ids) == 1:
        # When "all campaigns" is selected, get all integrations for the client
        client_integrations = db.query(models.Integration.id).filter(
            models.Integration.client_id.in_(effective_client_ids)
        ).distinct().all()
        m_integration_ids = [ci[0] for ci in client_integrations if ci[0]]
    
    m_stats = []
    if platform in ["all", "yandex"]:
        m_query = db.query(
            models.MetrikaGoals.date,
            func.sum(models.MetrikaGoals.conversion_count).label("leads")
        ).filter(
            models.MetrikaGoals.client_id.in_(effective_client_ids),
            models.MetrikaGoals.goal_id == "all",
            models.MetrikaGoals.date >= d_start,
            models.MetrikaGoals.date <= d_end
        )
        
        # CRITICAL: Filter MetrikaGoals by integration_id to match campaign selection
        if m_integration_ids:
            m_query = m_query.filter(models.MetrikaGoals.integration_id.in_(m_integration_ids))
        
        m_stats = m_query.group_by(models.MetrikaGoals.date).all()

    labels, costs, clicks, impressions, leads, cpc, cpa = [], [], [], [], [], [], []
    for i in range((d_end - d_start).days + 1):
        d = d_start + timedelta(days=i)
        labels.append(d.strftime("%d %b"))
        
        y_s = next((s for s in y_stats if s.date == d), None) if platform in ["all", "yandex"] else None
        v_s = next((s for s in v_stats if s.date == d), None) if platform in ["all", "vk"] else None
        m_s = next((s for s in m_stats if s.date == d), None) if m_stats else None
        
        c = float((y_s.cost if y_s else 0) + (v_s.cost if v_s else 0))
        cl = int((y_s.clicks if y_s else 0) + (v_s.clicks if v_s else 0))
        im = int((y_s.impressions if y_s else 0) + (v_s.impressions if v_s else 0))
        
        # Lead logic matching aggregate_summary
        # CRITICAL: Always prefer Metrika goals if available (they're more accurate)
        # Now we filter MetrikaGoals by integration_id, so we can use them even when campaigns are selected
        platform_le = int((y_s.leads if y_s else 0) + (v_s.leads if v_s else 0))
        metrika_le = int(m_s.leads if m_s else 0)
        
        # Use Metrika if available, otherwise fallback to platform conversions
        # This ensures consistency between "all campaigns" and specific campaign selection
        if metrika_le > 0:
            le = metrika_le
        else:
            le = platform_le
        
        costs.append(round(c, 2)); clicks.append(cl); impressions.append(im); leads.append(le)
        cpc.append(round(c/cl, 2) if cl > 0 else 0)
        cpa.append(round(c/le, 2) if le > 0 else 0)

    return {
        "labels": labels, 
        "costs": costs, 
        "clicks": clicks,
        "impressions": impressions,
        "leads": leads,
        "cpc": cpc,
        "cpa": cpa
    }

@router.get("/campaigns", response_model=List[schemas.CampaignStat])
@cache_response(ttl=900)
async def get_campaign_stats(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[str] = Query(None),
    campaign_ids: Optional[List[str]] = Query(None),
    platform: Optional[str] = "all",
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics grouped by campaign for the specified period.
    """
    # Safe UUID conversion
    u_client_id = None
    if client_id and client_id.strip():
        try: u_client_id = uuid.UUID(client_id)
        except: pass
    
    u_campaign_ids = None
    if campaign_ids:
        u_campaign_ids = []
        for cid in campaign_ids:
            if cid and cid.strip():
                try: u_campaign_ids.append(uuid.UUID(cid))
                except: pass
        if not u_campaign_ids: u_campaign_ids = None

    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not effective_client_ids: return []

    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()
    
    # CRITICAL: Проверяем наличие данных и запускаем синхронизацию в фоне, если нужно
    # Синхронизация выполняется асинхронно и не блокирует запрос
    if d_start:  # Только если указана начальная дата
        ensure_data_synced_async(db, effective_client_ids, d_start, d_end, platform, u_campaign_ids)

    return StatsService.get_campaign_stats(db, effective_client_ids, d_start, d_end, platform, u_campaign_ids)

@router.get("/keywords", response_model=List[schemas.KeywordStat])
@cache_response(ttl=900)
async def get_keyword_stats(
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
@cache_response(ttl=900)
async def get_group_stats(
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
@cache_response(ttl=900)
async def get_top_clients(
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
@cache_response(ttl=900)
async def get_goals(
    client_id: Optional[uuid.UUID] = None,
    integration_id: Optional[uuid.UUID] = None,  # NEW: Optional filter by integration
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get Metrika goals for the current client from database with cost calculation.
    CRITICAL: This endpoint reads from DB only - no API calls to avoid 429 errors.
    Optionally filter by integration_id to get goals for a specific Yandex account.
    
    Cost is calculated by distributing total ad spend proportionally to goal conversions.
    """
    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, client_id)
    if not effective_client_ids: return []

    # Default date range: last 14 days if not specified
    if not date_to:
        date_to_obj = datetime.utcnow().date()
    else:
        date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
    
    if not date_from:
        date_from_obj = date_to_obj - timedelta(days=13)
    else:
        date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()

    # Get total ad spend for cost distribution
    # Use StatsService to get accurate total cost
    summary = StatsService.aggregate_summary(db, effective_client_ids, date_from_obj, date_to_obj, "all", None)
    total_cost = float(summary.get("expenses", 0) or 0)

    query = db.query(
        models.MetrikaGoals.goal_id,
        models.MetrikaGoals.goal_name,
        func.sum(models.MetrikaGoals.conversion_count).label("count")
    ).filter(
        models.MetrikaGoals.client_id.in_(effective_client_ids),
        models.MetrikaGoals.date >= date_from_obj,
        models.MetrikaGoals.date <= date_to_obj
    )
    
    # NEW: Filter by integration_id if provided
    if integration_id:
        query = query.filter(models.MetrikaGoals.integration_id == integration_id)
    
    # Filter out "all" aggregated goals - we want individual goals
    query = query.filter(models.MetrikaGoals.goal_id != "all")
    
    goals = query.group_by(models.MetrikaGoals.goal_id, models.MetrikaGoals.goal_name).all()

    # Calculate total conversions for proportional cost distribution
    total_conversions = sum(int(g.count or 0) for g in goals)

    # Calculate trend and cost (simplified - compare with previous period)
    result = []
    for g in goals:
        # Get previous period data for trend calculation
        period_days = (date_to_obj - date_from_obj).days + 1
        prev_date_from = date_from_obj - timedelta(days=period_days)
        prev_date_to = date_from_obj - timedelta(days=1)
        
        prev_count = db.query(
            func.sum(models.MetrikaGoals.conversion_count)
        ).filter(
            models.MetrikaGoals.client_id.in_(effective_client_ids),
            models.MetrikaGoals.goal_id == g.goal_id,
            models.MetrikaGoals.date >= prev_date_from,
            models.MetrikaGoals.date <= prev_date_to
        ).scalar() or 0
        
        current_count = int(g.count or 0)
        trend = 0.0
        if prev_count > 0:
            trend = round(((current_count - prev_count) / prev_count) * 100, 1)
        
        # Calculate cost proportionally to conversions
        cost = 0.0
        if total_conversions > 0 and total_cost > 0:
            cost = round((current_count / total_conversions) * total_cost, 2)
        
        result.append({
            "id": g.goal_id,
            "name": g.goal_name or f"Goal {g.goal_id}",
            "count": current_count,
            "trend": trend,
            "cost": cost  # NEW: Add cost field
        })
    
    return result

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
@router.get("/export/csv")
async def export_stats_csv(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[str] = Query(None),
    campaign_ids: Optional[List[str]] = Query(None),
    platform: Optional[str] = "all",
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export statistics to CSV file.
    """
    # Safe UUID conversion
    u_client_id = None
    if client_id and client_id.strip():
        try: u_client_id = uuid.UUID(client_id)
        except: pass
    
    u_campaign_ids = None
    if campaign_ids:
        u_campaign_ids = []
        for cid in campaign_ids:
            if cid and cid.strip():
                try: u_campaign_ids.append(uuid.UUID(cid))
                except: pass
        if not u_campaign_ids: u_campaign_ids = None

    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not effective_client_ids:
        return StreamingResponse(io.StringIO("No data"), media_type="text/csv")
        
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()
    
    stats = StatsService.get_campaign_stats(db, effective_client_ids, d_start, d_end, platform, u_campaign_ids)
    
    output = io.StringIO()
    # Add BOM for Excel compatibility with UTF-8
    output.write('\ufeff')
    
    if stats:
        keys = ["name", "impressions", "clicks", "cost", "conversions", "cpc", "cpa"]
        writer = csv.DictWriter(output, fieldnames=keys, delimiter=';', extrasaction='ignore')
        
        # Header translation
        header = {
            "name": "Название кампании",
            "impressions": "Показы",
            "clicks": "Клики",
            "cost": "Расход (₽)",
            "conversions": "Лиды",
            "cpc": "CPC (₽)",
            "cpa": "CPA (₽)"
        }
        writer.writerow(header)
        writer.writerows(stats)
    else:
        output.write("Нет данных за выбранный период")
        
    output.seek(0)
    
    filename = f"report_{d_start or 'all'}_{d_end}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
