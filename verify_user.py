from core.database import SessionLocal
from core import models
from core.security import verify_password
import sys

def check_user():
    db = SessionLocal()
    email = "ddd@gmail.com"
    password = "12345678"
    
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            print(f"❌ User {email} NOT FOUND in database.")
            return

        print(f"✅ User found: {user.email}")
        print(f"   ID: {user.id}")
        
        # Check password
        is_valid = verify_password(password, user.password_hash)
        if is_valid:
            print(f"✅ Password '{password}' is CORRECT.")
        else:
            print(f"❌ Password '{password}' is INCORRECT.")
            print(f"   Stored Hash: {user.password_hash}")
            
    except Exception as e:
        print(f"❌ Database error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_user()
