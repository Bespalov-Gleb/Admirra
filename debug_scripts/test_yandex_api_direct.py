import asyncio
import sys
import os
import httpx
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import SessionLocal
from core import models, security
from automation.yandex_direct import YandexDirectAPI

async def test_api():
    db = SessionLocal()
    try:
        print("--- Testing Direct Live API Connection ---")
        integration = db.query(models.Integration).filter(
            models.Integration.platform == models.IntegrationPlatform.YANDEX_DIRECT
        ).first()
        
        if not integration:
            print("ERROR: No Yandex integration found in DB. Please connect via UI first.")
            return

        client = db.query(models.Client).filter(models.Client.id == integration.client_id).first()
        print(f"Integration found for client: {client.name}")
        print(f"Account ID (Login): {integration.account_id}")

        try:
            token = security.decrypt_token(integration.access_token)
            print(f"Token decrypted successfully. Length: {len(token)}")
        except Exception as e:
            print(f"ERROR: Could not decrypt token: {e}")
            return
        
        api = YandexDirectAPI(token)
        
        # 1. Who am I? (Get Login)
        print("\n[1] Checking Account Info...")
        try:
            headers = {"Authorization": f"OAuth {token}"}
            async with httpx.AsyncClient() as http:
                resp = await http.get("https://login.yandex.ru/info?format=json", headers=headers)
                if resp.status_code == 200:
                    info = resp.json()
                    print(f"   -> Connected as Yandex User: {info.get('login')} (ID: {info.get('id')})")
                    
                    # Optional: Update DB if missing
                    if not integration.account_id:
                         print("   -> Updating missing Account ID in Database...")
                         integration.account_id = info.get('login')
                         if not integration.platform_client_id:
                             integration.platform_client_id = security.encrypt_token(info.get('id'))
                         db.commit()
                         print("   -> Saved!")
                else:
                    print(f"   -> Failed to get user info: {resp.status_code}")
        except Exception as e:
            print(f"   -> Error checking info: {e}")

        # 2. List Campaigns
        print("\n[2] Listing Campaigns (Direct API)...")
        try:
             # Manual raw call to Campaigns service safely
             async with httpx.AsyncClient() as client:
                body = {
                    "method": "get",
                    "params": {
                        "SelectionCriteria": {},
                        "FieldNames": ["Id", "Name", "State", "Status"]
                    }
                }
                headers = api.headers
                
                resp = await client.post("https://api.direct.yandex.com/json/v5/campaigns", json=body, headers=headers)
                if resp.status_code == 200:
                    res_json = resp.json()
                    if "result" in res_json and "Campaigns" in res_json["result"]:
                        campaigns = res_json["result"]["Campaigns"]
                        print(f"   -> Found {len(campaigns)} Campaigns:")
                        for c in campaigns[:10]: # Show first 10
                            print(f"      - [{c['Id']}] {c['Name']} ({c['Status']})")
                    else:
                        print(f"   -> No Campaigns found in this account.")
                else:
                     print(f"   -> Failed to list campaigns: {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"   -> Error listing campaigns: {e}")

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        
        print(f"\n[3] Requesting Statistics Report ({start_date} to {end_date})...")
        
        try:
            data = await api.get_report(
                start_date.strftime("%Y-%m-%d"), 
                end_date.strftime("%Y-%m-%d")
            )
            print(f"--- API RESPONSE ---")
            print(f"Total Rows Retrieved: {len(data)}")
            
            if data:
                print("\nSample Data (First 3 rows):")
                for row in data[:3]:
                    print(row)
                print("\nSUCCESS: The API is returning data.")
            else:
                print("\nWARNING: Yandex API returned 0 rows. This means authentication works, but there are no stats for this period.")
                print("Possible reasons:")
                print("1. Campaigns are stopped.")
                print("2. New account with no history.")
                print("3. Wrong account selected (check Login above).")
                
        except Exception as e:
            print(f"\nCRITICAL ERROR during API call: {e}")

    except Exception as e:
        print(f"Script Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_api())
