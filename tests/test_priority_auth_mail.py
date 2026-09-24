import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from backend_api.services import auth_mail as mail


@pytest.fixture
def transport(monkeypatch):
    cfg = SimpleNamespace(
        smtp=SimpleNamespace(enabled=True, host='smtp.go2.unisender.ru', port=587,
                             user='synthetic', password='synthetic',
                             from_addr='noreply@example.test', use_tls=True),
        unisender=SimpleNamespace(api_key='synthetic', api_url='https://mail.example.test/api',
                                  from_name='AdMirra'),
    )
    monkeypatch.setattr(mail, 'get_config', lambda: cfg)
    post = Mock(return_value=httpx.Response(200, json={'status': 'success', 'job_id': 'synthetic'}))
    client = Mock()
    client.__enter__ = Mock(return_value=SimpleNamespace(post=post))
    client.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(mail.httpx, 'Client', Mock(return_value=client))
    smtp = Mock(return_value=True)
    monkeypatch.setattr(mail, '_send_sync', smtp)
    return cfg, post, smtp


@pytest.mark.parametrize('sender', ['send_login_otp_email', 'send_verification_link_email', 'send_reset_password_email'])
def test_only_requested_access_mail_bypasses_unavailability(transport, sender):
    cfg, post, smtp = transport
    assert asyncio.run(getattr(mail, sender)('user@example.test', 'synthetic-secret')) is True
    message = post.call_args.kwargs['json']['message']
    assert message['bypass_global'] == message['bypass_unavailable'] == 1
    assert message['bypass_unsubscribed'] == message['bypass_complained'] == 0
    assert message['track_links'] == message['track_read'] == 0
    assert message['from_email'] == cfg.smtp.from_addr
    assert message['recipients'] == [{'email': 'user@example.test'}]
    assert 'synthetic-secret' in message['body']['plaintext']
    smtp.assert_not_called()


@pytest.mark.parametrize('sender,args', [
    ('send_welcome_email', ('user@example.test', 'Name')),
    ('send_staff_invite_email', ('user@example.test', 'https://example.test', 'staff')),
    ('send_support_idea_email', ('support@example.test', 'Subject', 'Message', 'user@example.test')),
])
def test_other_mail_keeps_existing_suppression_policy(transport, sender, args):
    _, post, smtp = transport
    assert asyncio.run(getattr(mail, sender)(*args)) is True
    post.assert_not_called()
    smtp.assert_called_once()


@pytest.mark.parametrize('response', [
    httpx.Response(200, json={'status': 'success', 'job_id': 'test', 'failed_emails': {'user@example.test': 'unsubscribed'}}),
    httpx.Response(200, json={'status': 'success'}),
    httpx.Response(200, json={'status': 'error', 'message': 'private-provider-content'}),
    httpx.Response(403, json={'status': 'success', 'job_id': 'test'}),
    httpx.Response(502, text='private-provider-content'),
])
def test_rejection_does_not_report_success_or_retry_smtp(transport, response, caplog):
    _, post, smtp = transport
    post.return_value = response
    assert not mail._send_priority_auth_email('user@example.test', 'Subject', 'private-body')
    smtp.assert_not_called()
    assert 'private-provider-content' not in caplog.text
    assert 'private-body' not in caplog.text
    assert 'user@example.test' not in caplog.text


def test_ambiguous_timeout_never_falls_back_or_leaks_secrets(transport, caplog):
    _, post, smtp = transport
    post.side_effect = httpx.ReadTimeout('private-code-and-email')
    assert not mail._send_priority_auth_email('user@example.test', 'Subject', 'body')
    post.assert_called_once()
    smtp.assert_not_called()
    assert 'private-code-and-email' not in caplog.text


@pytest.mark.parametrize('missing', ['disabled', 'api_key', 'from_addr'])
def test_missing_config_does_not_send(transport, missing):
    cfg, post, smtp = transport
    if missing == 'disabled':
        cfg.smtp.enabled = False
    elif missing == 'api_key':
        cfg.unisender.api_key = ''
    else:
        cfg.smtp.from_addr = ''
    assert not mail._send_priority_auth_email('user@example.test', 'Subject', 'body')
    post.assert_not_called()
    smtp.assert_not_called()


def test_non_unisender_smtp_is_unchanged(transport):
    cfg, post, smtp = transport
    cfg.smtp.host = 'smtp.example.test'
    assert mail._send_priority_auth_email('user@example.test', 'Subject', 'body')
    post.assert_not_called()
    smtp.assert_called_once()
