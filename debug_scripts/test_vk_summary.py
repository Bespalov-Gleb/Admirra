import asyncio
import httpx
import json
import os

async def main():
    token_path = os.path.join("debug_scripts", "vk_token.txt")
    if not os.path.exists(token_path): return

    with open(token_path, "r") as f:
        token = f.read().strip()

    # Testing summary (total) stats
    url = "https://ads.vk.com/api/v2/statistics/ad_plans/summary.json"
    params = {
        "metrics": "base"
    }
    headers = {"Authorization": f"Bearer {token}"}

    print(f"\n--- Testing TOTAL Summary Stats (All Time) ---")
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            for item in items:
                total = item.get("total", {}).get("base", {})
                print(f"Plan ID: {item.get('id')} -> Total Shows: {total.get('shows')}, Total Spent: {total.get('spent')}")
        else:
            print(f"Error: {response.text}")

if __name__ == "__main__":
    asyncio.run(main())
