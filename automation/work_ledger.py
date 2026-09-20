"""PostgreSQL jobs + transactional outbox. Redis is transport, never job truth."""
from datetime import timedelta
import uuid
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert

from automation.work_tables import jobs, outbox
from core.runtime import env_int

CLAIM_LOCK = 731971031


def submit(db, *, kind, queue, key, resource, tenant, payload, replay_safe=False, max_attempts=3):
    """Caller commits the business change and this outbox record atomically."""
    job_id = uuid.uuid4()
    inserted = db.execute(insert(jobs).values(
        id=job_id, kind=kind, queue=queue, dedupe_key=key, resource=resource,
        tenant=str(tenant), payload=payload, replay_safe=replay_safe, max_attempts=max_attempts,
    ).on_conflict_do_nothing(index_elements=[jobs.c.dedupe_key]).returning(jobs.c.id)).scalar()
    if inserted is None:
        return db.execute(sa.select(jobs.c.id).where(jobs.c.dedupe_key == key)).scalar_one()
    db.execute(insert(outbox).values(job_id=job_id))
    return job_id


def _clock(db):
    return db.execute(sa.select(sa.func.clock_timestamp())).scalar_one()


def _serialize_claims(db):
    db.execute(sa.text("SELECT pg_advisory_xact_lock(:key)"), {"key": CLAIM_LOCK})


def recover_expired(db):
    """Safe work can retry; uncertain external effects require reconciliation."""
    _serialize_claims(db)
    now = _clock(db)
    expired = db.execute(sa.select(jobs).where(jobs.c.state == "running", jobs.c.lease_until <= now)
                         .with_for_update(skip_locked=True).limit(100)).mappings().all()
    for job in expired:
        can_retry = job["replay_safe"] and job["attempt"] < job["max_attempts"]
        state = "queued" if can_retry else "failed" if job["replay_safe"] else "uncertain"
        db.execute(jobs.update().where(jobs.c.id == job["id"]).values(
            state=state, lease_token=None, lease_until=None, error_type="WorkerLeaseExpired",
            available_at=now + timedelta(seconds=5), finished_at=None if can_retry else now,
        ))
        db.execute(outbox.update().where(outbox.c.job_id == job["id"]).values(next_publish_at=now))
        if not can_retry:
            db.execute(outbox.delete().where(outbox.c.job_id == job["id"]))
            if job["kind"] == "sync":
                # Keep the existing frontend polling contract terminal too.
                from core import models
                sync_id = uuid.UUID(job["payload"]["sync_job_id"])
                sync_job = db.get(models.SyncJob, sync_id)
                if sync_job and sync_job.status != models.SyncJobStatus.SUCCESS:
                    sync_job.status = models.SyncJobStatus.FAILED
                    sync_job.finished_at = now.replace(tzinfo=None)
                    sync_job.error = "Воркер остановлен; исчерпаны попытки восстановления"
                    integration = db.get(models.Integration, sync_job.integration_id)
                    if integration and integration.sync_status == models.IntegrationSyncStatus.PENDING:
                        integration.sync_status = models.IntegrationSyncStatus.FAILED
                        integration.error_message = sync_job.error
    return len(expired)


def claim(db, job_id, *, lease_seconds=None):
    _serialize_claims(db)
    now = _clock(db)
    job = db.execute(sa.select(jobs).where(jobs.c.id == job_id).with_for_update()).mappings().first()
    if not job or job["state"] != "queued" or job["available_at"] > now:
        return None
    # A resource is exclusive (e.g. full sync and goals-only sync of one cabinet).
    busy = db.execute(sa.select(jobs.c.id).where(jobs.c.resource == job["resource"], jobs.c.state == "running")).first()
    if busy:
        return None
    if job["kind"] == "sync" and job["payload"].get("after_sync_job_id"):
        from core import models
        previous_id = uuid.UUID(job["payload"]["after_sync_job_id"])
        previous = db.get(models.SyncJob, previous_id)
        # Never invert dependent windows even if messages arrive out of order.
        # Missing predecessor can follow an explicit retention/delete; a
        # still-active predecessor must finish first (success OR failure).
        if previous and previous.status in (models.SyncJobStatus.QUEUED, models.SyncJobStatus.RUNNING):
            return None
    if job["kind"] == "history.backfill":
        # One historical chunk globally; current manual/nightly work gets
        # priority, and newer chunks never jump over older queued windows.
        higher_priority = db.scalar(sa.select(sa.func.count()).select_from(jobs).where(
            jobs.c.queue.in_(["sync.manual", "sync.nightly"]), jobs.c.state == "queued", jobs.c.available_at <= now))
        history_busy = db.scalar(sa.select(sa.func.count()).select_from(jobs).where(
            jobs.c.kind == "history.backfill", jobs.c.state == "running"))
        earlier = db.scalar(sa.select(sa.func.count()).select_from(jobs).where(
            jobs.c.kind == "history.backfill", jobs.c.resource == job["resource"], jobs.c.state == "queued",
            jobs.c.payload["date_from"].astext < job["payload"]["date_from"]))
        last_history = db.scalar(sa.select(sa.func.max(jobs.c.finished_at)).where(jobs.c.kind == "history.backfill"))
        cooling = last_history and now < last_history + timedelta(seconds=env_int("DYNAMICS_BACKFILL_THROTTLE_SEC", 15, 0, 600))
        if higher_priority or history_busy or earlier or cooling:
            return None
    if job["queue"].startswith("sync."):
        running_sync = sa.and_(jobs.c.state == "running", jobs.c.queue.like("sync.%"))
        total = db.execute(sa.select(sa.func.count()).select_from(jobs).where(running_sync)).scalar_one()
        tenant = db.execute(sa.select(sa.func.count()).select_from(jobs).where(running_sync, jobs.c.tenant == job["tenant"])).scalar_one()
        if total >= env_int("SYNC_GLOBAL_CONCURRENCY", 4, 1, 32) or tenant >= env_int("SYNC_TENANT_CONCURRENCY", 2, 1, 16):
            return None
    token = uuid.uuid4()
    seconds = lease_seconds or env_int("TASK_LEASE_SECONDS", 120, 30, 600)
    db.execute(jobs.update().where(jobs.c.id == job_id).values(
        state="running", lease_token=token, lease_until=now + timedelta(seconds=seconds),
        heartbeat_at=now, attempt=job["attempt"] + 1, error_type=None,
    ))
    return {**dict(job), "lease_token": token, "attempt": job["attempt"] + 1}


def heartbeat(db, job_id, token):
    now = _clock(db)
    return db.execute(jobs.update().where(
        jobs.c.id == job_id, jobs.c.lease_token == token, jobs.c.state == "running", jobs.c.lease_until > now,
    ).values(heartbeat_at=now, lease_until=now + timedelta(seconds=env_int("TASK_LEASE_SECONDS", 120, 30, 600)))).rowcount == 1


def prune_completed(db):
    """Bound retention; never delete queued, running, or uncertain work."""
    cutoff = _clock(db) - timedelta(days=env_int("TASK_RETENTION_DAYS", 30, 7, 365))
    old = sa.select(jobs.c.id).where(jobs.c.state.in_(["succeeded", "failed"]), jobs.c.finished_at < cutoff,
                                  jobs.c.kind != "history.backfill")
    old = old.order_by(jobs.c.finished_at).limit(500).with_for_update(skip_locked=True)
    return db.execute(jobs.delete().where(jobs.c.id.in_(old))).rowcount


def finish(db, job_id, token, *, error=None):
    now = _clock(db)
    # Execution retries are explicit. Broker redelivery alone cannot replay an
    # external side effect after a completed/failed execution.
    state = "succeeded" if error is None else sa.case((jobs.c.replay_safe.is_(False), "uncertain"), else_="failed")
    changed = db.execute(jobs.update().where(
        jobs.c.id == job_id, jobs.c.lease_token == token, jobs.c.state == "running", jobs.c.lease_until > now,
    ).values(state=state, finished_at=now, lease_token=None, lease_until=None,
             error_type=type(error).__name__[:128] if error else None)).rowcount
    if changed:
        db.execute(outbox.delete().where(outbox.c.job_id == job_id))
    return bool(changed)


def reserve_publications(db, *, batch_size=10):
    """Short transaction: reserve attempts, never call Redis in here.

    Outbox deadline is the publication lease; publish_count is its monotonic
    generation/attempt count, not a business execution or success counter.
    """
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or not 1 <= batch_size <= 10:
        raise ValueError("Publication batch must contain 1..10 jobs")
    now = _clock(db)
    pending = db.execute(sa.select(jobs.c.id, jobs.c.queue).join(outbox, outbox.c.job_id == jobs.c.id).where(
        jobs.c.state == "queued", jobs.c.available_at <= now, outbox.c.next_publish_at <= now,
    ).order_by(sa.case(
        (jobs.c.queue == "sync.manual", 0), (jobs.c.queue == "reports", 1),
        (jobs.c.queue == "maintenance", 2), (jobs.c.queue == "sync.nightly", 3),
        (jobs.c.queue == "ai.prewarm", 4), else_=5), jobs.c.created_at, jobs.c.id)
        .with_for_update(of=outbox, skip_locked=True).limit(batch_size)).all()
    reserved = []
    for job_id, queue in pending:
        row = db.execute(outbox.update().where(outbox.c.job_id == job_id).values(
            next_publish_at=now + timedelta(seconds=120), publish_count=outbox.c.publish_count + 1,
        ).returning(outbox.c.publish_count, outbox.c.next_publish_at)).one()
        reserved.append({"job_id": job_id, "queue": queue, "generation": row.publish_count,
                         "deadline": row.next_publish_at})
    return reserved


def confirm_publication(db, publication):
    """A late publisher cannot postpone a successor/recovered job's attempt."""
    now = _clock(db)
    return db.execute(outbox.update().where(outbox.c.job_id == publication["job_id"],
        outbox.c.publish_count == publication["generation"], outbox.c.next_publish_at == publication["deadline"],
        outbox.c.next_publish_at > now).values(next_publish_at=now + timedelta(seconds=30))).rowcount == 1


def publish_pending(factory, send, *, batch_size=10):
    """Reserve/commit -> transport outside SQL -> fenced short confirmation.

    Outbox survives every send, including unknown results. Crash before or after
    send retries after the 120s reservation; successful queued work is replayed
    every 30s until claimed/terminal, so losing Redis cannot lose committed jobs.
    Execution deduplication remains the job ledger's responsibility.
    """
    with factory.begin() as db:
        pending = reserve_publications(db, batch_size=batch_size)
    for publication in pending:
        send(str(publication["job_id"]), publication["queue"])
        with factory.begin() as db:
            confirm_publication(db, publication)
    return len(pending)
