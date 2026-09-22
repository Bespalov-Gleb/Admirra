"""Durable integration sync, with no SQL connections across provider IO.

The business job and statistics become successful in one fenced transaction.
The module name is retained for compatibility with existing worker releases.
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
from automation import ads_sync_work as ads
from automation.integration_work_scope import require_scope, require_execution, IntegrationScopeChanged
from automation.sync_request import read_params, settings_digest

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Snapshot:
    integration_id: uuid.UUID
    client_id: uuid.UUID
    owner_id: uuid.UUID
    params: dict = field(repr=False)
    settings: str = field(repr=False)
    plan: goals.GoalPlan | ads.Plan | None = field(repr=False)


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
    if integration.platform not in ads.PLATFORMS | {models.IntegrationPlatform.YANDEX_METRIKA}:
        raise IntegrationScopeChanged("Unsupported integration platform")
    return job, integration, client


def prepare(factory, payload):
    with factory.begin() as db:
        job, integration, client = context(db, payload, lock=True)
        if job.status == models.SyncJobStatus.SUCCESS:
            return None
        params = read_params(job)
        if params.get("settings_digest") != settings_digest(integration, client):
            raise IntegrationScopeChanged("Queued integration settings changed; submit a new sync")
        start, end = (datetime.strptime(params[key], "%Y-%m-%d") for key in ("date_from", "date_to"))
        if start > end:
            raise ValueError("Invalid integration date window")
        if integration.platform != models.IntegrationPlatform.AVITO_ADS and not integration.access_token:
            raise ValueError("Integration credentials are unavailable")
        adapter = ads if integration.platform in ads.PLATFORMS else goals
        plan = adapter.prepare(db, integration.id, params["date_from"], params["date_to"])
        snapshot = Snapshot(integration.id, client.id, client.owner_id, params,
                            settings_digest(integration, client), plan)
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
                or settings_digest(integration, client) != snapshot.settings):
            raise goals.GoalSettingsChanged("Integration settings or request changed during collection")
        if isinstance(snapshot.plan, ads.Plan):
            ads.apply(db, snapshot.plan, rows)
        elif snapshot.plan is not None:
            goals.apply(db, snapshot.plan, rows, missing)
        rebase_followups(db, integration, client, snapshot.settings)
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


def rebase_followups(db, integration, client, previous_digest):
    """Carry only our own credential/default update into accepted later work.

    Do not adopt a user's concurrent settings change or widen the queued dates.
    The caller holds the client and integration locks used by enqueue.
    """
    import json
    current = settings_digest(integration, client)
    if current == previous_digest:
        return
    for queued in db.scalars(select(models.SyncJob).where(models.SyncJob.integration_id == integration.id,
            models.SyncJob.status == models.SyncJobStatus.QUEUED).with_for_update()):
        params = read_params(queued)
        if params.get("settings_digest") == previous_digest:
            queued.params = json.dumps({**params, "settings_digest": current})


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
        from automation.ads_sync_contract import IncompleteAdsSnapshot
        if isinstance(error, IncompleteAdsSnapshot):
            message = "Источник вернул неполные или некорректные данные. Прежние цифры сохранены. Повторите синхронизацию."
        elif isinstance(error, PermissionError) or "401" in str(error) or "expired_token" in str(error):
            message = "Не удалось подтвердить доступ к рекламному источнику. Проверьте подключение кабинета. Прежние данные сохранены."
        else:
            message = f"Не удалось обновить рекламный источник ({type(error).__name__}). Повторите синхронизацию."
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
                        title="Ошибка синхронизации", body=message,
                        meta={"integration_id": str(integration.id)})
            except Exception as notification_error:
                logger.warning("Sync failure notification rejected (%s)", type(notification_error).__name__)


async def collect_ads(factory, payload, snapshot):
    try:
        return snapshot, await ads.collect(snapshot.plan)
    except Exception as error:
        credentials = await ads.refresh(snapshot.plan, error)
        if not credentials or not credentials.get("access_token"):
            raise
        # Credential rotation has its own short fenced transaction. Nothing
        # else from the failed snapshot is saved; all levels are fetched again.
        with factory.begin() as db:
            job, integration, client = context(db, payload, lock=True)
            if read_params(job) != snapshot.params or settings_digest(integration, client) != snapshot.settings:
                raise IntegrationScopeChanged("Integration changed during OAuth renewal")
            ads.save_credentials(integration, credentials)
            rebase_followups(db, integration, client, snapshot.settings)
            import json
            job.params = json.dumps({**snapshot.params, "settings_digest": settings_digest(integration, client)})
        snapshot = prepare(factory, payload)
        return snapshot, await ads.collect(snapshot.plan)


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
                if isinstance(snapshot.plan, ads.Plan):
                    snapshot, rows = await collect_ads(factory, payload, snapshot)
                    missing = []
                else:
                    rows, missing = await goals.collect(snapshot.plan) if snapshot.plan is not None else ([], [])
                enrich = finish(factory, payload, snapshot, rows, missing)
            try:
                await asyncio.wait_for(collect_and_apply(), timeout=_JOB_TIMEOUT_SEC)
            except asyncio.TimeoutError:
                raise SyncJobTimeout("Превышено время синхронизации источника") from None
            break
        except Exception as error:
            if _is_retriable_error(error) and attempt < 2:
                await asyncio.sleep(2 ** (attempt + 1))
                continue
            try:
                record_failure(factory, payload, error)
            except Exception as record_error:
                logger.warning("Sync failure record rejected (%s)", type(record_error).__name__)
            raise
    if snapshot is None:
        return "already-complete"
    try:
        from backend_api.cache_service import CacheService
        CacheService.invalidate_client(str(snapshot.client_id))
    except Exception as error:
        logger.warning("Sync post-commit invalidation failed (%s)", type(error).__name__)
    if enrich:
        try:
            from automation.detector_hypothesis_work import execute as hypotheses
            await hypotheses(factory, snapshot.client_id, expected_owner_id=snapshot.owner_id)
        except LeaseLost:
            raise
        except Exception as error:
            logger.warning("Optional sync hypotheses failed (%s)", type(error).__name__)
    return "updated"


def run(factory, payload):
    async def wrapped():
        try:
            return await execute(factory, payload)
        finally:
            from automation.request_queue import shutdown_request_queue
            await shutdown_request_queue()
    return asyncio.run(wrapped())
