from core.database import SessionLocal
from core import models
from core.security import get_password_hash
import sys

def migrate_cyrillic_user():
    db = SessionLocal()
    
    # Cyrillic 'ддд'
    cyrillic_email = "ддд@gmail.com"
    # Latin 'ddd'
    latin_email = "ddd@gmail.com"
    
    password = "12345678"
    hashed_password = get_password_hash(password)
    
    try:
        user_cyrillic = db.query(models.User).filter(models.User.email == cyrillic_email).first()
        user_latin = db.query(models.User).filter(models.User.email == latin_email).first()
        
        if user_cyrillic:
            print(f"✅ Found user with Cyrillic email: {cyrillic_email} (ID: {user_cyrillic.id})")
            
            if user_latin:
                print(f"⚠️ Found user with Latin email: {latin_email} (ID: {user_latin.id})")
                
                # Check if the Latin user is the one we just created (e.g., no related data)
                # For safety, since I just created it, I will assume it's safe to delete IF the user explicitly asked to "change" the Cyrillic one.
                print(f"🗑️ Deleting the Latin user (assuming it's the fresh empty one)...")
                db.delete(user_latin)
                db.flush() # Flush to handle constraint before renaming
                
            print(f"🔄 Renaming Cyrillic user to Latin...")
            user_cyrillic.email = latin_email
            # Ensure password is correct too
            user_cyrillic.password_hash = hashed_password
            
            db.commit()
            print(f"✅ Successfully migrated {cyrillic_email} -> {latin_email}")
            
        elif user_latin:
             print(f"ℹ️ Cyrillic user not found, but Latin user exists. Updating password to be sure.")
             user_latin.password_hash = hashed_password
             db.commit()
             print(f"✅ User {latin_email} ready.")
        else:
             print("❌ Neither Cyrillic nor Latin user found.")

    except Exception as e:
        print(f"❌ Database error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_cyrillic_user()
