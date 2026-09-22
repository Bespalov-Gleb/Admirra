"""SQL-only project placement decisions, bounded reads and expiring entries."""
import hashlib
import json
import uuid
import sqlalchemy as sa
from core import models
from lead_validator.services.scoped_stats import StatsLimitExceeded

MAX_BLOCKS = 1000


def dimensions(source, campaign, content):
    return (source or 'direct', campaign or 'none', content or 'none')


def key(values):
    return hashlib.sha256(json.dumps(values, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def _owner(owner_id):
    if not isinstance(owner_id, uuid.UUID):
        raise ValueError('Placement reads require an explicit owner UUID')


def active_query(owner_id):
    _owner(owner_id)
    block, project = models.LeadPlacementBlock, models.PhoneProject
    return sa.select(block).join(project, project.id == block.project_id).where(
        block.owner_id == owner_id, project.owner_id == owner_id, project.is_active.is_(True),
        sa.or_(project.client_id.is_(None), sa.exists(sa.select(models.Client.id).where(
            models.Client.id == project.client_id, models.Client.owner_id == owner_id,
            models.Client.status == models.ClientStatus.ACTIVE))),
        block.expires_at > sa.func.clock_timestamp())


def is_blacklisted(db, owner_id, project_id, source, campaign, content):
    _owner(owner_id)
    if not isinstance(project_id, uuid.UUID):
        raise ValueError('Placement reads require an explicit project UUID')
    values = dimensions(source, campaign, content)
    if any(len(value) > 200 for value in values):
        return False
    block = models.LeadPlacementBlock
    return db.scalar(active_query(owner_id).with_only_columns(block.placement_key)
        .where(block.project_id == project_id, block.placement_key == key(values)).limit(1)) is not None


def get_blacklist(db, owner_id):
    block, project = models.LeadPlacementBlock, models.PhoneProject
    ttl = sa.cast(sa.func.extract('epoch', block.expires_at - sa.func.clock_timestamp()), sa.Integer)
    rows = db.execute(active_query(owner_id).with_only_columns(block.project_id, project.name,
        block.source, block.campaign, block.content, block.reason, ttl.label('ttl'))
        .order_by(block.project_id, block.placement_key).limit(MAX_BLOCKS + 1)).all()
    if len(rows) > MAX_BLOCKS:
        raise StatsLimitExceeded('Чёрный список превышает лимит выгрузки; требуется постраничный экспорт.')
    return [dict(project_id=str(row.project_id), project_name=row.name, source=row.source,
        campaign=row.campaign, content=row.content, reason=row.reason,
        ttl_seconds=max(row.ttl, 0), expires_in_days=max(row.ttl, 0) // 86400) for row in rows]
