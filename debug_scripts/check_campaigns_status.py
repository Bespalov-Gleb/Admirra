import sys
import os
import uuid
# Add root to sys.path
sys.path.append(os.getcwd())

from core.database import SessionLocal
from core import models

def check_campaigns():
    db = SessionLocal()
    try:
        print("--- CAMPAIGN STATUS CHECK ---")
        integrations = db.query(models.Integration).order_by(models.Integration.last_sync_at.desc()).all()
        
        if not integrations:
            print("No integrations found.")
            return

        for integ in integrations:
            client = db.query(models.Client).filter(models.Client.id == integ.client_id).first()
            print(f"\nIntegration: {integ.id} ({integ.platform.value})")
            print(f"Project: {client.name if client else 'Unknown'}")
            print(f"Account: {integ.account_id}")
            print(f"Last Sync At: {integ.last_sync_at}")
            print(f"Sync Status: {integ.sync_status.value}")
            print(f"Error: {integ.error_message}")
            
            campaigns = db.query(models.Campaign).filter(models.Campaign.integration_id == integ.id).all()
            print(f"Campaigns in DB: {len(campaigns)}")
            
            active_count = sum(1 for c in campaigns if c.is_active)
            print(f"Active Campaigns: {active_count}")
            
            if len(campaigns) > 0:
                print("Samples:")
                for c in campaigns[:10]:
                    print(f" - [{ 'X' if c.is_active else ' ' }] {c.name} (ExtID: {c.external_id})")
            
            # Check for stats
            stats_count = db.query(models.YandexStats).filter(models.YandexStats.client_id == integ.client_id).count()
            print(f"YandexStats records for this client: {stats_count}")
            
            vk_stats_count = db.query(models.VKStats).filter(models.VKStats.client_id == integ.client_id).count()
            print(f"VKStats records for this client: {vk_stats_count}")

    finally:
        db.close()

if __name__ == "__main__":
    check_campaigns()
