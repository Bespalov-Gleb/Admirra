from core.database import engine, Base, SessionLocal
from core import models
import sqlalchemy

def fix_and_fetch():
    # 1. Update Schema
    with engine.connect() as conn:
        try:
            conn.execute(sqlalchemy.text('ALTER TABLE clients ADD COLUMN IF NOT EXISTS spreadsheet_id VARCHAR;'))
            conn.commit()
            print("Database schema updated (spreadsheet_id added if missing).")
        except Exception as e:
            print(f"Note on schema update: {e}")
            
    # 2. Create potential new tables (like weekly_reports, etc.)
    Base.metadata.create_all(engine)
    print("Ensured all tables exist.")

    # 3. Fetch user data
    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(email='bghvhk@gmail.com').first()
        if not user:
            print("USER NOT FOUND: bghvhk@gmail.com")
            return

        print(f"\n--- USER INFO ---")
        print(f"Email: {user.email}")
        print(f"Password Hash: {user.password_hash}")
        
        clients = db.query(models.Client).filter_by(owner_id=user.id).all()
        for c in clients:
            print(f"\n  CLIENT: {c.name}")
            integrations = db.query(models.Integration).filter_by(client_id=c.id).all()
            if not integrations:
                print("    No tokens found for this client.")
            for i in integrations:
                print(f"    PLATFORM: {i.platform}")
                print(f"    TOKEN: {i.access_token}")
                print(f"    ACC_ID: {i.account_id}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_and_fetch()
