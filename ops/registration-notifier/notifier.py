"""Registration outbox consumer. No application imports, credentials or PII logs.

Unknown Telegram delivery outcomes are held for manual reconciliation, not
blindly retried. Explicit 429 and connection failures before sending may retry.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import re
import signal
import socket
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.request
import uuid
from zoneinfo import ZoneInfo

LOG = logging.getLogger('registration_notifier')
MAX_ATTEMPTS = 12
ALLOWED_BASES = {'https://api.telegram.org', 'http://10.78.0.3:8080/telegram'}


def clean(value, limit=180):
    text = ''.join(c if unicodedata.category(c)[0] != 'C' else ' ' for c in str(value or ''))
    return ' '.join(text.split())[:limit]


def format_message(user):
    name = clean(' '.join(filter(None, [user.get('first_name'), user.get('last_name')])))
    name = name or clean(user.get('username')) or 'не указано'
    email = clean(user.get('email'))
    if email.partition('@')[2].lower() in {'vk-oauth.admirra.ru', clean(user.get('synthetic_domain')).lower()}:
        email = ''
    providers = user.get('providers') or []
    method = ', '.join({'yandex': 'Яндекс ID', 'vk': 'VK ID', 'max': 'MAX'}.get(p, clean(p)) for p in providers)
    source = clean(user.get('registration_utm_source')) or 'не определён (UTM не переданы)'
    lines = [
        '🆕 Новая регистрация в AdMirra', '',
        f'Имя: {name}', f'Email: {email or "не предоставлен"}',
        f'Телефон: {clean(user.get("phone")) or "не предоставлен"}',
        f'Способ: {method or "Email / создание аккаунта на сайте"}',
        f'Источник: {source}',
    ]
    for key, label in [('registration_utm_medium', 'UTM medium'), ('registration_utm_campaign', 'Кампания')]:
        if clean(user.get(key)):
            lines.append(f'{label}: {clean(user[key])}')
    if not providers:
        lines.append('Email подтверждён: ' + ('да' if user.get('email_verified') else 'нет'))
    created = user.get('created_at')
    if isinstance(created, datetime):
        lines.append('Регистрация: ' + created.astimezone(ZoneInfo('Europe/Moscow')).strftime('%d.%m.%Y %H:%M МСК'))
    lines.append('ID: ' + clean(user.get('id'), 36))
    return '\n'.join(lines)


@dataclass(frozen=True)
class Outcome:
    state: str
    code: str = ''
    delay: int = 0
    message_id: int | None = None


def response_outcome(status, body):
    try:
        data = json.loads(body)
        if not isinstance(data, dict):
            raise ValueError()
    except (ValueError, TypeError):
        return Outcome('uncertain', 'invalid_response')
    message_id = (data.get('result') or {}).get('message_id') if isinstance(data.get('result'), dict) else None
    if status == 200 and data.get('ok') is True and type(message_id) is int:
        return Outcome('sent', message_id=message_id)
    if data.get('ok') is False and data.get('error_code') == 429:
        parameters = data.get('parameters')
        delay = parameters.get('retry_after', 60) if isinstance(parameters, dict) else 60
        if type(delay) is not int:
            delay = 60
        return Outcome('pending', 'rate_limit', max(5, min(delay, 86400)))
    if data.get('ok') is False and data.get('error_code') in (400, 401, 403, 404):
        return Outcome('failed', 'telegram_' + str(data['error_code']))
    return Outcome('uncertain', 'http_' + str(status))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def send_message(base, token, chat_id, message):
    if base not in ALLOWED_BASES or not re.fullmatch(r'[0-9]+:[A-Za-z0-9_-]+', token):
        raise ValueError('Invalid Telegram configuration')
    payload = json.dumps({'chat_id': chat_id, 'text': message,
                          'link_preview_options': {'is_disabled': True}}, ensure_ascii=False).encode()
    request = urllib.request.Request(base + '/bot' + token + '/sendMessage', data=payload,
                                     headers={'Content-Type': 'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request, timeout=15) as response:
            return response_outcome(response.status, response.read(16384))
    except urllib.error.HTTPError as exc:
        try:
            return response_outcome(exc.code, exc.read(16384))
        finally:
            exc.close()
    except urllib.error.URLError as exc:
        # These failures prove that the initial connection was not established.
        if isinstance(exc.reason, (ConnectionRefusedError, socket.gaierror)):
            return Outcome('pending', 'connect_failed', 60)
        return Outcome('uncertain', 'transport_error')
    except (TimeoutError, OSError, ValueError):
        return Outcome('uncertain', 'transport_error')


@contextmanager
def connect(config):
    import psycopg2
    from psycopg2.extras import RealDictCursor
    db = psycopg2.connect(Path(config['database_file']).read_text().strip(),
                         connect_timeout=5, application_name='registration-notifier',
                         options='-c statement_timeout=5000 -c lock_timeout=1000',
                         cursor_factory=RealDictCursor)
    try:
        with db:
            yield db
    finally:
        db.close()


def claim(db):
    with db.cursor() as cur:
        cur.execute("""UPDATE registration_notifier.outbox SET state='uncertain',
            error_code='expired_send', finished_at=clock_timestamp(), lease_token=NULL
            WHERE state='sending' AND lease_until < clock_timestamp()""")
        token = str(uuid.uuid4())
        cur.execute("""WITH next AS (
            SELECT user_id FROM registration_notifier.outbox
            WHERE state='pending' AND available_at <= clock_timestamp()
            ORDER BY available_at, created_at FOR UPDATE SKIP LOCKED LIMIT 1)
            UPDATE registration_notifier.outbox q SET state='sending', attempts=attempts+1,
            lease_token=%s, lease_until=clock_timestamp()+interval '120 seconds'
            FROM next WHERE q.user_id=next.user_id RETURNING q.user_id, q.attempts""", (token,))
        job = cur.fetchone()
        if not job:
            return None
        cur.execute("""SELECT u.id, u.first_name, u.last_name, u.username, u.email, u.phone,
            u.created_at, u.email_verified, u.registration_utm_source,
            u.registration_utm_medium, u.registration_utm_campaign,
            ARRAY(SELECT i.provider FROM public.user_oauth_identities i
                WHERE i.user_id=u.id ORDER BY i.created_at, i.provider) AS providers
            FROM public.users u WHERE u.id=%s""", (job['user_id'],))
        user = cur.fetchone()
        return dict(job, token=token, user=dict(user) if user else None)


def finish(db, job, outcome):
    state = outcome.state
    if state == 'pending' and job['attempts'] >= MAX_ATTEMPTS:
        state = 'failed'
    with db.cursor() as cur:
        cur.execute("""UPDATE registration_notifier.outbox SET state=%s, error_code=%s,
            message_id=%s, lease_token=NULL, lease_until=NULL,
            available_at=clock_timestamp()+(%s * interval '1 second'),
            finished_at=CASE WHEN %s='pending' THEN NULL ELSE clock_timestamp() END
            WHERE user_id=%s AND state='sending' AND lease_token=%s""",
            (state, outcome.code or None, outcome.message_id, outcome.delay, state, job['user_id'], job['token']))
        if cur.rowcount != 1:
            LOG.error('Delivery finalization lost claim')
    return state


def tick(config, sender=send_message, factory=connect):
    with factory(config) as db:
        job = claim(db)
    if job is None:
        return False
    if not job['user']:
        outcome = Outcome('failed', 'user_deleted')
    else:
        job['user']['synthetic_domain'] = config.get('synthetic_domain', 'vk-oauth.admirra.ru')
        token = Path(config['token_file']).read_text().strip()
        outcome = sender(config['api_base'], token, config['chat_id'], format_message(job['user']))
    with factory(config) as db:
        state = finish(db, job, outcome)
    LOG.info('Registration delivery state=%s code=%s', state, outcome.code or 'ok')
    return True


def queue_health(config):
    with connect(config) as db, db.cursor() as cur:
        cur.execute("""SELECT count(*) AS n FROM registration_notifier.outbox
            WHERE state IN ('failed', 'uncertain') OR
            (state='pending' AND available_at < clock_timestamp()-interval '10 minutes')""")
        count = cur.fetchone()['n']
    if count:
        LOG.error('Registration deliveries requiring attention: %d', count)
    return count == 0


def main():
    config = json.loads(Path(os.environ.get('NOTIFIER_CONFIG', '/run/secrets/config.json')).read_text())
    if config.get('api_base') not in ALLOWED_BASES or not isinstance(config.get('chat_id'), int) or config['chat_id'] >= 0:
        raise ValueError('Only an explicitly configured Telegram group is allowed')
    if '--smoke' in sys.argv:
        text = '[ТЕСТ ПОДКЛЮЧЕНИЯ — это не реальная регистрация]\n\n' + format_message({
            'first_name': 'Тест', 'last_name': 'AdMirra', 'email': 'test@example.invalid',
            'registration_utm_source': 'тест подключения', 'id': 'synthetic-test',
        })
        result = send_message(config['api_base'], Path(config['token_file']).read_text().strip(), config['chat_id'], text)
        print('Synthetic delivery:', result.state, 'code:', result.code or 'ok', 'message_id:', result.message_id)
        raise SystemExit(0 if result.state == 'sent' else 1)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    checked, healthy = 0, False
    while not stop.is_set():
        try:
            tick(config)
            if time.monotonic() - checked > 30:
                healthy = queue_health(config)
                checked = time.monotonic()
            if healthy:
                Path('/tmp/healthy').touch()
        except Exception as exc:
            # Exception messages may contain URLs, DB credentials, or PII.
            LOG.error('Notifier iteration failed: %s', type(exc).__name__)
        # Fewer than 20 messages/minute/group, including catch-up after downtime.
        stop.wait(3.2)


if __name__ == '__main__':
    main()
