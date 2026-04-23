import requests
import json

def test_vk_auth(client_id, client_secret):
    url = "https://ads.vk.com/api/v2/oauth2/token.json"
    
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }
    
    print(f"\n--- Тест пайвастшавӣ ба VK Ads ---")
    print(f"Ирсол ба: {url}")
    print(f"Бо маълумоти: client_id={client_id}, client_secret={'*' * len(client_secret)}")
    
    try:
        response = requests.post(url, data=payload)
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get('access_token')
            print("\n✅ МУВАФФАҚИЯТ!")
            print(f"Access Token гирифта шуд: {access_token[:15]}...")
            
            # Захира кардани токен дар файл
            with open("vk_token.txt", "w") as f:
                f.write(access_token)
            print("💡 Токени пурра дар файли 'vk_token.txt' захира шуд.")
            
            if data.get('refresh_token'):
                print(f"Refresh Token: {data.get('refresh_token')[:15]}...")
        else:
            print("\n❌ ХАТОГИИ API!")
            try:
                error_data = response.json()
                print(f"Паёми хатогӣ: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                
                if error_data.get('error') == 'invalid_client':
                    print("\n💡 ДИҚҚАТ: Ключҳо (Client ID ё Secret) нодуруст ҳастанд.")
                    print("Эҳтимол, шумо ID-и кабинетро ба ҷои Client ID ворид кардед.")
            except:
                print(f"Ҷавоби хом (Raw): {response.text}")
                
    except Exception as e:
        print(f"\n☢️ Хатогии системавӣ: {str(e)}")

if __name__ == "__main__":
    cid = input("Client ID-ро ворид кунед: ").strip()
    csecret = input("Client Secret-ро ворид кунед: ").strip()
    test_vk_auth(cid, csecret)
