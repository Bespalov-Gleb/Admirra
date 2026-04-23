import sys
import os
from sqlalchemy import create_engine, inspect

# Add root directory to path
sys.path.append(os.getcwd())

from core.database import SQLALCHEMY_DATABASE_URL

def check_db():
    print(f"Connecting to: {SQLALCHEMY_DATABASE_URL}")
    try:
        engine = create_engine(SQLALCHEMY_DATABASE_URL)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"Tables found: {tables}")
        
        if 'users' in tables:
            print("SUCCESS: 'users' table exists.")
        else:
            print("ERROR: 'users' table is MISSING.")
            
    except Exception as e:
        print(f"CONNECTION ERROR: {str(e)}")

if __name__ == "__main__":
    check_db()
