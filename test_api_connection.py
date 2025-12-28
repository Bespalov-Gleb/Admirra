import httpx
import json

def test_api_register():
    url = "http://localhost:8000/api/auth/register"
    payload = {
        "email": "network_test_1@example.com",
        "password": "testpassword123",
        "username": "network_user_1"
    }
    
    print(f"Sending POST to {url}...")
    try:
        response = httpx.post(url, json=payload, timeout=5.0)
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
    except Exception as e:
        print(f"NETWORK ERROR: {str(e)}")

if __name__ == "__main__":
    test_api_register()
