"""Operator-only inspection/resolution. No provider calls, resends or requeues.

Evidence must establish the final delivery outcome, not merely absence of logs.
Closing an unverified intake does not classify the contact as bad or as spam.
"""
import argparse
import json
import uuid

import sqlalchemy as sa

from core import models
from automation.work_tables import jobs, outbox, lead_exports, lead_resolutions
from lead_validator.services.project_intake import digest, scope


def _columns(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns} if row else None


def _load(db, kind, identifier, owner, *, lock=False):
    if kind not in ('intake', 'export') or not isinstance(identifier, uuid.UUID) or not isinstance(owner, uuid.UUID):
        raise ValueError('Explicit subject and owner UUIDs required')
    if kind == 'intake':
        row = db.get(models.LeadIntake, identifier)
        if not row or row.owner_id != owner:
            raise ValueError('Intake not found for this owner')
        project_id, lead_id, original_scope = row.project_id, row.lead_id, row.scope_digest
        job = receipt = None
    else:
        job = db.execute(sa.select(jobs).where(jobs.c.id == identifier)).mappings().first()
        if not job or job['kind'] != 'lead.export' or job['tenant'] != str(owner):
            raise ValueError('Export not found for this owner')
        payload = job['payload']
        if payload.get('owner_id') != str(owner) or payload.get('channel') not in ('crm', 'email', 'telegram', 'metrica'):
            raise ValueError('Invalid export binding')
        project_id, lead_id = uuid.UUID(payload['project_id']), uuid.UUID(payload['lead_id'])
        original_scope = payload['scope_digest']
        if job['resource'] != f"lead-export:{lead_id}:{payload['channel']}":
            raise ValueError('Invalid export resource')
        row = None
    # Same project -> intake/lead -> job/receipt lock order as the producers.
    project = db.get(models.PhoneProject, project_id, populate_existing=True, with_for_update=lock)
    if not project:
        raise ValueError('Project no longer exists')
    if kind == 'intake':
        row = db.get(models.LeadIntake, identifier, populate_existing=True, with_for_update=lock)
        if not row or row.owner_id != owner or row.project_id != project.id or row.lead_id != lead_id:
            raise ValueError('Intake binding changed')
    lead = db.get(models.Lead, lead_id, populate_existing=True, with_for_update=lock)
    if not lead or lead.project_id != project.id:
        raise ValueError('Lead binding changed')
    if kind == 'export':
        query = sa.select(jobs).where(jobs.c.id == identifier)
        latest = db.execute(query.with_for_update() if lock else query).mappings().one()
        if latest['payload'] != job['payload'] or latest['tenant'] != job['tenant'] or latest['resource'] != job['resource']:
            raise ValueError('Export binding changed')
        job = latest
        query = sa.select(lead_exports).where(lead_exports.c.job_id == identifier)
        receipt = db.execute(query.with_for_update() if lock else query).mappings().first()
    resolution = db.execute(sa.select(lead_resolutions).where(
        lead_resolutions.c.subject_type == kind, lead_resolutions.c.subject_id == identifier)).mappings().first()
    version = digest([_columns(row), _columns(lead), scope(project), dict(job) if job else None,
        dict(receipt) if receipt else None, dict(resolution) if resolution else None])
    return dict(project=project, lead=lead, intake=row, job=job, receipt=receipt, resolution=resolution,
        version=version, scope_current=project.owner_id == owner and scope(project) == original_scope)


def inspect(factory, kind, identifier, owner):
    with factory.begin() as db:
        db.execute(sa.text('SET TRANSACTION READ ONLY'))
        db.execute(sa.text("SET LOCAL statement_timeout = '5s'"))
        s = _load(db, kind, identifier, owner)
        now = db.scalar(sa.select(sa.func.clock_timestamp()))
        return dict(subject_type=kind, subject_id=str(identifier), owner_id=str(owner),
            project_id=str(s['project'].id), lead_id=str(s['lead'].id), version=s['version'],
            scope_current=s['scope_current'], lead_status=s['lead'].status.value,
            intake_state=s['intake'].state if s['intake'] else None,
            deadline_expired=s['intake'].deadline <= now if s['intake'] else None,
            job_state=s['job']['state'] if s['job'] else None,
            receipt_state=s['receipt']['state'] if s['receipt'] else None,
            provider_ref=s['receipt']['provider_ref'] if s['receipt'] else None,
            resolved=s['resolution'] is not None)


def resolve(factory, kind, identifier, owner, *, version, decision, actor, reason, evidence_ref):
    for name, value, low, high in [('version', version, 64, 64), ('actor', actor, 3, 128),
        ('reason', reason, 10, 1000), ('evidence_ref', evidence_ref, 10, 255)]:
        if not isinstance(value, str) or not low <= len(value.strip()) <= high or any(ord(c) < 32 for c in value):
            raise ValueError(f'Invalid bounded audit field: {name}')
    allowed = {'intake': {'close_unverified'}, 'export': {'confirm_delivered', 'close_without_resend'}}
    if decision not in allowed.get(kind, set()):
        raise ValueError('Unsupported operator decision')
    with factory.begin() as db:
        db.execute(sa.text("SET LOCAL statement_timeout = '5s'"))
        s = _load(db, kind, identifier, owner, lock=True)
        if s['resolution'] or version != s['version']:
            raise ValueError('State changed or already resolved; inspect again')
        now = db.scalar(sa.select(sa.func.clock_timestamp()))
        if kind == 'intake':
            row = s['intake']
            if row.state not in ('processing', 'held') or row.deadline > now or s['lead'].status != models.LeadStatus.PENDING:
                raise ValueError('Only expired, unverified admissions may be closed')
            row.state = 'closed'
            row.result = dict(success=False, lead_id=str(row.lead_id),
                rejection_reason='validation_closed_unverified', execution_time_ms=0)
            # Leave Lead.PENDING: an operational failure is not a negative
            # quality judgement. A late Context.finish sees closed and refuses.
        else:
            job, receipt = s['job'], s['receipt']
            if job['state'] not in ('uncertain', 'failed') or job['lease_token'] is not None or job['lease_until'] is not None:
                raise ValueError('Recover/drain the worker first; only stopped exports may be resolved')
            known_sent = receipt is not None and receipt['state'] == 'sent'
            if known_sent and decision != 'confirm_delivered':
                raise ValueError('A confirmed receipt cannot be downgraded to closed')
            if decision == 'confirm_delivered' and not known_sent:
                if not s['scope_current'] or not receipt or receipt['state'] != 'sending':
                    raise ValueError('Confirmation requires unchanged scope and an attempted delivery')
                if s['lead'].status not in (models.LeadStatus.VALID, models.LeadStatus.INVALID, models.LeadStatus.SPAM):
                    raise ValueError('Validation state changed')
                from automation.lead_export_work import snapshot_for
                try:
                    current = snapshot_for(db, s['project'], s['lead'], job['payload']['channel'])
                except Exception:
                    raise ValueError('Cannot verify original recipient/body; close without resend') from None
                if current is None or current.binding != receipt['body_digest'] or receipt['scope_digest'] != job['payload']['scope_digest']:
                    raise ValueError('Lead body or recipient changed since dispatch')
                setattr(s['lead'], 'exported_to_' + job['payload']['channel'], True)
                s['lead'].export_timestamp = now
            if receipt:
                db.execute(lead_exports.update().where(lead_exports.c.job_id == identifier).values(
                    state='sent' if decision == 'confirm_delivered' else 'closed', confirmed_at=now))
            db.execute(jobs.update().where(jobs.c.id == identifier).values(
                state='succeeded' if decision == 'confirm_delivered' else 'failed', finished_at=now,
                error_type=None if decision == 'confirm_delivered' else 'OperatorClosedWithoutResend'))
            db.execute(outbox.delete().where(outbox.c.job_id == identifier))
        db.execute(lead_resolutions.insert().values(subject_type=kind, subject_id=identifier,
            owner_id=owner, project_id=s['project'].id, version=version, decision=decision,
            actor=actor.strip(), reason=reason.strip(), evidence_ref=evidence_ref.strip()))
    return dict(resolved=str(identifier), decision=decision, resent=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=['intake', 'export'])
    parser.add_argument('identifier', type=uuid.UUID)
    parser.add_argument('--owner-id', type=uuid.UUID, required=True)
    parser.add_argument('--decision', choices=['close_unverified', 'confirm_delivered', 'close_without_resend'])
    for key in ('version', 'actor', 'reason', 'evidence-ref'):
        parser.add_argument('--' + key)
    args = parser.parse_args()
    from core.database import SessionLocal
    try:
        if args.decision:
            result = resolve(SessionLocal, args.kind, args.identifier, args.owner_id, decision=args.decision,
                **{key: getattr(args, key) for key in ('version', 'actor', 'reason', 'evidence_ref')})
        else:
            result = inspect(SessionLocal, args.kind, args.identifier, args.owner_id)
    except ValueError as error:
        parser.exit(2, str(error) + '\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
