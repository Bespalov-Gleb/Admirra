from core.database import SessionLocal
from core.models import User
from core.security import get_password_hash
import sys

def reset_password(email, new_password):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"❌ Корбар бо email {email} ёфт нашуд.")
            return

        print(f"Корбар ёфт шуд: {user.username} ({user.email})")
        
        hashed_pw = get_password_hash(new_password)
        user.password_hash = hashed_pw
        
        db.commit()
        print(f"✅ Парол барои {email} бо муваффақият ба '{new_password}' иваз карда шуд!")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    target_email = "ддд@gmail.com" # Email-и худро дар инҷо нависед
    new_pass = "123456"           # Пароли навро дар инҷо нависед
    
    reset_password(target_email, new_pass)
