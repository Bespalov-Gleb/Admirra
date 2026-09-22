"""Opt-in report barrier. SQL only; no sleep, render, provider IO or commit.

Enable only after legacy statistics writers are drained and durable coverage
has been populated. Immutable verified snapshots are reused, not revalidated
against live statistics on every recipient retry.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import uuid

import sqlalchemy as sa
from core import models, sync_coverage
from core.runtime import env_bool, env_int


class ReportDataPending(RuntimeError):
    pass


def enabled():
    if not env_bool("REPORT_FRESHNESS_GUARDS", False):
        return False
    if not env_bool("DURABLE_TASKS", False) or not env_bool("REPORT_DELIVERY_GUARDS", True):
        raise RuntimeError("Report freshness requires durable tasks and delivery guards")
    return True


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def public_state(delivery):
    state = getattr(delivery, "data_readiness", None) or {}
    # Never expose other team owners, raw settings or provider IDs in the API.
    if not state:
        return None
    result = {k: state[k] for k in ("status", "reason", "deadline", "revision", "checked_at", "refresh_status") if k in state}
    result["can_retry"] = (state.get("status") == "held" and state.get("reason") == "deadline_expired"
        and delivery.status == "pending" and not delivery.snapshot_data and not delivery.delivery_results
        and not delivery.sent_at and not delivery.approved_at)
    return result


def schedule_digest(rule):
    return _digest({column.name: getattr(rule, column.name) for column in models.ReportSchedule.__table__.columns
                    if column.name not in {"last_sent_at", "updated_at"}})


def _stop(delivery, state, reason, *, terminal=False):
    state.update(status="held" if terminal else "waiting", reason=reason)
    delivery.data_readiness = state
    raise ReportDataPending("Отчёт ожидает полные данные; нужна проверка" if terminal else "Отчёт ожидает обновления данных")


def client_ids(db, delivery):
    from backend_api.stats_service import StatsService
    ids = (StatsService.resolve_folder_client_ids(db, delivery.user_id, delivery.folder_id)
           if delivery.folder_id and not delivery.client_id else
           StatsService.get_effective_client_ids(db, delivery.user_id, delivery.client_id))
    return sorted(set(ids), key=str)


def prepare(db, delivery, user):
    """Acquire source locks; caller captures all template data before commit."""
    db.flush()
    db.scalar(sa.select(models.ReportDelivery).where(models.ReportDelivery.id == delivery.id)
              .execution_options(populate_existing=True).with_for_update())
    now = db.scalar(sa.select(sa.func.clock_timestamp()))
    old = dict(delivery.data_readiness or {})
    state = {**old, "checked_at": now.isoformat()}
    if delivery.user_id != user.id or not user.is_active:
        _stop(delivery, state, "scope_unavailable", terminal=True)
    if delivery.snapshot_data:
        if old.get("status") == "ready" and delivery.snapshot_data.get("coverage_revision") == old.get("revision"):
            return [uuid.UUID(v) for v in old["client_ids"]]
        _stop(delivery, state, "unverified_snapshot", terminal=True)
    if old.get("status") == "held":
        _stop(delivery, state, old.get("reason", "needs_review"), terminal=True)
    if not old:
        wait = env_int("REPORT_DATA_WAIT_MINUTES", 30, 1, 120)
        age = env_int("REPORT_DATA_MAX_AGE_MINUTES", 1440, 1, 1440)
        state.update(deadline=(now + timedelta(minutes=wait)).isoformat(),
                     not_before=(now - timedelta(minutes=age)).isoformat(), revision=0, request_epoch=str(uuid.uuid4()))
    state.setdefault("request_epoch", str(uuid.uuid4()))
    if delivery.schedule_id:
        rule = db.scalar(sa.select(models.ReportSchedule).where(models.ReportSchedule.id == delivery.schedule_id)
                         .execution_options(populate_existing=True).with_for_update())
        if rule is None or rule.user_id != user.id or not rule.enabled:
            _stop(delivery, state, "schedule_unavailable", terminal=True)
        signature = schedule_digest(rule)
        if old.get("schedule_digest") and old["schedule_digest"] != signature:
            _stop(delivery, state, "schedule_changed", terminal=True)
        state["schedule_digest"] = signature
    if now >= datetime.fromisoformat(state["deadline"]):
        _stop(delivery, state, "deadline_expired", terminal=True)
    ids = client_ids(db, delivery)
    if not ids or len(ids) > 200:
        _stop(delivery, state, "scope_unavailable_or_too_large", terminal=True)
    clients = list(db.scalars(sa.select(models.Client).where(models.Client.id.in_(ids))
        .order_by(models.Client.id).execution_options(populate_existing=True).with_for_update()))
    if len(clients) != len(ids) or any(c.status != models.ClientStatus.ACTIVE for c in clients):
        _stop(delivery, state, "scope_unavailable", terminal=True)
    integrations = list(db.scalars(sa.select(models.Integration).where(models.Integration.client_id.in_(ids))
        .order_by(models.Integration.id).limit(513).execution_options(populate_existing=True).with_for_update()))
    if len(integrations) > 512:
        _stop(delivery, state, "source_limit", terminal=True)
    owners = {c.id: c for c in clients}
    required = []
    start = delivery.start_date - timedelta(days=(delivery.end_date - delivery.start_date).days + 1)
    for integration in integrations:
        platform = integration.platform
        # Login-level Metrika integration is an OAuth link, not a statistical source.
        if platform == models.IntegrationPlatform.YANDEX_METRIKA and not str(integration.account_id).isdigit():
            continue
        stages = ["metrika_goals"] if platform == models.IntegrationPlatform.YANDEX_METRIKA else ["campaigns"]
        if platform not in {models.IntegrationPlatform.YANDEX_DIRECT, models.IntegrationPlatform.VK_ADS,
                            models.IntegrationPlatform.AVITO_ADS, models.IntegrationPlatform.YANDEX_METRIKA}:
            _stop(delivery, state, "unsupported_source", terminal=True)
        if platform in {models.IntegrationPlatform.YANDEX_DIRECT, models.IntegrationPlatform.AVITO_ADS}:
            try:
                selected = json.loads(integration.selected_goals or "[]")
            except (TypeError, ValueError):
                _stop(delivery, state, "invalid_goal_settings", terminal=True)
            if not isinstance(selected, list):
                _stop(delivery, state, "invalid_goal_settings", terminal=True)
            if selected or integration.primary_goal_id:
                stages.append("metrika_goals")
        client = owners[integration.client_id]
        required.append(dict(integration_id=str(integration.id), client_id=str(client.id), owner_id=str(client.owner_id),
            stages=stages, settings=sync_coverage.settings_digest(integration, client),
            date_from=start.isoformat(), date_to=delivery.end_date.isoformat()))
    if not required:
        _stop(delivery, state, "no_statistical_sources", terminal=True)
    request = dict(client_ids=[str(v) for v in ids], required=required,
        start=str(delivery.start_date), end=str(delivery.end_date))
    digest = _digest(request)
    if digest != old.get("request_digest"):
        state.update(request_digest=digest, revision=int(old.get("revision", 0)) + 1, **request)
    missing = []
    for requirement in required:
        result = sync_coverage.assess(db, integration_id=uuid.UUID(requirement["integration_id"]),
            client_id=uuid.UUID(requirement["client_id"]), owner_id=uuid.UUID(requirement["owner_id"]),
            stages=requirement["stages"], start=start, end=delivery.end_date,
            not_before=datetime.fromisoformat(state["not_before"]))
        if not result.ready:
            missing.append(dict(integration_id=requirement["integration_id"], reason=result.reason,
                                stages=list(result.missing_stages)))
    state["missing"] = missing
    if missing:
        _stop(delivery, state, "missing_or_stale")
    state.update(status="ready", reason="ready")
    delivery.data_readiness = state
    return ids


def enqueue_wait(db, delivery):
    """One next poll per delivery/minute, same resource; no timer/worker sleep."""
    from automation.work_ledger import submit
    from automation.work_tables import jobs
    state = delivery.data_readiness or {}
    if state.get("status") != "waiting":
        return None
    from automation.report_refresh import plan
    plan(db, delivery)
    now = db.scalar(sa.select(sa.func.clock_timestamp()))
    due = min(now.replace(second=0, microsecond=0) + timedelta(minutes=1), datetime.fromisoformat(state["deadline"]))
    job_id = submit(db, kind="reports.resume", queue="reports",
        key=f"report-data:{delivery.id}:{due.isoformat()}", resource=f"report-delivery:{delivery.id}",
        tenant=delivery.user_id, payload={"delivery_id": str(delivery.id), "owner_id": str(delivery.user_id)},
        replay_safe=False)
    db.execute(jobs.update().where(jobs.c.id == job_id, jobs.c.state == "queued").values(available_at=due))
    return job_id
