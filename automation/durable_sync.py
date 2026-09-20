"""Bridge the existing UI's SyncJob ledger into the durable task transport."""
import json
import uuid
from sqlalchemy import select

from core import models
from core.database import SessionLocal
from automation.work_ledger import submit, _serialize_claims
from automation.work_tables import jobs
from automation.sync_request import request_params, read_params, covers, merged


def _record_occurrence(db, occurrence, integration_id, job_id, owner_id):
    if occurrence:
        # A night tick which joins manual work must still remember that binding
        # after the manual job finishes; replaying the planner cannot resync it.
        submit(db, kind="sync.alias", queue="maintenance", key=f"night:{integration_id}:{occurrence}",
               resource=f"sync-alias:{integration_id}", tenant=owner_id,
               payload={"sync_job_id": str(job_id)}, replay_safe=True)


def enqueue(integration_id, *, days, force_full, trigger, date_from=None, date_to=None, occurrence=None, expected_owner_id=None):
    with SessionLocal() as db:
        # Queue coalescing and worker claim must never race. No provider IO or
        # long-running work occurs while this short control-plane lock is held.
        _serialize_claims(db)
        client_id = db.scalar(select(models.Integration.client_id).where(models.Integration.id == integration_id))
        client = db.query(models.Client).filter(models.Client.id == client_id).with_for_update().first()
        # Serializes enqueue even when requests hit different API instances.
        integration = db.query(models.Integration).filter(models.Integration.id == integration_id).with_for_update().first()
        if integration is None or client is None or integration.client_id != client.id:
            if expected_owner_id is not None:
                return None
            raise ValueError("Integration not found")
        if expected_owner_id is not None:
            # A queued calendar child must not follow a moved/paused cabinet to
            # another account. Recheck under the enqueue transaction's locks.
            if (client.id != integration.client_id or client.owner_id != expected_owner_id or client.status != models.ClientStatus.ACTIVE
                    or integration.connection_status != "active"):
                return None
        if occurrence:
            previous = db.execute(select(jobs.c.payload).where(
                jobs.c.dedupe_key == f"night:{integration_id}:{occurrence}")).scalar()
            if previous:
                return uuid.UUID(previous["sync_job_id"])
        params = request_params(integration, client, days=days, force_full=force_full, trigger=trigger,
                                date_from=date_from, date_to=date_to)
        active = db.query(models.SyncJob).filter(
            models.SyncJob.integration_id == integration_id,
            models.SyncJob.status.in_([models.SyncJobStatus.QUEUED, models.SyncJobStatus.RUNNING]),
        ).order_by(models.SyncJob.created_at, models.SyncJob.id).all()
        for existing in active:
            if covers(read_params(existing), params):
                if trigger != "auto" and existing.status == models.SyncJobStatus.QUEUED:
                    promoted = db.execute(jobs.update().where(jobs.c.kind == "sync", jobs.c.state == "queued",
                        jobs.c.tenant == str(client.owner_id),
                        jobs.c.payload["sync_job_id"].astext == str(existing.id)).values(queue="sync.manual")).rowcount
                    if promoted:
                        existing.params = json.dumps({**read_params(existing), "trigger": trigger})
                _record_occurrence(db, occurrence, integration_id, existing.id, client.owner_id)
                db.commit()
                return existing.id
        for pending in reversed(active):
            transport = db.execute(select(jobs.c.id, jobs.c.state, jobs.c.tenant).where(jobs.c.kind == "sync",
                jobs.c.payload["sync_job_id"].astext == str(pending.id))).first()
            if (pending.status == models.SyncJobStatus.QUEUED and transport and transport.state == "queued"
                    and transport.tenant == str(client.owner_id)):
                pending.params = json.dumps(merged(read_params(pending), params))
                if trigger != "auto":
                    db.execute(jobs.update().where(jobs.c.id == transport.id).values(queue="sync.manual"))
                _record_occurrence(db, occurrence, integration_id, pending.id, client.owner_id)
                db.commit()
                return pending.id
        if active:
            params["after_sync_job_id"] = str(active[-1].id)
        job_id = uuid.uuid4()
        job = models.SyncJob(id=job_id, integration_id=integration_id, status=models.SyncJobStatus.QUEUED,
                             stage="queued", progress=0, params=json.dumps(params))
        db.add(job)
        integration.sync_status = models.IntegrationSyncStatus.PENDING
        integration.error_message = None
        db.flush()
        submit(db, kind="sync", queue="sync.nightly" if trigger == "auto" else "sync.manual",
               key=f"night:{integration_id}:{occurrence}" if occurrence else f"sync:{job_id}",
               resource=f"integration:{integration_id}", tenant=client.owner_id,
               payload={"sync_job_id": str(job_id), "owner_id": str(client.owner_id),
                        "client_id": str(client.id), "after_sync_job_id": params.get("after_sync_job_id")}, replay_safe=True)
        db.commit()
        return job_id


def execute(payload):
    from backend_api.sync_jobs import _run_job_sync
    job_id = uuid.UUID(payload["sync_job_id"])
    with SessionLocal() as db:
        business_job = db.get(models.SyncJob, job_id)
        if business_job and business_job.status == models.SyncJobStatus.SUCCESS:
            return
        integration = db.get(models.Integration, business_job.integration_id) if business_job else None
        client = db.get(models.Client, integration.client_id) if integration else None
        if (not client or client.status != models.ClientStatus.ACTIVE or integration.connection_status != "active"
                or (payload.get("owner_id") and str(client.owner_id) != payload["owner_id"])
                or (payload.get("client_id") and str(client.id) != payload["client_id"])):
            if business_job:
                business_job.status = models.SyncJobStatus.FAILED
                business_job.stage = "skipped"
                business_job.error = "Источник удалён, отключён или изменил владельца"
                from datetime import datetime, timezone
                business_job.finished_at = datetime.now(timezone.utc)
                db.commit()
            raise ValueError("Queued sync scope is no longer authorized")
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
               resource=f"integration:{integration_id}", tenant=integration.client.owner_id,
               payload={"integration_id": str(integration_id), "date_from": date_from, "date_to": date_to}, replay_safe=True)
        db.commit()
