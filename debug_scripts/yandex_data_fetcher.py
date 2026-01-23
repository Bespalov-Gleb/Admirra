import httpx
import asyncio
import json
import os
from datetime import datetime, timedelta
from automation.yandex_direct import YandexDirectAPI

# Credentials from chat_2.md
CLIENT_ID = "3febb68881204d9380089f718e5251b1"
CLIENT_SECRET = "9183486924ce4d38919352d5b3df6d18"
REDIRECT_URI = "https://oauth.yandex.ru/verification_code"

async def get_access_token(code: str):
    url = "https://oauth.yandex.ru/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=data)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            print(f"Error getting token: {response.status_code} - {response.text}")
            return None

async def main():
    print("=== Yandex.Direct Data Fetcher ===")
    
    # 1. Authorization URL
    auth_url = f"https://oauth.yandex.ru/authorize?response_type=code&client_id={CLIENT_ID}"
    print(f"\n1. Go to this URL to authorize:\n{auth_url}")
    
    # 2. Get verification code from user
    code = input("\n2. Enter the verification code: ").strip()
    
    if not code:
        print("Error: Code is required.")
        return

    # 3. Exchange code for access token
    print("\nExchanging code for access token...")
    token = await get_access_token(code)
    
    if not token:
        print("Failed to get token.")
        return
        
    print(f"Successfully obtained token: {token[:10]}...")

    # 4. Fetch data using existing API class
    print("\nFetching reports for the last 90 days...")
    api = YandexDirectAPI(token)
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=89)  # 90 days total (including today)
    
    date_from = start_date.strftime("%Y-%m-%d")
    date_to = end_date.strftime("%Y-%m-%d")

    # Fetch Campaign stats
    print(f"Report Period: {date_from} to {date_to}")
    stats = await api.get_report(date_from, date_to, level="campaign")

    if stats:
        print("\n--- Campaign Statistics ---")
        print(f"{'Date':<12} | {'Campaign Name':<30} | {'Clicks':<6} | {'Cost':<10}")
        print("-" * 65)
        for s in stats:
            print(f"{s['date']:<12} | {s['campaign_name'][:30]:<30} | {s['clicks']:<6} | {s['cost']:<10.2f}")
    else:
        print("\nNo campaign statistics found or report is still being generated.")

    # Fetch Keyword stats
    print("\nFetching keyword reports...")
    keywords = await api.get_report(date_from, date_to, level="keyword")
    
    if keywords:
        print("\n--- Keyword Statistics (Top 10) ---")
        print(f"{'Keyword':<30} | {'Clicks':<6} | {'Cost':<10}")
        print("-" * 50)
        for k in keywords[:10]:
            print(f"{k['name'][:30]:<30} | {k['clicks']:<6} | {k['cost']:<10.2f}")
    else:
        print("No keyword statistics found.")

if __name__ == "__main__":
    asyncio.run(main())
