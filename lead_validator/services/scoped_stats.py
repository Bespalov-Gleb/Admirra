"""Bounded, owner-scoped reads of finalized persisted leads.

No process-global counters, local log files, provider calls or lead PII are read.
Intervals are half-open UTC. PENDING is not a rejected lead.
"""
from datetime import datetime, time, timedelta, timezone
import uuid

import sqlalchemy as sa
from core import models

MAX_PROJECT_ROWS = 1000
MAX_REASON_ROWS = 100
FINAL_STATUSES = (models.LeadStatus.VALID, models.LeadStatus.INVALID, models.LeadStatus.SPAM)


class StatsLimitExceeded(ValueError):
    pass


def _scope(owner_id, start, end):
    if not isinstance(owner_id, uuid.UUID):
        raise ValueError('An explicit owner UUID is required')
    if start.tzinfo is None or end.tzinfo is None or not start < end:
        raise ValueError('An aware, non-empty time interval is required')
    lead, project = models.Lead, models.PhoneProject
    return (project.owner_id == owner_id, lead.created_at >= start, lead.created_at < end,
            lead.status.in_(FINAL_STATUSES))


def rejected_condition():
    return sa.or_(models.Lead.status.in_((models.LeadStatus.INVALID, models.LeadStatus.SPAM)),
                  models.Lead.is_spam.is_(True))


def project_statistics(db, owner_id, *, days=7, now=None):
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 365:
        raise ValueError('days must be between 1 and 365')
    end = now or datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    filters = _scope(owner_id, start, end)
    lead, project = models.Lead, models.PhoneProject
    total = sa.func.count(lead.id)
    rejected = total.filter(rejected_condition())
    # One statement gives a consistent snapshot for totals and the project table.
    rows = db.execute(sa.select(project.id, project.name, total.label('total'), rejected.label('rejected')).select_from(project)
        .join(lead, lead.project_id == project.id).where(*filters)
        .group_by(project.id, project.name).order_by(total.desc(), project.id)
        .limit(MAX_PROJECT_ROWS + 1)).all()
    if len(rows) > MAX_PROJECT_ROWS:
        # Never show truncated project data as a complete account total.
        raise StatsLimitExceeded('Слишком много проектов за период. Выберите меньший период.')
    overall = {'total': 0, 'accepted': 0, 'rejected': 0, 'rejection_rate': 0.0}
    projects = []
    for row in rows:
        accepted = row.total - row.rejected
        overall['total'] += row.total
        overall['accepted'] += accepted
        overall['rejected'] += row.rejected
        projects.append({'project_id': row.id, 'project_name': row.name,
            'total': row.total, 'accepted': accepted, 'rejected': row.rejected,
            'acceptance_rate': round(accepted / row.total * 100, 2)})
    if overall['total']:
        overall['rejection_rate'] = round(overall['rejected'] / overall['total'] * 100, 2)
    return {'stats': overall, 'project_stats': projects}


def daily_rejections(db, owner_id, day):
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    lead = models.Lead
    # Categories, not free-form provider messages or user-supplied contents.
    reason = sa.func.left(sa.func.coalesce(sa.func.nullif(
        sa.func.split_part(lead.validation_reason, ':', 1), ''), 'unknown'), 200)
    count = sa.func.count(lead.id)
    rows = db.execute(sa.select(reason.label('reason'), count.label('count'),
            sa.func.sum(count).over().label('total')).select_from(lead)
        .join(models.PhoneProject, lead.project_id == models.PhoneProject.id)
        .where(*_scope(owner_id, start, end), rejected_condition())
        .group_by(reason).order_by(count.desc(), reason).limit(MAX_REASON_ROWS + 1)).all()
    total = int(rows[0].total) if rows else 0
    shown = rows[:MAX_REASON_ROWS]
    return {'date': day.isoformat(), 'timezone': 'UTC', 'total': total,
            'by_reason': {row.reason: row.count for row in shown},
            'by_reason_truncated': len(rows) > MAX_REASON_ROWS,
            'other_count': total - sum(row.count for row in shown),
            'source': 'persisted_project_leads'}
