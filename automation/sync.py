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

async def sync_integration(db: Session, integration: models.Integration, date_from: str, date_to: str):
    """
    Syncs a single integration for a given date range.
    """
    logger.info(f"Syncing {integration.platform} for client {integration.client_id}")
    
    if integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
        access_token = security.decrypt_token(integration.access_token)
        api = YandexDirectAPI(access_token)
        stats = await api.get_report(date_from, date_to)
        
        for s in stats:
            existing = db.query(models.YandexStats).filter(
                models.YandexStats.client_id == integration.client_id,
                models.YandexStats.date == datetime.strptime(s['date'], "%Y-%m-%d").date(),
                models.YandexStats.campaign_name == s['campaign_name']
            ).first()
            
            if existing:
                existing.impressions = s['impressions']
                existing.clicks = s['clicks']
                existing.cost = s['cost']
                existing.conversions = s['conversions']
            else:
                new_stat = models.YandexStats(
                    client_id=integration.client_id,
                    date=datetime.strptime(s['date'], "%Y-%m-%d").date(),
                    campaign_name=s['campaign_name'],
                    impressions=s['impressions'],
                    clicks=s['clicks'],
                    cost=s['cost'],
                    conversions=s['conversions']
                )
                db.add(new_stat)

        # Group stats
        group_stats = await api.get_report(date_from, date_to, level="group")
        for g in group_stats:
            existing_g = db.query(models.YandexGroups).filter(
                models.YandexGroups.client_id == integration.client_id,
                models.YandexGroups.date == datetime.strptime(g['date'], "%Y-%m-%d").date(),
                models.YandexGroups.campaign_name == g['campaign_name'],
                models.YandexGroups.group_name == g['name']
            ).first()

            if existing_g:
                existing_g.impressions = g['impressions']
                existing_g.clicks = g['clicks']
                existing_g.cost = g['cost']
                existing_g.conversions = g['conversions']
            else:
                db.add(models.YandexGroups(
                    client_id=integration.client_id,
                    date=datetime.strptime(g['date'], "%Y-%m-%d").date(),
                    campaign_name=g['campaign_name'],
                    group_name=g['name'],
                    impressions=g['impressions'],
                    clicks=g['clicks'],
                    cost=g['cost'],
                    conversions=g['conversions']
                ))

        # Keyword stats
        keyword_stats = await api.get_report(date_from, date_to, level="keyword")
        for k in keyword_stats:
            existing_k = db.query(models.YandexKeywords).filter(
                models.YandexKeywords.client_id == integration.client_id,
                models.YandexKeywords.date == datetime.strptime(k['date'], "%Y-%m-%d").date(),
                models.YandexKeywords.campaign_name == k['campaign_name'],
                models.YandexKeywords.keyword == k['name']
            ).first()

            if existing_k:
                existing_k.impressions = k['impressions']
                existing_k.clicks = k['clicks']
                existing_k.cost = k['cost']
                existing_k.conversions = k['conversions']
            else:
                db.add(models.YandexKeywords(
                    client_id=integration.client_id,
                    date=datetime.strptime(k['date'], "%Y-%m-%d").date(),
                    campaign_name=k['campaign_name'],
                    keyword=k['name'],
                    impressions=k['impressions'],
                    clicks=k['clicks'],
                    cost=k['cost'],
                    conversions=k['conversions']
                ))

    elif integration.platform == models.IntegrationPlatform.VK_ADS:
        access_token = security.decrypt_token(integration.access_token)
        api = VKAdsAPI(access_token, integration.account_id)
        stats = await api.get_statistics(date_from, date_to)
        
        for s in stats:
            existing = db.query(models.VKStats).filter(
                models.VKStats.client_id == integration.client_id,
                models.VKStats.date == datetime.strptime(s['date'], "%Y-%m-%d").date(),
                models.VKStats.campaign_name == s['campaign_name']
            ).first()
            
            if existing:
                existing.impressions = s['impressions']
                existing.clicks = s['clicks']
                existing.cost = s['cost']
                existing.conversions = s['conversions']
            else:
                new_stat = models.VKStats(
                    client_id=integration.client_id,
                    date=datetime.strptime(s['date'], "%Y-%m-%d").date(),
                    campaign_name=s['campaign_name'],
                    impressions=s['impressions'],
                    clicks=s['clicks'],
                    cost=s['cost'],
                    conversions=s['conversions']
                )
                db.add(new_stat)

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
