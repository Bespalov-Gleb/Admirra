"""SQL-only, bounded history producer for report freshness. No provider IO here."""
from datetime import date, datetime, timedelta
import hashlib
import uuid

import sqlalchemy as sa
from core import models, sync_coverage
from core.runtime import env_int
from automation.work_tables import jobs
from automation.work_ledger import submit

BUDGET_LOCK = 731971047


def gaps(start, end, intervals):
    cursor = start
    result = []
    for left, right in sorted(intervals):
        if right < cursor:
            continue
        if left > end:
            break
        if left > cursor:
            result.append((cursor, min(end, left - timedelta(days=1))))
        if right >= end:
            return result
        cursor = max(cursor, right + timedelta(days=1))
    if cursor <= end:
        result.append((cursor, end))
    return result


def uncovered(db, requirement, threshold):
    start, end = date.fromisoformat(requirement["date_from"]), date.fromisoformat(requirement["date_to"])
    rows = list(db.execute(sa.select(models.SyncCoverage.stage, models.SyncCoverage.date_from,
        models.SyncCoverage.date_to).where(models.SyncCoverage.integration_id == uuid.UUID(requirement["integration_id"]),
        models.SyncCoverage.client_id == uuid.UUID(requirement["client_id"]),
        models.SyncCoverage.owner_id == uuid.UUID(requirement["owner_id"]),
        models.SyncCoverage.settings_digest == requirement["settings"],
        models.SyncCoverage.observed_at >= threshold, models.SyncCoverage.stage.in_(requirement["stages"]),
        models.SyncCoverage.date_from <= end, models.SyncCoverage.date_to >= start).limit(sync_coverage.MAX_WINDOWS + 1)))
    if len(rows) > sync_coverage.MAX_WINDOWS:
        return [(start, end)]
    missing = sorted(window for stage in requirement["stages"]
                     for window in gaps(start, end, [(a, b) for s, a, b in rows if s == stage]))
    merged = []
    for left, right in missing:
        if merged and left <= merged[-1][1] + timedelta(days=1):
            merged[-1] = (merged[-1][0], max(right, merged[-1][1]))
        else:
            merged.append((left, right))
    return merged


def plan(db, delivery):
    """Caller holds delivery/source locks. Never wait for the budget lock:
    another report may hold it while waiting for one of these client rows.
    """
    state = dict(delivery.data_readiness or {})
    if state.get("status") != "waiting":
        return
    if not db.scalar(sa.select(sa.func.pg_try_advisory_xact_lock(BUDGET_LOCK))):
        return  # Next bounded readiness poll tries again.
    global_limit = env_int("REPORT_REFRESH_GLOBAL_JOBS", 8, 1, 32)
    owner_limit = env_int("REPORT_REFRESH_OWNER_JOBS", 2, 1, 4)
    active = list(db.execute(sa.select(jobs.c.tenant).where(jobs.c.kind == "history.backfill",
        jobs.c.payload["report_refresh"].is_not(None), jobs.c.state.in_(["queued", "running"]))))
    slots = min(2, max(0, global_limit - len(active)))
    by_owner = {}
    for (owner,) in active:
        by_owner[owner] = by_owner.get(owner, 0) + 1
    receipts = dict(state.get("refresh_jobs") or {})
    wanted = {row["integration_id"] for row in state.get("missing", []) if row["reason"] == "missing_or_stale"}
    for req in state.get("required", []):
        if not slots or len(receipts) >= 64:
            break
        if req["integration_id"] not in wanted or by_owner.get(req["owner_id"], 0) >= owner_limit:
            continue
        for left, right in uncovered(db, req, datetime.fromisoformat(state["not_before"])):
            while left <= right and slots and len(receipts) < 64 and by_owner.get(req["owner_id"], 0) < owner_limit:
                end = min(right, left + timedelta(days=29))
                key = hashlib.sha256(f'{state["request_epoch"]}:{req["integration_id"]}:{req["settings"]}:{left}:{end}'.encode()).hexdigest()
                if key not in receipts:
                    job = submit(db, kind="history.backfill", queue="sync.backfill",
                        key=f"report-refresh:{delivery.id}:{key}", resource=f'integration:{req["integration_id"]}',
                        tenant=req["owner_id"], replay_safe=True,
                        payload=dict(run_id=state["request_epoch"], owner_id=req["owner_id"], client_id=req["client_id"],
                            integration_id=req["integration_id"], date_from=str(left), date_to=str(end),
                            report_refresh=dict(delivery_id=str(delivery.id), viewer_id=str(delivery.user_id),
                                epoch=state["request_epoch"], request_digest=state["request_digest"], settings=req["settings"])))
                    receipts[key] = str(job)
                    by_owner[req["owner_id"]] = by_owner.get(req["owner_id"], 0) + 1
                    slots -= 1
                left = end + timedelta(days=1)
    state.update(refresh_jobs=receipts, refresh_status="limit" if len(receipts) >= 64 else "queued" if receipts else "capacity")
    delivery.data_readiness = state


def require_report(db, payload, integration, client):
    """Revalidate before HTTP AND before apply; payload isn't authorization."""
    from backend_api.reports import freshness
    from automation.integration_work_scope import IntegrationScopeChanged
    binding = payload["report_refresh"]
    delivery = db.scalar(sa.select(models.ReportDelivery).where(models.ReportDelivery.id == uuid.UUID(binding["delivery_id"]))
                         .execution_options(populate_existing=True))
    state = (delivery.data_readiness or {}) if delivery else {}
    user = db.get(models.User, delivery.user_id) if delivery else None
    now = db.scalar(sa.select(sa.func.clock_timestamp()))
    if (not freshness.enabled() or not delivery or not user or not user.is_active or delivery.status != "pending"
            or str(delivery.user_id) != binding["viewer_id"] or state.get("status") != "waiting"
            or state.get("request_epoch") != binding["epoch"] or state.get("request_digest") != binding["request_digest"]
            or now >= datetime.fromisoformat(state["deadline"])
            or sync_coverage.settings_digest(integration, client) != binding["settings"]
            or client.id not in freshness.client_ids(db, delivery)):
        raise IntegrationScopeChanged("Report refresh authorization expired or changed")
    if delivery.schedule_id:
        rule = db.get(models.ReportSchedule, delivery.schedule_id)
        if not rule or not rule.enabled or freshness.schedule_digest(rule) != state.get("schedule_digest"):
            raise IntegrationScopeChanged("Report schedule changed before refresh")
