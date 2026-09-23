from types import SimpleNamespace
from unittest.mock import AsyncMock
import time
import smtplib
import socket

import pytest
import sqlalchemy as sa

from core import models, delivery_outcome
from core.job_fence import fenced_job
from automation import lead_export_work as work, work_ledger as ledger
from automation.work_tables import jobs, lead_exports
from automation.work_errors import RejectedBeforeExternalIO
from lead_validator.services import project_intake as intake
from lead_validator.schemas import LeadInput
from tests.test_durable_work import pg, claim, expire
from tests.test_lead_scoped_stats import scope


@pytest.fixture
def prepared(scope, monkeypatch):
    s = scope
    monkeypatch.setenv('LEAD_DELIVERY_GUARDS', 'true')
    monkeypatch.setenv('DURABLE_TASKS', 'true')
    with s.factory.begin() as db:
        p = db.get(models.PhoneProject, s.project)
        p.crm_webhook_url = 'https://crm.example.test/lead'
    with s.factory() as db:
        lead = LeadInput(phone='+79000000001')
        context = intake.begin(db, s.project, lead, form_data=None, user_agent=None, referer=None, key='test')
        context.finish(lead, True, 'passed', time.time(), None, {})
        row = db.execute(sa.select(jobs)).mappings().one()
        s.job, s.payload, s.lead = row['id'], row['payload'], context.lead_id
    s.token = claim(s.factory, s.job)['lease_token']
    return s


async def execute(s, sender):
    with fenced_job(s.job, s.token):
        return await work.execute(s.factory, s.payload, sender=sender)


def receipt(s):
    with s.factory() as db:
        return db.execute(sa.select(lead_exports)).mappings().first()


@pytest.mark.asyncio
async def test_receipt_committed_before_io_confirmation_and_replay(prepared):
    s = prepared
    async def send(snapshot):
        assert s.engine.pool.checkedout() == 0
        assert receipt(s)['state'] == 'sending'
        assert snapshot.channel == 'crm' and snapshot.body['lead_id'] == str(s.lead)
        assert 'exported_to_crm' not in snapshot.body and 'form_data' not in snapshot.body
        return True, None
    sender = AsyncMock(side_effect=send)
    assert await execute(s, sender) == {'accepted': True}
    assert await execute(s, sender) == {'accepted': True, 'replayed': True}
    sender.assert_awaited_once()
    with s.factory() as db: assert db.get(models.Lead, s.lead).exported_to_crm
    assert receipt(s)['state'] == 'sent'
    expire(s.factory, s.job)
    with s.factory.begin() as db: ledger.recover_expired(db)
    with s.factory() as db: assert db.scalar(sa.select(jobs.c.state)) == 'succeeded'


@pytest.mark.asyncio
@pytest.mark.parametrize('mode', ['timeout', 'partial', 'rejected', 'settings', 'lease'])
async def test_no_blind_resend_after_ambiguous_or_rejected_delivery(prepared, mode):
    s = prepared
    async def send(snapshot):
        assert s.engine.pool.checkedout() == 0
        if mode == 'timeout': raise TimeoutError('synthetic')
        if mode == 'rejected':
            delivery_outcome.rejected()
            return False, None
        if mode == 'settings':
            with s.factory.begin() as db: db.get(models.PhoneProject, s.project).crm_webhook_url = 'https://changed.example.test/'
        if mode == 'lease':
            # Use a direct connection: this simulates a separate watchdog,
            # not the current fenced worker attempting to expire itself.
            with s.engine.begin() as db:
                db.execute(jobs.update().where(jobs.c.id == s.job).values(lease_until=sa.func.now() - sa.text("interval '1 second'")))
        return mode != 'partial', None
    sender = AsyncMock(side_effect=send)
    with pytest.raises((RuntimeError, RejectedBeforeExternalIO)): await execute(s, sender)
    with pytest.raises((RuntimeError, RejectedBeforeExternalIO)): await execute(s, sender)
    sender.assert_awaited_once()
    with s.factory() as db: assert not db.get(models.Lead, s.lead).exported_to_crm
    assert receipt(s)['state'] == ('rejected' if mode == 'rejected' else 'sending')


@pytest.mark.asyncio
async def test_other_channel_ack_does_not_invalidate_body(prepared):
    s = prepared
    async def send(snapshot):
        with s.factory.begin() as db:
            record = db.get(models.Lead, s.lead)
            record.exported_to_telegram = True
            record.export_timestamp = sa.func.now()
        return True, None
    assert await execute(s, send) == {'accepted': True}


@pytest.mark.asyncio
@pytest.mark.parametrize('change', ['owner', 'disabled', 'recipient', 'payload'])
async def test_scope_changes_prevent_first_dispatch(prepared, change):
    s = prepared
    with s.factory.begin() as db:
        project = db.get(models.PhoneProject, s.project)
        if change == 'owner': project.owner_id = s.other
        if change == 'disabled': project.is_active = False
        if change == 'recipient': project.crm_webhook_url = 'https://other.example.test/'
    if change == 'payload': s.payload = {**s.payload, 'owner_id': str(s.other)}
    sender = AsyncMock()
    with pytest.raises(RejectedBeforeExternalIO): await execute(s, sender)
    sender.assert_not_awaited()
    assert receipt(s) is None


@pytest.mark.parametrize('url', ['http://example.test', 'https://user:password@example.test', 'https://example.test:8443', 'https://example.test/#fragment'])
def test_crm_rejects_unsafe_targets(url):
    from lead_validator.services.crm_transport import target
    with pytest.raises(RejectedBeforeExternalIO): target(url)


@pytest.mark.parametrize('ip', ['127.0.0.1', '10.77.0.1', '169.254.169.254', '::1', '::ffff:127.0.0.1', 'ff02::1'])
def test_crm_never_connects_to_private_or_mixed_dns(monkeypatch, ip):
    from lead_validator.services import crm_transport as crm
    monkeypatch.setattr(crm.socket, 'getaddrinfo', lambda *a, **k: [(2, 1, 6, '', ('8.8.8.8', 443)), (2, 1, 6, '', (ip, 443))])
    monkeypatch.setattr(crm.socket, 'create_connection', lambda *a, **k: pytest.fail('Unsafe connect'))
    with pytest.raises(RejectedBeforeExternalIO): crm.post('https://crm.example.test/', {'lead_id': 'test'})


@pytest.mark.asyncio
@pytest.mark.parametrize('mode', ['ok', 'partial', 'all_refused', 'lost_ack', 'connect'])
async def test_smtp_preserves_thread_evidence_and_partial_acceptance(monkeypatch, mode):
    from lead_validator.services.email_sender import EmailSender
    sender = EmailSender()
    sender.enabled, sender.host, sender.port, sender.from_addr = True, 'smtp.example.test', 25, 'test@example.test'
    sender.use_tls, sender.user = False, None
    class SMTP:
        def __init__(self, *a, **k):
            if mode == 'connect': raise OSError('connect failed')
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def send_message(self, msg):
            if mode == 'all_refused': raise smtplib.SMTPRecipientsRefused({'test': (550, b'no')})
            if mode == 'lost_ack': raise TimeoutError('ack lost')
            return {'test': (550, b'no')} if mode == 'partial' else {}
    monkeypatch.setattr(smtplib, 'SMTP', SMTP)
    delivery_outcome.before_send()
    result = await sender.send_lead_notification(['test@example.test'], {'phone': 'synthetic'})
    assert result == (mode == 'ok')
    assert delivery_outcome.outcome.get() == ('rejected' if mode in ('connect', 'all_refused') else 'unknown')


@pytest.mark.asyncio
@pytest.mark.parametrize('provider', ['turnstile', 'recaptcha', 'smartcaptcha'])
@pytest.mark.parametrize('mode', ['ok', 'invalid', 'timeout', 'http', 'missing_key', 'malformed'])
async def test_project_captcha_uses_only_project_key(monkeypatch, provider, mode):
    from fastapi import HTTPException
    from lead_validator.services import project_captcha as captcha
    project = SimpleNamespace(captcha_provider=provider, captcha_secret_key='project-only-secret' if mode != 'missing_key' else None)
    calls = []
    class Client:
        def __init__(self, **kw): assert kw['follow_redirects'] is False
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, *, data):
            calls.append(url)
            assert 'project-only-secret' not in url and data['secret'] == 'project-only-secret'
            if mode == 'timeout': raise TimeoutError('synthetic')
            return SimpleNamespace(status_code=503 if mode == 'http' else 200,
                json=lambda: {} if mode == 'malformed' else {'success': mode == 'ok', 'status': 'ok' if mode == 'ok' else 'failed'})
    monkeypatch.setattr(captcha.httpx, 'AsyncClient', Client)
    if mode in ('timeout', 'http', 'missing_key', 'malformed'):
        with pytest.raises(HTTPException) as error: await captcha.validate(project, 'token', '127.0.0.1')
        assert error.value.status_code == 503
    else:
        result = await captcha.validate(project, 'token', '127.0.0.1')
        assert result[0] == (mode == 'ok')
    assert len(calls) == (0 if mode == 'missing_key' else 1)


@pytest.mark.asyncio
@pytest.mark.parametrize('mode', ['ok', 'partial', 'malformed', 'http'])
async def test_metrika_single_upload_acknowledgement(monkeypatch, mode):
    calls = []
    class Client:
        def __init__(self, **kw): assert kw['follow_redirects'] is False
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, *, headers, files):
            calls.append(url)
            assert url == 'https://api-metrika.yandex.net/management/v1/counter/123/offline_conversions/upload'
            assert headers['Authorization'] == 'OAuth synthetic'
            assert files['file'][1].splitlines() == ['ClientId,Target,DateTime', '123,goal1,100', '123,goal2,100']
            return SimpleNamespace(status_code=403 if mode == 'http' else 200,
                json=lambda: {} if mode == 'malformed' else {'uploading': {'id': 42, 'line_quantity': 1 if mode == 'partial' else 2}})
    monkeypatch.setattr(work.httpx, 'AsyncClient', Client)
    snapshot = work.Snapshot('metrica', {'token': 'synthetic', 'counter': '123'},
        'ClientId,Target,DateTime\n123,goal1,100\n123,goal2,100\n', 'digest')
    accepted, ref = await work.dispatch(snapshot)
    assert accepted == (mode == 'ok') and ref == ('42' if mode == 'ok' else None)
    assert len(calls) == 1


@pytest.mark.parametrize('mode', ['ok', 'ambiguous', 'foreign', 'no_token', 'no_client_id'])
def test_metrika_snapshot_requires_bound_integration(prepared, monkeypatch, mode):
    import json
    from core import security
    s = prepared
    with s.factory.begin() as db:
        client = models.Client(owner_id=s.owner, name='Synthetic')
        db.add(client); db.flush()
        project = db.get(models.PhoneProject, s.project)
        project.client_id = client.id
        record = db.get(models.Lead, s.lead)
        record.ym_uid = '' if mode == 'no_client_id' else '1234567'
        integration = models.Integration(client_id=client.id, platform=models.IntegrationPlatform.YANDEX_DIRECT,
            connection_status='active', access_token=security.encrypt_token('project-token'), selected_counters=json.dumps([123]))
        db.add(integration)
        if mode == 'ambiguous': integration.selected_counters = '[123,456]'
        if mode == 'no_token': integration.access_token = None
        if mode == 'foreign': client.owner_id = s.other
        db.flush()
        s.payload = {**s.payload, 'channel': 'metrica', 'scope_digest': intake.scope(project)}
        db.execute(jobs.update().where(jobs.c.id == s.job).values(payload=s.payload, resource=f'lead-export:{s.lead}:metrica'))
    with fenced_job(s.job, s.token), s.factory() as db:
        if mode != 'ok':
            with pytest.raises(RejectedBeforeExternalIO): work.prepare(db, s.payload)
        else:
            snapshot = work.prepare(db, s.payload)
            assert snapshot.destination['token'] == 'project-token'
            assert snapshot.destination['counter'] == '123'
            assert len(snapshot.body.splitlines()) == 3


def test_crm_pins_public_address_and_keeps_tls_hostname(monkeypatch):
    from lead_validator.services import crm_transport as crm
    from unittest.mock import Mock
    dns = Mock(return_value=[(2, 1, 6, '', ('8.8.8.8', 443))])
    raw, secured = Mock(), Mock()
    connect = Mock(return_value=raw)
    context = Mock()
    context.wrap_socket.return_value = secured
    monkeypatch.setattr(crm.socket, 'getaddrinfo', dns)
    monkeypatch.setattr(crm.socket, 'create_connection', connect)
    monkeypatch.setattr(crm.ssl, 'create_default_context', lambda: context)
    def request(self, method, path, *, body, headers):
        assert self.sock is secured and self.host == 'crm.example.test'
        assert method == 'POST' and path == '/lead?event=1'
        assert headers['Idempotency-Key'] == 'synthetic'
    monkeypatch.setattr(crm.http.client.HTTPSConnection, 'request', request)
    monkeypatch.setattr(crm.http.client.HTTPSConnection, 'getresponse', lambda self: SimpleNamespace(status=200))
    assert crm.post('https://crm.example.test/lead?event=1', {'lead_id': 'synthetic'})
    dns.assert_called_once()
    connect.assert_called_once_with(('8.8.8.8', 443), timeout=10)
    context.wrap_socket.assert_called_once_with(raw, server_hostname='crm.example.test')
    secured.close.assert_called_once()
