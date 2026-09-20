"""One explicitly approved production-account request and an identical replay.

Run inside backend using stdin. Tokens/prompts/answers are never printed.
The stable release-scoped key prevents a second provider run on script retry.
"""
import argparse
from datetime import timedelta
import json
import uuid

import httpx
import sqlalchemy as sa

from core import models, security
from core.database import SessionLocal
from backend_api.services.subscription import SubscriptionService
from ai.assistant import runs


def smoke(email, release):
    key = uuid.uuid5(uuid.NAMESPACE_URL, f'admirra:assistant-quota-smoke:{release}:{email}')
    with SessionLocal() as db:
        user = db.query(models.User).filter(models.User.email == email).one()
        assert user.is_active
        account = SubscriptionService._resolve_ai_quota_user(db, user)
        account_id = account.id
        used_before = int(account.ai_requests_used or 0)
        bypass = SubscriptionService.is_admin_bypass(account)
        token = security.create_access_token({'sub': email}, expires_delta=timedelta(minutes=10))
        prior = db.execute(sa.select(runs.runs).where(
            runs.runs.c.user_id == user.id, runs.runs.c.request_id == key)).mappings().first()
        if prior is not None:
            assert prior['state'] == 'succeeded', 'Previous smoke incomplete; inspect, do not retry automatically'
        user_id = user.id
    body = {'request_id': str(key), 'message': 'Ответь ровно: тест готов. Не используй инструменты.', 'effort': 'low'}
    headers = {'Authorization': f'Bearer {token}'}

    def call(client, payload):
        with client.stream('POST', '/api/assistant/chat', headers=headers, json=payload) as response:
            status = response.status_code
            if status != 200:
                return status, []
            events = [json.loads(line[6:]) for line in response.iter_lines() if line.startswith('data: ')]
            return status, events

    with httpx.Client(base_url='https://admirra.ru', timeout=180, follow_redirects=False) as client:
        status, events = call(client, body)
        assert status == 200, f'First request HTTP {status}'
        assert not any(event.get('type') == 'error' for event in events), 'Provider/agent error'
        done = next(event for event in events if event.get('type') == 'done')
        assert done.get('message_id') and done.get('content')
        with SessionLocal() as db:
            first = dict(db.execute(sa.select(runs.runs).where(
                runs.runs.c.user_id == user_id, runs.runs.c.request_id == key)).mappings().one())
            used_first = int(db.get(models.User, account_id).ai_requests_used or 0)
        status, replay = call(client, body)
        assert status == 200
        assert any(event.get('type') == 'meta' and event.get('replayed') for event in replay)
        assert next(event for event in replay if event.get('type') == 'done') == done
        conflict, _ = call(client, {**body, 'message': 'Changed payload: must not run'})
        assert conflict == 409
        unauth = client.get('/api/assistant/conversations').status_code
        assert unauth in (401, 403)
    with SessionLocal() as db:
        final = dict(db.execute(sa.select(runs.runs).where(runs.runs.c.id == first['id'])).mappings().one())
        used_final = int(db.get(models.User, account_id).ai_requests_used or 0)
        assert final['state'] == 'succeeded'
        assert final['provider_calls'] == first['provider_calls'] and final['usage'] == first['usage']
        assert used_final == used_first, 'Replay changed quota'
        if prior is None:
            assert used_first - used_before == (0 if bypass else 1), 'Unexpected quota delta'
        print(json.dumps({'first': 200, 'replay': 200, 'conflict': conflict, 'unauth': unauth,
            'state': final['state'], 'provider_calls': final['provider_calls'],
            'usage_entries': len(final['usage']), 'admin_bypass': bypass,
            'quota_delta': used_first - used_before, 'replay_quota_delta': used_final - used_first}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--email', required=True)
    parser.add_argument('--release', required=True)
    args = parser.parse_args()
    try:
        smoke(args.email, args.release)
    except Exception as error:
        print('Assistant smoke failed:', type(error).__name__)
        raise SystemExit(1)
