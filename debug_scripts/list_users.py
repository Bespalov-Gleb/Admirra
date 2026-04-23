import sys
import os
sys.path.append(os.getcwd())

from core.database import SessionLocal
from core import models

db = SessionLocal()
try:
    count = db.query(models.User).count()
    print(f"Total users: {count}")
    
    users = db.query(models.User).all()
    for u in users:
        print(f"- {u.email} ({u.username})")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
