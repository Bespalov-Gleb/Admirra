from sqlalchemy.orm import Session
from core.database import SessionLocal
from core import models, security
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
        for key, value in data.items():
            setattr(existing, key, value)
    else:
        db.add(model(**filters, **data))

async def sync_integration(db: Session, integration: models.Integration, date_from: str, date_to: str):
    """
    Syncs a single integration for a given date range.
    """
    logger.info(f"Syncing {integration.platform} for client {integration.client_id}")
    
    try:
        if integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
            access_token = security.decrypt_token(integration.access_token)
            api = YandexDirectAPI(access_token, integration.agency_client_login)
            
            try:
                stats = await api.get_report(date_from, date_to)
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
                        # Retry with new token
                        api = YandexDirectAPI(new_token_data["access_token"], integration.agency_client_login)
                        stats = await api.get_report(date_from, date_to)
                    else:
                        raise e
                else:
                    raise e

            for s in stats:
                # 1. Ensure Campaign exists
                campaign_external_id = str(s['campaign_id'])
                campaign = db.query(models.Campaign).filter_by(
                    integration_id=integration.id,
                    external_id=campaign_external_id
                ).first()
                
                if not campaign:
                    campaign = models.Campaign(
                        integration_id=integration.id,
                        external_id=campaign_external_id,
                        name=s['campaign_name'],
                        is_active=True
                    )
                    db.add(campaign)
                    db.flush()
                elif campaign.name != s['campaign_name']:
                    campaign.name = s['campaign_name']
                    db.flush()

                # OPTIMIZATION: Only sync data for active campaigns
                if not campaign.is_active:
                    continue

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
                _update_or_create_stats(db, models.YandexStats, filters, data)

            # Group and Keyword stats follow same pattern (skipped here for brevity but ideally they use the same 'api' instance)
            for level in ["group", "keyword"]:
                 try:
                     level_stats = await api.get_report(date_from, date_to, level=level)
                     for l in level_stats:
                         if level == "group":
                             filters = {"client_id": integration.client_id, "date": datetime.strptime(l['date'], "%Y-%m-%d").date(), "campaign_name": l['campaign_name'], "group_name": l['name']}
                             data = {"impressions": l['impressions'], "clicks": l['clicks'], "cost": l['cost'], "conversions": l['conversions']}
                             _update_or_create_stats(db, models.YandexGroups, filters, data)
                         else:
                             filters = {"client_id": integration.client_id, "date": datetime.strptime(l['date'], "%Y-%m-%d").date(), "campaign_name": l['campaign_name'], "keyword": l['name']}
                             data = {"impressions": l['impressions'], "clicks": l['clicks'], "cost": l['cost'], "conversions": l['conversions']}
                             _update_or_create_stats(db, models.YandexKeywords, filters, data)
                 except: continue

        elif integration.platform == models.IntegrationPlatform.VK_ADS:
            access_token = security.decrypt_token(integration.access_token)
            api = VKAdsAPI(access_token, integration.account_id)
            
            try:
                stats = await api.get_statistics(date_from, date_to)
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
            api = YandexMetricaAPI(access_token)
            
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
                    models.MetrikaGoals.client_id == integration.client_id,
                    models.MetrikaGoals.date == stat_date,
                    models.MetrikaGoals.goal_id == "all"
                ).first()

                if existing:
                    existing.conversion_count = total_reaches
                else:
                    db.add(models.MetrikaGoals(
                        client_id=integration.client_id,
                        date=stat_date,
                        goal_id="all",
                        goal_name="Selected Goals" if selected_goals else "All Goals",
                        conversion_count=total_reaches
                    ))

        # Update status on success
        integration.sync_status = models.IntegrationSyncStatus.SUCCESS
        integration.error_message = None
        integration.last_sync_at = datetime.utcnow()

    except Exception as e:
        logger.error(f"Sync failed for {integration.id}: {e}")
        integration.sync_status = models.IntegrationSyncStatus.FAILED
        integration.error_message = f"{type(e).__name__}: {str(e)}"
        db.flush()
        raise e

async def sync_data(days: int = 7):
    db: Session = SessionLocal()
    try:
        integrations = db.query(models.Integration).all()
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        date_from = start_date.strftime("%Y-%m-%d")
        date_to = end_date.strftime("%Y-%m-%d")

        for integration in integrations:
            await sync_integration(db, integration, date_from, date_to)
            
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
