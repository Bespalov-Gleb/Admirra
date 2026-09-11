"""Bridge the existing UI's SyncJob ledger into the durable task transport."""
import json
import uuid
from sqlalchemy import select

from core import models
from core.database import SessionLocal
from automation.work_ledger import submit


def enqueue(integration_id, *, days, force_full, trigger, date_from=None, date_to=None, occurrence=None):
    with SessionLocal() as db:
        # Serializes enqueue even when requests hit different API instances.
        integration = db.query(models.Integration).filter(models.Integration.id == integration_id).with_for_update().first()
        if integration is None:
            raise ValueError("Integration not found")
        if occurrence:
            from automation.work_tables import jobs
            previous = db.execute(select(jobs.c.payload).where(
                jobs.c.dedupe_key == f"night:{integration_id}:{occurrence}")).scalar()
            if previous:
                return uuid.UUID(previous["sync_job_id"])
        existing = db.query(models.SyncJob).filter(
            models.SyncJob.integration_id == integration_id,
            models.SyncJob.status.in_([models.SyncJobStatus.QUEUED, models.SyncJobStatus.RUNNING]),
        ).order_by(models.SyncJob.created_at).first()
        if existing:
            return existing.id
        params = {"days": days, "force_full": force_full, "trigger": trigger}
        if date_from and date_to:
            params.update(date_from=date_from, date_to=date_to)
        job_id = uuid.uuid4()
        job = models.SyncJob(id=job_id, integration_id=integration_id, status=models.SyncJobStatus.QUEUED,
                             stage="queued", progress=0, params=json.dumps(params))
        db.add(job)
        integration.sync_status = models.IntegrationSyncStatus.PENDING
        integration.error_message = None
        db.flush()
        submit(db, kind="sync", queue="sync.nightly" if trigger == "auto" else "sync.manual",
               key=f"night:{integration_id}:{occurrence}" if occurrence else f"sync:{job_id}",
               resource=f"integration:{integration_id}", tenant=integration.client_id,
               payload={"sync_job_id": str(job_id)}, replay_safe=True)
        db.commit()
        return job_id


def execute(payload):
    from backend_api.sync_jobs import _run_job_sync
    job_id = uuid.UUID(payload["sync_job_id"])
    with SessionLocal() as db:
        if db.execute(select(models.SyncJob.status).where(models.SyncJob.id == job_id)).scalar() == models.SyncJobStatus.SUCCESS:
            return
    _run_job_sync(job_id)
    with SessionLocal() as db:
        status = db.execute(select(models.SyncJob.status).where(models.SyncJob.id == job_id)).scalar()
        if status != models.SyncJobStatus.SUCCESS:
            raise RuntimeError("Sync did not complete successfully; see SyncJob error")


def enqueue_goals(integration_id, date_from, date_to):
    from datetime import datetime
    if datetime.strptime(date_from, "%Y-%m-%d") > datetime.strptime(date_to, "%Y-%m-%d"):
        raise ValueError("Invalid goals date range")
    with SessionLocal() as db:
        integration = db.query(models.Integration).filter(models.Integration.id == integration_id).with_for_update().first()
        if not integration:
            return
        # Small time bucket prevents a dashboard polling loop creating endless work.
        from sqlalchemy import func
        minute = int(db.execute(select(func.extract("epoch", func.clock_timestamp()))).scalar_one()) // 300
        submit(db, kind="goals", queue="sync.manual", key=f"goals:{integration_id}:{date_from}:{date_to}:{minute}",
               resource=f"integration:{integration_id}", tenant=integration.client_id,
               payload={"integration_id": str(integration_id), "date_from": date_from, "date_to": date_to}, replay_safe=True)
        db.commit()
