import sys
import os

# Add root directory to path
sys.path.append(os.getcwd())

from core.database import SessionLocal
from core import models

def check_usernames():
    db = SessionLocal()
    try:
        users = db.query(models.User).all()
        print(f"Users in DB: {len(users)}")
        for u in users:
            print(f"Email: {u.email}, Username: {u.username}")
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    check_usernames()
