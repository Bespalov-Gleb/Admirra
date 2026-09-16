"""Run inside the OLD backend before price cutover; stdout contains private IDs.

Host deploy captures output into a root-only backup, never prints it verbatim.
Only --freeze writes, filling absent snapshots without changing effective prices.
"""
import json
import sys
from collections import Counter

from core import models, pricing
from core.database import SessionLocal


def signature(sub):
    spec = pricing.plan_from_snapshot(sub.price_book_snapshot, pricing.resolve_plan(sub.plan_code))
    pending = None
    if sub.pending_plan_code:
        p = pricing.plan_from_snapshot(sub.pending_price_book_snapshot, pricing.resolve_plan(sub.pending_plan_code))
        pending = [p.code, p.price_month, p.price_year, p.extra_project_price_month, p.extra_project_price_year]
    return [spec.code, spec.price_month, spec.price_year, spec.extra_project_price_month,
            spec.extra_project_price_year, pending]


with SessionLocal() as db:
    freeze = '--freeze' in sys.argv
    if freeze:
        # Wait only briefly for online requests, never lock production indefinitely.
        from sqlalchemy import text
        db.execute(text("SET LOCAL lock_timeout = '5s'"))
    query = db.query(models.Subscription).order_by(models.Subscription.id)
    if freeze:
        query = query.with_for_update()
    rows = query.all()
    records = []
    changed = 0
    for sub in rows:
        before = signature(sub)
        records.append({
            'id':str(sub.id), 'plan_code':sub.plan_code, 'status':sub.status.value,
            'snapshot':sub.price_book_snapshot, 'version':sub.price_book_version,
            'pending_snapshot':sub.pending_price_book_snapshot,
            'signature':before,
        })
        if freeze:
            if not sub.price_book_snapshot:
                sub.price_book_snapshot = pricing.plan_snapshot(pricing.resolve_plan(sub.plan_code))
                sub.price_book_version = pricing.current_price_book_version()
                changed += 1
            if sub.pending_plan_code and not sub.pending_price_book_snapshot:
                sub.pending_price_book_snapshot = pricing.plan_snapshot(pricing.resolve_plan(sub.pending_plan_code))
                changed += 1
            if signature(sub) != before:
                raise RuntimeError('Snapshot freezing would change effective prices')
    if freeze:
        db.commit()
    # No names, mail addresses, tokens or payment account IDs.
    summary = {
        'subscriptions':len(rows),
        'missing_snapshots':sum(not r['snapshot'] for r in records),
        'missing_pending_snapshots':sum(bool(s.pending_plan_code) and not s.pending_price_book_snapshot for s in rows),
        'statuses':dict(Counter(r['status'] for r in records)),
        'changed':changed,
        'version':pricing.current_price_book_version(),
        'catalog':{k:[s.price_month,s.price_year,s.extra_project_price_month] for k,s in pricing.build_price_book().items()},
        'running_sync_jobs':db.query(models.SyncJob).filter(models.SyncJob.status == models.SyncJobStatus.RUNNING).count(),
        'sending_reports':db.query(models.ReportDelivery).filter(models.ReportDelivery.status == 'sending').count(),
    }
    print('BILLING_AUDIT_JSON=' + json.dumps({'summary':summary,'records':records}, ensure_ascii=False))
