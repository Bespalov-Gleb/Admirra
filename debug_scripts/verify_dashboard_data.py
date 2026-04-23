import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.getcwd())

from core.database import SessionLocal
from core import models
from sqlalchemy import func

def verify_dashboard_data():
    db = SessionLocal()
    try:
        print("=" * 70)
        print("САНҶИШИ МАЪЛУМОТ БАРОИ DASHBOARD")
        print("=" * 70)
        
        # Get the client
        client = db.query(models.Client).filter(
            models.Client.name == "трафик аккаунт"
        ).first()
        
        if not client:
            print("❌ Мизоҷ пайдо нашуд!")
            return
        
        print(f"\nМизоҷ: {client.name}")
        print(f"ID: {client.id}")
        
        # Check campaigns
        integration = db.query(models.Integration).filter(
            models.Integration.client_id == client.id
        ).first()
        
        campaigns = db.query(models.Campaign).filter(
            models.Campaign.integration_id == integration.id
        ).all()
        
        print(f"\nКампанияҳо: {len(campaigns)}")
        active_count = sum(1 for c in campaigns if c.is_active)
        print(f"Фаъол: {active_count}")
        
        # Simulate dashboard query (like in stats_service.py)
        print("\n" + "=" * 70)
        print("СИМУЛЯТСИЯИ ДАРХОСТИ DASHBOARD")
        print("=" * 70)
        
        # Query with is_active filter (like dashboard does)
        stats_query = db.query(
            func.sum(models.YandexStats.cost).label("total_cost"),
            func.sum(models.YandexStats.clicks).label("total_clicks"),
            func.sum(models.YandexStats.impressions).label("total_impressions"),
            func.sum(models.YandexStats.conversions).label("total_conversions"),
            func.count(models.YandexStats.id).label("row_count")
        ).join(
            models.Campaign, models.YandexStats.campaign_id == models.Campaign.id
        ).filter(
            models.YandexStats.client_id == client.id,
            models.Campaign.is_active == True
        ).first()
        
        print(f"\nНатиҷаи дархост (бо филтри is_active=True):")
        print(f"  Сатрҳо: {stats_query.row_count or 0}")
        print(f"  Харҷ: {float(stats_query.total_cost or 0):,.2f} ₽")
        print(f"  Кликҳо: {int(stats_query.total_clicks or 0):,}")
        print(f"  Намоишҳо: {int(stats_query.total_impressions or 0):,}")
        print(f"  Конверсияҳо: {int(stats_query.total_conversions or 0):,}")
        
        # Check by campaign
        print("\n" + "=" * 70)
        print("МАЪЛУМОТ АЗ РӮИ КАМПАНИЯ")
        print("=" * 70)
        
        campaign_stats = db.query(
            models.Campaign.name,
            models.Campaign.is_active,
            func.count(models.YandexStats.id).label("row_count"),
            func.sum(models.YandexStats.cost).label("total_cost"),
            func.min(models.YandexStats.date).label("min_date"),
            func.max(models.YandexStats.date).label("max_date")
        ).join(
            models.YandexStats, models.Campaign.id == models.YandexStats.campaign_id
        ).filter(
            models.Campaign.integration_id == integration.id
        ).group_by(models.Campaign.name, models.Campaign.is_active).all()
        
        for cs in campaign_stats:
            status = "✓" if cs.is_active else "✗"
            print(f"{status} {cs.name[:40]:40} | {cs.row_count:3} сатр | {float(cs.total_cost or 0):8.2f} ₽ | {cs.min_date} - {cs.max_date}")
        
        print("\n" + "=" * 70)
        if stats_query.row_count and stats_query.row_count > 0:
            print("✅ МУВАФФАҚ! Маълумот дар dashboard нишон дода мешавад!")
        else:
            print("❌ МУШКИЛӢ БОҚӢ МОНД!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Хато: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_dashboard_data()
