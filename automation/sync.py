from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from core.database import SessionLocal
from core import models, security
from core.logging_utils import log_event
from automation.yandex_direct import YandexDirectAPI
from automation.yandex_metrica import YandexMetricaAPI
from automation.vk_ads import VKAdsAPI
from automation.reports import generate_weekly_report, generate_monthly_report
from automation.google_sheets import GoogleSheetsService
from datetime import datetime, timedelta
import asyncio
import logging
import json
import os

# Yandex Direct Credentials (should ideally be in a shared config)
YANDEX_CLIENT_ID = os.getenv("YANDEX_CLIENT_ID", "e2a052c8cac54caeb9b1b05a593be932")
YANDEX_CLIENT_SECRET = os.getenv("YANDEX_CLIENT_SECRET", "a3ff5920d00e4ee7b8a8019e33cdaaf0")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _update_or_create_stats(db: Session, model, filters: dict, data: dict):
    """
    Helper to update an existing record or create a new one.
    """
    existing = db.query(model).filter_by(**filters).first()
    if existing:
        log_event("database", f"updating {model.__tablename__} record", filters)
        for key, value in data.items():
            setattr(existing, key, value)
    else:
        log_event("database", f"creating new {model.__tablename__} record", filters)
        db.add(model(**filters, **data))

async def sync_integration(db: Session, integration: models.Integration, date_from: str, date_to: str):
    """
    Syncs a single integration for a given date range.
    """
    logger.info(f"Syncing {integration.platform} for client {integration.client_id}")
    
    try:
        if integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
            access_token = security.decrypt_token(integration.access_token)
            
            # CRITICAL: Use exactly тот профиль, который пользователь выбрал на шаге 2.
            # В UI этот профиль сохраняется в integration.account_id.
            # agency_client_login раньше использовался как «подстраховка», но это приводило
            # к рассинхрону, когда в нём оставался старый логин другого профиля.
            # Теперь для всей фильтрации Direct используем только account_id.
            selected_profile = integration.account_id if integration.account_id and integration.account_id.lower() != "unknown" else None
            logger.info(
                f"Syncing Yandex Direct integration {integration.id} "
                f"with profile (account_id)={selected_profile}, agency_client_login={integration.agency_client_login}"
            )
            
            api = YandexDirectAPI(access_token, client_login=selected_profile)
            
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
                logger.warning(f"Failed to fetch balance for integration {integration.id}: {balance_data}")
            elif balance_data:
                integration.balance = balance_data.get("balance")
                integration.currency = balance_data.get("currency", "RUB")
                logger.info(f"Updated balance for integration {integration.id}: {integration.balance} {integration.currency}")
            else:
                logger.debug(f"Balance not available for integration {integration.id} (may require Direct Pro)")
            
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
                
                # EDGE CASE: Empty report handling
                if not stats or len(stats) == 0:
                    logger.info(f"Empty report received for integration {integration.id}. This may be normal if there are no campaigns or no activity in the date range.")
                    integration.sync_status = models.IntegrationSyncStatus.SUCCESS
                    integration.last_sync_at = datetime.utcnow()
                    db.commit()
                    
                    # CRITICAL: Clear dashboard cache after successful sync to ensure fresh data
                    # This prevents stale cached data from appearing on the dashboard
                    from backend_api.cache_service import CacheService
                    CacheService.clear()
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

            for s in stats:
                # 1. Ensure Campaign exists in DB
                campaign_external_id = str(s['campaign_id'])
                campaign = db.query(models.Campaign).filter_by(
                    integration_id=integration.id,
                    external_id=campaign_external_id
                ).first()
                
                # CRITICAL FIX: Skip stats for campaigns not in DB
                # This happens when Reports API returns data for ALL accessible accounts
                # but discover-campaigns only found campaigns for the token's account
                if not campaign:
                    logger.warning(
                        f"Skipping stats for campaign '{s['campaign_name']}' (ID: {campaign_external_id}) - "
                        f"not found in DB for integration {integration.id}. "
                        f"This campaign likely belongs to a different account that shares the token."
                    )
                    continue
                
                # Update campaign name if changed
                if campaign.name != s['campaign_name']:
                    campaign.name = s['campaign_name']
                    db.flush()

                # CRITICAL: Sync stats for ALL campaigns, not just active ones
                # This ensures statistics are available even for stopped/paused campaigns
                # The is_active flag is for user selection, not for data syncing
                # if not campaign.is_active:
                #     continue

                # 2. Update Stats
                filters = {
                    "client_id": integration.client_id,
                    "campaign_id": campaign.id,
                    "date": datetime.strptime(s['date'], "%Y-%m-%d").date()
                }
                data = {
                    "campaign_name": s['campaign_name'], 
                    "impressions": s['impressions'],
                    "clicks": s['clicks'],
                    "cost": s['cost'],
                    "conversions": s['conversions']
                }
                logger.info(f"💾 Saving stats for campaign '{campaign.name}' (ID: {campaign.external_id}) on {s['date']}: impressions={s['impressions']}, clicks={s['clicks']}, cost={s['cost']}")
                _update_or_create_stats(db, models.YandexStats, filters, data)
            
            # CRITICAL: Commit stats after processing all campaign stats
            # This ensures data is saved even if group/keyword sync fails
            db.commit()
            logger.info(f"✅ Committed {len(stats)} campaign stats records to database")
            
            # Clear cache after saving stats to ensure fresh data on dashboard
            from backend_api.cache_service import CacheService
            CacheService.clear()
            logger.info(f"🗑️ Cleared dashboard cache after saving Yandex stats for integration {integration.id}")

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
            
            for level, level_stats in level_stats_list:
                try:
                    for l in level_stats:
                        # CRITICAL: Verify that campaign_name belongs to this integration
                        # This prevents saving stats for campaigns from other profiles
                        campaign_name = l.get('campaign_name', '')
                        matching_campaign = db.query(models.Campaign).filter(
                            models.Campaign.integration_id == integration.id,
                            models.Campaign.name == campaign_name
                        ).first()
                        
                        if not matching_campaign:
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
                            _update_or_create_stats(db, models.YandexGroups, filters, data)
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
                            _update_or_create_stats(db, models.YandexKeywords, filters, data)
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
                    logger.info(f"Updated balance for integration {integration.id}: {integration.balance} {integration.currency}")
                else:
                    logger.debug(f"Balance not available for integration {integration.id}")
            except Exception as balance_err:
                logger.warning(f"Failed to fetch balance for integration {integration.id}: {balance_err}")
            
            try:
                log_event("sync", f"fetching vk statistics for {integration.id}")
                stats = await api.get_statistics(date_from, date_to)
                log_event("sync", f"received {len(stats)} rows from vk")
            except Exception as e:
                # VK Refresh using Client Credentials
                if integration.platform_client_id and integration.platform_client_secret:
                    from backend_api.services import IntegrationService
                    logger.info(f"Refreshing VK token for integration {integration.id}")
                    cid = security.decrypt_token(integration.platform_client_id)
                    cs = security.decrypt_token(integration.platform_client_secret)
                    vk_data = await IntegrationService.exchange_vk_token(cid, cs)
                    if vk_data and "access_token" in vk_data:
                        integration.access_token = security.encrypt_token(vk_data["access_token"])
                        db.flush()
                        api = VKAdsAPI(vk_data["access_token"], integration.account_id)
                        stats = await api.get_statistics(date_from, date_to)
                    else: raise e
                else: raise e

            for s in stats:
                campaign_external_id = str(s.get('campaign_id', ''))
                campaign_name = s.get('campaign_name', 'Unknown VK Campaign')
                
                campaign = None
                if campaign_external_id:
                    campaign = db.query(models.Campaign).filter_by(
                        integration_id=integration.id,
                        external_id=campaign_external_id
                    ).first()
                
                if not campaign:
                    campaign = models.Campaign(
                        integration_id=integration.id,
                        external_id=campaign_external_id,
                        name=campaign_name,
                        is_active=True
                    )
                    db.add(campaign)
                    db.flush()
                elif campaign.name != campaign_name:
                    campaign.name = campaign_name
                    db.flush()

                if not campaign.is_active: continue

                filters = {
                    "client_id": integration.client_id,
                    "campaign_id": campaign.id,
                    "date": datetime.strptime(s['date'], "%Y-%m-%d").date()
                }
                data = {
                    "campaign_name": campaign_name,
                    "impressions": s['impressions'],
                    "clicks": s['clicks'],
                    "cost": s['cost'],
                    "conversions": s['conversions']
                }
                _update_or_create_stats(db, models.VKStats, filters, data)

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

            metrics = "ym:s:anyGoalConversionRate,ym:s:sumGoalReachesAny"
            if selected_goals and len(selected_goals) > 0:
                goal_metrics = [f"ym:s:goal{gid}reaches" for gid in selected_goals]
                metrics = "ym:s:anyGoalConversionRate," + ",".join(goal_metrics)

            goals_data = await api.get_goals_stats(integration.account_id, date_from, date_to, metrics=metrics)
            
            for g in goals_data:
                stat_date = datetime.strptime(g['dimensions'][0]['name'], "%Y-%m-%d").date()
                
                # If specific goals were requested, sum their reaches
                total_reaches = 0
                if selected_goals and len(selected_goals) > 0:
                    for i in range(1, len(g['metrics'])):
                        total_reaches += int(g['metrics'][i])
                else:
                    total_reaches = int(g['metrics'][1]) if len(g['metrics']) > 1 else 0

                existing = db.query(models.MetrikaGoals).filter(
                    models.MetrikaGoals.integration_id == integration.id,  # CRITICAL: Check by integration, not client
                    models.MetrikaGoals.date == stat_date,
                    models.MetrikaGoals.goal_id == "all"
                ).first()

                if existing:
                    existing.conversion_count = total_reaches
                    existing.integration_id = integration.id  # Update integration_id for existing records
                else:
                    db.add(models.MetrikaGoals(
                        client_id=integration.client_id,
                        integration_id=integration.id,  # NEW: Link to specific integration
                        date=stat_date,
                        goal_id="all",
                        goal_name="Selected Goals" if selected_goals else "All Goals",
                        conversion_count=total_reaches
                    ))

        # Update status on success
        integration.sync_status = models.IntegrationSyncStatus.SUCCESS
        integration.error_message = None
        integration.last_sync_at = datetime.utcnow()
        
        # CRITICAL: Clear dashboard cache after successful sync to ensure fresh data
        # This prevents stale cached data from appearing on the dashboard
        from backend_api.cache_service import CacheService
        CacheService.clear()
        logger.info(f"🗑️ Cleared dashboard cache after syncing integration {integration.id}")

    except Exception as e:
        logger.error(f"Sync failed for {integration.id}: {e}")
        integration.sync_status = models.IntegrationSyncStatus.FAILED
        integration.error_message = f"{type(e).__name__}: {str(e)}"
        db.flush()
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
        integrations = db.query(models.Integration).all()
        
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
        clients = db.query(models.Client).all()
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
                    gs.export_raw_data(spreadsheet_id, client.id, db)
                    gs.export_reports(spreadsheet_id, client.id, db)
                    gs.export_metrika_goals(spreadsheet_id, client.id, db)
                    logger.info(f"Data exported to Google Sheets for client {client.name}")
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
