"""Replay-safe DB-only blacklist child. No provider IO or global Redis state."""
from datetime import timedelta
import hashlib
import json
import uuid
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from core import models
from core.job_fence import current_fence, LeaseLost
from automation.work_tables import jobs
from automation.work_errors import RejectedBeforeExternalIO
from automation.calendar_work import scheduled_time
from automation.billing_work import expired
from lead_validator.services.scoped_stats import FINAL_STATUSES, rejected_condition
from lead_validator.services.scoped_placements import key, MAX_BLOCKS
from core.runtime import env_int
from lead_validator.config import settings


def scope(project):
    return hashlib.sha256(json.dumps([str(project.id), str(project.owner_id),
        str(project.client_id), project.is_active]).encode()).hexdigest()


def parameters():
    days = env_int('PLACEMENT_BLACKLIST_LOOKBACK_DAYS', 21, 1, 90)
    minimum, threshold, ttl = (settings.PLACEMENT_BLACKLIST_MIN_LEADS,
        settings.PLACEMENT_BLACKLIST_THRESHOLD, settings.PLACEMENT_BLACKLIST_TTL_DAYS)
    if minimum < 1 or not 0 <= threshold <= 100 or not 1 <= ttl <= 90:
        raise ValueError('Invalid placement thresholds')
    return dict(days=days, minimum=minimum, threshold=threshold, ttl=ttl)


def execute(factory, payload):
    fence = current_fence.get()
    if fence is None:
        raise LeaseLost('Placement generation requires a durable lease')
    end = scheduled_time(payload)
    with factory.begin() as db:
        job = db.execute(sa.select(jobs).where(jobs.c.id == fence.job_id,
            jobs.c.lease_token == fence.token, jobs.c.state == 'running',
            jobs.c.lease_until > sa.func.clock_timestamp())).mappings().first()
        if job is None:
            raise LeaseLost('Placement execution expired')
        project = db.get(models.PhoneProject, uuid.UUID(payload['project_id']),
            populate_existing=True, with_for_update=True)
        if (not job or not project or job['kind'] != 'lead.blacklist.project' or job['payload'] != payload
                or job['tenant'] != str(project.owner_id) or payload['owner_id'] != str(project.owner_id)
                or job['resource'] != f'lead-blacklist:{project.id}' or not project.is_active
                or scope(project) != payload['scope_digest']):
            raise RejectedBeforeExternalIO('Placement project binding changed')
        if project.client_id:
            client = db.get(models.Client, project.client_id)
            if not client or client.owner_id != project.owner_id or client.status != models.ClientStatus.ACTIVE:
                raise RejectedBeforeExternalIO('Linked client scope changed')
        now = db.scalar(sa.select(sa.func.clock_timestamp()))
        if expired(end, now):
            raise RejectedBeforeExternalIO('Placement occurrence expired')
        config = parameters()
        # Payload is bound to the job; a changed deployment policy needs a new occurrence.
        if any(payload[name] != value for name, value in config.items()):
            raise RejectedBeforeExternalIO('Placement policy changed')
        lead, block = models.Lead, models.LeadPlacementBlock
        dims = [sa.func.coalesce(sa.func.nullif(col, ''), fallback) for col, fallback in
                ((lead.utm_source, 'direct'), (lead.utm_campaign, 'none'), (lead.utm_content, 'none'))]
        count = sa.func.count(lead.id)
        bad = count.filter(rejected_condition())
        rows = db.execute(sa.select(*dims, count, bad).where(lead.project_id == project.id,
            lead.created_at >= end - timedelta(days=config['days']), lead.created_at < end,
            lead.status.in_(FINAL_STATUSES), *[sa.func.length(d) <= 200 for d in dims],
            # Do not perpetuate a block solely through its own subsequent rejections.
            sa.or_(lead.validation_reason.is_(None), ~lead.validation_reason.like('utm_invalid:blacklisted_placement:%')))
            .group_by(*dims).having(count >= config['minimum'], bad * 100 >= count * config['threshold'])
            .order_by(*dims).limit(MAX_BLOCKS + 1)).all()
        if len(rows) > MAX_BLOCKS:
            raise RejectedBeforeExternalIO('Too many placements for a bounded update')
        db.execute(sa.delete(block).where(block.project_id == project.id,
            sa.or_(block.owner_id != project.owner_id, block.expires_at <= now)))
        # Occurrence-based expiry makes retries idempotent; existing unexpired decisions
        # are not extended every day. Empty input does not silently unblock them early.
        values = [dict(owner_id=project.owner_id, project_id=project.id,
                placement_key=key((source, campaign, content)), source=source, campaign=campaign, content=content,
                reason=f'{rejected}/{total} rejected; threshold {config["threshold"]:g}%',
                created_at=now, expires_at=end + timedelta(days=config['ttl']))
            for source, campaign, content, total, rejected in rows]
        if values:
            db.execute(insert(block).values(values).on_conflict_do_nothing())
        active = db.scalar(sa.select(sa.func.count()).select_from(block).where(block.project_id == project.id))
        if active > MAX_BLOCKS:
            raise RejectedBeforeExternalIO('Placement capacity exceeded; no partial update applied')
        return {'candidates': len(rows), 'active': active}
