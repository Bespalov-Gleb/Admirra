from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.engine import make_url
import sys
from core.config import get_config
from core.runtime import env_int, get_runtime

# We will use environment variables for the production URL
SQLALCHEMY_DATABASE_URL = get_config().database.url
if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError("Missing required environment variable: DATABASE_URL")

# Log the database connection info (without password) - use print to ensure it's visible
_db_url = make_url(SQLALCHEMY_DATABASE_URL)
print(f"[DATABASE] driver={_db_url.drivername} host={_db_url.host or 'local'}", file=sys.stderr, flush=True)

# Budget connections per process; multiplying replicas also multiplies pools.
# Legacy sizes stay unchanged until the explicit runtime-role cutover.
# pool_size - количество постоянных соединений в пуле
# max_overflow - максимальное количество дополнительных соединений сверх pool_size
# pool_timeout - время ожидания свободного соединения (в секундах)
# pool_recycle - время жизни соединения перед переподключением (в секундах)
# pool_pre_ping - проверка соединения перед использованием
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    # Только для тестов (in-memory sqlite). На проде — ветка else (Postgres).
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
else:
    _legacy_pool = get_runtime().role == "legacy"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=env_int("DB_POOL_SIZE", 20 if _legacy_pool else 5, 1, 100),
        max_overflow=env_int("DB_MAX_OVERFLOW", 30 if _legacy_pool else 5, 0, 100),
        pool_timeout=env_int("DB_POOL_TIMEOUT", 60 if _legacy_pool else 5, 1, 300),
        pool_recycle=env_int("DB_POOL_RECYCLE", 3600, 30, 86400),
        pool_pre_ping=True,  # Проверка соединения перед использованием
        connect_args={"connect_timeout": env_int("DB_CONNECT_TIMEOUT", 5, 1, 60)},
        echo=False,  # Отключаем SQL логирование для производительности
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
