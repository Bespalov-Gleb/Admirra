import asyncio
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional
import uuid

from core import models
from core.database import SessionLocal
from automation.sync import sync_integration

logger = logging.getLogger(__name__)

_worker_lock = threading.Lock()
_worker_started = False
_poll_interval_sec = 2.0


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

        job.status = models.SyncJobStatus.RUNNING
        job.stage = "syncing"
        job.progress = 5
        job.started_at = datetime.utcnow()
        job.attempt = (job.attempt or 0) + 1
        db.commit()

        days = 7
        try:
            if job.params:
                payload = json.loads(job.params)
                days = int(payload.get("days", days))
        except Exception:
            pass
        date_to = datetime.now().strftime("%Y-%m-%d")
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

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
                retriable = ("429" in err_lower) or ("rate" in err_lower) or ("timeout" in err_lower) or ("5" in err_lower)
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
        db.commit()
    except Exception as e:
        logger.exception("Sync job failed: %s", e)
        try:
            job = db.query(models.SyncJob).filter(models.SyncJob.id == job_id).first()
            if job:
                job.status = models.SyncJobStatus.FAILED
                job.error = str(e)[:1000]
                job.finished_at = datetime.utcnow()
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


def _worker_loop() -> None:
    logger.info("Sync job worker started")
    while True:
        db = SessionLocal()
        try:
            queued = db.query(models.SyncJob).filter(
                models.SyncJob.status == models.SyncJobStatus.QUEUED
            ).order_by(models.SyncJob.created_at.asc()).first()
            if not queued:
                db.close()
                threading.Event().wait(_poll_interval_sec)
                continue

            running_same = db.query(models.SyncJob).filter(
                models.SyncJob.integration_id == queued.integration_id,
                models.SyncJob.status == models.SyncJobStatus.RUNNING
            ).first()
            if running_same:
                db.close()
                threading.Event().wait(_poll_interval_sec)
                continue

            job_id = queued.id
            db.close()
            _run_job_sync(job_id)
        except Exception as e:
            logger.exception("Worker loop error: %s", e)
            try:
                db.close()
            except Exception:
                pass
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


def enqueue_sync_job(integration_id: uuid.UUID, days: int = 7) -> uuid.UUID:
    db = SessionLocal()
    try:
        existing = db.query(models.SyncJob).filter(
            models.SyncJob.integration_id == integration_id,
            models.SyncJob.status.in_([models.SyncJobStatus.QUEUED, models.SyncJobStatus.RUNNING]),
        ).order_by(models.SyncJob.created_at.desc()).first()
        if existing:
            ensure_sync_worker_started()
            return existing.id

        job = models.SyncJob(
            integration_id=integration_id,
            status=models.SyncJobStatus.QUEUED,
            stage="queued",
            progress=0,
            params=json.dumps({"days": days}),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        ensure_sync_worker_started()
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

