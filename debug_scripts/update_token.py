from core.database import SessionLocal
from core import models

def update_yandex_token(new_token: str):
    db = SessionLocal()
    try:
        # Мо интегратсияи Yandex-ро меёбем
        integration = db.query(models.Integration).filter_by(
            platform=models.IntegrationPlatform.YANDEX_DIRECT
        ).first()
        
        if integration:
            integration.access_token = new_token
            db.commit()
            print(f"Token updated successfully for client: {integration.client_id}")
        else:
            print("No Yandex integration found. Please run seed_test_data.py first.")
    except Exception as e:
        print(f"Error updating token: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    token = input("Enter your real Yandex OAuth Token: ")
    if token.strip():
        update_yandex_token(token.strip())
    else:
        print("Token cannot be empty.")
