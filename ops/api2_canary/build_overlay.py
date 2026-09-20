"""Patch the exact active billing backend into an API-only replica image.

The base image is intentionally the production digest, not repository HEAD.
Every source hash and replacement count is checked so a later image cannot be
silently patched with assumptions made for the 2026-09-20 canary.
"""
from __future__ import annotations

import hashlib
from pathlib import Path


FILES = {
    Path("/app/backend_api/main.py"): "3436bdecf91b563bbe5a501029fbbb03960aff9f505a184ca22be19a74247248",
    Path("/app/backend_api/health_routes.py"): "f530f342ab1d068a4a62774a58ca21c47a93ff692b7bb4fb7b849296bf93a777",
    Path("/app/core/database.py"): "17d998c81f7b7d2eb0c77f7fdc40794b4ab7fb3a3e8c12d02a5a72f93117ccc4",
}


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


for path, expected in FILES.items():
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise RuntimeError(f"unexpected base source: {path}")

main_path = Path("/app/backend_api/main.py")
main = main_path.read_text()
main = replace_once(
    main,
    "load_dotenv()\n",
    """load_dotenv()

# A replica must never run schema DDL, embedded synchronization or schedulers.
# The public production process keeps its legacy behaviour; this flag is set
# only on the private second node.
API_ONLY_REPLICA = (os.getenv("API_ONLY_REPLICA") or "").strip().lower() in {"1", "true", "yes"}
""",
    "replica flag",
)
main = replace_once(
    main,
    "\ninit_db_with_retry()\n",
    """
if API_ONLY_REPLICA:
    # Connectivity preflight only: the serving replica cannot run DDL or seeds.
    with engine.connect() as _replica_connection:
        _replica_connection.execute(text("SELECT 1"))
        _replica_connection.rollback()
    logger.info("API-only replica database preflight passed; schema bootstrap disabled")
else:
    init_db_with_retry()
""",
    "schema bootstrap guard",
)
main = replace_once(
    main,
    'async def startup_event():\n    """Инициализация при старте приложения"""\n',
    '''async def startup_event():
    """Инициализация при старте приложения"""
    if API_ONLY_REPLICA:
        logger.info("API-only replica started; embedded worker and schedulers disabled")
        return
''',
    "startup guard",
)
main = replace_once(
    main,
    'async def shutdown_event():\n    """Очистка при остановке приложения"""\n',
    '''async def shutdown_event():
    """Очистка при остановке приложения"""
    if API_ONLY_REPLICA:
        logger.info("API-only replica stopped")
        return
''',
    "shutdown guard",
)
main_path.write_text(main)

health_path = Path("/app/backend_api/health_routes.py")
health = health_path.read_text()
health = replace_once(
    health,
    "from fastapi import APIRouter, HTTPException\n",
    "from fastapi import APIRouter, HTTPException\nfrom sqlalchemy import text\n",
    "health SQL import",
)
health = replace_once(
    health,
    'router = APIRouter(prefix="/health", tags=["Health"])\n',
    '''router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live")
def live():
    """Process liveness. It intentionally has no external dependencies."""
    return {"status": "ok"}


@router.get("/ready")
def ready():
    """Short shared-database check used before admitting replica traffic."""
    from core.database import engine
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            connection.rollback()
    except Exception:
        logger.exception("Replica readiness database check failed")
        raise HTTPException(status_code=503, detail="database unavailable") from None
    return {"status": "ready", "database": "ok"}
''',
    "health endpoints",
)
health_path.write_text(health)

database_path = Path("/app/core/database.py")
database = database_path.read_text()
database = replace_once(database, "import sys\n", "import sys\nimport os\n", "database os import")
database = replace_once(
    database,
    '''else:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=20,  # Увеличено с 5 (по умолчанию) до 20
        max_overflow=30,  # Увеличено с 10 (по умолчанию) до 30
        pool_timeout=60,  # Увеличено с 30 до 60 секунд
''',
    '''else:
    api_only_replica = (os.getenv("API_ONLY_REPLICA") or "").strip().lower() in {"1", "true", "yes"}
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        # Keep the replica inside the dedicated role's connection budget.
        pool_size=5 if api_only_replica else 20,
        max_overflow=0 if api_only_replica else 30,
        pool_timeout=5 if api_only_replica else 60,
''',
    "bounded database pool",
)
database_path.write_text(database)
