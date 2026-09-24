"""Bounded owner-account GET probe. Run inside API; never print tokens/data.

Only 2 parallel requests; no sync enqueue, LLM, payments or report sends.
Summary GET retains its normal best-effort visit bookkeeping.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import json
import logging
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from core import models, security
from core.database import SessionLocal


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', action='append', required=True)
    a = p.parse_args()
    allowed = {'http://127.0.0.1:8001', 'http://10.77.0.2:8001', 'http://10.77.0.1:8001', 'https://admirra.ru'}
    assert set(a.base) <= allowed
    logging.disable(logging.CRITICAL)
    with SessionLocal() as db:
        user = db.query(models.User).filter(models.User.email == 'burlakov.timof@yandex.ru', models.User.is_active.is_(True)).one()
        token = security.create_access_token({'sub': user.email}, expires_delta=timedelta(minutes=10))
        clients = [str(row.id) for row in db.query(models.Client).filter(models.Client.owner_id == user.id,
            models.Client.name.in_(['FUN KIDS', 'БВК Новый / ВК'])).all()]
        assert len(clients) == 2
    end = date.today()
    period = f'start_date={end-timedelta(days=end.weekday())}&end_date={end}'
    paths = ['/api/auth/me', '/api/detector/cross-project']
    for cid in clients:
        paths.extend([f'/api/dashboard/summary?client_id={cid}&{period}&platform=all',
                      f'/api/detector/{cid}/summary', f'/api/detector/{cid}/campaign-highlights?{period}'])
    def one(item):
        base, path = item
        started = time.monotonic()
        code = 0
        try:
            with urlopen(Request(base + path, headers={'Authorization': 'Bearer ' + token}), timeout=20) as r:
                code = r.status
                data = json.loads(r.read(4*1024*1024))
                assert isinstance(data, (dict, list))
        except HTTPError as exc:
            code = exc.code
        except Exception:
            code = 0
        return {'base': base, 'route': path.split('?')[0], 'status': code,
                'ms': round((time.monotonic()-started)*1000, 1)}
    results = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        for repeat in range(2):
            results.extend(pool.map(one, [(base, path) for path in paths for base in a.base]))
    for base in a.base:
        rows = [r for r in results if r['base'] == base]
        times = sorted(r['ms'] for r in rows)
        print(json.dumps({'base': base, 'requests': len(rows), 'ok': sum(r['status'] == 200 for r in rows),
                          'max_ms': max(times), 'p95_ms': times[min(len(times)-1, int(len(times)*.95))],
                          'failures': [r for r in rows if r['status'] != 200]}), flush=True)
    assert all(r['status'] == 200 for r in results)


if __name__ == '__main__':
    main()
