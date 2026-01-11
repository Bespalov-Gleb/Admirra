import sys
import os

# Add the parent directory to sys.path so we can import 'core'
sys.path.append(os.getcwd())

from core.database import SessionLocal
from core import models

def check_exists(email, username):
    db = SessionLocal()
    try:
        user_email = db.query(models.User).filter(models.User.email == email).first()
        user_name = db.query(models.User).filter(models.User.username == username).first()
        
        print(f"Checking Email: {email}")
        if user_email:
            print(f"FOUND user with email {email}")
        else:
            print(f"Email {email} is available.")
            
        print(f"Checking Username: {username}")
        if user_name:
            print(f"FOUND user with username {username}")
        else:
            print(f"Username {username} is available.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_exists("iii@gmail.com", "iii")
