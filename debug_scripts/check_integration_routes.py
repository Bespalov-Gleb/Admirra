import requests
import uuid

# Replace with actual backend URL if different
BASE_URL = "http://127.0.0.1:8000/api"

# We need a valid token to bypass auth. 
# Since I can't easily get one, I'll just check if the route exists at all (expecting 401 or 405)
integration_id = "fe9585cc-8930-4a52-a451-77b21a5da980"

def check_route(method, path):
    url = f"{BASE_URL}/{path}"
    print(f"Checking {method} {url}...")
    try:
        response = requests.request(method, url)
        print(f"Response: {response.status_code} {response.reason}")
    except Exception as e:
        print(f"Error: {e}")

check_route("GET", f"integrations/{integration_id}")
check_route("PATCH", f"integrations/{integration_id}")
check_route("DELETE", f"integrations/{integration_id}")
check_route("OPTIONS", f"integrations/{integration_id}")
