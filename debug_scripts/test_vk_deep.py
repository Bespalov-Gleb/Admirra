import asyncio
import httpx
import json
import os
from datetime import datetime, timedelta

async def test_range(api, d_from, d_to, account_id=None):
    url = f"https://ads.vk.com/api/v2/statistics/ad_plans/day.json"
    params = {
        "date_from": d_from,
        "date_to": d_to,
        "metrics": "base"
    }
    if account_id:
        params["client_id"] = account_id

    print(f"\n--- Testing Range: {d_from} to {d_to} | Account ID: {account_id} ---")
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=api.headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            print(f"Found {len(items)} items.")
            for item in items:
                total = item.get("total", {}).get("base", {})
                if int(total.get("shows", 0)) > 0 or float(total.get("spent", 0)) > 0:
                    print(f"✅ DATA FOUND! Plan ID: {item.get('id')} -> Shows: {total.get('shows')}, Spent: {total.get('spent')}")
                else:
                    print(f"Plan ID: {item.get('id')} -> Empty (0)")
        else:
            print(f"Error: {response.text}")

async def main():
    token_path = os.path.join("debug_scripts", "vk_token.txt")
    if not os.path.exists(token_path): return

    with open(token_path, "r") as f:
        token = f.read().strip()

    class API: pass
    api = API()
    api.headers = {"Authorization": f"Bearer {token}"}

    # Variant 1: Last 12 months, NO account_id
    d_to = datetime.now().strftime("%Y-%m-%d")
    d_from = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    await test_range(api, d_from, d_to, None)

    # Variant 2: Last 12 months, WITH account_id
    await test_range(api, d_from, d_to, "592676405")

if __name__ == "__main__":
    asyncio.run(main())
