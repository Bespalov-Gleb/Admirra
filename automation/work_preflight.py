"""Fail startup before consuming jobs on a mismatched or undrained database."""
import os
from urllib.parse import urlsplit

import sqlalchemy as sa


def check_integration_bindings(db):
    unbound = db.scalar(sa.text("""
        SELECT count(*) FROM background_jobs
        WHERE kind IN ('goals', 'history.backfill') AND state IN ('queued', 'running')
          AND (payload->>'owner_id' IS DISTINCT FROM tenant
            OR nullif(payload->>'owner_id', '') IS NULL
            OR nullif(payload->>'client_id', '') IS NULL
            OR nullif(payload->>'integration_id', '') IS NULL
            OR resource IS DISTINCT FROM 'integration:' || (payload->>'integration_id'))
    """))
    if unbound:
        raise RuntimeError("Unbound legacy integration jobs must be reconciled/resubmitted before worker startup")


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


def check_lead_alert_bindings(db):
    legacy = db.scalar(sa.text("""
        SELECT count(*) FROM background_jobs
        WHERE kind IN ('lead.daily', 'lead.weekly')
          AND state IN ('queued', 'running', 'uncertain') AND NOT replay_safe
    """))
    if legacy:
        raise RuntimeError("Legacy global lead sends must be reconciled before scoped planners start")


def check_billing_bindings(db):
    from core.runtime import env_bool
    exists = db.scalar(sa.text("SELECT to_regclass('billing_provider_operations')"))
    enabled = env_bool("BILLING_PROVIDER_QUEUE", False)
    if enabled and not exists:
        raise RuntimeError("Billing provider queue requires its additive schema migration")
    if exists and not enabled:
        pending = db.scalar(sa.text("SELECT count(*) FROM billing_provider_operations WHERE status IN ('queued','dispatching','uncertain','rejected')"))
        if pending:
            raise RuntimeError("Cannot disable billing queue with unresolved financial operations")
    if enabled:
        unknown = db.scalar(sa.text("SELECT count(*) FROM background_jobs WHERE kind = 'billing.recurring' AND state = 'uncertain'"))
        if unknown:
            raise RuntimeError("Reconcile uncertain legacy billing writes before enabling account queue")


def check_lead_delivery_bindings(db):
    from core.runtime import env_bool
    enabled = env_bool('LEAD_DELIVERY_GUARDS', False)
    intake = db.scalar(sa.text("SELECT to_regclass('lead_intakes')"))
    receipts = db.scalar(sa.text("SELECT to_regclass('lead_export_receipts')"))
    resolutions = db.scalar(sa.text("SELECT to_regclass('lead_operation_resolutions')"))
    if enabled and (not intake or not receipts or not resolutions):
        raise RuntimeError('Lead delivery guards require their additive schema migration')
    if not enabled:
        pending = db.scalar(sa.text("SELECT count(*) FROM background_jobs WHERE kind = 'lead.export' AND state IN ('queued','running','uncertain')"))
        if pending or intake and db.scalar(sa.text("SELECT EXISTS (SELECT 1 FROM lead_intakes)")):
            # Even completed keys must remain authoritative: a rollback to the
            # global legacy path would bypass idempotency on provider retries.
            raise RuntimeError('Cannot disable lead delivery guards after persisted admissions; use a compatible release')


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
        check_integration_bindings(db)
        check_lead_alert_bindings(db)
        check_lead_delivery_bindings(db)
        check_billing_bindings(db)
        if not db.scalar(sa.text("SELECT to_regclass('lead_placement_blocks')")):
            raise RuntimeError('Scoped lead placements require their additive schema migration')
