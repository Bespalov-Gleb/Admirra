import requests
import json
from datetime import datetime, timedelta

def fetch_vk_stats(access_token):
    # 1. Суроғаи API барои омори рӯзонаи компанияҳо
    # Урл: https://ads.vk.com/api/v2/statistics/campaigns/day.json
    url = "https://ads.vk.com/api/v2/statistics/campaigns/day.json"
    
    # 2. Танзими Headers. Токен дар инҷо фиристода мешавад.
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    # 3. Танзими Вақт (Давраи омор)
    # Мо омори 7 рӯзи охирро мепурсем
    date_to = datetime.now().strftime("%Y-%m-%d")
    date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    params = {
        "date_from": date_from,
        "date_to": date_to,
        "metrics": "base" # "base" маънои Impressions, Clicks ва Spent (Хароҷот)-ро дорад.
    }
    
    print(f"\n--- Дархости омор аз VK Ads ---")
    print(f"Давра: {date_from} то {date_to}")
    
    try:
        response = requests.get(url, params=params, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ МАЪЛУМОТ ГИРИФТА ШУД!")
            
            # Сохтори маълумот дар VK Ads:
            # { "items": [ { "id": 123, "rows": [ { "date": "...", "base": { "spent": "100.20", "shows": 500, "clicks": 20 } } ] } ] }
            
            items = data.get("items", [])
            if not items:
                print("Дар ин давра ягон компания ё омор ёфт нашуд.")
            else:
                for item in items:
                    campaign_id = item.get("id")
                    print(f"\nКомпания ID: {campaign_id}")
                    for row in item.get("rows", []):
                        stats = row.get("base", {})
                        print(f"  Сана: {row.get('date')}")
                        print(f"  - Impressions (Показ): {stats.get('shows')}")
                        print(f"  - Clicks: {stats.get('clicks')}")
                        print(f"  - Cost (Spent): {stats.get('spent')} руб.")
                        
            # Захира кардани ҷавоби хом барои омӯзиш
            with open("vk_response_example.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("\n💡 Ҷавоби пурраи API дар файли 'vk_response_example.json' захира шуд.")
            
        else:
            print(f"\n❌ Хатогӣ: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"\n☢️ Хатогии системавӣ: {str(e)}")

if __name__ == "__main__":
    import os
    
    token = ""
    # Кӯшиш мекунем, ки токенро аз файли захирашуда гирем
    if os.path.exists("vk_token.txt"):
        with open("vk_token.txt", "r") as f:
            token = f.read().strip()
        print("✅ Токен аз файли 'vk_token.txt' гирифта шуд.")
    
    if not token:
        token = input("Access Token-ро ворид кунед: ").strip()
        
    if token:
        fetch_vk_stats(token)
    else:
        print("Токен ворид нашуд.")
