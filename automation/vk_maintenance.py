"""Bounded SQL-only maintenance of pending VK authorization links."""
import uuid

import sqlalchemy as sa

from automation.calendar_work import scheduled_time
from automation.work_ledger import submit
from core import models

PAGE_SIZE = 100


def run_page(factory, payload):
    from backend_api.integrations import _expire_vk_client_link_if_needed, VK_CLIENT_LINK_RETENTION
    scheduled = scheduled_time(payload).isoformat()
    cursor = uuid.UUID(payload["cursor"]) if payload.get("cursor") else None
    upper = uuid.UUID(payload["upper_id"]) if payload.get("upper_id") else None
    with factory.begin() as db:
        now = db.scalar(sa.select(sa.func.clock_timestamp()))
        query = sa.select(models.Integration).where(
            models.Integration.platform == models.IntegrationPlatform.VK_ADS,
            models.Integration.connection_status.in_(["awaiting_auth", "link_expired"]))
        if upper is None:
            upper = db.scalar(query.with_only_columns(models.Integration.id)
                              .order_by(models.Integration.id.desc()).limit(1))
        if upper is None:
            return {"scanned": 0, "expired": 0, "removed": 0, "has_next": False}
        query = query.where(models.Integration.id <= upper)
        if cursor:
            query = query.where(models.Integration.id > cursor)
        # An OAuth callback holding a row is not blocked/deleted by cleanup.
        # Skipped locked drafts are reconsidered at the next hourly occurrence.
        rows = db.scalars(query.order_by(models.Integration.id).limit(PAGE_SIZE + 1)
                          .with_for_update(skip_locked=True)).all()
        expired = removed = 0
        for integration in rows[:PAGE_SIZE]:
            if _expire_vk_client_link_if_needed(integration, now):
                expired += 1
            if integration.link_created_at and integration.link_created_at <= now - VK_CLIENT_LINK_RETENTION:
                db.delete(integration)
                removed += 1
        if len(rows) > PAGE_SIZE:
            last = str(rows[PAGE_SIZE - 1].id)
            submit(db, kind="vk.maintenance", queue="maintenance",
                   key=f"vk-page:{scheduled}:{last}", resource="calendar:vk.maintenance", tenant="system",
                   payload={"scheduled_at": scheduled, "cursor": last, "upper_id": str(upper)}, replay_safe=True)
        return {"scanned": min(len(rows), PAGE_SIZE), "expired": expired, "removed": removed,
                "has_next": len(rows) > PAGE_SIZE}
