import asyncio
from sqlalchemy import func
from core.database import SessionLocal
from core import models, security

def verify_data():
    db = SessionLocal()
    try:
        print("--- Verifying Yandex Data Integrity ---")
        
        # 1. Check Integrations
        integrations = db.query(models.Integration).filter(models.Integration.platform == models.IntegrationPlatform.YANDEX_DIRECT).all()
        print(f"Found {len(integrations)} Yandex integrations.")
        
        for integ in integrations:
            client = db.query(models.Client).filter(models.Client.id == integ.client_id).first()
            print(f"\nIntegration ID: {integ.id}")
            print(f"Associated Client (Project): {client.name}")
            print(f"Account ID (Login): {integ.account_id}")
            
            # 2. Check Stats
            stats_count = db.query(models.YandexStats).filter(models.YandexStats.client_id == integ.client_id).count()
            print(f"Total Stats Records (Days * Campaigns): {stats_count}")
            
            # 3. List Unique Campaigns
            campaigns = db.query(models.YandexStats.campaign_name).filter(models.YandexStats.client_id == integ.client_id).distinct().all()
            print(f"Unique Campaigns Found ({len(campaigns)}):")
            for c in campaigns:
                print(f" - {c[0]}")
                
            if stats_count == 0:
                print("WARNING: No statistics found. Sync might be failing or empty account.")
            else:
                print("SUCCESS: Data seems to be syncing.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_data()
