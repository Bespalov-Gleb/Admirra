import asyncio
import httpx
import json
import os

async def main():
    token_path = os.path.join("debug_scripts", "vk_token.txt")
    if not os.path.exists(token_path):
        print("vk_token.txt not found in debug_scripts/")
        return

    with open(token_path, "r") as f:
        token = f.read().strip()

    url = "https://ads.vk.com/api/v2/agency/clients.json"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    print(f"Fetching VK Ads Agency Clients...")
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            print(f"Found {len(items)} clients.")
            for item in items:
                print(f"Client Name: {item.get('name')} | ID: {item.get('id')} | Status: {item.get('status')}")
            
            with open(os.path.join("debug_scripts", "vk_clients.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            print(f"Error: {response.text}")

if __name__ == "__main__":
    asyncio.run(main())
