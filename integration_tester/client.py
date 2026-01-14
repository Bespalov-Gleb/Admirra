import httpx
import logging

logger = logging.getLogger(__name__)

class IntegrationApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.Client(base_url=self.base_url, timeout=30.0)
        self.token = None

    def login(self, email: str, password: str):
        logger.info(f"Logging in as {email}...")
        response = self.client.post("/auth/login", json={
            "email": email,
            "password": password
        })
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        self.client.headers.update({"Authorization": f"Bearer {self.token}"})
        logger.info("Login successful")
        return data

    def get(self, endpoint: str, params: dict = None):
        response = self.client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, json_data: dict = None):
        response = self.client.post(endpoint, json=json_data)
        response.raise_for_status()
        return response.json()

    def patch(self, endpoint: str, json_data: dict = None):
        response = self.client.patch(endpoint, json=json_data)
        response.raise_for_status()
        return response.json()

    def delete(self, endpoint: str):
        response = self.client.delete(endpoint)
        response.raise_for_status()
        return response
