import httpx
import asyncio
from core.database import SessionLocal
from core import models

# Credentials
CLIENT_ID = "3febb68881204d9380089f718e5251b1"
CLIENT_SECRET = "9183486924ce4d38919352d5b3df6d18"

async def get_access_token(code: str):
    url = "https://oauth.yandex.ru/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=data)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            print(f"Error getting token: {response.status_code} - {response.text}")
            return None

async def update_token(code: str):
    token = await get_access_token(code)
    if not token:
        return

    db = SessionLocal()
    try:
        # Get the first client (or specific one)
        client = db.query(models.Client).first()
        if not client:
            print("No client found in database. Create a client first.")
            return

        # Check if Yandex integration exists
        integration = db.query(models.Integration).filter(
            models.Integration.client_id == client.id,
            models.Integration.platform == models.IntegrationPlatform.YANDEX_DIRECT
        ).first()

        if integration:
            integration.access_token = token
            print(f"Updated Yandex token for client: {client.name}")
        else:
            new_integration = models.Integration(
                client_id=client.id,
                platform=models.IntegrationPlatform.YANDEX_DIRECT,
                access_token=token
            )
            db.add(new_integration)
            print(f"Created new Yandex integration for client: {client.name}")
        
        db.commit()
        print("Successfully saved to database.")
    except Exception as e:
        print(f"Database error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # The code from Ivan
    ivan_code = "4kfo7jcsuprctgke"
    asyncio.run(update_token(ivan_code))
