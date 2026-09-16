"""Run inside the deployed backend: one synthetic LLM call on the owner's test account.

Never prints tokens or customer data. Deletes the created conversation in finally.
Usage: python smoke.py --email TEST_ACCOUNT_EMAIL
"""
import argparse
from datetime import timedelta
import io
import json
import zipfile
import httpx

from core import models, security
from core.database import SessionLocal


def main(email):
    with SessionLocal() as db:
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            raise RuntimeError('Test account not found')
        token = security.create_access_token({'sub': user.email}, expires_delta=timedelta(minutes=5))
    cid = None
    with httpx.Client(base_url='http://127.0.0.1:8001/api/assistant',
                      headers={'Authorization': 'Bearer ' + token}, timeout=180) as client:
        try:
            r = client.post('/conversations', json={})
            r.raise_for_status()
            cid = r.json()['id']
            r = client.post(f'/conversations/{cid}/attachments', params={'filename': 'synthetic-check.txt'},
                content='Контрольное слово: БЕРЁЗА. Количество заявок: 34. Это синтетический тест, не данные проекта.'.encode(),
                headers={'Content-Type': 'application/octet-stream'})
            r.raise_for_status()
            aid = r.json()['id']
            print('upload: ok', flush=True)
            payload = {'conversation_id': cid, 'attachment_ids': [aid], 'effort': 'low',
                       'message': 'Работай только с приложенным документом, без инструментов и без проектов. '
                                  'Напиши его контрольное слово и количество заявок. Ответ до 30 слов.'}
            r = client.post('/chat', json=payload)
            r.raise_for_status()
            events = [json.loads(line[5:]) for line in r.text.splitlines() if line.startswith('data:')]
            if any(e.get('type') == 'error' for e in events):
                raise RuntimeError('LLM stream returned an error (no customer data printed)')
            done = next(e for e in events if e.get('type') == 'done')
            content = done.get('content', '')
            assert '34' in content and 'берёз' in content.lower(), 'Attachment text not reflected in answer'
            mid = done['message_id']
            print('live LLM read attachment and persisted message: ok', flush=True)
            for fmt in ('md', 'docx'):
                r = client.get(f'/conversations/{cid}/messages/{mid}/download', params={'format': fmt})
                r.raise_for_status()
                assert r.headers['cache-control'] == 'private, no-store'
                if fmt == 'docx':
                    assert zipfile.is_zipfile(io.BytesIO(r.content))
                else:
                    assert '34' in r.text
                print('download ' + fmt + ': ok', flush=True)
            r = client.get(f'/conversations/{cid}')
            r.raise_for_status()
            assert any(m.get('attachments') for m in r.json()['messages'])
            print('reopened conversation attachment metadata: ok', flush=True)
        finally:
            if cid:
                r = client.delete(f'/conversations/{cid}')
                r.raise_for_status()
                print('synthetic conversation and attachments removed: ok', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--email', required=True)
    main(parser.parse_args().email)
