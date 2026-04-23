from core.database import SessionLocal
from core import models
import random
from datetime import datetime, timedelta

def seed():
    db = SessionLocal()
    try:
        # 1. Ensure User
        user = db.query(models.User).filter_by(email="bghvhk@gmail.com").first()
        if not user:
            user = db.query(models.User).filter_by(email="admin@example.com").first()
        
        if not user:
            print("No suitable user found. Please register first.")
            return

        # 2. Ensure Client
        client = db.query(models.Client).filter_by(name="Test Client").first()
        if not client:
            client = models.Client(
                owner_id=user.id,
                name="Test Client",
                description="Demo client for Yandex"
            )
            db.add(client)
            db.flush()
            print("Created Test Client.")
        
        # 3. Ensure Integration
        integration = db.query(models.Integration).filter_by(client_id=client.id).first()
        if not integration:
            integration = models.Integration(
                client_id=client.id,
                platform=models.IntegrationPlatform.YANDEX_DIRECT,
                access_token="MOCK_TOKEN",
                account_id="test-account"
            )
            db.add(integration)
            print("Created Mock Integration.")

        # 4. Ensure 14 days of Stats
        existing_stats = db.query(models.YandexStats).filter_by(client_id=client.id).count()
        if existing_stats < 14:
            today = datetime.utcnow().date()
            for i in range(14):
                stat_date = today - timedelta(days=i)
                # Check if this specific day exists
                day_exists = db.query(models.YandexStats).filter_by(client_id=client.id, date=stat_date).first()
                if not day_exists:
                    db.add(models.YandexStats(
                        client_id=client.id,
                        date=stat_date,
                        campaign_name="General Campaign",
                        impressions=random.randint(5000, 15000),
                        clicks=random.randint(100, 500),
                        cost=round(random.uniform(500, 2000), 2),
                        conversions=random.randint(5, 20)
                    ))
            db.commit()
            print("14 days of Stats verified/added.")
        else:
            print("Stats already exist.")

    except Exception as e:
        print(f"Seed error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
