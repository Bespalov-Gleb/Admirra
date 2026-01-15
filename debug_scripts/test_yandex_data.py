import sys
import os
import asyncio

sys.path.append(os.getcwd())

from core.database import SessionLocal
from core import models, security
from automation.yandex_direct import YandexDirectAPI

async def test_yandex_api():
    db = SessionLocal()
    try:
        # Get the integration
        integration = db.query(models.Integration).filter(
            models.Integration.id == "a7fa38c8-ad9a-4783-8e09-92756a836912"
        ).first()
        
        if not integration:
            print("Integration not found!")
            return
        
        access_token = security.decrypt_token(integration.access_token)
        
        print(f"Testing Yandex Direct API")
        print(f"Account: {integration.account_id}")
        print(f"Agency Client Login: {integration.agency_client_login}")
        print()
        
        # Test 1: Get campaigns
        print("=" * 60)
        print("TEST 1: Fetching campaigns list")
        print("=" * 60)
        api = YandexDirectAPI(access_token, integration.agency_client_login)
        campaigns = await api.get_campaigns()
        print(f"Found {len(campaigns)} campaigns:")
        for c in campaigns[:10]:
            print(f"  - {c['name']} (ID: {c['id']}, Status: {c['status']})")
        
        # Test 2: Get report for last 7 days
        print("\n" + "=" * 60)
        print("TEST 2: Fetching report for last 7 days")
        print("=" * 60)
        from datetime import datetime, timedelta
        end = datetime.now().date()
        start = end - timedelta(days=7)
        
        date_from = start.strftime("%Y-%m-%d")
        date_to = end.strftime("%Y-%m-%d")
        
        print(f"Date range: {date_from} to {date_to}")
        stats = await api.get_report(date_from, date_to)
        print(f"Received {len(stats)} rows")
        
        if len(stats) > 0:
            print("\nSample data (first 5 rows):")
            for s in stats[:5]:
                print(f"  {s['date']} | {s['campaign_name'][:30]:30} | Cost: {s['cost']:10.2f} | Clicks: {s['clicks']:5}")
        else:
            print("\n⚠ NO DATA RETURNED!")
            print("\nPossible reasons:")
            print("1. No ad spend in this period")
            print("2. Campaigns were paused/stopped")
            print("3. Agency client login is incorrect")
            print("4. Token doesn't have access to this client's data")
        
        # Test 3: Try without agency_client_login
        print("\n" + "=" * 60)
        print("TEST 3: Fetching report WITHOUT agency_client_login")
        print("=" * 60)
        api_no_agency = YandexDirectAPI(access_token, None)
        stats_no_agency = await api_no_agency.get_report(date_from, date_to)
        print(f"Received {len(stats_no_agency)} rows")
        
        if len(stats_no_agency) > 0:
            print("\n✓ Data found when NOT using agency_client_login!")
            print("This suggests the agency_client_login might be incorrect.")
            print("\nSample data:")
            for s in stats_no_agency[:5]:
                print(f"  {s['date']} | {s['campaign_name'][:30]:30} | Cost: {s['cost']:10.2f}")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_yandex_api())
