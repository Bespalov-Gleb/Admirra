import sys
import os

# Add root directory to path
sys.path.append(os.getcwd())

from core.database import SessionLocal
from backend_api.auth import register_user
from core import schemas

def test_registration():
    db = SessionLocal()
    try:
        user_in = schemas.UserCreate(
            email="iii@gmail.com",
            password="testpassword123",
            username="iii"
        )
        print("Attempting registration...")
        result = register_user(user=user_in, db=db)
        print(f"SUCCESS: {result}")
    except Exception as e:
        print(f"REGISTRATION ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_registration()
