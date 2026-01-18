from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import sys
from dotenv import load_dotenv

# Load .env file only if DATABASE_URL is not already set (Docker sets it)
load_dotenv(override=False)

# We will use environment variables for the production URL
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/analytics_db")

# Log the database connection info (without password) - use print to ensure it's visible
if "@" in SQLALCHEMY_DATABASE_URL:
    host_part = SQLALCHEMY_DATABASE_URL.split("@")[1]
    print(f"[DATABASE] Connecting to database at: {host_part}", file=sys.stderr, flush=True)
else:
    print(f"[DATABASE] Using DATABASE_URL: {SQLALCHEMY_DATABASE_URL[:30]}...", file=sys.stderr, flush=True)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
