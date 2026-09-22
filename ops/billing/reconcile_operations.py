"""Operator-only reconciliation; inspect is read-only, retry needs explicit evidence.

Run as a module in the candidate application environment. Never calls a provider
mutation. Unknown outcomes require a human to establish that the earlier request
has FINISHED (including checking CP), not merely that it disappeared from logs.
"""
import argparse
import asyncio
import json
import uuid
from datetime import datetime, timezone
import sqlalchemy as sa
from core import models, billing_intents as intent
from automation.work_tables import jobs, outbox


def _version(row, job):
    return intent.digest((row.id, row.status, row.updated_at, row.evidence, dict(job) if job else None))


async def inspect(factory, operation_id):
    from backend_api.services.cloudpayments import CloudPaymentsService as CP
    with factory() as db:
        row = db.get(models.BillingProviderOperation, operation_id)
        if row is None:
            raise ValueError('Operation not found')
        job = db.execute(sa.select(jobs).where(jobs.c.id == row.job_id)).mappings().first()
        result = {**intent.public(row, job), 'owner_id': str(row.user_id), 'job_state': job['state'] if job else None,
            'version': _version(row, job), 'evidence': row.evidence}
        owner = str(row.user_id)
    # No SQL connection while CP responds. No emails, card/token/raw CP dumps.
    subscriptions = await CP.find_subscriptions(owner)
    if len(subscriptions) > 20:
        raise ValueError('Provider result exceeds reconciliation bound')
    result['provider'] = [{k: s.get(k) for k in ('Id', 'Status', 'Amount', 'Currency', 'Interval', 'Period')}
                          for s in subscriptions]
    result['provider_fingerprint'] = intent.digest(result['provider'])
    return result


async def retry_current(factory, operation_id, *, version, provider_fingerprint, actor, reason, settled_reference):
    if not intent.enabled() or min(len(actor.strip()), len(reason.strip()), len(settled_reference.strip())) < 10:
        raise ValueError('Enabled queue, named operator, reason and settled provider evidence (10+ characters) required')
    if max(len(actor), len(reason), len(settled_reference)) > 1000:
        raise ValueError('Audit fields exceed limit')
    observed = await inspect(factory, operation_id)
    if observed['version'] != version or observed['provider_fingerprint'] != provider_fingerprint:
        raise ValueError('Operation/provider changed; inspect again before deciding')
    with factory.begin() as db:
        row = db.get(models.BillingProviderOperation, operation_id)
        sub = db.scalar(sa.select(models.Subscription).where(models.Subscription.id == row.subscription_id,
            models.Subscription.user_id == row.user_id).with_for_update())
        row = db.scalar(sa.select(models.BillingProviderOperation).where(models.BillingProviderOperation.id == operation_id)
            .execution_options(populate_existing=True).with_for_update())
        job = db.execute(sa.select(jobs).where(jobs.c.id == row.job_id).with_for_update()).mappings().first()
        if (not job or job['state'] not in {'uncertain', 'failed'} or row.status not in intent.OPEN
                or _version(row, job) != version):
            raise ValueError('Only unchanged, stopped operations can be reconciled')
        if sub is None:
            raise ValueError('Missing account subscription; manual finance reconciliation required')
        # Old request is NEVER replayed; a new intent re-derives current terms.
        # The human evidence explicitly attests no old request can arrive later.
        row.status = 'superseded'
        row.evidence = {**row.evidence, 'resolution': {'actor': actor, 'reason': reason,
            'settled_reference': settled_reference, 'at': datetime.now(timezone.utc).isoformat(),
            'provider_fingerprint': provider_fingerprint, 'decision': 'retry_current'}}
        db.execute(jobs.update().where(jobs.c.id == row.job_id).values(state='failed',
            lease_token=None, lease_until=None, finished_at=sa.func.now(), error_type='OperatorReconciled'))
        db.execute(outbox.delete().where(outbox.c.job_id == row.job_id))
        successor = intent.enqueue(db, sub, row.command, row.provider_id)
        return {'resolved': str(row.id), 'next_operation': str(successor.id)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation_id', type=uuid.UUID)
    parser.add_argument('--retry-current', action='store_true')
    for name in ('version', 'provider-fingerprint', 'actor', 'reason', 'settled-reference'):
        parser.add_argument('--' + name)
    args = parser.parse_args()
    from core.database import SessionLocal
    if args.retry_current:
        values = {key: getattr(args, key) or '' for key in
                  ('version', 'provider_fingerprint', 'actor', 'reason', 'settled_reference')}
        result = asyncio.run(retry_current(SessionLocal, args.operation_id, **values))
    else:
        result = asyncio.run(inspect(SessionLocal, args.operation_id))
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
