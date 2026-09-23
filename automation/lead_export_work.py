"""One lead/channel per durable job, with a committed dispatch receipt before IO."""
from dataclasses import dataclass, field
from datetime import timezone
import csv
import io
import json
import uuid

import httpx
import sqlalchemy as sa

from core import models, security, delivery_outcome
from core.job_fence import current_fence, LeaseLost
from core.runtime import env_bool
from automation.work_errors import RejectedBeforeExternalIO
from automation.work_tables import jobs, lead_exports
from lead_validator.services.project_intake import require_project, scope, digest


CHANNELS = {'crm', 'email', 'telegram', 'metrica'}


def require_scope(db, payload):
    fence = current_fence.get()
    if fence is None:
        raise LeaseLost('Lead export requires a durable lease')
    job = db.execute(sa.select(jobs).where(jobs.c.id == fence.job_id, jobs.c.lease_token == fence.token,
        jobs.c.state == 'running', jobs.c.lease_until > sa.func.clock_timestamp())).mappings().first()
    if job is None:
        raise LeaseLost('Lead export lease expired')
    if (job['kind'] != 'lead.export' or job['payload'] != payload or payload.get('channel') not in CHANNELS
            or job['tenant'] != payload.get('owner_id')
            or job['resource'] != f"lead-export:{payload.get('lead_id')}:{payload.get('channel')}"):
        raise RejectedBeforeExternalIO('Lead export job binding changed')
    try:
        project = require_project(db, uuid.UUID(payload['project_id']), owner_id=uuid.UUID(payload['owner_id']))
    except Exception as exc:
        if isinstance(exc, LeaseLost): raise
        raise RejectedBeforeExternalIO('Lead project is no longer authorized') from None
    lead = db.get(models.Lead, uuid.UUID(payload['lead_id']), populate_existing=True, with_for_update=True)
    if not lead or lead.project_id != project.id or scope(project) != payload['scope_digest']:
        raise RejectedBeforeExternalIO('Lead or recipient settings changed')
    if lead.status not in (models.LeadStatus.VALID, models.LeadStatus.INVALID, models.LeadStatus.SPAM):
        raise RejectedBeforeExternalIO('Lead validation is not complete')
    return project, lead


@dataclass(frozen=True)
class Snapshot:
    channel: str
    destination: object = field(repr=False)
    body: object = field(repr=False)
    binding: str


def prepare(db, payload):
    project, lead = require_scope(db, payload)
    return snapshot_for(db, project, lead, payload['channel'])


def snapshot_for(db, project, lead, channel):
    """SQL-only payload construction shared with operator evidence verification."""
    if channel not in CHANNELS:
        raise RejectedBeforeExternalIO('Unsupported lead export channel')
    if getattr(lead, 'exported_to_' + channel):
        return None
    data = {column.name: getattr(lead, column.name) for column in models.Lead.__table__.columns
            if not column.name.startswith('exported_to_')
            and column.name not in ('form_data', 'client_ip', 'fingerprint', 'export_timestamp', 'updated_at')}
    data = json.loads(json.dumps(data, default=str, ensure_ascii=False))
    data['lead_id'] = str(lead.id)
    data['status'] = ('потенциальный спам' if lead.is_spam or lead.status == models.LeadStatus.SPAM
                      else 'заявка отклонена' if lead.status != models.LeadStatus.VALID
                      else 'проверено' if lead.is_verified else 'валидная заявка')
    if len(json.dumps(data, ensure_ascii=False).encode()) > 65536:
        raise RejectedBeforeExternalIO('Lead export exceeds the payload limit')
    if channel == 'crm':
        from lead_validator.services.crm_transport import target
        target(project.crm_webhook_url or '')
        destination, body = project.crm_webhook_url, data
    elif channel == 'email':
        from lead_validator.services.email_sender import email_sender
        if not email_sender.enabled:
            raise RejectedBeforeExternalIO('Lead email is not configured')
        try:
            destination = json.loads(project.email_recipients or '[]')
            if (not isinstance(destination, list) or not 1 <= len(destination) <= 20
                    or any(not isinstance(x, str) or len(x) > 254 or '@' not in x
                           or any(c in x for c in '\r\n') for x in destination)):
                raise ValueError()
        except Exception:
            raise RejectedBeforeExternalIO('Invalid bounded email recipient list') from None
        body = data
    elif channel == 'telegram':
        from lead_validator.services.telegram import telegram_notifier
        if not telegram_notifier.enabled or not telegram_notifier.token or not (project.telegram_chat_id or '').strip():
            raise RejectedBeforeExternalIO('Lead Telegram is not configured')
        destination = project.telegram_chat_id.strip()
        def label(value): return ' '.join(str(value or '—').split())[:200]
        body = '\n'.join([f'Заявка: {label(project.name)}', f"Статус: {data['status']}",
            f'Телефон: {label(lead.phone)}', f'Имя: {label(lead.name)}', f'Email: {label(lead.email)}',
            f'Причина: {label(lead.validation_reason)}', f'Источник: {label(lead.utm_source)}',
            f'Кампания: {label(lead.utm_campaign)}', f'ID: {lead.id}'])
    else:
        if not project.client_id or not project.enable_metrica_export or lead.status != models.LeadStatus.VALID or lead.is_spam:
            raise RejectedBeforeExternalIO('Lead Metrika export is not authorized')
        if not (lead.ym_uid or '').isascii() or not (lead.ym_uid or '').isdigit() or len(lead.ym_uid) > 32:
            raise RejectedBeforeExternalIO('A real Metrika client ID is required')
        integrations = db.scalars(sa.select(models.Integration).where(
            models.Integration.client_id == project.client_id,
            models.Integration.platform == models.IntegrationPlatform.YANDEX_DIRECT,
            models.Integration.connection_status == 'active').limit(2)).all()
        if len(integrations) != 1:
            raise RejectedBeforeExternalIO('Metrika requires one unambiguous project integration')
        integration = integrations[0]
        try:
            counters = json.loads(integration.selected_counters or '[]')
            if not isinstance(counters, list) or len(counters) != 1 or not str(counters[0]).isdigit():
                raise ValueError()
            token = security.decrypt_token(integration.access_token)
            if not token: raise ValueError()
        except Exception:
            raise RejectedBeforeExternalIO('Explicit Metrika token and one counter are required') from None
        destination = {'token': token, 'counter': str(counters[0]), 'integration_id': str(integration.id)}
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ClientId', 'Target', 'DateTime'])
        stamp = int(lead.created_at.replace(tzinfo=timezone.utc).timestamp()) if lead.created_at.tzinfo is None else int(lead.created_at.timestamp())
        for goal in ('качественный_лид', 'все_лиды'):
            writer.writerow([lead.ym_uid, goal, stamp])
        body = output.getvalue()
    return Snapshot(channel, destination, body, digest([destination, body]))


async def dispatch(snapshot):
    channel, destination, body = snapshot.channel, snapshot.destination, snapshot.body
    if channel == 'crm':
        from lead_validator.services.crm_transport import post
        return await delivery_outcome.in_thread(post, destination, body), None
    if channel == 'email':
        from lead_validator.services.email_sender import email_sender
        return await email_sender.send_lead_notification(destination, body), None
    if channel == 'telegram':
        from lead_validator.services.telegram import telegram_notifier
        return await telegram_notifier.send_message(body, parse_mode=None, chat_id=destination), None
    url = f"https://api-metrika.yandex.net/management/v1/counter/{destination['counter']}/offline_conversions/upload"
    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
        delivery_outcome.before_send()
        response = await client.post(url, headers={'Authorization': f"OAuth {destination['token']}"},
            files={'file': ('conversions.csv', body, 'text/csv')})
        delivery_outcome.response_received(response)
        if response.status_code != 200: return False, None
        uploading = response.json().get('uploading') or {}
        reference = uploading.get('id')
        # A 200 or partial CSV acknowledgement alone is not proof that both
        # goals were accepted. Matching to site visits is a later provider step.
        accepted = type(reference) is int and reference >= 0 and uploading.get('line_quantity') == 2
        return accepted, str(reference) if accepted else None


async def execute(factory, payload, *, sender=None):
    if not env_bool('LEAD_DELIVERY_GUARDS', False):
        raise RejectedBeforeExternalIO('Lead delivery guards are disabled')
    with factory.begin() as db:
        require_scope(db, payload)
        job_id = current_fence.get().job_id
        receipt = db.execute(sa.select(lead_exports).where(lead_exports.c.job_id == job_id).with_for_update()).mappings().first()
        if receipt:
            if receipt['state'] == 'sent': return {'accepted': True, 'replayed': True}
            if receipt['state'] == 'rejected': raise RejectedBeforeExternalIO('Previous export was rejected')
            raise RuntimeError('Previous export requires reconciliation; no resend')
        snapshot = prepare(db, payload)
        if snapshot is None: return {'accepted': True, 'replayed': True}
        db.execute(lead_exports.insert().values(job_id=job_id, scope_digest=payload['scope_digest'],
            body_digest=snapshot.binding, state='sending'))
    delivery_outcome.before_send()
    try:
        accepted, reference = await (sender or dispatch)(snapshot)
    except Exception:
        if delivery_outcome.outcome.get() != 'rejected':
            raise RuntimeError('Lead export outcome is uncertain; reconcile') from None
        accepted, reference = False, None
    if not accepted:
        if delivery_outcome.outcome.get() == 'rejected':
            with factory.begin() as db:
                db.execute(lead_exports.update().where(lead_exports.c.job_id == job_id)
                    .values(state='rejected', confirmed_at=sa.func.clock_timestamp()))
            raise RejectedBeforeExternalIO('Provider rejected lead export')
        raise RuntimeError('Lead export outcome is uncertain')
    with factory.begin() as db:
        try:
            project, lead = require_scope(db, payload)
            latest = prepare(db, payload)
            if latest is None or latest.binding != snapshot.binding:
                raise ValueError('Lead export inputs changed')
        except Exception:
            raise RuntimeError('Lead scope changed after sending; reconcile') from None
        setattr(lead, 'exported_to_' + snapshot.channel, True)
        lead.export_timestamp = db.scalar(sa.select(sa.func.clock_timestamp()))
        db.execute(lead_exports.update().where(lead_exports.c.job_id == job_id).values(
            state='sent', provider_ref=reference, confirmed_at=sa.func.clock_timestamp()))
    return {'accepted': True}
