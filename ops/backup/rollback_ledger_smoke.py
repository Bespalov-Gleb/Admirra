"""Synthetic durable admissions survive an API-only rollback on a restore DB.

Never run against production. No scheduler, consumer or external side effects.
Execute with the candidate for seed; with each application image for check.
"""
import os
import sys
from urllib.parse import urlsplit


def isolated():
    url = urlsplit(os.environ.get('DATABASE_URL', ''))
    if (os.getenv('WW_TEST') != '1' or not os.getenv('WW_TEST_ID', '').startswith('restore-')
            or url.hostname != '127.0.0.1' or url.path != '/restore'):
        raise RuntimeError('Only the isolated network-none restore database is allowed')


def run(mode):
    isolated()
    import sqlalchemy as sa
    from core.database import SessionLocal
    from automation import work_ledger as ledger
    from automation.work_tables import jobs, outbox
    from automation.work_preflight import check
    check()
    prefix = 'isolated-rollback-acceptance:'
    def submit(db, name):
        return ledger.submit(db, kind='acceptance.rollback', queue='maintenance',
            key=prefix + name, resource=prefix + name, tenant='isolated-acceptance',
            payload={'synthetic': True}, replay_safe=False)
    with SessionLocal.begin() as db:
        if mode == 'seed':
            if db.scalar(sa.select(sa.func.count()).select_from(jobs).where(jobs.c.dedupe_key.startswith(prefix))):
                raise RuntimeError('Synthetic markers already exist')
            submit(db, 'queued')
            unknown = submit(db, 'unknown')
            execution = ledger.claim(db, unknown)
            assert execution is not None
            assert ledger.finish(db, unknown, execution['lease_token'], error=RuntimeError('Synthetic uncertain effect'))
        rows = {row['dedupe_key'].removeprefix(prefix): row for row in db.execute(
            sa.select(jobs).where(jobs.c.dedupe_key.startswith(prefix))).mappings()}
        assert set(rows) == {'queued', 'unknown'}
        assert rows['queued']['state'] == 'queued' and rows['unknown']['state'] == 'uncertain'
        assert rows['queued']['attempt'] == 0 and rows['unknown']['attempt'] == 1
        assert submit(db, 'queued') == rows['queued']['id']
        assert submit(db, 'unknown') == rows['unknown']['id']
        assert ledger.claim(db, rows['unknown']['id']) is None
        assert db.scalar(sa.select(sa.func.count()).select_from(outbox).where(
            outbox.c.job_id.in_([row['id'] for row in rows.values()]))) == 1
    print('Isolated rollback ledger: queued and uncertain retained, dedupe/replay guards passed')


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) == 2 else ''
    if mode not in {'seed', 'check'}:
        raise SystemExit('Expected seed or check')
    run(mode)
