import asyncio
import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Optional
import uuid

from core import models
from core.database import SessionLocal
from automation.sync import sync_integration
from backend_api.services.project_settings import is_project_paused, update_actual_start_date

logger = logging.getLogger(__name__)

_worker_lock = threading.Lock()
_worker_started = False
_poll_interval_sec = 2.0
_stale_job_timeout = timedelta(hours=2)

# Parallel worker config — tune via env vars without code changes
_MAX_WORKERS = int(os.getenv("SYNC_WORKER_CONCURRENCY", "4"))
_MAX_PER_CLIENT = int(os.getenv("SYNC_WORKER_MAX_PER_CLIENT", "2"))

# Shared state for in-process job tracking (protected by _slots_lock)
_slots_lock = threading.Lock()
_active_job_ids: set = set()
_active_integration_ids: set = set()
_active_client_counts: dict = {}
# Signaled when a slot frees up OR a new job arrives — wakes scheduler immediately
_slot_freed = threading.Event()


def _as_naive_utc(value: Optional[datetime]) -> Optional[datetime]:
    if not value:
        return None
    return value.replace(tzinfo=None)


def _fail_stale_job(db, job: models.SyncJob) -> None:
    job.status = models.SyncJobStatus.FAILED
    job.stage = "stale"
    job.progress = job.progress or 0
    job.error = "Sync job was marked failed because it exceeded the stale timeout"
    job.finished_at = datetime.utcnow()
    integration = db.query(models.Integration).filter(models.Integration.id == job.integration_id).first()
    if integration and integration.sync_status == models.IntegrationSyncStatus.PENDING:
        integration.sync_status = models.IntegrationSyncStatus.FAILED
        integration.error_message = job.error


def _claim_queued_job(job_id: uuid.UUID) -> bool:
    """Atomically move a queued job to RUNNING so another worker/process cannot take it."""
    db = SessionLocal()
    try:
        claimed = db.query(models.SyncJob).filter(
            models.SyncJob.id == job_id,
            models.SyncJob.status == models.SyncJobStatus.QUEUED,
        ).update(
            {
                models.SyncJob.status: models.SyncJobStatus.RUNNING,
                models.SyncJob.stage: "syncing",
                models.SyncJob.progress: 5,
                models.SyncJob.started_at: datetime.utcnow(),
            },
            synchronize_session=False,
        )
        db.commit()
        return claimed == 1
    except Exception:
        db.rollback()
        logger.exception("Failed to claim sync job %s", job_id)
        return False
    finally:
        db.close()


def _mark_stale_running_jobs(db) -> int:
    now = datetime.utcnow()
    stale_count = 0
    running_jobs = db.query(models.SyncJob).filter(
        models.SyncJob.status == models.SyncJobStatus.RUNNING
    ).all()
    for job in running_jobs:
        started_at = _as_naive_utc(job.started_at or job.created_at)
        if started_at and now - started_at > _stale_job_timeout:
            _fail_stale_job(db, job)
            stale_count += 1
    if stale_count:
        db.commit()
    return stale_count


def _release_slot(job_id: uuid.UUID, integration_id: uuid.UUID, client_id: uuid.UUID) -> None:
    with _slots_lock:
        _active_job_ids.discard(job_id)
        _active_integration_ids.discard(integration_id)
        count = _active_client_counts.get(client_id, 1) - 1
        if count <= 0:
            _active_client_counts.pop(client_id, None)
        else:
            _active_client_counts[client_id] = count
    _slot_freed.set()  # Wake scheduler immediately so it picks the next job without delay


def _run_job_sync(job_id: uuid.UUID) -> None:
    db = SessionLocal()
    try:
        job = db.query(models.SyncJob).filter(models.SyncJob.id == job_id).first()
        if not job:
            return
        integration = db.query(models.Integration).filter(models.Integration.id == job.integration_id).first()
        if not integration:
            job.status = models.SyncJobStatus.FAILED
            job.error = "Integration not found"
            job.finished_at = datetime.utcnow()
            db.commit()
            return
        if is_project_paused(integration.client):
            job.status = models.SyncJobStatus.FAILED
            job.stage = "skipped"
            job.error = "Проект на паузе: синхронизация остановлена"
            job.finished_at = datetime.utcnow()
            db.commit()
            return

        job.status = models.SyncJobStatus.RUNNING
        job.stage = "syncing"
        job.progress = 5
        job.started_at = job.started_at or datetime.utcnow()
        job.attempt = (job.attempt or 0) + 1
        db.commit()

        days = 7
        force_full = False
        try:
            if job.params:
                payload = json.loads(job.params)
                days = int(payload.get("days", days))
                force_full = bool(payload.get("force_full", False))
        except Exception:
            pass

        # Incremental sync: if recently synced, only fetch the gap — not the full requested window
        last_sync = integration.last_sync_at
        is_first_sync = last_sync is None or integration.sync_status == models.IntegrationSyncStatus.NEVER
        if not force_full and not is_first_sync:
            if last_sync.tzinfo is not None:
                last_sync = last_sync.replace(tzinfo=None)
            days_since_last = max(0, (datetime.utcnow() - last_sync).days)
            if days_since_last < 1:
                days = 3
            elif days_since_last < days:
                days = min(days_since_last + 3, days)

        date_to = datetime.now().strftime("%Y-%m-%d")
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        logger.info(
            "Sync job %s: %d days (%s→%s), is_first_sync=%s, force_full=%s",
            job_id, days, date_from, date_to, is_first_sync, force_full,
        )

        retries = 3
        delay_sec = 2
        last_error: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            job.attempt = attempt
            db.commit()
            try:
                async def _run():
                    await sync_integration(db, integration, date_from, date_to)
                asyncio.run(_run())
                last_error = None
                break
            except Exception as e:
                last_error = e
                err_lower = str(e).lower()
                retriable = (
                    "429" in err_lower or "rate" in err_lower
                    or "timeout" in err_lower or "5" in err_lower
                )
                if not retriable or attempt >= retries:
                    raise
                time.sleep(delay_sec)
                delay_sec *= 2
        if last_error:
            raise last_error

        job.progress = 100
        job.stage = "done"
        job.status = models.SyncJobStatus.SUCCESS
        job.finished_at = datetime.utcnow()
        update_actual_start_date(db, integration.client_id)
        try:
            from backend_api.services.detector import run_detector_for_client
            run_detector_for_client(db, integration.client_id)
        except Exception as det_err:
            logger.exception("Detector failed for client %s: %s", integration.client_id, det_err)
        db.commit()
    except Exception as e:
        logger.exception("Sync job failed: %s", e)
        try:
            job = db.query(models.SyncJob).filter(models.SyncJob.id == job_id).first()
            if job:
                job.status = models.SyncJobStatus.FAILED
                job.error = str(e)[:1000]
                job.finished_at = datetime.utcnow()
                integration = db.query(models.Integration).filter(
                    models.Integration.id == job.integration_id
                ).first()
                if integration and integration.sync_status == models.IntegrationSyncStatus.PENDING:
                    integration.sync_status = models.IntegrationSyncStatus.FAILED
                    integration.error_message = str(e)[:1000]
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


def _run_job_tracked(job_id: uuid.UUID, integration_id: uuid.UUID, client_id: uuid.UUID) -> None:
    """Thin wrapper that always releases the parallel slot when the job finishes."""
    try:
        _run_job_sync(job_id)
    finally:
        _release_slot(job_id, integration_id, client_id)
        logger.debug("Slot released for job %s (integration %s)", job_id, integration_id)


def _worker_loop() -> None:
    logger.info(
        "Sync job worker started (max_workers=%d, max_per_client=%d)",
        _MAX_WORKERS, _MAX_PER_CLIENT,
    )
    while True:
        try:
            # Block until a slot frees or a new job arrives (or poll timeout as safety net)
            _slot_freed.wait(timeout=_poll_interval_sec)
            _slot_freed.clear()

            # Fast-path: skip DB query if all slots are taken
            with _slots_lock:
                active_count = len(_active_job_ids)
            if active_count >= _MAX_WORKERS:
                continue

            db = SessionLocal()
            try:
                stale_count = _mark_stale_running_jobs(db)
                if stale_count:
                    logger.warning("Marked %d stale sync job(s) as failed", stale_count)

                with _slots_lock:
                    busy_int_ids = set(_active_integration_ids)

                query = (
                    db.query(models.SyncJob, models.Integration)
                    .join(models.Integration, models.SyncJob.integration_id == models.Integration.id)
                    .filter(models.SyncJob.status == models.SyncJobStatus.QUEUED)
                )
                if busy_int_ids:
                    query = query.filter(models.SyncJob.integration_id.notin_(busy_int_ids))
                queued_jobs = query.order_by(models.SyncJob.created_at.asc()).all()
            finally:
                db.close()

            if not queued_jobs:
                continue

            # Fair round: fill all free slots, respecting per-client cap
            for job, integration in queued_jobs:
                client_id = integration.client_id
                # Atomic check-and-acquire under the lock
                with _slots_lock:
                    if len(_active_job_ids) >= _MAX_WORKERS:
                        break
                    if integration.id in _active_integration_ids:
                        continue
                    if _active_client_counts.get(client_id, 0) >= _MAX_PER_CLIENT:
                        continue
                    # Slot acquired — register before releasing the lock
                    _active_job_ids.add(job.id)
                    _active_integration_ids.add(integration.id)
                    _active_client_counts[client_id] = _active_client_counts.get(client_id, 0) + 1

                if not _claim_queued_job(job.id):
                    _release_slot(job.id, integration.id, client_id)
                    continue

                t = threading.Thread(
                    target=_run_job_tracked,
                    args=(job.id, integration.id, client_id),
                    name=f"sync-{job.id}",
                    daemon=True,
                )
                t.start()
                logger.info(
                    "▶ Started sync job %s | integration %s | client %s | active=%d/%d",
                    job.id, integration.id, client_id,
                    len(_active_job_ids), _MAX_WORKERS,
                )

        except Exception as e:
            logger.exception("Worker loop error: %s", e)
            threading.Event().wait(_poll_interval_sec)


def ensure_sync_worker_started() -> None:
    global _worker_started
    if _worker_started:
        return
    with _worker_lock:
        if _worker_started:
            return
        t = threading.Thread(target=_worker_loop, daemon=True, name="sync-job-worker")
        t.start()
        _worker_started = True


def enqueue_sync_job(integration_id: uuid.UUID, days: int = 7, force_full: bool = False) -> uuid.UUID:
    db = SessionLocal()
    try:
        existing = db.query(models.SyncJob).filter(
            models.SyncJob.integration_id == integration_id,
            models.SyncJob.status.in_([models.SyncJobStatus.QUEUED, models.SyncJobStatus.RUNNING]),
        ).order_by(models.SyncJob.created_at.desc()).first()
        if existing:
            stale_started_at = _as_naive_utc(existing.started_at or existing.created_at)
            if (
                existing.status == models.SyncJobStatus.RUNNING
                and stale_started_at
                and datetime.utcnow() - stale_started_at > _stale_job_timeout
            ):
                _fail_stale_job(db, existing)
                db.commit()
            else:
                db.commit()
                ensure_sync_worker_started()
                return existing.id

        existing = db.query(models.SyncJob).filter(
            models.SyncJob.integration_id == integration_id,
            models.SyncJob.status.in_([models.SyncJobStatus.QUEUED, models.SyncJobStatus.RUNNING]),
        ).order_by(models.SyncJob.created_at.desc()).first()
        if existing:
            db.commit()
            ensure_sync_worker_started()
            return existing.id

        integration = db.query(models.Integration).filter(models.Integration.id == integration_id).first()
        if integration:
            integration.sync_status = models.IntegrationSyncStatus.PENDING
            integration.error_message = None

        job = models.SyncJob(
            integration_id=integration_id,
            status=models.SyncJobStatus.QUEUED,
            stage="queued",
            progress=0,
            params=json.dumps({"days": days, "force_full": force_full}),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        ensure_sync_worker_started()
        _slot_freed.set()  # Wake scheduler immediately — don't wait for next poll tick
        return job.id
    finally:
        db.close()


def get_last_job(integration_id: uuid.UUID) -> Optional[models.SyncJob]:
    db = SessionLocal()
    try:
        return db.query(models.SyncJob).filter(
            models.SyncJob.integration_id == integration_id
        ).order_by(models.SyncJob.created_at.desc()).first()
    finally:
        db.close()
