"""Bounded, replay-safe calendar planning. Parents never call providers.

Each page commits its children and continuation in one transaction. Child keys
are per occurrence/scope, so a replayed page cannot repeat a business operation.
"""
from datetime import datetime, timedelta, timezone
import uuid
from zoneinfo import ZoneInfo

import sqlalchemy as sa

from core import models
from automation.work_ledger import submit

PAGE_SIZE = 100
MSK = ZoneInfo("Europe/Moscow")


def scheduled_time(payload):
    value = datetime.fromisoformat(payload["scheduled_at"])
    if value.tzinfo is None:
        raise ValueError("Calendar occurrence requires a timezone")
    return value.astimezone(timezone.utc)


def report_expired(scheduled, now):
    return now - scheduled > timedelta(minutes=15) or scheduled > now + timedelta(minutes=1)


def plan_page(factory, kind, payload):
    if kind not in {"nightly.enqueue", "reports.rules", "reports.export"}:
        raise ValueError("Unsupported calendar planner")
    scheduled = scheduled_time(payload)
    stamp = scheduled.isoformat()
    owner_id = uuid.UUID(payload["owner_id"]) if payload.get("owner_id") else None
    cursor = uuid.UUID(payload["cursor"]) if payload.get("cursor") else None
    upper = uuid.UUID(payload["upper_id"]) if payload.get("upper_id") else None
    with factory.begin() as db:
        now = db.scalar(sa.select(sa.func.clock_timestamp()))
        if kind == "reports.rules" and report_expired(scheduled, now):
            return {"planned": 0, "skipped": "expired_occurrence"}
        if kind == "reports.rules" and cursor is None:
            from backend_api.reports.scheduler import recover_stale_report_deliveries
            recover_stale_report_deliveries(db, owner_id=owner_id)
        if kind == "nightly.enqueue":
            identity = models.Integration.id
            owner = models.Client.owner_id
            query = sa.select(identity, owner).select_from(models.Integration).join(models.Client).where(
                models.Client.status == models.ClientStatus.ACTIVE,
                models.Integration.connection_status == "active")
            child_kind, queue = "nightly.integration", "maintenance"
        elif kind == "reports.export":
            identity, owner = models.Client.id, models.Client.owner_id
            query = sa.select(identity, owner).where(models.Client.status == models.ClientStatus.ACTIVE)
            child_kind, queue = "reports.project", "reports"
        else:
            identity = models.ReportSchedule.id
            owner = models.ReportSchedule.user_id
            local = scheduled.astimezone(MSK)
            weekday = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")[local.weekday()]
            days = ["daily", weekday] + (["weekdays"] if local.weekday() < 5 else [])
            query = sa.select(identity, owner).where(models.ReportSchedule.enabled.is_(True),
                models.ReportSchedule.send_time == local.strftime("%H:%M"), models.ReportSchedule.day.in_(days))
            child_kind, queue = "reports.rule", "reports"
        query = query.where(owner.is_not(None))
        if owner_id is not None:
            query = query.where(owner == owner_id)
        if upper is None:
            upper = db.execute(query.order_by(identity.desc()).limit(1)).first()
            upper = upper[0] if upper else None
        if upper is None:
            return {"planned": 0, "skipped": "no_matching_scopes"}
        query = query.where(identity <= upper)
        if cursor:
            query = query.where(identity > cursor)
        rows = db.execute(query.order_by(identity).limit(PAGE_SIZE + 1)).all()
        for target_id, target_owner in rows[:PAGE_SIZE]:
            field = {"nightly.enqueue": "integration_id", "reports.export": "client_id", "reports.rules": "rule_id"}[kind]
            submit(db, kind=child_kind, queue=queue,
                key=f"{child_kind}:{target_id}:{stamp}", resource=f"{child_kind}:{target_id}",
                tenant=target_owner, payload={field: str(target_id), "owner_id": str(target_owner), "scheduled_at": stamp},
                replay_safe=kind == "nightly.enqueue")
        if len(rows) > PAGE_SIZE:
            last = str(rows[PAGE_SIZE - 1][0])
            continuation = {"scheduled_at": stamp, "cursor": last, "upper_id": str(upper)}
            if owner_id:
                continuation["owner_id"] = str(owner_id)
            submit(db, kind=kind, queue="maintenance", key=f"calendar-page:{kind}:{stamp}:{owner_id}:{last}",
                resource=f"calendar:{kind}", tenant="system", payload=continuation, replay_safe=True)
        return {"planned": min(len(rows), PAGE_SIZE), "has_next": len(rows) > PAGE_SIZE}


def enqueue_nightly(payload):
    from automation.durable_sync import enqueue
    from automation.main import AUTO_SYNC_DAYS
    return enqueue(uuid.UUID(payload["integration_id"]), days=AUTO_SYNC_DAYS,
        force_full=False, trigger="auto", occurrence=scheduled_time(payload).isoformat(),
        expected_owner_id=uuid.UUID(payload["owner_id"]))


async def run_report(payload):
    from backend_api.reports.scheduler import run_scheduled_report_rules
    scheduled = scheduled_time(payload)
    if report_expired(scheduled, datetime.now(timezone.utc)):
        return {"skipped": "expired_occurrence"}
    return await run_scheduled_report_rules(scheduled_at=scheduled,
        rule_id=uuid.UUID(payload["rule_id"]), owner_id=uuid.UUID(payload["owner_id"]))


def export_project(factory, payload, *, service_factory=None):
    """Per-project DB work -> detached values -> external Sheets IO.

    Child is non-replayable: timeout after a sheet was written is not evidence
    that no write happened. It must not invoke the former global export pass.
    """
    from automation.reports import generate_weekly_report, generate_monthly_report
    from automation.google_sheets import GoogleSheetsService
    target = scheduled_time(payload).date()
    client_id, owner_id = uuid.UUID(payload["client_id"]), uuid.UUID(payload["owner_id"])
    with factory() as db:
        client = db.get(models.Client, client_id)
        if client is None or client.owner_id != owner_id or client.status != models.ClientStatus.ACTIVE:
            return {"skipped": "scope_changed"}
        # Legacy report helpers commit their own pure-SQL aggregates.
        generate_weekly_report(db, client_id, target)
        generate_monthly_report(db, client_id, target.year, target.month)
        spreadsheet_id = client.spreadsheet_id
        snapshot = GoogleSheetsService.prepare_snapshot(client_id, db) if spreadsheet_id else None
    if snapshot is None:
        return {"reports": "generated", "sheets": "not_configured"}
    # Constructor may perform credential/discovery IO: it too is outside SQL.
    service = (service_factory or GoogleSheetsService)()
    if not service.configured:
        raise RuntimeError("Project requires Sheets export but credentials are not configured")
    with factory() as db:
        client = db.get(models.Client, client_id)
        if (client is None or client.owner_id != owner_id or client.status != models.ClientStatus.ACTIVE
                or client.spreadsheet_id != spreadsheet_id):
            return {"skipped": "scope_changed"}
    return {"reports": "generated", "sheets": service.write_snapshot(spreadsheet_id, snapshot)}
