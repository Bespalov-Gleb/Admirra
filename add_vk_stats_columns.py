#!/usr/bin/env python3
"""
Скрипт для добавления колонок cpc и cpa в таблицу vk_stats.
Используется когда миграции Alembic не синхронизированы с БД.
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
    print("❌ Ошибка: DATABASE_URL не установлен")
    sys.exit(1)

print("=" * 60)
print("Добавление колонок cpc и cpa в таблицу vk_stats")
print("=" * 60)
print()

try:
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # Check if columns already exist
    with engine.connect() as conn:
        # Check if cpc column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='vk_stats' AND column_name='cpc'
        """))
        cpc_exists = result.fetchone() is not None
        
        # Check if cpa column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='vk_stats' AND column_name='cpa'
        """))
        cpa_exists = result.fetchone() is not None
        
        if cpc_exists and cpa_exists:
            print("✅ Колонки cpc и cpa уже существуют в таблице vk_stats")
            sys.exit(0)
        
        # Add columns
        if not cpc_exists:
            print("📝 Добавление колонки cpc...")
            conn.execute(text("ALTER TABLE vk_stats ADD COLUMN cpc NUMERIC(20, 2) NULL"))
            conn.commit()
            print("✅ Колонка cpc успешно добавлена")
        else:
            print("ℹ️  Колонка cpc уже существует")
        
        if not cpa_exists:
            print("📝 Добавление колонки cpa...")
            conn.execute(text("ALTER TABLE vk_stats ADD COLUMN cpa NUMERIC(20, 2) NULL"))
            conn.commit()
            print("✅ Колонка cpa успешно добавлена")
        else:
            print("ℹ️  Колонка cpa уже существует")
        
        print()
        print("=" * 60)
        print("✅ Колонки успешно добавлены в таблицу vk_stats!")
        print("=" * 60)
        
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

