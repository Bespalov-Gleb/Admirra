import asyncio
import httpx
import json
import os
from datetime import datetime, timedelta

# Replicating the logic from automation/vk_ads.py to test it locally/standalone
class VKAdsAPI:
    def __init__(self, access_token: str, account_id: str = None):
        self.base_url = "https://ads.vk.com/api/v2"
        self.headers = {
            "Authorization": f"Bearer {access_token}"
        }
        self.account_id = account_id

    async def get_statistics(self, date_from: str, date_to: str):
        url = f"{self.base_url}/statistics/ad_plans/day.json"
        params = {
            "date_from": date_from,
            "date_to": date_to,
            "metrics": "base"
        }
        if self.account_id:
            params["client_id"] = self.account_id

        async with httpx.AsyncClient() as client:
            print(f"Requesting URL: {url}")
            print(f"Params: {params}")
            response = await client.get(url, params=params, headers=self.headers)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error Body: {response.text}")
                return None

async def main():
    token_path = os.path.join("debug_scripts", "vk_token.txt")
    if not os.path.exists(token_path):
        print("vk_token.txt not found in debug_scripts/")
        return

    with open(token_path, "r") as f:
        token = f.read().strip()

    # We use the account ID from previous logs
    account_id = "592676405" 
    api = VKAdsAPI(token, account_id)

    # Test for a recent range (90 days)
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

    print(f"Testing VK Ads API (ad_plans) for period: {start_date} to {end_date}")
    data = await api.get_statistics(start_date, end_date)

    if data:
        with open(os.path.join("debug_scripts", "vk_test_result.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        items = data.get("items", [])
        print(f"Found {len(items)} items.")
        
        for item in items:
            total = item.get("total", {}).get("base", {})
            print(f"Plan ID: {item.get('id')} -> Shows: {total.get('shows')}, Clicks: {total.get('clicks')}, Spent: {total.get('spent')}")

if __name__ == "__main__":
    asyncio.run(main())
