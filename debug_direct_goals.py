import httpx
import json
import asyncio

async def debug_direct_goals():
    TOKEN = "y0__xDmgreoBxiq3Twgw9OR-hUqR5xVDGYTx9oE-EKfF_UnRdZGQw"
    URL = "https://api.direct.yandex.com/json/v5/goals"
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept-Language": "ru",
        "Client-Login": "sintez-digital"
    }
    
    payload = {
        "method": "get",
        "params": {
            "SelectionCriteria": {}
        }
    }
    
    async with httpx.AsyncClient() as client:
        print("--- Calling Direct.Goals.get ---")
        resp = await client.post(URL, json=payload, headers=headers)
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(debug_direct_goals())
