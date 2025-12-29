import asyncio
import os
from sqlalchemy.orm import Session
from core.database import SessionLocal
from core import models, security
from automation.sync import sync_integration
from datetime import datetime, timedelta

async def test_vk_logic():
    print("--- Testing VK Integration Logic ---")
    db = SessionLocal()
    try:
        # 1. Check if we have any VK integrations
        vk_integrations = db.query(models.Integration).filter(
            models.Integration.platform == models.IntegrationPlatform.VK_ADS
        ).all()
        
        if not vk_integrations:
            print("INFO: No VK Ads integrations found in database.")
            return

        for integration in vk_integrations:
            print(f"\nChecking Integration ID: {integration.id}")
            print(f"Platform: {integration.platform}")
            print(f"Account ID: {integration.account_id}")
            
            # Check if new fields are populated
            has_client_id = integration.platform_client_id is not None
            has_client_secret = integration.platform_client_secret is not None
            print(f"Stored Credentials: {'Yes' if has_client_id and has_client_secret else 'No'}")

            # 2. Try to sync (this will test decryption and API call)
            # We use a short date range for testing
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=1)
            date_from = start_date.strftime("%Y-%m-%d")
            date_to = end_date.strftime("%Y-%m-%d")
            
            print(f"Attempting sync for {date_from} to {date_to}...")
            try:
                # We expect this might fail if tokens are invalid/expired, 
                # but it should at least trigger the refresh logic if credentials exist.
                await sync_integration(db, integration, date_from, date_to)
                db.commit()
                print("SUCCESS: Sync completed (at least logic-wise).")
            except Exception as e:
                print(f"SYNC FAILED/ERROR: {e}")
                
        # 3. Check stats table
        stats_count = db.query(models.VKStats).count()
        print(f"\nTotal VK Stats rows in DB: {stats_count}")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_vk_logic())
