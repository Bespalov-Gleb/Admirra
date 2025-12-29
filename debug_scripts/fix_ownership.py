from core.database import SessionLocal
from core import models

def fix_ownership():
    db = SessionLocal()
    try:
        target_user = db.query(models.User).filter(models.User.email == 'bghvhk@gmail.com').first()
        if target_user:
            # Reassign all clients to bghvhk@gmail.com
            db.query(models.Client).update({models.Client.owner_id: target_user.id})
            db.commit()
            print(f"Success: All clients reassigned to {target_user.email}")
        else:
            print("User bghvhk@gmail.com not found. Please create this user first.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_ownership()
