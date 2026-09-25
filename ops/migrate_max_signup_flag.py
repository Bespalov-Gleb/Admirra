"""Bounded expand phase for f79ca3b4c5d6; no user backfill or revision switch.

Run with the migration/table-owner DB role, --apply required for writes.
The normal API role intentionally has no DDL rights; never grant it those rights.
Old API/workers remain compatible; retain column when rolling code back.
Advance Alembic only with a coordinated EXPECTED_SCHEMA_REVISION rollout across
APIs, workers, schedulers and monitoring. Never stamp ahead of those consumers.
"""
import sys
from sqlalchemy import text

OLD = 'f68b92a3b4c5'
NEW = 'f79ca3b4c5d6'

def migrate(connection):
    connection.execute(text("SET LOCAL lock_timeout = '2s'"))
    connection.execute(text("SET LOCAL statement_timeout = '10s'"))
    connection.execute(text("SELECT pg_advisory_xact_lock(7920250925)"))
    revisions = connection.execute(text('SELECT version_num FROM alembic_version')).scalars().all()
    assert revisions in ([OLD], [NEW]), 'Unexpected migration revision; no changes made'
    column = connection.execute(text("SELECT data_type, is_nullable FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='max_oauth_login_attempts' AND column_name='is_new_user'")).first()
    if column:
        assert tuple(column) == ('boolean', 'NO'), 'Unexpected column definition'
        return 'already applied'
    connection.execute(text('ALTER TABLE max_oauth_login_attempts ADD COLUMN is_new_user boolean NOT NULL DEFAULT false'))
    return 'applied'

if __name__ == '__main__':
    from core.database import engine
    if '--apply' not in sys.argv:
        with engine.connect() as c:
            print('Current revision:', c.execute(text('SELECT version_num FROM alembic_version')).scalars().all())
    else:
        with engine.begin() as c: result=migrate(c)
        print('MAX signup flag:',result)
