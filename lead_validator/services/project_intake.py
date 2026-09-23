"""Short SQL admission -> detached validation -> atomic decision + export outbox.

An interrupted admission is held, never silently revalidated or re-exported.
This path is opt-in until all API/worker releases have its schema and handlers.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
import hashlib
import hmac
import json
import re
from types import SimpleNamespace
import uuid

from fastapi import HTTPException
import sqlalchemy as sa

from core import models, security
from core.runtime import env_bool, env_int
from automation.work_ledger import submit
from lead_validator.config import settings
from lead_validator.schemas import ValidationResult
from lead_validator.services.scoped_placements import is_blacklisted


def digest(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str, separators=(',', ':')).encode()
    return hmac.new(security.SECRET_KEY.encode(), raw, hashlib.sha256).hexdigest()


def scope(project):
    return digest({column.name: getattr(project, column.name) for column in models.PhoneProject.__table__.columns})


def require_project(db, project_id, *, owner_id=None):
    project = db.get(models.PhoneProject, project_id, populate_existing=True, with_for_update=True)
    if (not project or not project.is_active or owner_id is not None and project.owner_id != owner_id):
        raise HTTPException(409, 'Проект изменён или недоступен')
    if project.client_id:
        client = db.get(models.Client, project.client_id, populate_existing=True, with_for_update=True)
        if not client or client.owner_id != project.owner_id or client.status != models.ClientStatus.ACTIVE:
            raise HTTPException(409, 'Связанный рекламный проект недоступен')
    return project


def release_read(db):
    if db.new or db.dirty or db.deleted:
        raise RuntimeError('Lead admission requires a read-only request session')
    db.rollback()


async def reserve_intake(owner_id):
    from lead_validator.services.diagnostics import _RESERVE
    from lead_validator.services.redis_service import redis_service
    async def reserve():
        client = await redis_service._get_client()
        if client is None:
            raise RuntimeError('Limiter unavailable')
        return await client.eval(_RESERVE, 3, f'lead:intake:{owner_id}:minute',
            f'lead:intake:{owner_id}:hour', 'lead:intake:global:minute',
            env_int('LEAD_INTAKE_PER_MINUTE', 60, 1, 10000), 60,
            env_int('LEAD_INTAKE_PER_HOUR', 1000, 1, 100000), 3600,
            env_int('LEAD_INTAKE_GLOBAL_PER_MINUTE', 600, 1, 100000), 60)
    try:
        allowed = await asyncio.wait_for(reserve(), timeout=2)
    except Exception:
        raise HTTPException(503, 'Приём заявок временно недоступен') from None
    if allowed != 1:
        raise HTTPException(429, 'Лимит приёма заявок исчерпан',
                            headers={'Retry-After': str(max(1, -int(allowed)))})


@dataclass
class Context:
    db: object = field(repr=False)
    project: object = field(repr=False)
    intake_id: uuid.UUID
    lead_id: uuid.UUID
    scope_digest: str
    blocked: bool
    form_data: dict | None = field(repr=False)

    async def reject(self, lead, reason, start_time, dadata=None, **_):
        return self.finish(lead, False, reason, start_time, dadata, {})

    async def accept(self, lead, dadata, start_time, note=None, **_):
        from lead_validator.services.lead_enrichment import enrich
        values = await enrich(lead, dadata, self.project, self.form_data)
        return self.finish(lead, True, note or 'passed_all_checks', start_time, dadata, values)

    def finish(self, lead, accepted, reason, start_time, dadata, values):
        import time
        db = self.db
        release_read(db)
        try:
            project = require_project(db, self.project.id, owner_id=self.project.owner_id)
            intake = db.get(models.LeadIntake, self.intake_id, with_for_update=True)
            now = db.scalar(sa.select(sa.func.clock_timestamp()))
            if not intake or intake.state != 'processing':
                raise HTTPException(409, 'Решение по заявке уже зафиксировано')
            if scope(project) != self.scope_digest or now >= intake.deadline:
                intake.state = 'held'
                db.commit()
                raise HTTPException(409, 'Настройки изменились или истекло время проверки')
            record = db.get(models.Lead, self.lead_id, with_for_update=True)
            if not record or record.project_id != project.id:
                raise HTTPException(409, 'Заявка недоступна')
            if record.status != models.LeadStatus.PENDING:
                intake.state = 'held'
                db.commit()
                raise HTTPException(409, 'Статус заявки изменён во время проверки')
            if accepted and settings.UTM_VALIDATION_ENABLED and is_blacklisted(db,
                    project.owner_id, project.id, lead.utm_source, lead.utm_campaign, lead.utm_content):
                accepted, reason = False, 'utm_invalid:blacklisted_placement'
            # Serializing final decisions on the project prevents two concurrent
            # admissions of the same phone/email from both becoming valid.
            if accepted:
                digits = ''.join(filter(str.isdigit, lead.phone))
                matches = [models.Lead.phone.in_([digits, '+' + digits])]
                contact_email = values.get('email') or lead.email
                if contact_email:
                    matches.append(sa.func.lower(sa.func.trim(models.Lead.email)) == contact_email.strip().lower())
                duplicate = db.scalar(sa.select(models.Lead.id).where(
                    models.Lead.project_id == project.id, models.Lead.id != record.id,
                    models.Lead.status == models.LeadStatus.VALID, models.Lead.is_spam.is_(False),
                    models.Lead.created_at >= now - timedelta(seconds=settings.PHONE_DUPLICATE_TTL_SEC),
                    sa.or_(*matches)).limit(1))
                if duplicate:
                    accepted, reason = False, 'duplicate_contact'
            # Preserve this fixed internal code: blacklist-generated rejections
            # must not train/reinforce the placement blacklist itself.
            if reason != 'utm_invalid:blacklisted_placement':
                reason = re.sub(r'[^a-zA-Z0-9_\-.]', '_', reason.split(':', 1)[0])[:100]
            record.is_valid = accepted
            record.is_spam = not accepted and 'spam' in reason.lower()
            record.status = (models.LeadStatus.VALID if accepted else
                             models.LeadStatus.SPAM if record.is_spam else models.LeadStatus.INVALID)
            record.validation_reason = reason
            for name in ('type', 'provider', 'region', 'city'):
                setattr(record, 'phone_' + name, getattr(dadata, name, None))
            record.dadata_qc = getattr(dadata, 'qc', None)
            for name, value in values.items():
                setattr(record, name, value)
            result = ValidationResult(success=accepted, lead_id=str(record.id),
                rejection_reason=None if accepted else reason,
                execution_time_ms=round((time.time() - start_time) * 1000, 2),
                phone_type=record.phone_type, phone_provider=record.phone_provider,
                phone_region=record.phone_region, dadata_qc=record.dadata_qc,
                lead_score=record.lead_score, qualification_tier=record.qualification_tier)
            channels = []
            if project.crm_webhook_url: channels.append('crm')
            if project.email_recipients: channels.append('email')
            if project.telegram_chat_id: channels.append('telegram')
            if accepted and project.enable_metrica_export and lead.ym_uid: channels.append('metrica')
            for channel in channels:
                submit(db, kind='lead.export', queue='reports',
                    key=f'lead-export:{record.id}:{channel}', resource=f'lead-export:{record.id}:{channel}',
                    tenant=project.owner_id, replay_safe=False, max_attempts=1,
                    payload={'project_id': str(project.id), 'owner_id': str(project.owner_id),
                        'lead_id': str(record.id), 'scope_digest': self.scope_digest, 'channel': channel})
            intake.state, intake.result = 'done', result.model_dump()
            db.commit()  # Decision and every recipient job are all-or-nothing.
            return result
        except BaseException:
            db.rollback()
            raise


def begin(db, project_id, lead, *, form_data, user_agent, referer, key=None, authorization_digest=None):
    release_read(db)
    data = lead.model_dump()
    # Strict bounds before persisting user-controlled form data or queueing work.
    encoded = json.dumps({'lead': data, 'form': form_data}, ensure_ascii=False)
    if len(encoded.encode()) > 65536 or any(len(str(v)) > 4096 for v in data.values() if v is not None):
        raise HTTPException(413, 'Слишком большой запрос')
    for column in models.Lead.__table__.columns:
        limit = getattr(column.type, 'length', None)
        if limit and data.get(column.name) is not None and len(str(data[column.name])) > limit:
            raise HTTPException(413, 'Поле заявки превышает допустимую длину')
    if key is not None and (not isinstance(key, str) or not 1 <= len(key) <= 200):
        raise HTTPException(422, 'Некорректный Idempotency-Key')
    # Provider retries may arrive through another egress IP; transport metadata
    # must not change the identity of an otherwise identical submitted event.
    fingerprint = digest({'lead': {k: v for k, v in data.items() if k != 'client_ip'}, 'form': form_data})
    key_digest = digest(['explicit', key]) if key else digest(['body', fingerprint])
    try:
        project = require_project(db, project_id)
        if authorization_digest is not None and scope(project) != authorization_digest:
            raise HTTPException(409, 'Настройки проекта изменены после авторизации запроса')
        if project.enable_bitrix_check:
            raise HTTPException(409, 'Для Bitrix требуется проектная привязка; общая CRM недоступна')
        current = db.scalar(sa.select(models.LeadIntake).where(models.LeadIntake.project_id == project.id,
            models.LeadIntake.owner_id == project.owner_id, models.LeadIntake.key_digest == key_digest))
        if current:
            if current.payload_digest != fingerprint:
                raise HTTPException(409, 'Idempotency-Key уже использован для другого запроса')
            if current.state in ('done', 'closed'):
                return ValidationResult.model_validate(current.result)
            raise HTTPException(409, 'Проверка выполняется или требует сверки; повторная обработка запрещена')
        snapshot = SimpleNamespace(**{c.name: getattr(project, c.name) for c in models.PhoneProject.__table__.columns})
        lead_id, intake_id = uuid.uuid4(), uuid.uuid4()
        now = db.scalar(sa.select(sa.func.clock_timestamp()))
        columns = ('phone', 'email', 'name', 'utm_source', 'utm_medium', 'utm_campaign',
                   'utm_content', 'utm_term', 'client_ip', 'geo_country', 'browser_timezone', 'ym_uid')
        db.add(models.Lead(id=lead_id, project_id=project.id, **{k: data[k] for k in columns},
            user_agent=(user_agent or '')[:512] or None, referer=(referer or '')[:2048] or None,
            form_data=json.dumps(form_data, ensure_ascii=False) if form_data else None,
            status=models.LeadStatus.PENDING, is_valid=False))
        db.flush()
        bound = scope(snapshot)
        db.add(models.LeadIntake(id=intake_id, project_id=project.id, owner_id=project.owner_id,
            lead_id=lead_id, key_digest=key_digest, payload_digest=fingerprint, scope_digest=bound,
            state='processing', deadline=now + timedelta(minutes=5)))
        blocked = is_blacklisted(db, project.owner_id, project.id, lead.utm_source, lead.utm_campaign, lead.utm_content)
        db.commit()
        return Context(db, snapshot, intake_id, lead_id, bound, blocked, form_data)
    finally:
        db.rollback()


async def run(validator, lead, client_ip, user_agent, referer, project_id, db, form_data,
              skip_request_validation, skip_antibot_validation, key, *, authorization_digest=None):
    if not env_bool('DURABLE_TASKS', False) or db is None:
        raise HTTPException(503, 'Надёжный приём заявок не настроен')
    if client_ip: lead.client_ip = client_ip
    release_read(db)
    try:
        project = require_project(db, project_id)
        if authorization_digest is not None and scope(project) != authorization_digest:
            raise HTTPException(409, 'Настройки проекта изменены после авторизации запроса')
        owner_id = project.owner_id
    finally:
        db.rollback()
    await reserve_intake(owner_id)
    context = begin(db, project_id, lead, form_data=form_data, user_agent=user_agent, referer=referer,
                    key=key, authorization_digest=authorization_digest)
    if isinstance(context, ValidationResult):
        return context
    return await validator.validate(lead, client_ip, user_agent, referer, project_id, db, form_data,
        skip_request_validation, skip_antibot_validation, _context=context)
