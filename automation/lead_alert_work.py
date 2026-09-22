"""DB-backed quality alerts: bounded planning, scoped snapshot, guarded send.

Only finalized, persisted leads from the explicitly bound phone project count.
One short message/recipient/occurrence; HTTP never holds an SQL connection.
An ambiguous send is not retried and holds the project's delivery resource.
This is not the immediate new-lead export or a global placement blacklist.
"""
from dataclasses import dataclass, field
from datetime import timedelta
import hashlib
import json
import uuid

import sqlalchemy as sa

from automation.calendar_work import scheduled_time
from automation.billing_work import expired
from automation.work_errors import RejectedBeforeExternalIO
from automation.work_ledger import submit
from automation.work_tables import jobs, lead_deliveries
from core import models, delivery_outcome
from core.job_fence import current_fence, LeaseLost
from lead_validator.config import settings

PAGE_SIZE = 100
PARENTS = {"lead.daily", "lead.weekly"}
CHILDREN = {"lead.daily.project", "lead.weekly.project"}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def scope(project):
    return digest([str(project.id), str(project.owner_id), str(project.client_id),
                   project.is_active, (project.telegram_chat_id or "").strip()])


def plan_page(factory, kind, payload):
    if kind not in PARENTS:
        raise ValueError("Unsupported lead alert planner")
    scheduled = scheduled_time(payload)
    stamp = scheduled.isoformat()
    cursor = uuid.UUID(payload["cursor"]) if payload.get("cursor") else None
    upper = uuid.UUID(payload["upper_id"]) if payload.get("upper_id") else None
    owner = uuid.UUID(payload["owner_id"]) if payload.get("owner_id") else None
    days = 7 if kind == "lead.weekly" else settings.ALERT_LOOKBACK_DAYS
    minimum, threshold = settings.ALERT_MIN_LEADS, settings.ALERT_THRESHOLD_PERCENT
    if not (1 <= days <= 90 and minimum >= 1 and 0 <= threshold <= 100):
        raise RejectedBeforeExternalIO("Invalid lead alert thresholds")
    p = models.PhoneProject
    with factory.begin() as db:
        if expired(scheduled, db.scalar(sa.select(sa.func.clock_timestamp()))):
            return {"planned": 0, "skipped": "expired_occurrence"}
        query = sa.select(p).where(p.is_active.is_(True), sa.func.length(sa.func.trim(p.telegram_chat_id)) > 0)
        if owner:
            query = query.where(p.owner_id == owner)
        if upper is None:
            last = db.scalar(query.order_by(p.id.desc()).limit(1))
            upper = last.id if last else None
        if upper is None:
            return {"planned": 0, "has_next": False}
        query = query.where(p.id <= upper)
        if cursor:
            query = query.where(p.id > cursor)
        rows = db.scalars(query.order_by(p.id).limit(PAGE_SIZE + 1)).all()
        child_kind = kind + ".project"
        for project in rows[:PAGE_SIZE]:
            submit(db, kind=child_kind, queue="reports", key=f"{child_kind}:{project.id}:{stamp}",
                resource=f"lead-alert:{project.id}", tenant=project.owner_id, replay_safe=False,
                payload={"project_id": str(project.id), "owner_id": str(project.owner_id),
                    "scope_digest": scope(project), "scheduled_at": stamp, "days": days,
                    "minimum": minimum, "threshold": threshold})
        if len(rows) > PAGE_SIZE:
            last = str(rows[PAGE_SIZE - 1].id)
            continuation = {"scheduled_at": stamp, "cursor": last, "upper_id": str(upper)}
            if owner:
                continuation["owner_id"] = str(owner)
            submit(db, kind=kind, queue="maintenance", key=f"lead-page:{kind}:{stamp}:{owner}:{last}",
                resource=f"calendar:{kind}", tenant="system", payload=continuation, replay_safe=True)
        return {"planned": min(len(rows), PAGE_SIZE), "has_next": len(rows) > PAGE_SIZE}


def require_scope(db, kind, payload):
    fence = current_fence.get()
    if fence is None:
        raise LeaseLost("Lead alert requires the durable executor")
    job = db.execute(sa.select(jobs).where(jobs.c.id == fence.job_id, jobs.c.lease_token == fence.token,
        jobs.c.state == "running", jobs.c.lease_until > sa.func.clock_timestamp())).mappings().first()
    if job is None:
        raise LeaseLost("Lead alert execution expired")
    project = db.get(models.PhoneProject, uuid.UUID(payload["project_id"]), populate_existing=True, with_for_update=True)
    if (kind not in CHILDREN or job["kind"] != kind or job["payload"] != payload
            or job["resource"] != f"lead-alert:{payload['project_id']}"
            or project is None or not project.is_active or not (project.telegram_chat_id or "").strip()
            or str(project.owner_id) != payload["owner_id"] or str(project.owner_id) != job["tenant"]
            or scope(project) != payload["scope_digest"]):
        raise RejectedBeforeExternalIO("Lead alert scope or recipient changed")
    if project.client_id:
        client = db.get(models.Client, project.client_id)
        if not client or client.owner_id != project.owner_id or client.status != models.ClientStatus.ACTIVE:
            raise RejectedBeforeExternalIO("Linked lead project is paused or has changed owner")
    return project


@dataclass(frozen=True)
class Snapshot:
    text: str = field(repr=False)
    chat_id: str = field(repr=False)
    scope_digest: str


def label(value, maximum=40):
    # Plain text, never interpret UTM strings as Telegram markup.
    return " ".join(str(value or "—").split())[:maximum]


def prepare(db, kind, payload):
    project = require_scope(db, kind, payload)
    end = scheduled_time(payload)
    if expired(end, db.scalar(sa.select(sa.func.clock_timestamp()))):
        return None
    days, minimum, threshold = payload["days"], payload["minimum"], payload["threshold"]
    if not (1 <= days <= 90 and minimum >= 1 and 0 <= threshold <= 100):
        raise RejectedBeforeExternalIO("Invalid lead alert thresholds")
    start = end - timedelta(days=days)
    lead = models.Lead
    filters = (lead.project_id == project.id, lead.created_at >= start, lead.created_at < end,
               lead.status.in_([models.LeadStatus.VALID, models.LeadStatus.INVALID, models.LeadStatus.SPAM]))
    rejected = sa.or_(lead.status.in_([models.LeadStatus.INVALID, models.LeadStatus.SPAM]), lead.is_spam.is_(True))
    count = sa.func.count(lead.id)
    bad = sa.func.count(lead.id).filter(rejected)
    total, rejected_total = db.execute(sa.select(count, bad).where(*filters)).one()
    dimensions = [sa.func.coalesce(sa.func.nullif(column, ""), fallback) for column, fallback in (
        (lead.utm_source, "direct"), (lead.utm_campaign, "none"), (lead.utm_content, "none"))]
    sources = db.execute(sa.select(*dimensions, count, bad).where(*filters).group_by(*dimensions)
        .having(count >= minimum, bad * 100.0 >= count * threshold)
        .order_by((bad * 100.0 / count).desc(), bad.desc(), *dimensions).limit(10)).all()
    if not total or (kind == "lead.daily.project" and not sources):
        return None
    lines = ["Качество заявок: " + label(project.name, 80),
        f"Период (UTC): {start:%d.%m.%Y %H:%M} — {end:%d.%m.%Y %H:%M}, конец не включён.",
        f"Проверено: {total}. Отклонено: {rejected_total} ({rejected_total / total:.1%})."]
    if sources:
        lines.append(f"Источники с долей отклонений от {threshold:g}% (не менее {minimum} заявок), до 10 худших:")
        for source, campaign, placement, amount, rejected_amount in sources:
            lines.append(f"• {label(source)} / {label(campaign)} / {label(placement)}: "
                         f"{rejected_amount} из {amount} ({rejected_amount / amount:.1%}).")
    else:
        lines.append("Источников, превышающих заданный порог, нет.")
    text = "\n".join(lines)
    if len(text.encode("utf-16-le")) // 2 > 3900:
        raise RejectedBeforeExternalIO("Lead alert exceeds the bounded message size")
    return Snapshot(text, project.telegram_chat_id.strip(), scope(project))


async def execute(factory, kind, payload, *, notifier=None):
    from lead_validator.services.telegram import telegram_notifier
    notifier = notifier or telegram_notifier
    # Reject before creating a sending intent when delivery is not configured.
    if not notifier.enabled or not notifier.token:
        raise RejectedBeforeExternalIO("Lead Telegram delivery is not configured")
    with factory.begin() as db:
        require_scope(db, kind, payload)
        job_id = current_fence.get().job_id
        receipt = db.execute(sa.select(lead_deliveries).where(lead_deliveries.c.job_id == job_id)
                             .with_for_update()).mappings().first()
        if receipt:
            if receipt["state"] == "sent":
                return {"accepted": True, "replayed": True}
            if receipt["state"] == "rejected":
                raise RejectedBeforeExternalIO("Previous lead delivery was rejected")
            raise RuntimeError("Lead delivery outcome requires reconciliation")
        snapshot = prepare(db, kind, payload)
        if snapshot is None:
            return {"skipped": "empty_or_expired"}
        db.execute(lead_deliveries.insert().values(job_id=job_id, scope_digest=snapshot.scope_digest,
            body_digest=digest(snapshot.text), state="sending"))
    # The commit above validates the lease. Never fall back to the global chat.
    delivery_outcome.before_send()
    accepted = await notifier.send_message(snapshot.text, parse_mode=None, chat_id=snapshot.chat_id)
    if not accepted:
        if delivery_outcome.outcome.get() == "rejected":
            with factory.begin() as db:
                db.execute(lead_deliveries.update().where(lead_deliveries.c.job_id == job_id)
                    .values(state="rejected", confirmed_at=sa.func.clock_timestamp()))
            raise RejectedBeforeExternalIO("Telegram rejected lead alert")
        raise RuntimeError("Telegram lead alert delivery is uncertain")
    with factory.begin() as db:
        try:
            require_scope(db, kind, payload)
        except RejectedBeforeExternalIO as exc:
            # HTTP already happened: this must NOT be classified as no send.
            raise RuntimeError("Lead alert scope changed during delivery; reconcile") from exc
        db.execute(lead_deliveries.update().where(lead_deliveries.c.job_id == job_id)
            .values(state="sent", confirmed_at=sa.func.clock_timestamp()))
    return {"accepted": True}
