import sys
import os
import asyncio
from datetime import datetime, timedelta

sys.path.append(os.getcwd())

from core.database import SessionLocal
from core import models, security
from automation.sync import sync_integration

async def test_sync():
    db = SessionLocal()
    try:
        # Find the Test Project integration with campaigns
        integration = db.query(models.Integration).filter(
            models.Integration.id == "a7fa38c8-ad9a-4783-8e09-92756a836912"
        ).first()
        
        if not integration:
            print("Integration not found!")
            return
        
        print(f"Testing sync for: {integration.id}")
        print(f"Platform: {integration.platform.value}")
        print(f"Account: {integration.account_id}")
        print(f"Agency Client Login: {integration.agency_client_login}")
        
        # Sync last 30 days
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        date_from = start_date.strftime("%Y-%m-%d")
        date_to = end_date.strftime("%Y-%m-%d")
        
        print(f"\nSyncing from {date_from} to {date_to}...")
        
        try:
            await sync_integration(db, integration, date_from, date_to)
            db.commit()
            print("\n✓ Sync completed successfully!")
            
            # Check results
            stats_count = db.query(models.YandexStats).filter(
                models.YandexStats.client_id == integration.client_id
            ).count()
            print(f"Stats records created: {stats_count}")
            
        except Exception as e:
            print(f"\n✗ Sync failed with error:")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            import traceback
            traceback.print_exc()
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_sync())
