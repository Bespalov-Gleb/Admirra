"""Bounded subscription maintenance planning; never charges or mails in a parent.

Legacy per-subscription calculations remain unchanged. Children have separate
resources and are non-replayable: ambiguous outcomes require reconciliation.
This module does not claim to remove all SQL/HTTP overlap in legacy billing.
"""
from datetime import datetime, timedelta, timezone
import uuid

import sqlalchemy as sa

from automation.calendar_work import scheduled_time
from automation.work_ledger import submit
from core import models

PAGE_SIZE = 100


def expired(scheduled, now):
    return scheduled > now + timedelta(minutes=1) or now - scheduled > timedelta(hours=24)


def plan_page(factory, payload):
    scheduled = scheduled_time(payload)
    stamp = scheduled.isoformat()
    cursor = uuid.UUID(payload["cursor"]) if payload.get("cursor") else None
    upper = uuid.UUID(payload["upper_id"]) if payload.get("upper_id") else None
    owner_id = uuid.UUID(payload["owner_id"]) if payload.get("owner_id") else None
    sub = models.Subscription
    with factory.begin() as db:
        now = db.scalar(sa.select(sa.func.clock_timestamp()))
        if expired(scheduled, now):
            return {"planned": 0, "skipped": "expired_occurrence"}
        warning = sa.and_(sub.current_period_end >= now + timedelta(days=6),
            sub.current_period_end < now + timedelta(days=8),
            sub.status.in_([models.SubscriptionStatus.ACTIVE, models.SubscriptionStatus.TRIAL]))
        recurring = sa.and_(sub.recurring_sync_required.is_(True), sub.cancel_at_period_end.is_(False),
                           sub.cloudpayments_subscription_id.is_not(None))
        query = sa.select(sub.id, sub.user_id, sub.current_period_end,
                          warning.label("warning"), recurring.label("recurring")).where(sa.or_(warning, recurring))
        if owner_id:
            query = query.where(sub.user_id == owner_id)
        if upper is None:
            last = db.execute(query.order_by(sub.id.desc()).limit(1)).first()
            upper = last.id if last else None
        if upper is None:
            return {"planned": 0, "skipped": "no_matching_scopes"}
        query = query.where(sub.id <= upper)
        if cursor:
            query = query.where(sub.id > cursor)
        rows = db.execute(query.order_by(sub.id).limit(PAGE_SIZE + 1)).all()
        planned = 0
        for row in rows[:PAGE_SIZE]:
            child = {"subscription_id": str(row.id), "owner_id": str(row.user_id), "scheduled_at": stamp}
            for kind, due in (("billing.warning", row.warning), ("billing.recurring", row.recurring)):
                if not due:
                    continue
                parameters = dict(child)
                if kind == "billing.warning":
                    parameters["period_end"] = row.current_period_end.isoformat()
                submit(db, kind=kind, queue="maintenance", key=f"{kind}:{row.id}:{stamp}",
                       resource=f"{kind}:{row.id}", tenant=row.user_id, payload=parameters, replay_safe=False)
                planned += 1
        if len(rows) > PAGE_SIZE:
            last = str(rows[PAGE_SIZE - 1].id)
            continuation = {"scheduled_at": stamp, "cursor": last, "upper_id": str(upper)}
            if owner_id:
                continuation["owner_id"] = str(owner_id)
            submit(db, kind="billing.maintenance", queue="maintenance",
                   key=f"billing-page:{stamp}:{owner_id}:{last}", resource="calendar:billing.maintenance",
                   tenant="system", payload=continuation, replay_safe=True)
        return {"planned": planned, "scanned": min(len(rows), PAGE_SIZE), "has_next": len(rows) > PAGE_SIZE}


async def execute(kind, payload):
    if kind not in {"billing.warning", "billing.recurring"}:
        raise ValueError("Unsupported billing child kind")
    if expired(scheduled_time(payload), datetime.now(timezone.utc)):
        return {"skipped": "expired_occurrence"}
    from backend_api.services.billing_notifications import send_overflow_renewal_warnings, reconcile_recurring_totals
    scope = {"subscription_id": uuid.UUID(payload["subscription_id"]), "owner_id": uuid.UUID(payload["owner_id"])}
    if kind == "billing.warning":
        period_end = datetime.fromisoformat(payload["period_end"])
        if period_end.tzinfo is None:
            raise ValueError("Billing period requires a timezone")
        count = await send_overflow_renewal_warnings(**scope, expected_period_end=period_end)
    else:
        count = await reconcile_recurring_totals(**scope)
    return {"completed": count}
