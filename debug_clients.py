import httpx
import json
import asyncio

async def debug_clients():
    TOKEN = "y0__xDmgreoBxiq3Twgw9OR-hUqR5xVDGYTx9oE-EKfF_UnRdZGQw"
    URL = "https://api.direct.yandex.com/json/v5/clients"
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept-Language": "ru"
    }
    
    payload = {
        "method": "get",
        "params": {
            "FieldNames": ["Login", "ClientInfo", "ManagedLogins"]
        }
    }
    
    async with httpx.AsyncClient() as client:
        print("--- Calling Clients.get ---")
        resp = await client.post(URL, json=payload, headers=headers)
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))

    # Also try AgencyClients just in case
    print("\n--- Calling AgencyClients.get ---")
    URL_AGENCY = "https://api.direct.yandex.com/json/v5/agencyclients"
    payload_agency = {
        "method": "get",
        "params": {
            "SelectionCriteria": {"Archived": "NO"},
            "FieldNames": ["Login", "ClientInfo"]
        }
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(URL_AGENCY, json=payload_agency, headers=headers)
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(debug_clients())
