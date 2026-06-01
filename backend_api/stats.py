from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from core.database import get_db
from core import models, schemas, security
from datetime import datetime, timedelta, date
from typing import List, Optional
import uuid
from backend_api.stats_service import StatsService
from backend_api.top_ads_service import get_top_ads_with_images
import csv
import io
from fastapi.responses import StreamingResponse
import json
import logging
import asyncio
from automation.sync import sync_integration, sync_metrika_goals_background
from automation.vk_goal_action_mapping import get_vk_goal_action_name_ru
from backend_api.sync_jobs import enqueue_sync_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# Дедупликация ensure_data_synced: не запускать повторный sync для интеграции в течение 30 сек
_sync_last_started: dict = {}
_sync_cooldown_sec = 30

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

async def sync_integration_background_async(
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
        CacheService.invalidate_client(str(integration.client_id))
        logger.info(f"🗑️ Cleared dashboard cache after sync for integration {integration.id}")
        
    except Exception as e:
        logger.error(f"❌ Error in background sync for integration {integration_id}: {e}")
        db.rollback()
    finally:
        db.close()

def sync_integration_background(
    integration_id: uuid.UUID,
    date_from_str: str,
    date_to_str: str
):
    """
    Синхронная обертка для запуска синхронизации в отдельном потоке.
    Запускает асинхронную синхронизацию в отдельном event loop, чтобы не блокировать основной event loop FastAPI.
    """
    try:
        d_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()
        d_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()
        days = max(1, (d_to - d_from).days + 1)
    except Exception:
        days = 7
    enqueue_sync_job(integration_id, days)

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
    
    # Очищаем кеш при запуске синка — следующий запрос получит свежие данные после завершения
    from backend_api.cache_service import CacheService
    for cid in client_ids:
        CacheService.invalidate_client(str(cid))
    
    # Получаем все интеграции для этих клиентов
    integrations = (
        db.query(models.Integration)
        .join(models.Client, models.Client.id == models.Integration.client_id)
        .filter(
            models.Integration.client_id.in_(client_ids),
            models.Client.status == models.ClientStatus.ACTIVE,
        )
        .all()
    )
    
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
    # CRITICAL: Ограничиваем количество одновременных синхронизаций, чтобы не исчерпать пул соединений
    # Максимум 5 одновременных синхронизаций (остальные будут ждать освобождения соединений)
    MAX_CONCURRENT_SYNCS = 5
    date_from_str = d_start.strftime("%Y-%m-%d")
    date_to_str = d_end.strftime("%Y-%m-%d")
    
    # Запускаем синхронизацию только для первых MAX_CONCURRENT_SYNCS интеграций
    # Остальные будут синхронизированы при следующем запросе
    integrations_to_sync = integrations[:MAX_CONCURRENT_SYNCS]
    if len(integrations) > MAX_CONCURRENT_SYNCS:
        logger.warning(f"⚠️ Too many integrations ({len(integrations)}). Syncing only first {MAX_CONCURRENT_SYNCS}. Rest will sync on next request.")
    
    # Дедупликация: не запускать повторный sync для той же интеграции в течение _sync_cooldown_sec
    import time as _time
    _now = _time.time()
    for integration in integrations_to_sync:
        try:
            _last = _sync_last_started.get(str(integration.id), 0)
            if _now - _last < _sync_cooldown_sec:
                logger.debug(f"📤 Skip sync for {integration.id} (cooldown {_sync_cooldown_sec - int(_now - _last)}s)")
                continue
            _sync_last_started[str(integration.id)] = _now
            sync_integration_background(integration.id, date_from_str, date_to_str)
            logger.info(f"📤 Background sync task created for integration {integration.id}")
        except Exception as e:
            logger.error(f"❌ Error creating background sync task for integration {integration.id}: {e}")

@router.get("/summary", response_model=schemas.StatsSummary)
async def get_summary(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[str] = Query(None),
    campaign_ids: Optional[List[str]] = Query(None),
    goal_action_ids: Optional[List[str]] = Query(None),
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

    u_goal_action_ids = None
    if goal_action_ids:
        u_goal_action_ids = [gid for gid in goal_action_ids if gid and gid.strip()]
        if not u_goal_action_ids:
            u_goal_action_ids = None

    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not effective_client_ids:
        return {"expenses": 0, "impressions": 0, "clicks": 0, "leads": 0, "cpc": 0, "cpa": 0, "balance": 0, "currency": "RUB", "trends": None}

    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else d_end - timedelta(days=13)
    
    print(f"DEBUG: get_summary - campaign_ids: {campaign_ids}, u_campaign_ids: {u_campaign_ids}")
    return StatsService.aggregate_summary(db, effective_client_ids, d_start, d_end, platform, u_campaign_ids, u_goal_action_ids)

@router.get("/dynamics", response_model=schemas.DynamicsStat)
async def get_dynamics(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[str] = Query(None),
    campaign_ids: Optional[List[str]] = Query(None),
    goal_action_ids: Optional[List[str]] = Query(None),
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

    u_goal_action_ids = None
    if goal_action_ids:
        u_goal_action_ids = [gid for gid in goal_action_ids if gid and gid.strip()]
        if not u_goal_action_ids:
            u_goal_action_ids = None

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
        # При "все кампании" — все интеграции клиента (не фильтруем по active)
        if len(effective_client_ids) == 1:
            client_integrations = db.query(models.Integration.id).filter(
                models.Integration.client_id.in_(effective_client_ids)
            ).distinct().all()
            integration_ids = [ci[0] for ci in client_integrations if ci[0]]
            if integration_ids:
                y_stats = y_stats.filter(models.Campaign.integration_id.in_(integration_ids))
    y_stats = y_stats.group_by(models.YandexStats.date).all()

    # #region agent log
    _ys = [{"date": str(s.date), "cost": float(s.cost or 0), "clicks": s.clicks, "impressions": s.impressions, "leads": s.leads} for s in (y_stats or [])[:5]]
    logger.info(f"[DEBUG stats] YandexStats count={len(y_stats or [])} sample={_ys} client_ids={[str(c) for c in effective_client_ids]} period={d_start}..{d_end}")
    # #endregion

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
    elif u_goal_action_ids:
        v_stats = v_stats.filter(models.Campaign.vk_goal_action_id.in_(u_goal_action_ids))
    else:
        if len(effective_client_ids) == 1:
            client_integrations = db.query(models.Integration.id).filter(
                models.Integration.client_id.in_(effective_client_ids)
            ).distinct().all()
            integration_ids = [ci[0] for ci in client_integrations if ci[0]]
            if integration_ids:
                v_stats = v_stats.filter(models.Campaign.integration_id.in_(integration_ids))
    v_stats = v_stats.group_by(models.VKStats.date).all()

    # Metrica Goals dynamics — при "все кампании" НЕ фильтруем по integration
    m_integration_ids = None
    if u_campaign_ids:
        campaign_integrations = db.query(models.Campaign.integration_id).filter(
            models.Campaign.id.in_(u_campaign_ids)
        ).distinct().all()
        m_integration_ids = [ci[0] for ci in campaign_integrations if ci[0]]
    
    m_stats = []
    if platform in ["all", "yandex"]:
        # Важно: используем тот же фильтр selected_goals, что и в summary,
        # чтобы суточные лиды на графике совпадали с итогом за период.
        selected_goal_ids = set()
        for i in db.query(models.Integration).filter(
            models.Integration.client_id.in_(effective_client_ids),
            models.Integration.platform.in_([
                models.IntegrationPlatform.YANDEX_DIRECT,
                models.IntegrationPlatform.YANDEX_METRIKA,
            ]),
        ).all():
            if i.selected_goals:
                try:
                    sg = json.loads(i.selected_goals) if isinstance(i.selected_goals, str) else i.selected_goals
                    selected_goal_ids.update(str(g) for g in (sg or []))
                except Exception:
                    pass
            if i.primary_goal_id:
                selected_goal_ids.add(str(i.primary_goal_id))

        # Лиды по дням = сумма по всем целям (как в summary и на круговой диаграмме)
        m_query = db.query(
            models.MetrikaGoals.date,
            func.sum(models.MetrikaGoals.conversion_count).label("leads")
        ).filter(
            models.MetrikaGoals.client_id.in_(effective_client_ids),
            models.MetrikaGoals.goal_id != "all",
            models.MetrikaGoals.date >= d_start,
            models.MetrikaGoals.date <= d_end
        )

        if selected_goal_ids:
            m_query = m_query.filter(models.MetrikaGoals.goal_id.in_(selected_goal_ids))
        
        # CRITICAL: Filter MetrikaGoals by integration_id to match campaign selection
        if m_integration_ids:
            m_query = m_query.filter(models.MetrikaGoals.integration_id.in_(m_integration_ids))
        
        m_stats = m_query.group_by(models.MetrikaGoals.date).all()

        # #region agent log
        _ms = [{"date": str(s.date), "leads": s.leads} for s in (m_stats or [])[:5]]
        _m_total = sum(int(s.leads or 0) for s in (m_stats or []))
        _y_total = sum(int(s.leads or 0) for s in (y_stats or []))
        _raw_q = db.query(models.MetrikaGoals.goal_id, func.sum(models.MetrikaGoals.conversion_count).label("cnt")).filter(
            models.MetrikaGoals.client_id.in_(effective_client_ids),
            models.MetrikaGoals.goal_id != "all",
            models.MetrikaGoals.date >= d_start,
            models.MetrikaGoals.date <= d_end
        )
        if selected_goal_ids:
            _raw_q = _raw_q.filter(models.MetrikaGoals.goal_id.in_(selected_goal_ids))
        if m_integration_ids:
            _raw_q = _raw_q.filter(models.MetrikaGoals.integration_id.in_(m_integration_ids))
        _raw_m = _raw_q.group_by(models.MetrikaGoals.goal_id).all()
        _raw_total = sum(int(r.cnt or 0) for r in _raw_m)
        logger.info(f"[DEBUG stats] MetrikaGoals count={len(m_stats or [])} sample={_ms} m_total={_m_total} y_total={_y_total} raw_by_goal={[(r.goal_id, r.cnt) for r in _raw_m[:5]]}")
        try:
            with open(r"c:\Users\ArdorPC\PycharmProjects\TraficAgent\.cursor\debug.log", "a") as _f:
                _f.write(__import__("json").dumps({"location":"stats.py:get_dynamics","message":"Metrika vs Yandex totals","data":{"m_total":_m_total,"y_total":_y_total,"raw_total":_raw_total,"raw_by_goal":[(r.goal_id, int(r.cnt or 0)) for r in _raw_m],"m_integration_ids":str(m_integration_ids),"period":f"{d_start}..{d_end}","m_sample":_ms[:5]},"timestamp":__import__("time").time()*1000,"hypothesisId":"H4"}) + "\n")
        except Exception: pass
        # #endregion

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
        
        # Лиды для Yandex — Метрика приоритетна; fallback на Direct если Metrika пусто
        metrika_le = int(m_s.leads if m_s else 0)
        yandex_le = int(y_s.leads if y_s else 0)
        vk_le = int(v_s.leads if v_s else 0)
        if platform == "vk":
            le = vk_le
        elif u_campaign_ids:
            # MetrikaGoals are integration-scoped in the current schema. For a
            # selected campaign set (also used by directions), use campaign-
            # scoped Direct conversions to avoid overcounting the whole cabinet.
            le = yandex_le + vk_le
        else:
            le = (metrika_le if metrika_le > 0 else yandex_le) + vk_le
        # #region agent log
        if le > 0:
            try:
                with open(r"c:\Users\ArdorPC\PycharmProjects\TraficAgent\.cursor\debug.log", "a") as _f:
                    _f.write(__import__("json").dumps({"location":"stats.py:leads_source","message":"Day with leads","data":{"date":str(d),"metrika_le":metrika_le,"yandex_le":yandex_le,"used":("metrika" if metrika_le > 0 else "yandex"),"le":le},"timestamp":__import__("time").time()*1000,"hypothesisId":"H4"}) + "\n")
            except Exception: pass
        # #endregion
        
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
async def get_campaign_stats(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[str] = Query(None),
    campaign_ids: Optional[List[str]] = Query(None),
    goal_action_ids: Optional[List[str]] = Query(None),
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

    u_goal_action_ids = None
    if goal_action_ids:
        u_goal_action_ids = [gid for gid in goal_action_ids if gid and gid.strip()]
        if not u_goal_action_ids:
            u_goal_action_ids = None

    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not effective_client_ids: return []

    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()
    
    return StatsService.get_campaign_stats(db, effective_client_ids, d_start, d_end, platform, u_campaign_ids, u_goal_action_ids)


@router.get("/top-ads", response_model=List[dict])
async def get_top_ads(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[str] = Query(None),
    campaign_ids: Optional[List[str]] = Query(None),
    goal_action_ids: Optional[List[str]] = Query(None),
    platform: Optional[str] = "all",
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get top 4 ads (posts) by conversions. For Yandex: real ads with image_url from Ads.get + AdImages.get.
    For VK: fallback to campaign-level (no image_url).
    """
    u_client_id = None
    if client_id and client_id.strip():
        try:
            u_client_id = uuid.UUID(client_id)
        except Exception:
            pass

    u_campaign_ids = None
    if campaign_ids:
        u_campaign_ids = []
        for cid in campaign_ids:
            if cid and cid.strip():
                try:
                    u_campaign_ids.append(uuid.UUID(cid))
                except Exception:
                    pass
        if not u_campaign_ids:
            u_campaign_ids = None

    u_goal_action_ids = None
    if goal_action_ids:
        u_goal_action_ids = [gid for gid in goal_action_ids if gid and gid.strip()]
        if not u_goal_action_ids:
            u_goal_action_ids = None

    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not effective_client_ids:
        return []

    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()

    try:
        ads = await get_top_ads_with_images(
            db, effective_client_ids, d_start, d_end,
            platform, u_campaign_ids, u_goal_action_ids, limit=16
        )
        return ads
    except Exception as e:
        logger.warning(f"top-ads error, fallback to campaign-level: {e}")
        campaigns = StatsService.get_campaign_stats(
            db, effective_client_ids, d_start, d_end, platform, u_campaign_ids, u_goal_action_ids
        )
        sorted_campaigns = sorted(
            campaigns,
            key=lambda x: (x.get("conversions", 0) or 0, x.get("cost", 0) or 0),
            reverse=True
        )
        top = sorted_campaigns[:4]
        return [
            {
                "id": c["id"],
                "title": c["name"],
                "image_url": None,
                "impressions": c.get("impressions", 0),
                "clicks": c.get("clicks", 0),
                "cost": c.get("cost", 0),
                "conversions": c.get("conversions", 0),
                "ctr": round((c.get("clicks", 0) or 0) / (c.get("impressions", 1) or 1) * 100, 2),
                "platform": "yandex" if c["name"].startswith("[ЯД]") else "vk",
            }
            for c in top
        ]


@router.get("/activity-by-weekday", response_model=dict)
async def get_activity_by_weekday(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[str] = Query(None),
    campaign_ids: Optional[List[str]] = Query(None),
    goal_action_ids: Optional[List[str]] = Query(None),
    platform: Optional[str] = "all",
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get clicks and leads aggregated by day of week.
    Returns: {"clicks": {"0": N, ...}, "leads": {"0": N, ...}} where 0=Sunday, 1=Monday, ..., 6=Saturday.
    """
    u_client_id = None
    if client_id and client_id.strip():
        try:
            u_client_id = uuid.UUID(client_id)
        except Exception:
            pass

    u_campaign_ids = None
    if campaign_ids:
        u_campaign_ids = []
        for cid in campaign_ids:
            if cid and cid.strip():
                try:
                    u_campaign_ids.append(uuid.UUID(cid))
                except Exception:
                    pass
        if not u_campaign_ids:
            u_campaign_ids = None

    u_goal_action_ids = None
    if goal_action_ids:
        u_goal_action_ids = [gid for gid in goal_action_ids if gid and gid.strip()]
        if not u_goal_action_ids:
            u_goal_action_ids = None

    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not effective_client_ids:
        empty = {str(i): 0 for i in range(7)}
        return {"clicks": dict(empty), "leads": dict(empty)}

    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()

    return StatsService.get_activity_by_weekday(
        db, effective_client_ids, d_start, d_end, platform, u_campaign_ids, u_goal_action_ids
    )


@router.get("/audience-age", response_model=List[dict])
async def get_audience_age(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[str] = Query(None),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get audience age distribution from Yandex Metrica.
    Returns list of {age_interval: str, visits: int}.
    """
    u_client_id = None
    if client_id and client_id.strip():
        try:
            u_client_id = uuid.UUID(client_id)
        except Exception:
            pass

    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not effective_client_ids or len(effective_client_ids) != 1:
        return []

    # Get integration with Metrika: YANDEX_METRIKA или YANDEX_DIRECT с selected_counters
    integration = db.query(models.Integration).filter(
        models.Integration.client_id.in_(effective_client_ids),
        models.Integration.platform == models.IntegrationPlatform.YANDEX_METRIKA
    ).first()
    if not integration or not integration.access_token or not integration.selected_counters:
        integration = db.query(models.Integration).filter(
            models.Integration.client_id.in_(effective_client_ids),
            models.Integration.platform == models.IntegrationPlatform.YANDEX_DIRECT,
            models.Integration.selected_counters.isnot(None),
            models.Integration.selected_counters != ""
        ).first()
    if not integration or not integration.access_token or not integration.selected_counters:
        return []

    import json
    try:
        counters = json.loads(integration.selected_counters) if isinstance(integration.selected_counters, str) else integration.selected_counters
    except Exception:
        counters = []
    if not counters:
        return []

    counter_id = str(counters[0]) if counters else None
    if not counter_id:
        return []

    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else d_end - timedelta(days=30)
    date_from = d_start.strftime("%Y-%m-%d")
    date_to = d_end.strftime("%Y-%m-%d")

    from automation.yandex_metrica import YandexMetricaAPI
    access_token = security.decrypt_token(integration.access_token)
    api = YandexMetricaAPI(access_token)
    try:
        data = await api.get_audience_age(counter_id, date_from, date_to)
    except Exception as e:
        logger.warning(f"Metrika audience-age error: {e}")
        return []

    result = []
    for row in data:
        dims = row.get("dimensions", [])
        metrics = row.get("metrics", [])
        age_name = dims[0].get("name", "unknown") if dims else "unknown"
        visits = int(metrics[0]) if metrics else 0
        result.append({"age_interval": age_name, "visits": visits})
    return result


@router.get("/keywords", response_model=List[schemas.KeywordStat])
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
async def get_goals(
    client_id: Optional[uuid.UUID] = None,
    integration_id: Optional[uuid.UUID] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    platform: Optional[str] = Query("all", description="yandex | vk | all"),
    campaign_ids: Optional[str] = Query(None, description="comma-separated campaign UUIDs (для VK)"),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get goals for the current client from database.
    - platform=yandex: Metrika goals (конверсии по целям Метрики)
    - platform=vk: VK goal actions (разбивка по типам ЦД: подписчики, трафик, лид-формы и т.д.)
    - platform=all: Yandex only (Metrika). VK при all не показываем — разные метрики.
    
    Cost is calculated by distributing total ad spend proportionally to conversions.
    """
    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, client_id)
    # #region agent log
    try:
        import json, os
        _log = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".cursor", "debug.log"))
        with open(_log, "a", encoding="utf-8") as _f:
            _f.write(json.dumps({"id":"get_goals_entry","timestamp":__import__("time").time()*1000,"location":"stats.py:get_goals","message":"get_goals called","data":{"client_id":str(client_id) if client_id else None,"date_from":date_from,"date_to":date_to,"effective_client_ids":[str(x) for x in (effective_client_ids or [])],"effective_count":len(effective_client_ids or [])},"hypothesisId":"B","runId":"post-fix"}) + "\n")
    except Exception: pass
    # #endregion
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

    # ——— VK: разбивка по типам целевых действий (подписчики, трафик, лид-формы и т.д.) ———
    if (platform or "").lower() == "vk":
        u_campaign_ids = None
        if campaign_ids:
            try:
                u_campaign_ids = [uuid.UUID(x.strip()) for x in campaign_ids.split(",") if x.strip()]
            except ValueError:
                pass
        vk_q = db.query(
            models.Campaign.vk_goal_action_id,
            models.Campaign.vk_goal_action_name,
            func.sum(models.VKStats.conversions).label("count"),
            func.sum(models.VKStats.cost).label("cost"),
        ).join(models.VKStats, models.VKStats.campaign_id == models.Campaign.id).filter(
            models.VKStats.client_id.in_(effective_client_ids),
            models.VKStats.date >= date_from_obj,
            models.VKStats.date <= date_to_obj,
            models.Campaign.is_active.is_(True),
            models.Campaign.vk_goal_action_id.isnot(None),
            models.Campaign.vk_goal_action_id != "",
        )
        if u_campaign_ids:
            vk_q = vk_q.filter(models.Campaign.id.in_(u_campaign_ids))
        vk_rows = vk_q.group_by(
            models.Campaign.vk_goal_action_id,
            models.Campaign.vk_goal_action_name,
        ).all()

        result = []
        period_days = (date_to_obj - date_from_obj).days + 1
        prev_date_from = date_from_obj - timedelta(days=period_days)
        prev_date_to = date_from_obj - timedelta(days=1)

        for row in vk_rows:
            prev_q = db.query(
                func.sum(models.VKStats.conversions),
                func.sum(models.VKStats.cost),
            ).join(models.Campaign, models.VKStats.campaign_id == models.Campaign.id).filter(
                models.VKStats.client_id.in_(effective_client_ids),
                models.Campaign.vk_goal_action_id == row.vk_goal_action_id,
                models.Campaign.is_active.is_(True),
                models.VKStats.date >= prev_date_from,
                models.VKStats.date <= prev_date_to,
            )
            if u_campaign_ids:
                prev_q = prev_q.filter(models.Campaign.id.in_(u_campaign_ids))
            prev_count, prev_cost = prev_q.first() or (0, 0)

            current_count = int(row.count or 0)
            current_cost = float(row.cost or 0)
            prev_count = int(prev_count or 0)
            prev_cost = float(prev_cost or 0)
            trend = 0.0
            current_cpl = current_cost / current_count if current_count > 0 else 0
            prev_cpl = prev_cost / prev_count if prev_count > 0 else 0
            if prev_cpl > 0 and current_cpl > 0:
                trend = round(((current_cpl - prev_cpl) / prev_cpl) * 100, 1)

            name = (row.vk_goal_action_name or "").strip() or get_vk_goal_action_name_ru(row.vk_goal_action_id or "")
            if not name:
                name = str(row.vk_goal_action_id or "ЦД")

            result.append({
                "id": str(row.vk_goal_action_id or ""),
                "name": name,
                "count": current_count,
                "trend": trend,
                "cost": current_cost,
            })

        return result

    # ——— Yandex / all: Metrika goals ———

    query = db.query(
        models.MetrikaGoals.goal_id,
        models.MetrikaGoals.goal_name,
        func.sum(models.MetrikaGoals.conversion_count).label("count")
    ).filter(
        models.MetrikaGoals.client_id.in_(effective_client_ids),
        models.MetrikaGoals.date >= date_from_obj,
        models.MetrikaGoals.date <= date_to_obj
    )
    
    if integration_id:
        query = query.filter(models.MetrikaGoals.integration_id == integration_id)
    
    # Individual goals (goal_id != "all")
    query_indiv = query.filter(models.MetrikaGoals.goal_id != "all")
    goals = query_indiv.group_by(models.MetrikaGoals.goal_id, models.MetrikaGoals.goal_name).all()

    # Фильтр по selected_goals: показывать только цели, выбранные пользователем при интеграции
    selected_goal_ids = set()
    for i in db.query(models.Integration).filter(
        models.Integration.client_id.in_(effective_client_ids),
        models.Integration.platform.in_([
            models.IntegrationPlatform.YANDEX_DIRECT,
            models.IntegrationPlatform.YANDEX_METRIKA,
        ]),
    ).all():
        if i.selected_goals:
            try:
                sg = json.loads(i.selected_goals) if isinstance(i.selected_goals, str) else i.selected_goals
                selected_goal_ids.update(str(g) for g in (sg or []))
            except Exception:
                pass
        if i.primary_goal_id:
            selected_goal_ids.add(str(i.primary_goal_id))
    if selected_goal_ids:
        goals = [g for g in goals if str(g.goal_id) in selected_goal_ids]

    # Если нет индивидуальных целей — НЕ возвращаем агрегат (goal_id="all"). Агрегат с именем
    # "Selected Goals" — техническая запись из sync; показывать её как цель было бы некорректно.
    # Пустой список = синк ещё идёт или цели не настроены. Триггерим sync при необходимости.
    if not goals:
        any_count = db.query(func.count(models.MetrikaGoals.id)).filter(
            models.MetrikaGoals.client_id.in_(effective_client_ids),
            models.MetrikaGoals.date >= date_from_obj,
            models.MetrikaGoals.date <= date_to_obj
        ).scalar() or 0
        logger.info(f"📊 get_goals: 0 goals for client {effective_client_ids}, period {date_from_obj}–{date_to_obj}. Total MetrikaGoals rows: {any_count}")
        # Запускаем sync целей по требованию — данные появятся после retry на фронте
        for i in db.query(models.Integration).filter(
            models.Integration.client_id.in_(effective_client_ids),
            models.Integration.platform == models.IntegrationPlatform.YANDEX_DIRECT
        ).all():
            if (i.selected_goals or i.primary_goal_id) and i.selected_counters:
                sync_metrika_goals_background(i.id, str(date_from_obj), str(date_to_obj))
                logger.info(f"📊 get_goals: triggered goals-only sync for integration {i.id}")
                break  # один sync достаточно

    # #region agent log
    try:
        import json, os
        _db_total = db.query(func.count(models.MetrikaGoals.id)).filter(
            models.MetrikaGoals.client_id.in_(effective_client_ids),
            models.MetrikaGoals.date >= date_from_obj,
            models.MetrikaGoals.date <= date_to_obj
        ).scalar() or 0
        _log = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".cursor", "debug.log"))
        with open(_log, "a", encoding="utf-8") as _f:
            _f.write(json.dumps({"id":"get_goals_result","timestamp":__import__("time").time()*1000,"location":"stats.py:get_goals","message":"get_goals result","data":{"goals_count":len(goals),"result_len":len([g for g in goals]),"db_total_rows":_db_total,"date_from":str(date_from_obj),"date_to":str(date_to_obj)},"hypothesisId":"E","runId":"post-fix"}) + "\n")
    except Exception: pass
    # #endregion

    period_days = (date_to_obj - date_from_obj).days + 1
    prev_date_from = date_from_obj - timedelta(days=period_days)
    prev_date_to = date_from_obj - timedelta(days=1)

    # Yandex/Metrika stores goal reaches separately from Direct spend. Without
    # campaign-goal attribution, assigning spend per individual goal would make
    # every goal's CPL identical. Return no per-goal cost instead of fake CPL.
    result = []
    for g in goals:
        prev_count = db.query(
            func.sum(models.MetrikaGoals.conversion_count)
        ).filter(
            models.MetrikaGoals.client_id.in_(effective_client_ids),
            models.MetrikaGoals.goal_id == g.goal_id,
            models.MetrikaGoals.date >= prev_date_from,
            models.MetrikaGoals.date <= prev_date_to
        ).scalar() or 0

        current_count = int(g.count or 0)
        count_trend = 0.0
        if prev_count > 0:
            count_trend = round(((current_count - int(prev_count)) / int(prev_count)) * 100, 1)

        result.append({
            "id": g.goal_id,
            "name": g.goal_name or f"Goal {g.goal_id}",
            "count": current_count,
            "trend": count_trend,
            "cost": None,
        })
    
    return result

@router.get("/integrations", response_model=List[schemas.DashboardIntegrationStatus])
def get_integrations_status(
    client_id: Optional[str] = Query(None),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    u_client_id = None
    if client_id:
        try:
            u_client_id = uuid.UUID(client_id)
        except ValueError:
            pass
    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not effective_client_ids: return []

    # Get integrations with balance for connected platforms
    integrations = db.query(
        models.Integration.platform,
        models.Integration.balance,
        models.Integration.currency
    ).filter(models.Integration.client_id.in_(effective_client_ids)).all()

    platform_data = {}
    for row in integrations:
        raw = row.platform.value if hasattr(row.platform, 'value') else str(row.platform)
        p = raw.lower().replace("-", "_")  # YANDEX_DIRECT -> yandex_direct
        if p not in platform_data or (row.balance is not None and platform_data[p].get("balance") is None):
            platform_data[p] = {
                "platform": p,  # lowercase для совместимости с фронтом
                "is_connected": True,
                "balance": float(row.balance) if row.balance is not None else None,
                "currency": row.currency
            }
        elif p in platform_data and row.balance is not None and platform_data[p].get("balance") is not None:
            # Sum balance if multiple integrations for same platform
            platform_data[p]["balance"] = (platform_data[p]["balance"] or 0) + float(row.balance)

    all_platforms = ["yandex_direct", "vk_ads", "google_ads", "facebook_ads", "instagram", "telegram"]
    return [
        platform_data.get(p, {"platform": p, "is_connected": False, "balance": None, "currency": None})
        for p in all_platforms
    ]
@router.get("/export/csv")
async def export_stats_csv(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[str] = Query(None),
    campaign_ids: Optional[List[str]] = Query(None),
    goal_action_ids: Optional[List[str]] = Query(None),
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

    u_goal_action_ids = None
    if goal_action_ids:
        u_goal_action_ids = [gid for gid in goal_action_ids if gid and gid.strip()]
        if not u_goal_action_ids:
            u_goal_action_ids = None

    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not effective_client_ids:
        return StreamingResponse(io.StringIO("No data"), media_type="text/csv")
        
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()
    
    stats = StatsService.get_campaign_stats(db, effective_client_ids, d_start, d_end, platform, u_campaign_ids, u_goal_action_ids)
    
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
