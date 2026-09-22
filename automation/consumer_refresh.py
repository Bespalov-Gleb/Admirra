"""SQL-only refresh coordinator. Shared budget with reports, no paid actions.

Client/integration locks precede request locks. Scheduler uses NOWAIT savepoints
to skip busy sources, never blocks sync writers or holds SQL during HTTP.
"""
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session
from core import models, consumer_freshness, sync_coverage
from core.data_requirements import requirements, DataNotReady
from core.runtime import env_bool, env_int
from automation.report_refresh import BUDGET_LOCK, uncovered
from automation.work_tables import jobs
from automation.work_ledger import submit


def enabled():
    if not env_bool("CONSUMER_REFRESH_ENABLED", False):
        return False
    if not (env_bool("REPORT_FRESHNESS_GUARDS", False) and env_bool("DURABLE_TASKS", False)
            and env_bool("REPORT_DELIVERY_GUARDS", True)):
        raise RuntimeError("Consumer refresh requires durable report freshness")
    return True


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def authorized(db, user_id, ids):
    from backend_api.stats_service import StatsService
    user = db.get(models.User, user_id)
    return bool(user and user.is_active and set(ids).issubset(StatsService.get_effective_client_ids(db, user_id, None)))


def public(row):
    state = row.state
    status = row.status
    reason = state.get("reason")
    if status == "waiting" and datetime.now(timezone.utc) >= datetime.fromisoformat(state["deadline"]):
        status, reason = "held", "deadline_expired"
    return {"id": str(row.id), "status": status, "reason": reason,
        "deadline": state["deadline"], "can_retry": status == "held",
        "message": {"waiting": "Обновляем недостающие данные. Повторите действие после завершения.",
                    "ready": "Данные готовы. Можно повторить действие.",
                    "held": "Обновление остановлено. Проверьте подключения и повторите подготовку."}[status]}


def lookup(db, consumer, user_id, scope, required):
    """Read only; show an existing preparation without refreshing its deadline."""
    if not enabled():
        return None
    ids, start, end = scope
    key = _hash((sorted(set(ids), key=str), start, end, required))
    row = db.scalar(sa.select(models.DataRefreshRequest).where(models.DataRefreshRequest.user_id == user_id,
        models.DataRefreshRequest.consumer == consumer, models.DataRefreshRequest.request_key == key))
    return public(row) if row else None


def request(db, consumer, user_id, ids, start, end, *, retry=False):
    if not enabled() or not consumer_freshness.enabled(consumer):
        return None
    if type(start) is not date or type(end) is not date or not 0 <= (end - start).days < 7320:
        raise DataNotReady("invalid_period")
    ids = sorted(set(ids), key=str)
    if not ids or not authorized(db, user_id, ids):
        raise DataNotReady("scope_unavailable")
    required = requirements(db, ids, start, end)
    if not db.scalar(sa.select(sa.func.pg_try_advisory_xact_lock(BUDGET_LOCK))):
        return None
    now = db.scalar(sa.select(sa.func.clock_timestamp()))
    key = _hash((ids, start, end, required))
    row = db.scalar(sa.select(models.DataRefreshRequest).where(models.DataRefreshRequest.user_id == user_id,
        models.DataRefreshRequest.consumer == consumer, models.DataRefreshRequest.request_key == key).with_for_update())
    if row and retry and row.status == "waiting" and now >= datetime.fromisoformat(row.state["deadline"]):
        # Status GET can expose expiry while scheduler is down. One explicit
        # retry is enough; don't require a first click merely to persist held.
        row.status = "held"
        row.next_check_at = now
    if row and (row.status == "waiting" or (row.status == "held" and not retry)):
        advance(db, row, required=required)
        return public(row)
    if row and row.status == "ready":
        try:
            consumer_freshness.verify(db, ids, start, end)
            return public(row)
        except DataNotReady:
            pass
    if row and retry and now < row.next_check_at:
        return public(row)
    count = db.scalar(sa.select(sa.func.count()).select_from(models.DataRefreshRequest).where(
        models.DataRefreshRequest.status == "waiting"))
    own = db.scalar(sa.select(sa.func.count()).select_from(models.DataRefreshRequest).where(
        models.DataRefreshRequest.status == "waiting", models.DataRefreshRequest.user_id == user_id))
    if count >= 128 or own >= 8:
        return {"status": "held", "reason": "capacity", "can_retry": True,
                "message": "Очередь обновления заполнена. Повторите позже."}
    if row is None:
        row = models.DataRefreshRequest(user_id=user_id, consumer=consumer, request_key=key)
        db.add(row)
    row.status = "waiting"
    row.state = {"ids": [str(v) for v in ids], "from": str(start), "to": str(end), "required": required,
        "deadline": (now + timedelta(minutes=env_int("REPORT_DATA_WAIT_MINUTES", 30, 1, 120))).isoformat(),
        "epoch": str(uuid.uuid4()), "jobs": [], "reason": "missing_or_stale"}
    row.next_check_at = now
    db.flush()
    advance(db, row, required=required)
    return public(row)


def advance(db, row, *, required=None):
    if row.status != "waiting":
        return
    state = dict(row.state)
    now = db.scalar(sa.select(sa.func.clock_timestamp()))
    row.next_check_at = now + timedelta(seconds=30)
    def hold(reason):
        row.status = "held"
        row.state = {**state, "reason": reason}
    if not enabled() or not consumer_freshness.enabled(row.consumer):
        return hold("disabled")
    if now >= datetime.fromisoformat(state["deadline"]):
        return hold("deadline_expired")
    ids = [uuid.UUID(v) for v in state["ids"]]
    if not authorized(db, row.user_id, ids):
        return hold("scope_unavailable")
    start, end = date.fromisoformat(state["from"]), date.fromisoformat(state["to"])
    try:
        required = required or requirements(db, ids, start, end)
        if required != state["required"]:
            return hold("settings_changed")
        consumer_freshness.verify(db, ids, start, end)
    except DataNotReady as exc:
        if exc.reason != "missing_or_stale":
            return hold(exc.reason)
    else:
        row.status = "ready"
        row.state = {**state, "reason": "ready"}
        if row.consumer == "detector":
            # SQL-only deterministic recalculation; no LLM or external send.
            from backend_api.services.detector_iteration3 import run_detector_iteration3
            for client_id in ids:
                run_detector_iteration3(db, client_id)
        return
    receipts = list(state["jobs"])
    previous = list(db.execute(sa.select(jobs.c.id, jobs.c.state).where(jobs.c.id.in_([uuid.UUID(v) for v in receipts])))) if receipts else []
    if len(previous) != len(receipts) or any(s in {"failed", "uncertain"} for _, s in previous):
        return hold("refresh_failed")
    if len(receipts) >= 64:
        if not any(s in {"queued", "running"} for _, s in previous):
            return hold("history_limit")
        return
    if not db.scalar(sa.select(sa.func.pg_try_advisory_xact_lock(BUDGET_LOCK))):
        return
    # Reports and every consumer share one producer budget.
    active = list(db.execute(sa.select(jobs).where(jobs.c.kind == "history.backfill",
        jobs.c.state.in_(["queued", "running"])).limit(1025)).mappings())
    slots = max(0, min(2, env_int("REPORT_REFRESH_GLOBAL_JOBS", 8, 1, 32) - len(active)))
    threshold = now - timedelta(minutes=env_int("REPORT_DATA_MAX_AGE_MINUTES", 1440, 1, 1440))
    for req in required:
        for left, right in uncovered(db, req, threshold):
            while left <= right and len(receipts) < 64:
                stop = min(right, left + timedelta(days=29))
                match = next((j for j in active if j["payload"].get("consumer_refresh", {}).get("settings") == req["settings"]
                    and j["payload"].get("integration_id") == req["integration_id"]
                    and j["payload"]["date_from"] <= str(left) and j["payload"]["date_to"] >= str(stop)), None)
                if match:
                    if str(match["id"]) not in receipts:
                        receipts.append(str(match["id"]))
                elif slots and sum(j["tenant"] == req["owner_id"] for j in active) < env_int("REPORT_REFRESH_OWNER_JOBS", 2, 1, 4):
                    payload = dict(run_id=state["epoch"], client_id=req["client_id"], owner_id=req["owner_id"],
                        integration_id=req["integration_id"], date_from=str(left), date_to=str(stop),
                        consumer_refresh={"settings": req["settings"]})
                    job = submit(db, kind="history.backfill", queue="sync.backfill", resource=f'integration:{req["integration_id"]}',
                        key=f'consumer-refresh:{row.id}:{state["epoch"]}:{_hash(payload)}', tenant=req["owner_id"], payload=payload, replay_safe=True)
                    if str(job) not in receipts:
                        receipts.append(str(job))
                        slots -= 1
                        active.append({"id": job, "tenant": req["owner_id"], "payload": payload})
                left = stop + timedelta(days=1)
    row.state = {**state, "jobs": receipts, "reason": "queued" if receipts else "capacity"}


def reconcile(db):
    if not enabled():
        return
    db.execute(sa.text("SET LOCAL lock_timeout = '1500ms'"))
    db.execute(sa.text("SET LOCAL statement_timeout = '20000ms'"))
    candidates = list(db.scalars(sa.select(models.DataRefreshRequest.id).where(models.DataRefreshRequest.status == "waiting",
        models.DataRefreshRequest.next_check_at <= sa.func.clock_timestamp()).order_by(models.DataRefreshRequest.next_check_at).limit(5)))
    for ident in candidates:
        try:
            with db.begin_nested():
                row = db.get(models.DataRefreshRequest, ident)
                ids = [uuid.UUID(v) for v in row.state["ids"]]
                # No wait on a busy writer. Hold client before request, like admission.
                list(db.scalars(sa.select(models.Client).where(models.Client.id.in_(ids)).order_by(models.Client.id).with_for_update(nowait=True)))
                row = db.scalar(sa.select(models.DataRefreshRequest).where(models.DataRefreshRequest.id == ident)
                    .execution_options(populate_existing=True).with_for_update(nowait=True))
                advance(db, row)
        except sa.exc.DBAPIError as exc:
            if getattr(exc.orig, "pgcode", None) not in {"55P03", "57014"}:
                raise
            # Busy sources must not starve all later requests on every tick.
            with db.begin_nested():
                row = db.scalar(sa.select(models.DataRefreshRequest).where(models.DataRefreshRequest.id == ident)
                    .with_for_update(skip_locked=True))
                if row and row.status == "waiting":
                    row.next_check_at = db.scalar(sa.select(sa.func.clock_timestamp())) + timedelta(seconds=30)
        except Exception:
            # A failing derived calculation is isolated from publishing sync /
            # billing / report jobs. Never keep retrying a broken detector here.
            with db.begin_nested():
                row = db.scalar(sa.select(models.DataRefreshRequest).where(models.DataRefreshRequest.id == ident)
                    .execution_options(populate_existing=True).with_for_update(skip_locked=True))
                if row and row.status == "waiting":
                    row.status = "held"
                    row.state = {**row.state, "reason": "preparation_failed"}
    # Bounded retention; pending authorizations are never removed here.
    expired = sa.select(models.DataRefreshRequest.id).where(models.DataRefreshRequest.status != "waiting",
        models.DataRefreshRequest.next_check_at < sa.func.clock_timestamp() - sa.text("interval '30 days'"))\
        .limit(50).with_for_update(skip_locked=True)
    db.execute(sa.delete(models.DataRefreshRequest).where(models.DataRefreshRequest.id.in_(expired)))


def require_request(db, payload, integration, client):
    from core.job_fence import current_fence
    from automation.integration_work_scope import IntegrationScopeChanged
    fence = current_fence.get()
    expected = payload["consumer_refresh"]["settings"]
    if not enabled() or sync_coverage.settings_digest(integration, client) != expected:
        raise IntegrationScopeChanged("Refresh source changed")
    linked = db.scalars(sa.select(models.DataRefreshRequest).where(models.DataRefreshRequest.status == "waiting",
        sa.cast(models.DataRefreshRequest.state, JSONB)["jobs"].contains([str(fence.job_id)])).limit(129)).all()
    now = db.scalar(sa.select(sa.func.clock_timestamp()))
    for row in linked:
        state = row.state
        if (consumer_freshness.enabled(row.consumer) and now < datetime.fromisoformat(state["deadline"])
                and str(client.id) in state["ids"] and authorized(db, row.user_id, [client.id])
                and any(r["integration_id"] == str(integration.id) and r["settings"] == expected
                    and r["date_from"] <= payload["date_from"] <= payload["date_to"] <= r["date_to"] for r in state["required"])):
            return
    raise IntegrationScopeChanged("Refresh authorization expired or revoked")


def enqueue_error(db, consumer, user_id, error):
    scope = getattr(error, "refresh_scope", None)
    if not scope or not enabled():
        return None
    bind = db.get_bind()
    if not isinstance(bind, sa.engine.Engine):
        return None
    try:
        with Session(bind=bind) as write, write.begin():
            write.execute(sa.text("SET LOCAL lock_timeout = '1500ms'"))
            write.execute(sa.text("SET LOCAL statement_timeout = '20000ms'"))
            return request(write, consumer, user_id, *scope)
    except DataNotReady as exc:
        return {"status": "held", "reason": exc.reason, "can_retry": False,
                "message": "Данные недоступны. Проверьте подключение проекта."}
    except sa.exc.DBAPIError as exc:
        if getattr(exc.orig, "pgcode", None) not in {"55P03", "57014"}:
            raise
        return {"status": "held", "reason": "source_busy", "can_retry": True,
                "message": "Источник занят обновлением. Повторите позже."}
