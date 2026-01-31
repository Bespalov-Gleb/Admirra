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

# CRITICAL: Увеличиваем размер пула соединений для предотвращения TimeoutError
# pool_size - количество постоянных соединений в пуле
# max_overflow - максимальное количество дополнительных соединений сверх pool_size
# pool_timeout - время ожидания свободного соединения (в секундах)
# pool_recycle - время жизни соединения перед переподключением (в секундах)
# pool_pre_ping - проверка соединения перед использованием
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=20,  # Увеличено с 5 (по умолчанию) до 20
    max_overflow=30,  # Увеличено с 10 (по умолчанию) до 30
    pool_timeout=60,  # Увеличено с 30 до 60 секунд
    pool_recycle=3600,  # Переподключение каждые 1 час
    pool_pre_ping=True,  # Проверка соединения перед использованием
    echo=False  # Отключаем SQL логирование для производительности
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
