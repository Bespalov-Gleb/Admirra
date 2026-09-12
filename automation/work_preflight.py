"""Fail startup before consuming jobs on a mismatched or undrained database."""
import os
from urllib.parse import urlsplit

import sqlalchemy as sa


def prepare_worker_parent():
    """Preflight may open SQL connections; parent must not retain them at fork.

    Child processes create their own pool in worker_process_init. Heartbeats
    share each child's two-connection budget, not a separate unlimited pool.
    """
    check()
    from core.database import engine
    if engine.pool.checkedout():
        raise RuntimeError("Cannot fork a worker with checked-out SQL connections")
    engine.dispose()


def check():
    from core.database import engine
    if (os.getenv("WW_TEST") == "1" and os.getenv("WW_TEST_ID")
            and urlsplit(os.getenv("DATABASE_URL", "")).hostname == "test-db"):
        return  # Schema-isolated failure tests do not install the full app DB.
    expected = os.getenv("EXPECTED_SCHEMA_REVISION")
    from core.runtime import env_bool
    if env_bool("DURABLE_TASKS", False) and not env_bool("REPORT_DELIVERY_GUARDS", True):
        raise RuntimeError("Durable workers require REPORT_DELIVERY_GUARDS")
    if env_bool("SHARED_READ_CACHE", False) and not os.getenv("READ_CACHE_REDIS_URL"):
        raise RuntimeError("READ_CACHE_REDIS_URL is required for shared reads")
    if not expected or os.getenv("APP_RELEASE", "unknown") == "unknown":
        raise RuntimeError("A versioned release and EXPECTED_SCHEMA_REVISION are required")
    with engine.begin() as db:
        db.execute(sa.text("SET TRANSACTION READ ONLY"))
        db.execute(sa.text("SET LOCAL statement_timeout = '5s'"))
        versions = db.execute(sa.text("SELECT version_num FROM alembic_version")).scalars().all()
        if versions != [expected]:
            raise RuntimeError("Database schema does not match this worker release")
        orphaned = db.scalar(sa.text("""
            SELECT count(*) FROM sync_jobs s
            WHERE s.status IN ('QUEUED', 'RUNNING') AND NOT EXISTS (
                SELECT 1 FROM background_jobs b WHERE b.kind = 'sync'
                AND b.payload->>'sync_job_id' = s.id::text AND b.state IN ('queued','running')
            )
        """))
        if orphaned:
            raise RuntimeError("Legacy sync jobs must be drained/reconciled before durable workers start")
