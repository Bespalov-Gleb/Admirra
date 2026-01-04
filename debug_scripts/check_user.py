import sys
import os

# Add the parent directory to sys.path so we can import 'core'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import SessionLocal
from core import models, security

def check_user():
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == "ddd@gmail.com").first()
        if not user:
            print("User 'ddd@gmail.com' NOT FOUND.")
        else:
            print(f"User found: {user.email}")
            print(f"Role: {user.role}")
            print(f"Is Active: {user.is_active}")
            print(f"Password Hash: {user.password_hash}")
            
            # Verify password
            is_valid = security.verify_password("12345678", user.password_hash)
            print(f"Password '12345678' valid? {is_valid}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_user()
