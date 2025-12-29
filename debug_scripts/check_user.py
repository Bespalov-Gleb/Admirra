import sys
import os

# Add root directory to path
sys.path.append(os.getcwd())

from core.database import SessionLocal
from core import models

def check_user():
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == "cfcg@gmail.com").first()
        if user:
            print(f"USER FOUND: {user.email}, id={user.id}")
        else:
            print("USER NOT FOUND: cfcg@gmail.com")
            
        all_users = db.query(models.User).all()
        print(f"Total users in DB: {len(all_users)}")
        for u in all_users:
            print(f"- {u.email}")
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    check_user()
