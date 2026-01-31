#!/usr/bin/env python3
"""
Скрипт для добавления колонок cpc и cpa в таблицу vk_stats.
Можно выполнить в контейнере: docker compose exec backend python add_vk_columns.py
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load .env file
load_dotenv(override=False)

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

print("=" * 60)
print("Adding cpc and cpa columns to vk_stats table")
print("=" * 60)
print()

try:
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if columns exist
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='vk_stats' AND column_name IN ('cpc', 'cpa')
        """))
        existing_columns = {row[0] for row in result}
        
        if 'cpc' in existing_columns and 'cpa' in existing_columns:
            print("Columns cpc and cpa already exist in vk_stats table")
            sys.exit(0)
        
        # Add columns
        if 'cpc' not in existing_columns:
            print("Adding column cpc...")
            conn.execute(text("ALTER TABLE vk_stats ADD COLUMN cpc NUMERIC(20, 2) NULL"))
            conn.commit()
            print("Column cpc added successfully")
        
        if 'cpa' not in existing_columns:
            print("Adding column cpa...")
            conn.execute(text("ALTER TABLE vk_stats ADD COLUMN cpa NUMERIC(20, 2) NULL"))
            conn.commit()
            print("Column cpa added successfully")
        
        print()
        print("=" * 60)
        print("Columns added successfully!")
        print("=" * 60)
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

