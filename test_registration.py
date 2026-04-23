#!/usr/bin/env python3
"""
Скрипт для тестирования регистрации пользователя.
Используется для диагностики проблем с регистрацией на сервере.
"""
import requests
import json
import sys

# Настройки
API_BASE_URL = "http://localhost:8001/api"  # Измените на URL вашего сервера
# Для продакшена: API_BASE_URL = "https://your-domain.com/api"

def test_registration(email, password, username, first_name=None, last_name=None):
    """Тестирует регистрацию пользователя."""
    url = f"{API_BASE_URL}/auth/register"
    
    payload = {
        "email": email,
        "password": password,
        "username": username,
    }
    
    if first_name:
        payload["first_name"] = first_name
    if last_name:
        payload["last_name"] = last_name
    
    print(f"🔍 Тестирование регистрации...")
    print(f"   URL: {url}")
    print(f"   Email: {email}")
    print(f"   Username: {username}")
    print()
    
    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"📊 Статус ответа: {response.status_code}")
        print(f"📋 Заголовки ответа:")
        for key, value in response.headers.items():
            print(f"   {key}: {value}")
        print()
        
        try:
            data = response.json()
            print(f"📦 Тело ответа (JSON):")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except:
            print(f"📦 Тело ответа (текст):")
            print(response.text)
        
        print()
        
        if response.status_code == 200:
            print("✅ Регистрация успешна!")
            if "access_token" in data:
                print(f"   Токен получен: {data['access_token'][:20]}...")
            return True
        else:
            print(f"❌ Регистрация не удалась")
            if "detail" in data:
                print(f"   Ошибка: {data['detail']}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Ошибка подключения к {url}")
        print(f"   Убедитесь, что сервер запущен и доступен")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ Таймаут при подключении к {url}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Использование:")
        print("  python test_registration.py <email> <password> <username> [first_name] [last_name]")
        print()
        print("Пример:")
        print("  python test_registration.py test@example.com password123 testuser")
        print("  python test_registration.py test@example.com password123 testuser Иван Иванов")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    username = sys.argv[3]
    first_name = sys.argv[4] if len(sys.argv) > 4 else None
    last_name = sys.argv[5] if len(sys.argv) > 5 else None
    
    success = test_registration(email, password, username, first_name, last_name)
    sys.exit(0 if success else 1)


