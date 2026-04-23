from core.database import SessionLocal
from core import models
from core.security import get_password_hash
import sys

def fix_user():
    db = SessionLocal()
    email = "ddd@gmail.com"
    password = "12345678"
    
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        
        hashed_password = get_password_hash(password)
        
        if user:
            print(f"🔄 Updating existing user {email}...")
            user.password_hash = hashed_password
            db.commit()
            print(f"✅ User {email} updated with password '{password}'")
        else:
            print(f"🆕 Creating new user {email}...")
            new_user = models.User(
                email=email,
                username="testuser",
                first_name="Test",
                last_name="User",
                password_hash=hashed_password,
                role=models.UserRole.MANAGER
            )
            db.add(new_user)
            db.commit()
            print(f"✅ User {email} created with password '{password}'")
            
    except Exception as e:
        print(f"❌ Database error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_user()
