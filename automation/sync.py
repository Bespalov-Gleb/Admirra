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
    
    if integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
        access_token = security.decrypt_token(integration.access_token)
        api = YandexDirectAPI(access_token)
        
        # Campaign stats
        stats = await api.get_report(date_from, date_to)
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
                    name=s['campaign_name']
                )
                db.add(campaign)
                db.flush()
            elif campaign.name != s['campaign_name']:
                campaign.name = s['campaign_name']
                db.flush()

            # 2. Update Stats
            filters = {
                "client_id": integration.client_id,
                "campaign_id": campaign.id,
                "date": datetime.strptime(s['date'], "%Y-%m-%d").date()
            }
            data = {
                "campaign_name": s['campaign_name'], # Keep for compatibility
                "impressions": s['impressions'],
                "clicks": s['clicks'],
                "cost": s['cost'],
                "conversions": s['conversions']
            }
            _update_or_create_stats(db, models.YandexStats, filters, data)

        # Group stats
        group_stats = await api.get_report(date_from, date_to, level="group")
        for g in group_stats:
            filters = {
                "client_id": integration.client_id,
                "date": datetime.strptime(g['date'], "%Y-%m-%d").date(),
                "campaign_name": g['campaign_name'],
                "group_name": g['name']
            }
            data = {
                "impressions": g['impressions'],
                "clicks": g['clicks'],
                "cost": g['cost'],
                "conversions": g['conversions']
            }
            _update_or_create_stats(db, models.YandexGroups, filters, data)

        # Keyword stats
        keyword_stats = await api.get_report(date_from, date_to, level="keyword")
        for k in keyword_stats:
            filters = {
                "client_id": integration.client_id,
                "date": datetime.strptime(k['date'], "%Y-%m-%d").date(),
                "campaign_name": k['campaign_name'],
                "keyword": k['name']
            }
            data = {
                "impressions": k['impressions'],
                "clicks": k['clicks'],
                "cost": k['cost'],
                "conversions": k['conversions']
            }
            _update_or_create_stats(db, models.YandexKeywords, filters, data)

    elif integration.platform == models.IntegrationPlatform.VK_ADS:
        access_token = security.decrypt_token(integration.access_token)
        api = VKAdsAPI(access_token, integration.account_id)
        stats = await api.get_statistics(date_from, date_to)
        
        # If no stats and we have client credentials, try to refresh and retry once
        if not stats and integration.platform_client_id and integration.platform_client_secret:
            logger.info(f"Retrying VK sync with fresh token for client {integration.client_id}")
            from backend_api.services import IntegrationService
            try:
                client_id = security.decrypt_token(integration.platform_client_id)
                client_secret = security.decrypt_token(integration.platform_client_secret)
                vk_data = await IntegrationService.exchange_vk_token(client_id, client_secret)
                
                new_access_token = vk_data["access_token"]
                integration.access_token = security.encrypt_token(new_access_token)
                if vk_data.get("refresh_token"):
                    integration.refresh_token = security.encrypt_token(vk_data["refresh_token"])
                
                # Retry with new token
                api = VKAdsAPI(new_access_token, integration.account_id)
                stats = await api.get_statistics(date_from, date_to)
            except Exception as e:
                logger.error(f"Failed to refresh VK token: {e}")

        for s in stats:
            # 1. Ensure Campaign exists
            # VK Ads stats might not have an explicit external campaign ID in the same way, 
            # but usually it's in s['campaign_id'] if the API helper provides it.
            # Let's assume s['campaign_id'] and s['campaign_name'] are available.
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
                    name=campaign_name
                )
                db.add(campaign)
                db.flush()
            elif campaign.name != campaign_name:
                campaign.name = campaign_name
                db.flush()

            # 2. Update Stats
            filters = {
                "client_id": integration.client_id,
                "campaign_id": campaign.id,
                "date": datetime.strptime(s['date'], "%Y-%m-%d").date()
            }
            data = {
                "campaign_name": campaign_name, # Keep for compatibility
                "impressions": s['impressions'],
                "clicks": s['clicks'],
                "cost": s['cost'],
                "conversions": s['conversions']
            }
            _update_or_create_stats(db, models.VKStats, filters, data)

    elif integration.platform == models.IntegrationPlatform.YANDEX_METRIKA:
        if not integration.account_id:
            logger.warning(f"No counter ID (account_id) for Metrica integration {integration.id}")
            return
        
        access_token = security.decrypt_token(integration.access_token)
        api = YandexMetricaAPI(access_token)
        goals = await api.get_goals_stats(integration.account_id, date_from, date_to)
        
        for g in goals:
            stat_date = datetime.strptime(g['dimensions'][0]['name'], "%Y-%m-%d").date()
            
            existing = db.query(models.MetrikaGoals).filter(
                models.MetrikaGoals.client_id == integration.client_id,
                models.MetrikaGoals.date == stat_date,
                models.MetrikaGoals.goal_id == "all"
            ).first()

            reach = int(g['metrics'][1]) if len(g['metrics']) > 1 else 0

            if existing:
                existing.conversion_count = reach
            else:
                db.add(models.MetrikaGoals(
                    client_id=integration.client_id,
                    date=stat_date,
                    goal_id="all",
                    goal_name="All Goals",
                    conversion_count=reach
                ))

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
                # Generate weekly report for current week
                generate_weekly_report(db, client.id, end_date)
                # Generate monthly report for current month
                generate_monthly_report(db, client.id, end_date.year, end_date.month)
            except Exception as e:
                logger.error(f"Error generating reports for client {client.id}: {e}")

        # Google Sheets Export
        gs = GoogleSheetsService()
        for client in clients:
            # We assume each client has a spreadsheet_id. 
            # I'll add this field to the Client model in the next step.
            # For now, we skip if not present or use a placeholder if needed.
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
