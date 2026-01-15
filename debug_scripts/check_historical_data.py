import sys
import os
from datetime import datetime

sys.path.append(os.getcwd())

from core.database import SessionLocal
from core import models
from sqlalchemy import func

def check_historical_data():
    db = SessionLocal()
    try:
        print("=" * 70)
        print("САНҶИШИ МАЪЛУМОТҲОИ ТАЪРИХӢ (HISTORICAL DATA CHECK)")
        print("=" * 70)
        
        # Check all YandexStats
        print("\n1. МАЪЛУМОТИ ЯНДЕКС (YandexStats):")
        print("-" * 70)
        
        # Get date range
        date_range = db.query(
            func.min(models.YandexStats.date).label('min_date'),
            func.max(models.YandexStats.date).label('max_date'),
            func.count(models.YandexStats.id).label('total_rows')
        ).first()
        
        if date_range and date_range.total_rows > 0:
            print(f"Ҷамъи сатрҳо (Total rows): {date_range.total_rows:,}")
            print(f"Санаи аввалин (First date): {date_range.min_date}")
            print(f"Санаи охирин (Last date): {date_range.max_date}")
            
            # Check by year
            print("\nМаълумот аз рӯи сол (Data by year):")
            yearly = db.query(
                func.extract('year', models.YandexStats.date).label('year'),
                func.count(models.YandexStats.id).label('count'),
                func.sum(models.YandexStats.cost).label('total_cost')
            ).group_by(func.extract('year', models.YandexStats.date)).order_by('year').all()
            
            for y in yearly:
                print(f"  {int(y.year)}: {y.count:,} сатр, {float(y.total_cost or 0):,.2f} ₽")
            
            # Check by client
            print("\nМаълумот аз рӯи мизоҷ (Data by client):")
            by_client = db.query(
                models.Client.name,
                func.count(models.YandexStats.id).label('count'),
                func.min(models.YandexStats.date).label('min_date'),
                func.max(models.YandexStats.date).label('max_date')
            ).join(models.Client, models.YandexStats.client_id == models.Client.id
            ).group_by(models.Client.name).all()
            
            for c in by_client:
                print(f"  {c.name}: {c.count:,} сатр ({c.min_date} то {c.max_date})")
            
            # Check active vs inactive campaigns
            print("\nМаълумот аз рӯи кампанияҳо (Data by campaigns):")
            active_stats = db.query(func.count(models.YandexStats.id)).join(
                models.Campaign, models.YandexStats.campaign_id == models.Campaign.id
            ).filter(models.Campaign.is_active == True).scalar()
            
            inactive_stats = db.query(func.count(models.YandexStats.id)).join(
                models.Campaign, models.YandexStats.campaign_id == models.Campaign.id
            ).filter(models.Campaign.is_active == False).scalar()
            
            print(f"  Кампанияҳои фаъол (Active campaigns): {active_stats:,} сатр")
            print(f"  Кампанияҳои ғайрифаъол (Inactive campaigns): {inactive_stats:,} сатр")
            
        else:
            print("❌ МАЪЛУМОТ НЕСТ (NO DATA)")
        
        # Check VK Stats
        print("\n\n2. МАЪЛУМОТИ VK (VKStats):")
        print("-" * 70)
        vk_count = db.query(func.count(models.VKStats.id)).scalar()
        print(f"Ҷамъи сатрҳо: {vk_count:,}")
        
        # Check Metrika
        print("\n\n3. МАЪЛУМОТИ МЕТРИКА (MetrikaGoals):")
        print("-" * 70)
        metrika_count = db.query(func.count(models.MetrikaGoals.id)).scalar()
        print(f"Ҷамъи сатрҳо: {metrika_count:,}")
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"Хато (Error): {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_historical_data()
