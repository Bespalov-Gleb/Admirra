"""Read-only attribution parity/timing probe; run inside API with owner scope.

No tokens or per-campaign data printed. PostgreSQL enforces read-only sessions.
Only Metrika GETs and bounded, disposable Redis read-cache entries are produced.
"""
import argparse
import asyncio
import hashlib
import json
import logging
import os
import time
import uuid


async def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project', type=uuid.UUID, required=True)
    p.add_argument('--start', required=True)
    p.add_argument('--end', required=True)
    p.add_argument('--warm-only', action='store_true')
    args = p.parse_args()
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from core import models
    from backend_api.directions import get_direction_stats
    logging.getLogger('httpx').setLevel(logging.WARNING)
    engine = create_engine(os.environ['DATABASE_URL'], pool_size=1, max_overflow=0,
        connect_args={'options': '-c default_transaction_read_only=on -c statement_timeout=20000'})
    results = []
    try:
        for enabled in ([True] if args.warm_only else [False, True, True]):
            os.environ['SHARED_READ_CACHE'] = 'true' if enabled else 'false'
            started = time.monotonic()
            with Session(engine) as db:
                project = db.get(models.Client, args.project)
                assert project is not None
                user = db.get(models.User, project.owner_id)
                result = await asyncio.wait_for(get_direction_stats(client_id=args.project,
                    start_date=args.start, end_date=args.end, platform='yandex', current_user=user, db=db), 90)
            digest = hashlib.sha256(json.dumps(result, sort_keys=True, default=str).encode()).hexdigest()
            results.append(dict(cache=enabled, seconds=round(time.monotonic()-started, 3),
                                result_hash=digest, direction_count=len(result['items'])))
            print(json.dumps(results[-1]), flush=True)
        assert len({r['result_hash'] for r in results}) == 1, 'Attribution changed across reads; investigate before rollout'
    finally:
        engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
