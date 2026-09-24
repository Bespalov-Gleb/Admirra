"""Single-host balance monitor; stdlib only, no DB, app imports or LLM calls.

Credentials arrive via systemd LoadCredential. URLs are fixed, redirects and
environment proxies disabled. Logs never include response bodies or exceptions.
Delivery attempts are persisted BEFORE sending: ambiguous sends wait 12h instead
of replaying every tick. Exactly-once delivery is not promised by Telegram.
"""
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import time
from decimal import Decimal
from urllib.error import HTTPError
from urllib.request import Request, ProxyHandler, HTTPRedirectHandler, build_opener

CREDITS_URL = 'http://10.78.0.3:8080/api/v1/credits'
TELEGRAM_BASE = 'http://10.78.0.3:8080/telegram'
REPEAT = 12 * 3600


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def request_json(request):
    opener = build_opener(ProxyHandler({}), NoRedirect())
    with opener.open(request, timeout=20) as response:
        body = response.read(65537)
        if len(body) > 65536:
            raise ValueError('oversized_response')
        return json.loads(body, parse_float=Decimal)


def number(value):
    if type(value) not in (int, float, Decimal):
        raise ValueError('invalid_number')
    value = Decimal(str(value))
    if not value.is_finite() or value < 0:
        raise ValueError('invalid_number')
    return value


def balance(payload):
    data = payload['data']
    # A negative REMAINING balance is real debt, not an API failure.
    return number(data['total_credits']) - number(data['total_usage'])


def level(value, warning, critical):
    return 'critical' if value <= critical else 'warning' if value <= warning else 'ok'


def save(path, state):
    temp = path.with_suffix('.tmp')
    with temp.open('w') as stream:
        os.chmod(temp, 0o600)
        json.dump(state, stream, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def notify(state, slot, event, message, now, persist, send, repeat=False):
    old = state.get(slot, {})
    same = old.get('event') == event
    if same and (now - old['attempt_at'] < REPEAT or (old.get('sent') and not repeat)):
        return
    state[slot] = {'event': event, 'attempt_at': now, 'sent': False}
    persist(state)
    try:
        send(message)
    except Exception:
        print('telegram_delivery_unconfirmed; retry_after_cooldown', flush=True)
    else:
        state[slot]['sent'] = True
    persist(state)


def poll(state, config, fetch, send, persist, now):
    warning, critical = number(config['warning_usd']), number(config['critical_usd'])
    if not 0 < critical < warning:
        raise ValueError('invalid_thresholds')
    try:
        remaining = balance(fetch())
    except Exception:
        state['failures'] = state.get('failures', 0) + 1
        persist(state)
        if state['failures'] >= 3:
            notify(state, 'health_notice', 'failed',
                   '⚠️ AdMirra: не удалось проверить баланс OpenRouter три раза подряд. '
                   'Остаток неизвестен — это не означает нулевой баланс. '
                   'Проверьте доступность API и срок действия Management key.',
                   now, persist, send, repeat=True)
        return False
    if state.get('health_notice', {}).get('event') == 'failed':
        notify(state, 'health_notice', 'restored',
               '✅ AdMirra: проверка баланса OpenRouter снова работает.', now, persist, send)
    elif state.get('health_notice', {}).get('event') == 'restored' and not state['health_notice'].get('sent'):
        notify(state, 'health_notice', 'restored',
               '✅ AdMirra: проверка баланса OpenRouter снова работает.', now, persist, send)
    state['failures'] = 0
    state['last_success_at'] = now
    state['remaining_usd'] = str(remaining)
    current = level(remaining, warning, critical)
    previous = state.get('balance_notice', {}).get('event')
    titles = {
        'warning': '⚠️ Низкий баланс OpenRouter',
        'critical': '🚨 Критический баланс OpenRouter',
        'ok': '✅ Баланс OpenRouter в норме' if previous else '✅ Мониторинг баланса OpenRouter включён',
    }
    message = (f'{titles[current]}\nОстаток: ${remaining:,.2f}\n'
               f'Предупреждение: ≤ ${warning:g}; критический: ≤ ${critical:g}.\n'
               'Проверка каждые 15 минут.')
    if current != 'ok':
        message += '\nПополнить: https://openrouter.ai/settings/credits'
    notify(state, 'balance_notice', current, message, now, persist, send,
           repeat=current == 'critical')
    persist(state)
    return True


def send_telegram(config, token, message):
    if not re.fullmatch(r'[0-9]+:[A-Za-z0-9_-]+', token):
        raise ValueError('invalid_bot_token')
    if type(config['chat_id']) is not int or config['chat_id'] >= 0:
        raise ValueError('expected_group')
    request = Request(TELEGRAM_BASE + '/bot' + token + '/sendMessage',
                      data=json.dumps({'chat_id': config['chat_id'], 'text': message,
                                       'link_preview_options': {'is_disabled': True}}).encode(),
                      headers={'Content-Type': 'application/json'})
    result = request_json(request)
    if result.get('ok') is not True or type(result.get('result', {}).get('message_id')) is not int:
        raise ValueError('unconfirmed_delivery')


def fetch_credits(key):
    if not re.fullmatch(r'sk-or-[A-Za-z0-9_-]+', key):
        raise ValueError('invalid_management_key')
    return request_json(Request(CREDITS_URL, headers={'Authorization': 'Bearer ' + key}))


def main():
    credentials = Path(os.environ['CREDENTIALS_DIRECTORY'])
    directory = Path(os.environ['STATE_DIRECTORY'])
    with (directory / 'lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        path = directory / 'state.json'
        # Corrupt state fails closed; don't replay the initial notice on every tick.
        state = json.loads(path.read_text()) if path.exists() else {}
        config = json.loads((credentials / 'config').read_text())
        key = (credentials / 'management-key').read_text().strip()
        token = (credentials / 'telegram-token').read_text().strip()
        ok = poll(state, config, lambda: fetch_credits(key),
                  lambda message: send_telegram(config, token, message),
                  lambda value: save(path, value), time.time())
        print('balance_check_ok' if ok else 'balance_check_unavailable', flush=True)
        return 0 if ok else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        # No traceback: urllib exceptions can contain bot credentials in URLs.
        print('balance_monitor_failed; inspect configuration/state permissions', flush=True)
        sys.exit(1)
