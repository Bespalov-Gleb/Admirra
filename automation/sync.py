from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from core.database import SessionLocal
from core import models, security
from core.logging_utils import log_event
from automation.yandex_direct import YandexDirectAPI
from automation.yandex_metrica import YandexMetricaAPI
from automation.vk_ads import (
    VKAdsAPI,
    exchange_vk_agency_client_credentials_for_integration,
    vk_campaigns_error_needs_agency_client_retry,
)
from automation.reports import generate_weekly_report, generate_monthly_report
from automation.google_sheets import GoogleSheetsService
import asyncio
import logging
import json
import os
import uuid
from core.config import get_config

cfg = get_config()

# Yandex Direct Credentials (should ideally be in a shared config)
YANDEX_CLIENT_ID = cfg.oauth.yandex_client_id
YANDEX_CLIENT_SECRET = cfg.oauth.yandex_client_secret

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _update_or_create_stats(db: Session, model, filters: dict, data: dict, verbose: bool = True):
    """
    Helper to update an existing record or create a new one.
    Handles race conditions with unique index by retrying on IntegrityError.
    verbose: если False, не логировать каждую операцию (для массовых вставок)
    """
    existing = db.query(model).filter_by(**filters).first()
    if existing:
        if verbose:
            log_event("database", f"updating {model.__tablename__} record", filters)
        for key, value in data.items():
            setattr(existing, key, value)
    else:
        if verbose:
            log_event("database", f"creating new {model.__tablename__} record", filters)
        try:
            db.add(model(**filters, **data))
            db.flush()  # Flush to trigger unique constraint check immediately
        except IntegrityError:
            # Handle race condition: if another process created the record between query and insert
            # Re-query and update instead
            db.rollback()
            existing = db.query(model).filter_by(**filters).first()
            if existing:
                if verbose:
                    log_event("database", f"updating {model.__tablename__} record (retry after conflict)", filters)
                for key, value in data.items():
                    setattr(existing, key, value)
            else:
                # Re-raise if still not found (shouldn't happen)
                raise


def _bulk_upsert_stats_by_key(db: Session, model, rows: list):
    """
    Batched upsert by logical key (client_id, campaign_id, date) without per-row SELECT/flush.
    """
    if not rows:
        return 0

    campaign_ids = list({r["campaign_id"] for r in rows})
    dates = [r["date"] for r in rows]
    min_date = min(dates)
    max_date = max(dates)
    client_id = rows[0]["client_id"]

    existing = db.query(model).filter(
        model.client_id == client_id,
        model.campaign_id.in_(campaign_ids),
        model.date >= min_date,
        model.date <= max_date,
    ).all()
    existing_map = {(e.client_id, e.campaign_id, e.date): e for e in existing}

    updated = 0
    for row in rows:
        key = (row["client_id"], row["campaign_id"], row["date"])
        rec = existing_map.get(key)
        if rec:
            for k, v in row.items():
                setattr(rec, k, v)
            updated += 1
        else:
            db.add(model(**row))
    return updated


async def _sync_metrika_goals_for_direct(
    db: Session, 
    integration: models.Integration, 
    date_from: str, 
    date_to: str,
    access_token: str,
    selected_profile: str = None
):
    """
    Sync Metrika goals for Yandex Direct integration.
    Uses counters selected in integration settings (selected_counters), not from campaigns.
    """
    # Get selected goals
    selected_goals = []
    if integration.selected_goals:
        try:
            if isinstance(integration.selected_goals, str):
                import json
                selected_goals = json.loads(integration.selected_goals)
            else:
                selected_goals = integration.selected_goals
        except:
            selected_goals = []
    
    if not selected_goals and not integration.primary_goal_id:
        logger.debug(f"No goals selected for Direct integration {integration.id}, skipping Metrika goals sync")
        return
    
    # CRITICAL: Get counter IDs from integration settings (selected_counters), not from campaigns
    selected_counter_ids = []
    if integration.selected_counters:
        try:
            if isinstance(integration.selected_counters, str):
                import json
                selected_counter_ids = json.loads(integration.selected_counters)
            else:
                selected_counter_ids = integration.selected_counters
        except Exception as e:
            logger.warning(f"Failed to parse selected_counters for integration {integration.id}: {e}")
            selected_counter_ids = []
    
    if not selected_counter_ids:
        logger.debug(f"No counters selected in settings for Direct integration {integration.id}, skipping Metrika goals sync")
        return
    
    # Convert to set of strings for consistency
    all_counter_ids = set(str(cid) for cid in selected_counter_ids)
    
    logger.info(f"🔄 Using {len(all_counter_ids)} selected Metrika counters for Direct integration {integration.id}: {list(all_counter_ids)}")
    
    # Use Metrika API to sync goals for these counters
    from automation.yandex_metrica import YandexMetricaAPI
    metrika_api = YandexMetricaAPI(access_token, client_login=selected_profile)
    
    # Check if this is first sync
    has_existing_data = db.query(models.MetrikaGoals).filter(
        models.MetrikaGoals.integration_id == integration.id
    ).first() is not None
    
    # Determine date range: 90 days for first sync, otherwise use provided range
    sync_date_from = date_from
    sync_date_to = date_to
    
    if not has_existing_data or integration.sync_status == models.IntegrationSyncStatus.NEVER:
        end_date_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
        start_date_obj = end_date_obj - timedelta(days=89)
        sync_date_from = start_date_obj.strftime("%Y-%m-%d")
        sync_date_to = end_date_obj.strftime("%Y-%m-%d")
        logger.info(f"🔄 First sync for Direct integration {integration.id}: fetching 90 days of goals data ({sync_date_from} to {sync_date_to})")
    
    # Защита от конкурентной записи целей для одной интеграции
    sync_key = str(integration.id)
    with _metrika_goals_write_lock:
        if sync_key in _metrika_goals_write_in_progress:
            logger.info(f"⏭️ Skip goals sync: already running for integration {integration.id}")
            return
        _metrika_goals_write_in_progress.add(sync_key)

    # Use request queue
    from automation.request_queue import get_request_queue
    queue = await get_request_queue()

    try:
        # Sync goals for each counter
        for counter_id in all_counter_ids:
            # CRITICAL: First, get list of available goals for this counter
            # Вызываем напрямую (без очереди) — Management API отделён от Stat API, не блокирует очередь
            available_goals = []
            goal_names_map = {}
            try:
                goal_info = await metrika_api.get_counter_goals(counter_id)
                available_goals = [str(g.get("id")) for g in (goal_info or []) if g.get("id")]
                goal_names_map = {str(g.get("id")): g.get("name", f"Goal {g.get('id')}") for g in (goal_info or [])}
                logger.info(f"📊 Counter {counter_id} has {len(available_goals)} available goals: {available_goals[:10]}...")
            except Exception as goals_info_err:
                logger.warning(f"Failed to fetch available goals for counter {counter_id}: {goals_info_err}")
                # Continue without filtering - will fail later but at least we tried
            
            # CRITICAL: Для суммы на дашборде нужны ВСЕ цели (goal_id != "all").
            # Иначе: Метрика 5 конверсий → дашборд 1 (если синкаем только selected_goals).
            # Синкаем available_goals когда есть — сумма совпадёт с Метрикой.
            valid_goals_for_counter = []
            if available_goals:
                if selected_goals and len(selected_goals) > 0:
                    valid_goals_for_counter = [gid for gid in selected_goals if str(gid) in available_goals]
                    invalid_goals = [gid for gid in selected_goals if str(gid) not in available_goals]
                    if invalid_goals:
                        logger.warning(f"⚠️ Counter {counter_id} does not have these goals (skipping): {invalid_goals}")
                    # Синкаем ВСЕ доступные цели для корректной суммы (selected только для aggregate)
                    if len(valid_goals_for_counter) < len(available_goals):
                        valid_goals_for_counter = available_goals
                        logger.info(f"📊 Using all {len(available_goals)} goals so dashboard sum matches Metrika")
                else:
                    valid_goals_for_counter = available_goals
                    logger.info(f"📊 selected_goals empty — using all {len(available_goals)} available goals for counter {counter_id}")
            elif selected_goals and len(selected_goals) > 0:
                valid_goals_for_counter = selected_goals
                logger.warning(f"⚠️ Could not verify goal availability for counter {counter_id}, using selected_goals")
            elif integration.primary_goal_id:
                valid_goals_for_counter = [str(integration.primary_goal_id)]
                logger.info(f"📊 selected_goals empty, no available_goals — using primary_goal_id {integration.primary_goal_id}")
            
            # Sync aggregated goals
            # CRITICAL: Use visits (целевые визиты) — в этом проекте это и есть лиды.
            # 1 визит = 1 лид, даже если цель сработала несколько раз в рамках визита.
            goals_for_aggregate = valid_goals_for_counter
            primary_str = str(integration.primary_goal_id) if integration.primary_goal_id else None
            if primary_str and primary_str in (valid_goals_for_counter or []):
                goals_for_aggregate = [primary_str]
                logger.info(f"📊 Using primary_goal_id for aggregate: {integration.primary_goal_id}")
            
            metrics = "ym:s:anyGoalConversionRate,ym:s:sumGoalVisitsAny"
            if goals_for_aggregate and len(goals_for_aggregate) > 0:
                goal_metrics = [f"ym:s:goal{gid}visits" for gid in goals_for_aggregate]
                metrics = "ym:s:anyGoalConversionRate," + ",".join(goal_metrics)

            logger.info(f"📊 Requesting Stat API (goals visits) for counter {counter_id}, period {sync_date_from}–{sync_date_to}")
            goals_data = await queue.enqueue('metrica', metrika_api.get_goals_stats, counter_id, sync_date_from, sync_date_to, metrics=metrics)
            logger.info(f"📊 Goals data back from queue for counter {counter_id}: {len(goals_data or [])} rows")
            if not goals_data and goals_for_aggregate:
                # Fallback: только ym:s:sumGoalVisitsAny (агрегат по всем целям)
                logger.info(f"📊 Goal-specific metric returned 0 rows, trying ym:s:sumGoalVisitsAny")
                goals_data = await queue.enqueue('metrica', metrika_api.get_goals_stats, counter_id, sync_date_from, sync_date_to, metrics="ym:s:sumGoalVisitsAny")
            logger.info(f"📊 Metrika API returned {len(goals_data or [])} days of goals data for counter {counter_id}")
            
            # #region agent log
            _agg_saved = 0
            _sample_visits = None
            # #endregion
            # Save aggregated goals (bytime returns list of {dimensions: [{name: date}], metrics: [...]})
            for g in (goals_data or []):
                try:
                    if not isinstance(g, dict):
                        logger.warning(f"📊 Skipping non-dict goals row: type={type(g)}")
                        continue
                    stat_date = datetime.strptime(g['dimensions'][0]['name'], "%Y-%m-%d").date()
                    # CRITICAL: When primary_goal_id - use single goal value; else sum (but summing causes double count!)
                    # При fallback на sumGoalVisitsAny — только metrics[0]
                    total_visits = 0
                    if goals_for_aggregate and len(goals_for_aggregate) > 0:
                        if len(goals_for_aggregate) == 1:
                            total_visits = int(g['metrics'][1]) if len(g['metrics']) > 1 else (int(g['metrics'][0]) if g.get('metrics') else 0)
                        else:
                            for i in range(1, len(g['metrics'])):
                                total_visits += int(g['metrics'][i])
                    else:
                        total_visits = int(g['metrics'][1]) if len(g['metrics']) > 1 else (int(g['metrics'][0]) if g.get('metrics') else 0)
                    
                    existing = db.query(models.MetrikaGoals).filter(
                        models.MetrikaGoals.integration_id == integration.id,
                        models.MetrikaGoals.date == stat_date,
                        models.MetrikaGoals.goal_id == "all"
                    ).first()
                    
                    if existing:
                        existing.conversion_count = total_visits
                    else:
                        db.add(models.MetrikaGoals(
                            client_id=integration.client_id,
                            integration_id=integration.id,
                            date=stat_date,
                            goal_id="all",
                            goal_name="Selected Goals" if selected_goals else "All Goals",
                            conversion_count=total_visits
                        ))
                    _agg_saved += 1
                    if _sample_visits is None:
                        _sample_visits = total_visits
                except Exception as parse_err:
                    logger.warning(f"📊 Failed to parse/save goals row: {parse_err}. Row keys: {list(g.keys()) if isinstance(g, dict) else type(g)}")
            # #region agent log
            logger.info(f"[DEBUG sync Metrika] agg_rows_saved={_agg_saved} sample_visits={_sample_visits} integration_id={integration.id} counter_id={counter_id}")
            # #endregion
            # Commit aggregate goals immediately so dashboard shows data even if individual goals sync fails or is slow
            try:
                db.commit()
                logger.info(f"📊 Committed {_agg_saved} aggregate goal rows for counter {counter_id}")
            except Exception as commit_err:
                logger.warning(f"📊 Failed to commit aggregate goals for counter {counter_id}: {commit_err}")
            # Sync individual goals: только выбранные цели (selected_goals)
            goals_to_sync_individual = valid_goals_for_counter
            individual_goals_saved = 0
            if goals_to_sync_individual and len(goals_to_sync_individual) > 0:
                logger.info(f"📊 Syncing {len(goals_to_sync_individual)} individual goals for counter {counter_id} (selected goals only)")
                # goal_names_map already populated above when fetching available goals
                
                # Sync goals one by one with delays
                for idx, goal_id in enumerate(goals_to_sync_individual):
                    try:
                        # Add delay between requests to avoid rate limits
                        if idx > 0:
                            await asyncio.sleep(1.0)  # 1 second delay between goal requests
                        
                        # CRITICAL: Use visits (целевые визиты), а не reaches
                        goal_metrics = f"ym:s:goal{goal_id}visits"
                        goal_data = await queue.enqueue('metrica', metrika_api.get_goals_stats, counter_id, sync_date_from, sync_date_to, metrics=goal_metrics)
                        
                        goal_name = goal_names_map.get(str(goal_id), f"Goal {goal_id}") if goal_names_map else f"Goal {goal_id}"
                        
                        # Save individual goal data (goal_data may be None on API error)
                        for g in (goal_data or []):
                            if len(g.get('metrics', [])) > 0:
                                stat_date = datetime.strptime(g['dimensions'][0]['name'], "%Y-%m-%d").date()
                                visits = int(g['metrics'][0]) if g['metrics'] else 0
                                
                                existing = db.query(models.MetrikaGoals).filter(
                                    models.MetrikaGoals.integration_id == integration.id,
                                    models.MetrikaGoals.date == stat_date,
                                    models.MetrikaGoals.goal_id == str(goal_id)
                                ).first()
                                
                                if existing:
                                    existing.conversion_count = visits
                                else:
                                    db.add(models.MetrikaGoals(
                                        client_id=integration.client_id,
                                        integration_id=integration.id,
                                        date=stat_date,
                                        goal_id=str(goal_id),
                                        goal_name=goal_name,
                                        conversion_count=visits
                                    ))
                                individual_goals_saved += 1
                    except Exception as goal_err:
                        logger.warning(f"Failed to sync individual goal {goal_id} for counter {counter_id}: {goal_err}")
                        # Continue with next goal even if this one fails
                logger.info(f"📊 Saved {individual_goals_saved} individual goal records for counter {counter_id}")
        _dedupe_metrika_goals_for_integration(db, integration.id, sync_date_from, sync_date_to)
        logger.info(f"✅ Completed Metrika goals sync for Direct integration {integration.id}")
    finally:
        with _metrika_goals_write_lock:
            _metrika_goals_write_in_progress.discard(sync_key)


# Блокировка: не запускать несколько sync целей для одной интеграции одновременно
_sync_goals_in_progress: set = set()
_sync_goals_lock = __import__("threading").Lock()
_metrika_goals_write_in_progress: set = set()
_metrika_goals_write_lock = __import__("threading").Lock()


def _dedupe_metrika_goals_for_integration(
    db: Session,
    integration_id: uuid.UUID,
    date_from: str,
    date_to: str,
):
    """
    Удаляет дубли в metrika_goals по ключу (integration_id, date, goal_id),
    оставляя запись с наибольшим id.
    """
    if not integration_id:
        return

    # Важно: сначала отправляем все pending UPDATE/INSERT в БД,
    # иначе последующее raw DELETE может удалить строки, которые ORM
    # еще считает "грязными", что приводит к StaleDataError на flush.
    db.flush()

    d_from = datetime.strptime(date_from, "%Y-%m-%d").date()
    d_to = datetime.strptime(date_to, "%Y-%m-%d").date()

    res = db.execute(
        text(
            """
            DELETE FROM metrika_goals mg
            USING metrika_goals dup
            WHERE mg.id < dup.id
              AND mg.integration_id = dup.integration_id
              AND mg.date = dup.date
              AND mg.goal_id = dup.goal_id
              AND mg.integration_id = :integration_id
              AND mg.date BETWEEN :d_from AND :d_to
              AND dup.integration_id = :integration_id
              AND dup.date BETWEEN :d_from AND :d_to
            """
        ),
        {
            "integration_id": str(integration_id),
            "d_from": d_from,
            "d_to": d_to,
        },
    )
    deleted = getattr(res, "rowcount", 0) or 0
    if deleted > 0:
        logger.warning(
            "🧹 Removed %s duplicate metrika_goals rows for integration %s (%s..%s)",
            deleted,
            integration_id,
            d_from,
            d_to,
        )
    # После raw SQL очищаем identity-map, чтобы ORM не держал устаревшие row-state.
    db.expire_all()


def sync_metrika_goals_background(
    integration_id: uuid.UUID,
    date_from_str: str,
    date_to_str: str
):
    """
    Запускает только синхронизацию целей Метрики в фоне (без отчётов/баланса).
    Вызывается из get_goals при пустом ответе, чтобы подтянуть цели по требованию.
    """
    import threading
    from core.database import SessionLocal
    from core import security

    with _sync_goals_lock:
        if integration_id in _sync_goals_in_progress:
            logger.debug(f"📊 Goals sync already in progress for integration {integration_id}, skipping")
            return
        _sync_goals_in_progress.add(integration_id)

    def run_in_thread():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        db = SessionLocal()
        try:
            integration = db.query(models.Integration).filter(
                models.Integration.id == integration_id
            ).first()
            if not integration or integration.platform != models.IntegrationPlatform.YANDEX_DIRECT:
                return
            if not (integration.selected_goals or integration.primary_goal_id) or not integration.selected_counters:
                return
            access_token = security.decrypt_token(integration.access_token)
            selected_profile = integration.agency_client_login or integration.account_id
            if selected_profile and str(selected_profile).lower() in ("unknown", "none", ""):
                selected_profile = None
            new_loop.run_until_complete(
                _sync_metrika_goals_for_direct(
                    db, integration, date_from_str, date_to_str,
                    access_token, selected_profile
                )
            )
            db.commit()
            from backend_api.cache_service import CacheService
            CacheService.invalidate_client(str(integration.client_id))
            logger.info(f"✅ Goals-only sync completed for integration {integration_id}")
        except Exception as e:
            logger.error(f"❌ Goals-only sync failed for {integration_id}: {e}")
            db.rollback()
        finally:
            db.close()
            new_loop.close()
            with _sync_goals_lock:
                _sync_goals_in_progress.discard(integration_id)

    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()


async def sync_integration(db: Session, integration: models.Integration, date_from: str, date_to: str):
    """
    Syncs a single integration for a given date range.
    """
    logger.info(f"Syncing {integration.platform} for client {integration.client_id}")
    from backend_api.services.project_settings import is_project_paused, update_actual_start_date
    if is_project_paused(integration.client):
        raise ValueError("Проект на паузе: синхронизация остановлена")
    
    try:
        if integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
            access_token = security.decrypt_token(integration.access_token)
            
            # CRITICAL: Use exactly тот профиль, который пользователь выбрал на шаге 2.
            # В UI этот профиль сохраняется в integration.account_id и integration.agency_client_login.
            # Приоритет: agency_client_login (более точный), затем account_id
            # Это логин рекламного кабинета (например, "istore-habarovsk"), который используется в Client-Login заголовке
            selected_profile = None
            if integration.agency_client_login and integration.agency_client_login.lower() not in ["unknown", "none", ""]:
                selected_profile = integration.agency_client_login
            elif integration.account_id and integration.account_id.lower() not in ["unknown", "none", ""]:
                selected_profile = integration.account_id
            
            logger.info(
                f"Syncing Yandex Direct integration {integration.id} "
                f"with profile: agency_client_login='{integration.agency_client_login}', account_id='{integration.account_id}', "
                f"selected_profile='{selected_profile}'"
            )
            
            # Попробуем взять пользовательский FinanceToken для Яндекс.Директа
            # из настроек владельца проекта (User.yandex_finance_token).
            finance_token = None
            try:
                if integration.client and integration.client.owner:
                    finance_token = getattr(integration.client.owner, "yandex_finance_token", None)
                    if finance_token:
                        logger.info(f"💰 Found FinanceToken in user settings for integration {integration.id} (owner: {integration.client.owner.email})")
                        logger.debug(f"💰 FinanceToken length: {len(finance_token)} characters")
                    else:
                        logger.warning(f"⚠️ FinanceToken not found in user settings for integration {integration.id} (owner: {integration.client.owner.email})")
            except Exception as e:
                logger.warning(f"⚠️ Failed to get FinanceToken from user settings: {e}")
                finance_token = None

            api = YandexDirectAPI(access_token, client_login=selected_profile, finance_token=finance_token)
            
            # Параллельно получаем баланс и статистику кампаний
            log_event("sync", f"fetching yandex report and balance for {integration.id}")
            balance_task = api.get_balance()
            stats_task = api.get_report(date_from, date_to)
            
            # Ждем оба запроса параллельно
            balance_data, stats = await asyncio.gather(
                balance_task,
                stats_task,
                return_exceptions=True
            )
            
            # Обрабатываем баланс
            if isinstance(balance_data, Exception):
                logger.error(f"❌ Failed to fetch balance for integration {integration.id}: {balance_data}")
                logger.error(f"❌ Exception type: {type(balance_data).__name__}")
                import traceback
                logger.error(f"❌ Exception traceback: {traceback.format_exc()}")
                # Очищаем баланс, если он был сохранен ранее
                if integration.balance is not None:
                    integration.balance = None
                    integration.currency = None
                    db.commit()
                    logger.info(f"🗑️ Cleared balance for integration {integration.id} due to error")
            elif balance_data is not None:
                balance_value = balance_data.get("balance")
                currency_value = balance_data.get("currency", "RUB")
                logger.info(f"💰 Received balance data for integration {integration.id}: balance={balance_value}, currency={currency_value}")
                logger.info(f"💰 Full balance_data: {balance_data}")
                
                if balance_value is not None:
                    integration.balance = balance_value
                    integration.currency = currency_value
                    # CRITICAL: Сохраняем баланс сразу после обновления с commit, чтобы он был доступен на дашборде
                    # даже если последующая обработка статистики завершится ошибкой
                    db.commit()
                    # CRITICAL: Очищаем кеш дашборда сразу после обновления баланса, чтобы изменения были видны сразу
                    from backend_api.cache_service import CacheService
                    CacheService.invalidate_client(str(integration.client_id))
                    logger.info(f"✅ Updated and committed balance for integration {integration.id}: {integration.balance} {integration.currency}")
                    logger.info(f"🗑️ Cleared dashboard cache after updating balance")
                else:
                    logger.warning(f"⚠️ Balance data received but balance value is None for integration {integration.id}")
                    # Очищаем баланс, если он был сохранен ранее
                    if integration.balance is not None:
                        integration.balance = None
                        integration.currency = None
                        db.commit()
                        logger.info(f"🗑️ Cleared balance for integration {integration.id} (balance value is None)")
            else:
                # CRITICAL: balance_data is None - это означает, что баланс не получен (profile mismatch или другой профиль)
                logger.warning(f"⚠️ Balance not available for integration {integration.id} (may require Direct Pro or FinanceToken, or profile mismatch)")
                logger.warning(f"⚠️ FinanceToken was {'provided' if finance_token else 'NOT provided'} for this request")
                logger.warning(f"⚠️ Selected profile: '{selected_profile}'")
                # CRITICAL: Очищаем баланс ВСЕГДА, даже если он уже None или 0.0
                # Это гарантирует, что старые значения не останутся в БД
                old_balance = integration.balance
                integration.balance = None
                integration.currency = None
                db.commit()
                logger.info(f"🗑️ Cleared balance for integration {integration.id} (was: {old_balance}, now: None) - balance not available or profile mismatch")
                # Очищаем кеш дашборда, чтобы изменения были видны сразу
                from backend_api.cache_service import CacheService
                CacheService.invalidate_client(str(integration.client_id))
                logger.info(f"🗑️ Cleared dashboard cache after clearing balance")
            
            # Обрабатываем статистику
            if isinstance(stats, Exception):
                # If unauthorized and we have a refresh token, try to refresh
                if ("401" in str(stats) or "Unauthorized" in str(stats)) and integration.refresh_token:
                    from backend_api.services import IntegrationService
                    logger.info(f"Refreshing Yandex token for integration {integration.id}")
                    rt = security.decrypt_token(integration.refresh_token)
                    new_token_data = await IntegrationService.refresh_yandex_token(rt, YANDEX_CLIENT_ID, YANDEX_CLIENT_SECRET)
                    if new_token_data and "access_token" in new_token_data:
                        integration.access_token = security.encrypt_token(new_token_data["access_token"])
                        if "refresh_token" in new_token_data:
                            integration.refresh_token = security.encrypt_token(new_token_data["refresh_token"])
                        db.flush()
                        # Retry with new token (use same client_login to maintain profile filtering)
                        api = YandexDirectAPI(new_token_data["access_token"], client_login=selected_profile)
                        stats = await api.get_report(date_from, date_to)
                    else:
                        raise stats
                else:
                    raise stats
            
            try:
                log_event("sync", f"received {len(stats)} rows from yandex")
                # #region agent log
                logger.info(f"[DEBUG sync Direct] rows={len(stats)} first_row={stats[0] if stats else None} integration_id={integration.id}")
                # #endregion

                # EDGE CASE: Empty report handling
                if not stats or len(stats) == 0:
                    logger.info(f"Empty report received for integration {integration.id}. This may be normal if there are no campaigns or no activity in the date range.")

                    # CRITICAL: Sync Metrika goals BEFORE setting SUCCESS — иначе дашборд покажет «синхронизация завершена» до появления данных Метрики
                    has_goals = bool(integration.selected_goals) or bool(integration.primary_goal_id)
                    has_counters = bool(integration.selected_counters)
                    if has_goals and has_counters:
                        try:
                            logger.info(f"🔄 Syncing Metrika goals (empty report path) for Direct integration {integration.id}")
                            await _sync_metrika_goals_for_direct(db, integration, date_from, date_to, access_token, selected_profile)
                            db.commit()
                            from backend_api.cache_service import CacheService
                            CacheService.invalidate_client(str(integration.client_id))
                            logger.info(f"✅ Metrika goals synced and committed for integration {integration.id} (empty report)")
                        except Exception as goals_err:
                            logger.warning(f"Metrika goals sync failed after empty report: {goals_err}")

                    # SUCCESS только после полной синхронизации (Direct + Metrika)
                    integration.sync_status = models.IntegrationSyncStatus.SUCCESS
                    integration.error_message = None
                    integration.last_sync_at = datetime.utcnow()
                    db.commit()

                    from backend_api.cache_service import CacheService
                    CacheService.invalidate_client(str(integration.client_id))
                    logger.info(f"🗑️ Cleared dashboard cache after syncing integration {integration.id}")
                    return
            except Exception as e:
                # If unauthorized and we have a refresh token, try to refresh
                if ("401" in str(e) or "Unauthorized" in str(e)) and integration.refresh_token:
                    from backend_api.services import IntegrationService
                    logger.info(f"Refreshing Yandex token for integration {integration.id}")
                    rt = security.decrypt_token(integration.refresh_token)
                    new_token_data = await IntegrationService.refresh_yandex_token(rt, YANDEX_CLIENT_ID, YANDEX_CLIENT_SECRET)
                    if new_token_data and "access_token" in new_token_data:
                        integration.access_token = security.encrypt_token(new_token_data["access_token"])
                        if "refresh_token" in new_token_data:
                            integration.refresh_token = security.encrypt_token(new_token_data["refresh_token"])
                        db.flush()
                        # Retry with new token (use same client_login to maintain profile filtering)
                        api = YandexDirectAPI(new_token_data["access_token"], client_login=selected_profile)
                        stats = await api.get_report(date_from, date_to)
                    else:
                        raise e
                else:
                    raise e

            ext_ids = [str(s["campaign_id"]) for s in stats if s.get("campaign_id") is not None]
            existing_campaigns = db.query(models.Campaign).filter(
                models.Campaign.integration_id == integration.id,
                models.Campaign.external_id.in_(ext_ids),
            ).all()
            campaign_map = {c.external_id: c for c in existing_campaigns}
            yandex_rows = []

            for s in stats:
                campaign_external_id = str(s["campaign_id"])
                campaign = campaign_map.get(campaign_external_id)
                if not campaign:
                    logger.warning(f"[DEBUG sync SKIP] campaign_id={campaign_external_id} campaign_name={s.get('campaign_name')} not in DB for integration={integration.id}")
                    continue
                if campaign.name != s["campaign_name"]:
                    campaign.name = s["campaign_name"]

                yandex_rows.append({
                    "client_id": integration.client_id,
                    "campaign_id": campaign.id,
                    "date": datetime.strptime(s["date"], "%Y-%m-%d").date(),
                    "campaign_name": s["campaign_name"],
                    "impressions": s["impressions"],
                    "clicks": s["clicks"],
                    "cost": s["cost"],
                    "conversions": s["conversions"],
                })
                # #region agent log
                if not hasattr(sync_integration, "_yandex_logged"):
                    sync_integration._yandex_logged = set()
                if str(integration.id) not in sync_integration._yandex_logged and yandex_rows:
                    logger.info(f"[DEBUG sync SAVE] YandexStats sample={yandex_rows[0]} integration_id={integration.id} client_id={integration.client_id}")
                    sync_integration._yandex_logged.add(str(integration.id))
                # #endregion
            _bulk_upsert_stats_by_key(db, models.YandexStats, yandex_rows)

            # CRITICAL: Commit stats after processing all campaign stats
            # This ensures data is saved even if group/keyword sync fails
            db.commit()
            logger.info(f"✅ Committed {len(stats)} campaign stats records to database")
            
            # Clear cache after saving stats to ensure fresh data on dashboard
            from backend_api.cache_service import CacheService
            CacheService.invalidate_client(str(integration.client_id))
            logger.info(f"🗑️ Cleared dashboard cache after saving Yandex stats for integration {integration.id}")

            # CRITICAL: Sync Metrika goals for Direct integrations if goals are selected
            # Goals are linked to Direct campaigns through Metrika counters (CounterIds)
            has_selected_goals = bool(integration.selected_goals) or bool(integration.primary_goal_id)
            has_selected_counters = bool(integration.selected_counters)
            
            logger.info(f"🔄 Checking Metrika goals sync for Direct integration {integration.id}: "
                       f"has_selected_goals={has_selected_goals}, has_selected_counters={has_selected_counters}, "
                       f"selected_goals={integration.selected_goals}, selected_counters={integration.selected_counters}")
            
            if has_selected_goals and has_selected_counters:
                try:
                    logger.info(f"🔄 Syncing Metrika goals for Direct integration {integration.id}")
                    await _sync_metrika_goals_for_direct(db, integration, date_from, date_to, access_token, selected_profile)
                    db.commit()  # CRITICAL: Commit goals data
                    from backend_api.cache_service import CacheService
                    CacheService.invalidate_client(str(integration.client_id))
                    logger.info(f"✅ Successfully synced and committed Metrika goals for Direct integration {integration.id}")
                    logger.info(f"🗑️ Cleared dashboard cache after Metrika goals sync")
                except Exception as goals_err:
                    logger.error(f"❌ Failed to sync Metrika goals for Direct integration {integration.id}: {goals_err}", exc_info=True)
                    # Don't fail the entire sync if goals sync fails
            elif has_selected_goals and not has_selected_counters:
                logger.warning(f"⚠️ Direct integration {integration.id} has selected goals but no selected_counters. "
                              f"Goals sync skipped. Please select Metrika counters in integration settings.")
            elif not has_selected_goals:
                logger.debug(f"Direct integration {integration.id} has no selected goals, skipping Metrika goals sync")

            # Group and Keyword stats - получаем параллельно
            # CRITICAL: Filter by integration_id to avoid saving data from other profiles
            group_task = api.get_report(date_from, date_to, level="group")
            keyword_task = api.get_report(date_from, date_to, level="keyword")
            
            group_stats_result, keyword_stats_result = await asyncio.gather(
                group_task,
                keyword_task,
                return_exceptions=True
            )
            
            # Обрабатываем group stats
            if isinstance(group_stats_result, Exception):
                logger.warning(f"Error syncing group stats: {group_stats_result}")
                group_stats_result = []
            
            level_stats_list = [
                ("group", group_stats_result if not isinstance(group_stats_result, Exception) else []),
                ("keyword", keyword_stats_result if not isinstance(keyword_stats_result, Exception) else [])
            ]

            # Оптимизация: не делаем SELECT campaign для каждой строки статистики.
            # Предзагружаем названия кампаний этой интеграции в set.
            integration_campaign_names = {
                row[0]
                for row in db.query(models.Campaign.name)
                .filter(models.Campaign.integration_id == integration.id)
                .all()
                if row and row[0]
            }
            
            for level, level_stats in level_stats_list:
                try:
                    for l in level_stats:
                        # CRITICAL: Verify that campaign_name belongs to this integration
                        # This prevents saving stats for campaigns from other profiles
                        campaign_name = l.get('campaign_name', '')
                        if campaign_name not in integration_campaign_names:
                            logger.debug(
                                f"Skipping {level} stats for campaign '{campaign_name}' - "
                                f"not found in DB for integration {integration.id}. "
                                f"This campaign likely belongs to a different profile."
                            )
                            continue
                        
                        if level == "group":
                            filters = {
                                "client_id": integration.client_id,
                                "date": datetime.strptime(l['date'], "%Y-%m-%d").date(),
                                "campaign_name": campaign_name,
                                "group_name": l['name']
                            }
                            data = {
                                "impressions": l['impressions'],
                                "clicks": l['clicks'],
                                "cost": l['cost'],
                                "conversions": l['conversions']
                            }
                            _update_or_create_stats(db, models.YandexGroups, filters, data, verbose=False)
                        else:
                            filters = {
                                "client_id": integration.client_id,
                                "date": datetime.strptime(l['date'], "%Y-%m-%d").date(),
                                "campaign_name": campaign_name,
                                "keyword": l['name']
                            }
                            data = {
                                "impressions": l['impressions'],
                                "clicks": l['clicks'],
                                "cost": l['cost'],
                                "conversions": l['conversions']
                            }
                            _update_or_create_stats(db, models.YandexKeywords, filters, data, verbose=False)
                except Exception as e:
                    logger.warning(f"Error syncing {level} stats: {e}")
                    continue

        elif integration.platform == models.IntegrationPlatform.VK_ADS:
            access_token = security.decrypt_token(integration.access_token)
            api = VKAdsAPI(access_token, integration.account_id)
            
            # Получаем баланс перед синхронизацией статистики
            try:
                balance_data = await api.get_balance()
                if balance_data:
                    integration.balance = balance_data.get("balance")
                    integration.currency = balance_data.get("currency", "RUB")
                    # CRITICAL: Сохраняем баланс сразу после обновления с commit, чтобы он был доступен на дашборде
                    # даже если последующая обработка статистики завершится ошибкой
                    db.commit()
                    # CRITICAL: Очищаем кеш дашборда сразу после обновления баланса, чтобы изменения были видны сразу
                    from backend_api.cache_service import CacheService
                    CacheService.invalidate_client(str(integration.client_id))
                    logger.info(f"✅ Updated and committed balance for integration {integration.id}: {integration.balance} {integration.currency}")
                    logger.info(f"🗑️ Cleared dashboard cache after updating balance")
                else:
                    logger.debug(f"Balance not available for integration {integration.id}")
            except Exception as balance_err:
                logger.warning(f"Failed to fetch balance for integration {integration.id}: {balance_err}")

            # Синхронизируем список кампаний и их целевые действия
            goal_actions_synced = 0
            campaigns_updated = 0

            async def _vk_get_campaigns_with_agency_fallback():
                nonlocal api
                try:
                    return await api.get_campaigns()
                except Exception as ex:
                    if not vk_campaigns_error_needs_agency_client_retry(ex):
                        raise
                    vk_secret = (os.getenv("VK_CLIENT_SECRET") or "").strip()
                    if not vk_secret:
                        raise
                    from backend_api.integrations import VK_CLIENT_ID

                    plain = security.decrypt_token(integration.access_token)
                    td = await exchange_vk_agency_client_credentials_for_integration(
                        client_id=VK_CLIENT_ID,
                        client_secret=vk_secret,
                        agency_access_token=plain,
                        agency_client_login=integration.agency_client_login,
                        account_id=integration.account_id,
                    )
                    if not td:
                        raise ex
                    integration.access_token = security.encrypt_token(td["access_token"])
                    if td.get("refresh_token"):
                        integration.refresh_token = security.encrypt_token(
                            td["refresh_token"]
                        )
                    exp_in = td.get("expires_in")
                    if exp_in is not None:
                        try:
                            integration.expires_at = datetime.now(timezone.utc) + timedelta(
                                seconds=int(exp_in)
                            )
                        except (TypeError, ValueError):
                            pass
                    db.commit()
                    new_plain = security.decrypt_token(integration.access_token)
                    api = VKAdsAPI(new_plain, integration.account_id)
                    return await api.get_campaigns()

            try:
                vk_campaigns = await _vk_get_campaigns_with_agency_fallback()
                campaign_ids = [str(c.get("id")) for c in vk_campaigns if c.get("id")]
                
                # Пытаемся получить целевые действия из статистики
                # Используем последние 30 дней для получения актуальных целей
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
                goal_actions_map = await api.get_goal_actions_from_statistics(
                    campaign_ids, 
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d")
                )
                
                # НОВОЕ: Получаем целевые действия через AdGroup → package_id → Packages.objective
                # (согласно рекомендации поддержки VK Ads)
                try:
                    goal_actions_from_packages = await api.get_goal_actions_from_packages(campaign_ids)
                    
                    # Объединяем результаты: приоритет у packages (более точный источник)
                    for camp_id, (pkg_id, pkg_name) in goal_actions_from_packages.items():
                        goal_actions_map[camp_id] = (pkg_id, pkg_name)
                except Exception as pkg_err:
                    logger.error(f"❌ ОШИБКА при вызове get_goal_actions_from_packages: {pkg_err}", exc_info=True)
                
                for c in vk_campaigns:
                    external_id = str(c.get("id") or "")
                    if not external_id:
                        continue
                    campaign = db.query(models.Campaign).filter_by(
                        integration_id=integration.id,
                        external_id=external_id
                    ).first()
                    incoming_name = c.get("name")
                    if not campaign:
                        campaign = models.Campaign(
                            integration_id=integration.id,
                            external_id=external_id,
                            name=incoming_name or f"Campaign {external_id}",
                            is_active=True
                        )
                        db.add(campaign)
                        db.flush()
                    else:
                        if incoming_name and not str(incoming_name).startswith("Campaign ") and campaign.name != incoming_name:
                            campaign.name = incoming_name

                    # Пробуем получить целевое действие из статистики
                    goal_action_id, goal_action_name = goal_actions_map.get(external_id, (None, None))
                    
                    # Если не нашли в статистике, пробуем из ответа ad_plans
                    if not goal_action_id and not goal_action_name:
                        goal_action_id = c.get("goal_action_id")
                        goal_action_name = c.get("goal_action_name")
                    
                    if goal_action_id or goal_action_name:
                        campaign.vk_goal_action_id = goal_action_id
                        campaign.vk_goal_action_name = goal_action_name
                        goal_actions_synced += 1
                    campaigns_updated += 1
                
                db.commit()
            except Exception as campaigns_err:
                logger.error(f"❌ Ошибка синхронизации кампаний VK: {campaigns_err}")
                db.rollback()
            
            try:
                log_event("sync", f"fetching vk statistics for {integration.id}")
                stats = await api.get_statistics(date_from, date_to)
                log_event("sync", f"received {len(stats)} rows from vk")
            except Exception as e:
                # VK Token Refresh: Try refresh_token first (OAuth flow), then fallback to client_credentials
                # Согласно документации VK ID: Access token живет 1 час, refresh_token используется для обновления
                if ("401" in str(e) or "Unauthorized" in str(e)) and integration.refresh_token:
                    from backend_api.services import IntegrationService
                    logger.info(f"🔄 Refreshing VK token using refresh_token for integration {integration.id}")
                    rt = security.decrypt_token(integration.refresh_token)
                    # Используем VK_CLIENT_ID и VK_CLIENT_SECRET из integrations.py
                    from backend_api.integrations import VK_CLIENT_ID, VK_CLIENT_SECRET
                    new_token_data = await IntegrationService.refresh_vk_token(rt, VK_CLIENT_ID, VK_CLIENT_SECRET)
                    
                    if new_token_data and "access_token" in new_token_data:
                        integration.access_token = security.encrypt_token(new_token_data["access_token"])
                        if "refresh_token" in new_token_data:
                            integration.refresh_token = security.encrypt_token(new_token_data["refresh_token"])
                        db.flush()
                        api = VKAdsAPI(new_token_data["access_token"], integration.account_id)
                        stats = await api.get_statistics(date_from, date_to)
                        logger.info(f"✅ VK token refreshed successfully, retrying statistics fetch")
                    else:
                        logger.warning(f"⚠️ VK refresh_token failed, trying client_credentials fallback")
                        # Fallback to client_credentials if refresh_token fails
                        if integration.platform_client_id and integration.platform_client_secret:
                            cid = security.decrypt_token(integration.platform_client_id)
                            cs = security.decrypt_token(integration.platform_client_secret)
                            vk_data = await IntegrationService.exchange_vk_token(cid, cs)
                            if vk_data and "access_token" in vk_data:
                                integration.access_token = security.encrypt_token(vk_data["access_token"])
                                db.flush()
                                api = VKAdsAPI(vk_data["access_token"], integration.account_id)
                                stats = await api.get_statistics(date_from, date_to)
                            else:
                                raise e
                        else:
                            raise e
                # Fallback: VK Refresh using Client Credentials (if no refresh_token available)
                elif integration.platform_client_id and integration.platform_client_secret:
                    from backend_api.services import IntegrationService
                    logger.info(f"🔄 Refreshing VK token using client_credentials for integration {integration.id}")
                    cid = security.decrypt_token(integration.platform_client_id)
                    cs = security.decrypt_token(integration.platform_client_secret)
                    vk_data = await IntegrationService.exchange_vk_token(cid, cs)
                    if vk_data and "access_token" in vk_data:
                        integration.access_token = security.encrypt_token(vk_data["access_token"])
                        db.flush()
                        api = VKAdsAPI(vk_data["access_token"], integration.account_id)
                        stats = await api.get_statistics(date_from, date_to)
                    else:
                        raise e
                else:
                    raise e

            ext_ids = [str(s.get("campaign_id", "")) for s in stats if s.get("campaign_id")]
            existing_campaigns = db.query(models.Campaign).filter(
                models.Campaign.integration_id == integration.id,
                models.Campaign.external_id.in_(ext_ids),
            ).all()
            campaign_map = {c.external_id: c for c in existing_campaigns}

            vk_rows = []
            for s in stats:
                campaign_external_id = str(s.get("campaign_id", ""))
                campaign_name = s.get("campaign_name", "Unknown VK Campaign")
                campaign = campaign_map.get(campaign_external_id)
                if not campaign:
                    campaign = models.Campaign(
                        integration_id=integration.id,
                        external_id=campaign_external_id,
                        name=campaign_name,
                        is_active=True,
                    )
                    db.add(campaign)
                    db.flush()
                    campaign_map[campaign_external_id] = campaign
                elif campaign.name != campaign_name:
                    campaign.name = campaign_name

                if not campaign.is_active:
                    continue

                vk_rows.append({
                    "client_id": integration.client_id,
                    "campaign_id": campaign.id,
                    "date": datetime.strptime(s["date"], "%Y-%m-%d").date(),
                    "campaign_name": campaign_name,
                    "impressions": s["impressions"],
                    "clicks": s["clicks"],
                    "cost": s["cost"],
                    "conversions": s["conversions"],
                    "cpc": s.get("cpc"),
                    "cpa": s.get("cpa"),
                })
            _bulk_upsert_stats_by_key(db, models.VKStats, vk_rows)
            processed_count = len(vk_rows)
            db.commit()
            
            # Clear cache after saving stats to ensure fresh data on dashboard
            from backend_api.cache_service import CacheService
            CacheService.invalidate_client(str(integration.client_id))
            
            # ИТОГОВАЯ СВОДКА В КОНЦЕ
            logger.info("=" * 80)
            logger.info(f"✅ VK ADS СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА для интеграции {integration.id}")
            logger.info(f"   📊 Статистика: {processed_count} записей сохранено")
            logger.info(f"   📋 Кампании: {campaigns_updated} обновлено")
            logger.info(f"   🎯 Целевые действия: {goal_actions_synced} синхронизировано")
            if goal_actions_synced == 0:
                logger.warning(f"   ⚠️ ВНИМАНИЕ: Целевые действия не найдены!")
                logger.warning(f"   💡 Проверь структуру ответа API - возможно нужен другой endpoint")
            if hasattr(api, "debug_events") and api.debug_events:
                logger.info("   🔎 VK ADS API ОТВЕТЫ (ПОСЛЕДНИЕ):")
                for event in api.debug_events[-60:]:
                    logger.info(f"     - {event}")
            logger.info("=" * 80)

        elif integration.platform == models.IntegrationPlatform.YANDEX_METRIKA:
            if not integration.account_id:
                logger.warning(f"No counter ID (account_id) for Metrica integration {integration.id}")
                integration.error_message = "No counter ID (account_id) configured"
                integration.sync_status = models.IntegrationSyncStatus.FAILED
                return
            
            access_token = security.decrypt_token(integration.access_token)
            
            # CRITICAL: Use selected profile (agency_client_login) to ensure we sync stats for the correct profile
            # This ensures statistics are synced only for counters belonging to the selected profile
            selected_profile = integration.agency_client_login if integration.agency_client_login and integration.agency_client_login.lower() != "unknown" else None
            logger.info(f"Syncing Yandex Metrika integration {integration.id} with profile: {selected_profile} (counter_id={integration.account_id})")
            
            api = YandexMetricaAPI(access_token, client_login=selected_profile)
            
            # Filter by selected goals if provided
            selected_goals = []
            if integration.selected_goals:
                try:
                    if isinstance(integration.selected_goals, str):
                        import json
                        selected_goals = json.loads(integration.selected_goals)
                    else:
                        selected_goals = integration.selected_goals
                except:
                    selected_goals = []

            # CRITICAL: Check if this is first sync or if we need to fetch 90 days of historical data
            # Check if we have any goals data in DB for this integration
            has_existing_data = db.query(models.MetrikaGoals).filter(
                models.MetrikaGoals.integration_id == integration.id
            ).first() is not None
            
            # Determine actual date range: 90 days for first sync, otherwise use provided range
            sync_date_from = date_from
            sync_date_to = date_to
            
            if not has_existing_data or integration.sync_status == models.IntegrationSyncStatus.NEVER:
                # First sync: fetch 90 days of historical data
                end_date_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
                start_date_obj = end_date_obj - timedelta(days=89)  # 90 days total (including today)
                sync_date_from = start_date_obj.strftime("%Y-%m-%d")
                sync_date_to = end_date_obj.strftime("%Y-%m-%d")
                logger.info(f"🔄 First sync for integration {integration.id}: fetching 90 days of goals data ({sync_date_from} to {sync_date_to})")
            else:
                logger.info(f"🔄 Regular sync for integration {integration.id}: fetching goals data ({sync_date_from} to {sync_date_to})")

            # CRITICAL: Use visits (целевые визиты), а не reaches
            metrics = "ym:s:anyGoalConversionRate,ym:s:sumGoalVisitsAny"
            if selected_goals and len(selected_goals) > 0:
                goal_metrics = [f"ym:s:goal{gid}visits" for gid in selected_goals]
                metrics = "ym:s:anyGoalConversionRate," + ",".join(goal_metrics)

            # CRITICAL: Use request queue to avoid 429 errors
            from automation.request_queue import get_request_queue
            queue = await get_request_queue()
            goals_data = await queue.enqueue('metrica', api.get_goals_stats, integration.account_id, sync_date_from, sync_date_to, metrics=metrics)
            
            # Sync individual goals: только выбранные цели (selected_goals)
            if selected_goals and len(selected_goals) > 0:
                goal_info_list = await queue.enqueue('metrica', api.get_counter_goals, integration.account_id) or []
                for goal_id in selected_goals:
                    try:
                        # CRITICAL: Use visits (целевые визиты), а не reaches
                        goal_metrics = f"ym:s:goal{goal_id}visits"
                        goal_data = await queue.enqueue('metrica', api.get_goals_stats, integration.account_id, sync_date_from, sync_date_to, metrics=goal_metrics)
                        
                        # Get goal name from API (goal_info_list already fetched above)
                        goal_name = "Unknown Goal"
                        for g in goal_info_list:
                            if str(g.get("id")) == str(goal_id):
                                goal_name = g.get("name", f"Goal {goal_id}")
                                break
                        
                        # Save individual goal data
                        for g in (goal_data or []):
                            if len(g.get('metrics', [])) > 0:
                                stat_date = datetime.strptime(g['dimensions'][0]['name'], "%Y-%m-%d").date()
                                visits = int(g['metrics'][0]) if g['metrics'] else 0
                                
                                existing = db.query(models.MetrikaGoals).filter(
                                    models.MetrikaGoals.integration_id == integration.id,
                                    models.MetrikaGoals.date == stat_date,
                                    models.MetrikaGoals.goal_id == str(goal_id)
                                ).first()
                                
                                if existing:
                                    existing.conversion_count = visits
                                else:
                                    db.add(models.MetrikaGoals(
                                        client_id=integration.client_id,
                                        integration_id=integration.id,
                                        date=stat_date,
                                        goal_id=str(goal_id),
                                        goal_name=goal_name,
                                        conversion_count=visits
                                    ))
                    except Exception as goal_err:
                        logger.warning(f"Failed to sync individual goal {goal_id}: {goal_err}")
            
            # Sync aggregated "all" goals data
            for g in goals_data:
                stat_date = datetime.strptime(g['dimensions'][0]['name'], "%Y-%m-%d").date()
                
                # CRITICAL: Используем visits (целевые визиты)
                total_visits = 0
                if selected_goals and len(selected_goals) > 0:
                    for i in range(1, len(g['metrics'])):
                        total_visits += int(g['metrics'][i])
                else:
                    total_visits = int(g['metrics'][1]) if len(g['metrics']) > 1 else 0

                existing = db.query(models.MetrikaGoals).filter(
                    models.MetrikaGoals.integration_id == integration.id,  # CRITICAL: Check by integration, not client
                    models.MetrikaGoals.date == stat_date,
                    models.MetrikaGoals.goal_id == "all"
                ).first()

                if existing:
                    existing.conversion_count = total_visits
                    existing.integration_id = integration.id  # Update integration_id for existing records
                else:
                    db.add(models.MetrikaGoals(
                        client_id=integration.client_id,
                        integration_id=integration.id,  # NEW: Link to specific integration
                        date=stat_date,
                        goal_id="all",
                        goal_name="Selected Goals" if selected_goals else "All Goals",
                        conversion_count=total_visits
                    ))

        # Update status on success
        integration.sync_status = models.IntegrationSyncStatus.SUCCESS
        integration.error_message = None
        integration.last_sync_at = datetime.utcnow()
        update_actual_start_date(db, integration.client_id)

        try:
            from backend_api.services.detector import run_detector_for_client
            run_detector_for_client(db, integration.client_id)
        except Exception as det_err:
            logger.exception("Detector failed for client %s: %s", integration.client_id, det_err)

        # CRITICAL: Clear dashboard cache after successful sync to ensure fresh data
        # This prevents stale cached data from appearing on the dashboard
        from backend_api.cache_service import CacheService
        CacheService.invalidate_client(str(integration.client_id))
        logger.info(f"🗑️ Cleared dashboard cache after syncing integration {integration.id}")

    except Exception as e:
        logger.error(f"Sync failed for {integration.id}: {e}")
        integration.sync_status = models.IntegrationSyncStatus.FAILED
        integration.error_message = f"{type(e).__name__}: {str(e)}"
        db.flush()
        # Создаём in-app уведомление об ошибке синхронизации
        try:
            from backend_api.services.notifications import create_notification
            owner_id = integration.client.owner_id if integration.client else None
            if owner_id:
                platform_name = integration.platform.value if integration.platform else "интеграции"
                create_notification(
                    db,
                    user_id=owner_id,
                    type="sync_failed",
                    title=f"Ошибка синхронизации {platform_name}",
                    body=str(e)[:200],
                    meta={"integration_id": str(integration.id)},
                )
                db.flush()
        except Exception as notify_err:
            logger.warning(f"Failed to create sync-failed notification: {notify_err}")
        raise e

async def sync_data(days: int = 7, max_concurrent: int = 5):
    """
    Synchronize all integrations with parallel processing.
    
    Args:
        days: Number of days to sync (default 7)
        max_concurrent: Maximum number of concurrent sync operations (default 5)
    """
    db: Session = SessionLocal()
    try:
        integrations = (
            db.query(models.Integration)
            .join(models.Client, models.Client.id == models.Integration.client_id)
            .filter(models.Client.status == models.ClientStatus.ACTIVE)
            .all()
        )
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        date_from = start_date.strftime("%Y-%m-%d")
        date_to = end_date.strftime("%Y-%m-%d")

        # Use asyncio.gather() for parallel synchronization with semaphore for rate limiting
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def sync_with_semaphore(integration):
            async with semaphore:
                try:
                    await sync_integration(db, integration, date_from, date_to)
                except Exception as e:
                    # Log error but don't stop other syncs
                    logger.error(f"Failed to sync integration {integration.id}: {e}")
        
        # Run all syncs in parallel (with semaphore limiting concurrency)
        logger.info(f"Starting parallel sync for {len(integrations)} integrations (max {max_concurrent} concurrent)")
        await asyncio.gather(*[sync_with_semaphore(i) for i in integrations], return_exceptions=True)
            
        db.commit()

        # Generate reports for each client
        clients = db.query(models.Client).filter(models.Client.status == models.ClientStatus.ACTIVE).all()
        for client in clients:
            try:
                generate_weekly_report(db, client.id, end_date)
                generate_monthly_report(db, client.id, end_date.year, end_date.month)
            except Exception as e:
                logger.error(f"Error generating reports for client {client.id}: {e}")

        # Google Sheets Export
        gs = GoogleSheetsService()
        for client in clients:
            spreadsheet_id = getattr(client, 'spreadsheet_id', None)
            if spreadsheet_id and gs.service:
                try:
                    summary = gs.export_all(spreadsheet_id, client.id, db)
                    logger.info(f"Data exported to Google Sheets for client {client.name}: {summary}")
                except Exception as e:
                    logger.error(f"Error exporting to Sheets for client {client.name}: {e}")

        logger.info("Данные успешно синхронизированы и отчеты обновлены")
    except Exception as e:
        logger.error(f"Ошибка при синхронизации: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    days = 7
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            print("Usage: python -m automation.sync [days]")
            sys.exit(1)
    
    asyncio.run(sync_data(days=days))
