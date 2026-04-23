import asyncio
import os
from automation.vk_ads import VKAdsAPI

async def verify():
    token_file = "vk_token.txt"
    if not os.path.exists(token_file):
        print(f"Error: {token_file} matching not found.")
        return

    with open(token_file, "r") as f:
        access_token = f.read().strip()

    # Cabinet ID from user's screenshot
    account_id = "20585645"
    
    api = VKAdsAPI(access_token, account_id)
    
    print(f"--- Testing VKAdsAPI Optimization ---")
    print(f"Account ID: {account_id}")
    
    # 1. Test campaign names fetching
    print("\nFetching Campaign Names...")
    names = await api._get_campaign_names()
    if names:
        print(f"SUCCESS: Found {len(names)} campaigns:")
        for cid, name in names.items():
            print(f"   - {cid}: {name}")
    else:
        print("INFO: No campaigns found or error occurred.")

    # 2. Test statistics fetching with names mapping
    print("\nFetching Statistics (Last 7 days)...")
    from datetime import datetime, timedelta
    date_to = datetime.now().strftime("%Y-%m-%d")
    date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    stats = await api.get_statistics(date_from, date_to)
    if stats:
        print(f"SUCCESS: Successfully fetched {len(stats)} stat rows:")
        for s in stats[:5]: # Show first 5
            print(f"   - {s['date']} | {s['campaign_name']} | Clicks: {s['clicks']} | Cost: {s['cost']}")
    else:
        print("INFO: No stats found (expected if campaigns are inactive).")

if __name__ == "__main__":
    asyncio.run(verify())
