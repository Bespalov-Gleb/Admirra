"""Durable, project-scoped history loading. No API-process threads or globals."""
from datetime import timedelta
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, insert

from automation.work_tables import jobs
from automation.work_ledger import submit

metadata = sa.MetaData()
runs = sa.Table("history_backfill_runs", metadata,
    sa.Column("client_id", UUID(as_uuid=True), primary_key=True),
    sa.Column("run_id", UUID(as_uuid=True), nullable=False, unique=True),
    sa.Column("status", sa.String(16), nullable=False),
    sa.Column("months", sa.Integer, nullable=False),
    sa.Column("steps_total", sa.Integer, nullable=False),
    sa.Column("steps_done", sa.Integer, nullable=False, server_default="0"),
    sa.Column("steps_failed", sa.Integer, nullable=False, server_default="0"),
    sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.Column("finished_at", sa.DateTime(timezone=True)),
    sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
)


def progress(db, row):
    if row["status"] != "running":
        return dict(row)
    counts = db.execute(sa.select(jobs.c.state, sa.func.count(), sa.func.max(jobs.c.finished_at)).where(
        jobs.c.kind == "history.backfill", jobs.c.payload["run_id"].astext == str(row["run_id"])
    ).group_by(jobs.c.state)).all()
    states = {state: count for state, count, _ in counts}
    done = states.get("succeeded", 0)
    failed = states.get("failed", 0) + states.get("uncertain", 0)
    active = states.get("queued", 0) + states.get("running", 0)
    complete = not active
    # Missing jobs must never masquerade as a fully loaded history.
    status = "running" if active else "done" if done == row["steps_total"] else "partial"
    finish = max((dt for _, _, dt in counts if dt), default=None) if complete else None
    if complete and finish is None:
        finish = db.scalar(sa.select(sa.func.clock_timestamp()))
    return {**dict(row), "status": status, "steps_done": done, "steps_failed": failed, "finished_at": finish}


def reconcile(db, *, min_age_seconds=0):
    rows = db.execute(sa.select(runs).where(runs.c.status == "running",
        runs.c.checked_at <= sa.func.clock_timestamp() - timedelta(seconds=min_age_seconds)).order_by(runs.c.checked_at)
        .limit(100).with_for_update(skip_locked=True)).mappings().all()
    for row in rows:
        state = progress(db, row)
        db.execute(runs.update().where(runs.c.client_id == row["client_id"]).values(
            status=state["status"], steps_done=state["steps_done"], steps_failed=state["steps_failed"],
            finished_at=state["finished_at"], checked_at=sa.func.clock_timestamp()))
    # Retain active group members even if one chunk completed >30 days ago.
    active_runs = sa.select(sa.cast(runs.c.run_id, sa.Text)).where(runs.c.status == "running")
    old = sa.select(jobs.c.id).where(jobs.c.kind == "history.backfill", jobs.c.state.in_(["succeeded", "failed"]),
        jobs.c.finished_at < sa.func.now() - sa.text("interval '30 days'"),
        jobs.c.payload["run_id"].astext.not_in(active_runs)).order_by(jobs.c.finished_at).limit(500)
    db.execute(jobs.delete().where(jobs.c.id.in_(old)))


def submit_project(db, client_id, integration_ids, chunks, months, cooldown_seconds, *, tenant_id):
    """Caller holds the Client row lock; different overlapping scopes dedupe."""
    now = db.scalar(sa.select(sa.func.clock_timestamp()))
    old = db.execute(sa.select(runs).where(runs.c.client_id == client_id).with_for_update()).mappings().first()
    if old:
        state = progress(db, old)
        if state["status"] == "running":
            return "already_running"
        if state["finished_at"] and now < state["finished_at"] + timedelta(seconds=cooldown_seconds):
            return "cooldown"
    if not integration_ids:
        return "no_integrations"
    run_id = uuid.uuid4()
    values = dict(client_id=client_id, run_id=run_id, status="running", months=months,
        steps_total=len(integration_ids) * len(chunks), steps_done=0, steps_failed=0,
        started_at=now, finished_at=None, checked_at=now)
    db.execute(insert(runs).values(**values).on_conflict_do_update(index_elements=[runs.c.client_id], set_=values))
    # Earliest windows first. Global backfill concurrency is separately capped.
    for integration_id in sorted(integration_ids, key=str):
        for start, end in chunks:
            submit(db, kind="history.backfill", queue="sync.backfill",
                key=f"backfill:{run_id}:{integration_id}:{start}", resource=f"integration:{integration_id}",
                tenant=tenant_id, payload={"run_id": str(run_id), "client_id": str(client_id),
                    "owner_id": str(tenant_id),
                    "integration_id": str(integration_id), "date_from": start.isoformat(), "date_to": end.isoformat()},
                replay_safe=True)
    return "started"


def start(client_ids, months):
    from core.database import SessionLocal
    from core import models
    from backend_api.services.dynamics_backfill import _build_chunks, CHUNK_DAYS, COOLDOWN_SEC
    months = max(1, min(12, int(months)))
    chunks = _build_chunks(months, max(1, min(90, CHUNK_DAYS)))
    reasons = []
    with SessionLocal.begin() as db:
        # Stable locking order prevents deadlocks between overlapping requests.
        clients = db.query(models.Client).filter(models.Client.id.in_(client_ids)).order_by(models.Client.id).with_for_update().all()
        for client in clients:
            from backend_api.services.project_settings import is_project_paused
            if is_project_paused(client):
                reasons.append("paused")
                continue
            ids = db.execute(sa.select(models.Integration.id).where(models.Integration.client_id == client.id,
                models.Integration.connection_status == "active", models.Integration.platform.in_([
                    models.IntegrationPlatform.YANDEX_DIRECT, models.IntegrationPlatform.VK_ADS,
                    models.IntegrationPlatform.AVITO_ADS]))).scalars().all()
            reasons.append(submit_project(db, client.id, ids, chunks, months, COOLDOWN_SEC,
                                          tenant_id=client.owner_id))
    return {"started": "started" in reasons, "projects_started": reasons.count("started"),
            "reason": None if "started" in reasons else reasons[0] if reasons else "no_client", **status(client_ids)}


def status(client_ids):
    from core.database import SessionLocal
    from backend_api.services.dynamics_backfill import _earliest_data_date, COOLDOWN_SEC, BACKFILL_MONTHS
    with SessionLocal() as db:
        rows = db.execute(sa.select(runs).where(runs.c.client_id.in_(client_ids))).mappings().all()
        states = [progress(db, row) for row in rows]
        hist = _earliest_data_date(db, client_ids)
        now = db.scalar(sa.select(sa.func.clock_timestamp()))
    active = any(row["status"] == "running" for row in states)
    total = sum(row["steps_total"] for row in states)
    done = sum(row["steps_done"] for row in states)
    failed = sum(row["steps_failed"] for row in states)
    until = max((row["finished_at"] + timedelta(seconds=COOLDOWN_SEC) for row in states if row["finished_at"]), default=None)
    state = "running" if active else "idle" if not states else "done" if all(row["status"] == "done" for row in states) else "partial"
    message = {"running": "Загрузка истории в очереди…", "done": "История загружена",
               "partial": "Часть истории не загружена. Проверьте ошибки синхронизации.", "idle": None}[state]
    return {"status": state, "running": active, "steps_total": total, "steps_done": done,
        "steps_failed": failed, "progress": int(done / total * 100) if total else 0,
        "message": message, "error": message if state == "partial" else None,
        "history_from": hist.isoformat() if hist else None, "months": max((s["months"] for s in states), default=BACKFILL_MONTHS),
        "cooldown_until": until.isoformat() if until else None, "in_cooldown": bool(until and until > now)}


async def execute(payload):
    from core.database import SessionLocal
    from automation.sync import sync_integration
    from automation.integration_work_scope import require_scope
    with SessionLocal() as db:
        integration, _ = require_scope(db, payload, kind="history.backfill", integration_id=payload["integration_id"])
        await sync_integration(db, integration, payload["date_from"], payload["date_to"], historical=True)
        db.commit()
