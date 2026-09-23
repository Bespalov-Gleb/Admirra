"""Read-only bounded lead intake/export evidence, without contact data or tokens."""
import argparse
import json
import uuid

import sqlalchemy as sa
from core import models
from automation.work_tables import jobs, lead_exports


def snapshot(db, *, owner_id=None, limit=50):
    if type(limit) is not int or not 1 <= limit <= 200:
        raise ValueError('Limit must be 1..200')
    if owner_id is not None and not isinstance(owner_id, uuid.UUID):
        raise ValueError('Owner must be a UUID')
    intake = models.LeadIntake.__table__
    outstanding = sa.select(intake.c.id, intake.c.project_id, intake.c.lead_id, intake.c.state,
        intake.c.created_at, intake.c.deadline).where(intake.c.state.in_(['processing', 'held']))
    if owner_id: outstanding = outstanding.where(intake.c.owner_id == owner_id)
    rows = db.execute(outstanding.order_by(intake.c.created_at, intake.c.id).limit(limit + 1)).mappings().all()
    exports = sa.select(jobs.c.id, jobs.c.state.label('job_state'), jobs.c.created_at,
        lead_exports.c.state.label('receipt_state'), lead_exports.c.provider_ref).outerjoin(
        lead_exports, lead_exports.c.job_id == jobs.c.id).where(jobs.c.kind == 'lead.export',
        jobs.c.state.in_(['queued', 'running', 'uncertain', 'failed']))
    if owner_id: exports = exports.where(jobs.c.tenant == str(owner_id))
    deliveries = db.execute(exports.order_by(jobs.c.created_at, jobs.c.id).limit(limit + 1)).mappings().all()
    return {'intakes': [dict(row) for row in rows[:limit]], 'intakes_truncated': len(rows) > limit,
            'exports': [dict(row) for row in deliveries[:limit]], 'exports_truncated': len(deliveries) > limit,
            'read_only': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner-id', type=uuid.UUID)
    parser.add_argument('--limit', type=int, default=50)
    args = parser.parse_args()
    from core.database import engine
    with engine.begin() as db:
        db.execute(sa.text('SET TRANSACTION READ ONLY'))
        db.execute(sa.text("SET LOCAL statement_timeout = '5s'"))
        result = snapshot(db, owner_id=args.owner_id, limit=args.limit)
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
