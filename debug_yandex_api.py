import httpx
import json
import asyncio

TOKEN = "y0__xDmgreoBxiq3Twgw9OR-hUqR5xVDGYTx9oE-EKfF_UnRdZGQw"

async def debug_yandex():
    async with httpx.AsyncClient() as client:
        # 1. Check User Info (Passport)
        print("--- 1. Yandex Passport Info ---")
        headers = {"Authorization": f"OAuth {TOKEN}"}
        resp = await client.get("https://login.yandex.ru/info?format=json", headers=headers)
        print(f"Status: {resp.status_code}")
        print(f"Data: {json.dumps(resp.json(), indent=2)}")
        login = resp.json().get("login")

        # 2. Check Agency Status
        print("\n--- 2. Yandex Direct Agency Clients ---")
        direct_headers = {"Authorization": f"Bearer {TOKEN}", "Accept-Language": "ru"}
        payload = {
            "method": "get",
            "params": {
                "SelectionCriteria": {"Archived": "NO"},
                "FieldNames": ["Login", "ClientInfo", "RepresentedBy"],
                "Page": {"Limit": 10}
            }
        }
        resp = await client.post("https://api.direct.yandex.com/json/v5/agencyclients", json=payload, headers=direct_headers)
        print(f"Status: {resp.status_code}")
        print(f"Data: {json.dumps(resp.json(), indent=2)}")

        # 3. Check Metrica Counters
        print("\n--- 3. Yandex Metrica Counters ---")
        # Try without specific login first, then with login
        metrica_resp = await client.get("https://api-metrika.yandex.net/management/v1/counters", headers=headers)
        print(f"Counters Status (Global): {metrica_resp.status_code}")
        print(f"Counters Data: {json.dumps(metrica_resp.json(), indent=2)}")
        
        if login:
            metrica_resp_login = await client.get(f"https://api-metrika.yandex.net/management/v1/counters?ulogin={login}", headers=headers)
            print(f"\nCounters Status (with login {login}): {metrica_resp_login.status_code}")
            # print(f"Counters Data: {json.dumps(metrica_resp_login.json(), indent=2)}")

if __name__ == "__main__":
    asyncio.run(debug_yandex())
