import httpx
import json
import asyncio

async def debug_metrica():
    TOKEN = "y0__xDmgreoBxiq3Twgw9OR-hUqR5xVDGYTx9oE-EKfF_UnRdZGQw"
    URL = "https://api-metrika.yandex.net/management/v1/counters"
    
    headers = {
        "Authorization": f"OAuth {TOKEN}",
        "Accept-Language": "ru"
    }
    
    logins = ["sintez-digital", "kcu-stroi-412538-fibw", None] # None means wildcard
    
    async with httpx.AsyncClient() as client:
        for login in logins:
            print(f"\n--- Checking Metrica for login: {login} ---")
            params = {}
            if login:
                params["ulogin"] = login
            
            try:
                resp = await client.get(URL, headers=headers, params=params)
                print(f"Status: {resp.status_code}")
                if resp.status_code == 200:
                    data = resp.json()
                    counters = data.get("counters", [])
                    print(f"Found {len(counters)} counters")
                    for c in counters:
                        cid = c["id"]
                        name = c["name"]
                        print(f"  Counter: {name} (ID: {cid})")
                        
                        # Fetch goals for this counter
                        goals_url = f"https://api-metrika.yandex.net/management/v1/counter/{cid}/goals"
                        g_resp = await client.get(goals_url, headers=headers)
                        if g_resp.status_code == 200:
                            goals = g_resp.json().get("goals", [])
                            print(f"    Found {len(goals)} goals")
                            for g in goals:
                                print(f"      - {g['name']} (ID: {g['id']})")
                        else:
                            print(f"    Failed to fetch goals: {g_resp.status_code}")
                else:
                    print(f"Error: {resp.text}")
            except Exception as e:
                print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(debug_metrica())
