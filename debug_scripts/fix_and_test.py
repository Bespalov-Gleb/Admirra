from core.database import engine, Base, SessionLocal
from core import models
import sqlalchemy
from core.security import verify_password

def diagnostic():
    print("--- DB DIAGNOSTIC START ---")
    
    # 1. Essential Schema Fixes
    with engine.connect() as conn:
        # Check users table for 'username'
        try:
            conn.execute(sqlalchemy.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR;"))
            conn.commit()
            print("Verified 'username' column in 'users' table.")
        except Exception as e:
            print(f"Error updating users table: {e}")

        # Check clients table for 'spreadsheet_id'
        try:
            conn.execute(sqlalchemy.text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS spreadsheet_id VARCHAR;"))
            conn.commit()
            print("Verified 'spreadsheet_id' column in 'clients' table.")
        except Exception as e:
            print(f"Error updating clients table: {e}")

    # 2. Sync metadata
    try:
        Base.metadata.create_all(engine)
        print("MetaData create_all executed successfully.")
    except Exception as e:
        print(f"MetaData error: {e}")

    # 3. Test Login Data
    db = SessionLocal()
    try:
        user_email = 'bghvhk@gmail.com'
        test_pass = '12345678'
        user = db.query(models.User).filter_by(email=user_email).first()
        
        if user:
            print(f"User {user_email} found.")
            # Verify password
            is_valid = verify_password(test_pass, user.password_hash)
            print(f"Password verification for '12345678': {is_valid}")
            if not is_valid:
                print("WARNING: Password in DB does not match '12345678'.")
        else:
            print(f"User {user_email} NOT found in DB.")
            
    except Exception as e:
        print(f"Query error: {e}")
    finally:
        db.close()
    
    print("--- DB DIAGNOSTIC END ---")

if __name__ == "__main__":
    diagnostic()
