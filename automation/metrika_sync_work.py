"""Durable standalone Metrika sync, with no SQL connections across provider IO.

The business job and statistics become successful in one fenced transaction.
Legacy consumers and other advertising platforms are intentionally unchanged.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
import logging
import uuid

from sqlalchemy import select

from core import models
from core.job_fence import LeaseLost
from automation import metrika_goal_work as goals
from automation.integration_work_scope import require_scope, require_execution, IntegrationScopeChanged
from automation.sync_request import read_params, settings_digest

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Snapshot:
    integration_id: uuid.UUID
    client_id: uuid.UUID
    owner_id: uuid.UUID
    params: dict = field(repr=False)
    settings: tuple = field(repr=False)
    plan: goals.GoalPlan | None = field(repr=False)


def context(db, payload, *, lock=False):
    job = db.get(models.SyncJob, uuid.UUID(payload["sync_job_id"]))
    if job is None:
        raise IntegrationScopeChanged("Sync business job is unavailable")
    integration_id = job.integration_id
    if lock:
        # Same order as enqueue/apply. Locks never span external calls.
        db.scalar(select(models.Client).where(models.Client.id == uuid.UUID(payload["client_id"]))
                  .with_for_update().execution_options(populate_existing=True))
        db.scalar(select(models.Integration).where(models.Integration.id == integration_id)
                  .with_for_update().execution_options(populate_existing=True))
        job = db.scalar(select(models.SyncJob).where(models.SyncJob.id == job.id)
                        .with_for_update().execution_options(populate_existing=True))
        if job is None or job.integration_id != integration_id:
            raise IntegrationScopeChanged("Sync integration binding changed")
    integration, client = require_scope(db, payload, kind="sync", integration_id=integration_id)
    if integration.platform != models.IntegrationPlatform.YANDEX_METRIKA:
        raise IntegrationScopeChanged("Detached sync requires standalone Metrika")
    return job, integration, client


def prepare(factory, payload):
    with factory.begin() as db:
        job, integration, client = context(db, payload, lock=True)
        if job.status == models.SyncJobStatus.SUCCESS:
            return None
        params = read_params(job)
        if params.get("settings_digest") != settings_digest(integration, client):
            raise IntegrationScopeChanged("Queued Metrika settings changed; submit a new sync")
        start, end = (datetime.strptime(params[key], "%Y-%m-%d") for key in ("date_from", "date_to"))
        if start > end:
            raise ValueError("Invalid Metrika date window")
        if not integration.access_token:
            raise ValueError("Metrika credentials are unavailable")
        plan = goals.prepare(db, integration.id, params["date_from"], params["date_to"])
        snapshot = Snapshot(integration.id, client.id, client.owner_id, params,
                            goals.signature(integration, client), plan)
        job.status, job.stage, job.progress = models.SyncJobStatus.RUNNING, "syncing", 5
        job.started_at = job.started_at or datetime.utcnow()
        job.finished_at, job.error = None, None
        job.attempt = (job.attempt or 0) + 1
        return snapshot


def finish(factory, payload, snapshot, rows, missing):
    from automation.sync import _run_detector_after_sync
    from backend_api.sync_jobs import _keep_pending_followup
    from backend_api.services.project_settings import update_actual_start_date
    with factory.begin() as db:
        job, integration, client = context(db, payload, lock=True)
        if (integration.id != snapshot.integration_id or read_params(job) != snapshot.params
                or goals.signature(integration, client) != snapshot.settings):
            raise goals.GoalSettingsChanged("Metrika settings or request changed during collection")
        if snapshot.plan is not None:
            goals.apply(db, snapshot.plan, rows, missing)
        integration.sync_status = models.IntegrationSyncStatus.SUCCESS
        integration.error_message = None
        integration.last_sync_at = datetime.utcnow()
        integration.last_sync_trigger = "auto" if snapshot.params.get("trigger") == "auto" else "manual"
        update_actual_start_date(db, client.id)
        # Authorization links are not counters and did not run the legacy detector.
        enrich = snapshot.plan is not None and _run_detector_after_sync(db, client.id)
        job.status, job.stage, job.progress = models.SyncJobStatus.SUCCESS, "done", 100
        job.finished_at, job.error = datetime.utcnow(), None
        _keep_pending_followup(db, job, integration)
    return enrich


def record_failure(factory, payload, error):
    """Record the job failure, but never alter a moved/reconfigured integration."""
    from backend_api.sync_jobs import _keep_pending_followup
    with factory.begin() as db:
        job = db.get(models.SyncJob, uuid.UUID(payload["sync_job_id"]))
        if job is None:
            return
        require_execution(db, payload, kind="sync", integration_id=job.integration_id)
        client = db.scalar(select(models.Client).where(models.Client.id == uuid.UUID(payload["client_id"]))
                           .with_for_update())
        integration = db.scalar(select(models.Integration).where(models.Integration.id == job.integration_id)
                                .with_for_update())
        # Successful data must not turn into failure because optional cache/LLM failed.
        if job.status == models.SyncJobStatus.SUCCESS:
            return
        message = f"Не удалось обновить Метрику ({type(error).__name__}). Повторите синхронизацию."
        job.status, job.stage, job.error = models.SyncJobStatus.FAILED, "failed", message
        job.finished_at = datetime.utcnow()
        if (client and integration and integration.client_id == client.id
                and str(client.owner_id) == payload.get("owner_id")
                and settings_digest(integration, client) == read_params(job).get("settings_digest")):
            if integration.sync_status == models.IntegrationSyncStatus.PENDING:
                integration.sync_status, integration.error_message = models.IntegrationSyncStatus.FAILED, message
            _keep_pending_followup(db, job, integration)
            from backend_api.services.notifications import create_notification
            try:
                with db.begin_nested():
                    create_notification(db, user_id=client.owner_id, type="sync_failed",
                        title="Ошибка синхронизации Метрики", body=message,
                        meta={"integration_id": str(integration.id)})
            except Exception as notification_error:
                logger.warning("Metrika failure notification rejected (%s)", type(notification_error).__name__)


async def execute(factory, payload):
    from backend_api.sync_jobs import _is_retriable_error, _JOB_TIMEOUT_SEC, SyncJobTimeout
    snapshot, enrich = None, False
    for attempt in range(3):
        try:
            async def collect_and_apply():
                nonlocal snapshot, enrich
                snapshot = prepare(factory, payload)
                if snapshot is None:
                    return
                rows, missing = await goals.collect(snapshot.plan) if snapshot.plan is not None else ([], [])
                enrich = finish(factory, payload, snapshot, rows, missing)
            try:
                await asyncio.wait_for(collect_and_apply(), timeout=_JOB_TIMEOUT_SEC)
            except asyncio.TimeoutError:
                raise SyncJobTimeout("Превышено время синхронизации Метрики") from None
            break
        except Exception as error:
            if _is_retriable_error(error) and attempt < 2:
                await asyncio.sleep(2 ** (attempt + 1))
                continue
            try:
                record_failure(factory, payload, error)
            except Exception as record_error:
                logger.warning("Metrika failure record rejected (%s)", type(record_error).__name__)
            raise
    if snapshot is None:
        return "already-complete"
    try:
        from backend_api.cache_service import CacheService
        CacheService.invalidate_client(str(snapshot.client_id))
    except Exception as error:
        logger.warning("Metrika post-commit invalidation failed (%s)", type(error).__name__)
    if enrich:
        try:
            from automation.detector_hypothesis_work import execute as hypotheses
            await hypotheses(factory, snapshot.client_id, expected_owner_id=snapshot.owner_id)
        except LeaseLost:
            raise
        except Exception as error:
            logger.warning("Optional Metrika hypotheses failed (%s)", type(error).__name__)
    return "updated"


def run(factory, payload):
    async def wrapped():
        try:
            return await execute(factory, payload)
        finally:
            from automation.request_queue import shutdown_request_queue
            await shutdown_request_queue()
    return asyncio.run(wrapped())
