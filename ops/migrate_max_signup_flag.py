"""Bounded additive migration, equivalent to f79ca3b4c5d6; no user backfill.

Run in the live API environment via stdin, --apply required for writes.
Old API/workers remain compatible; retain column when rolling code back.
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
    if revisions == [NEW]:
        connection.execute(text('SELECT is_new_user FROM max_oauth_login_attempts LIMIT 0'))
        return 'already applied'
    assert revisions == [OLD], 'Unexpected migration revision; no changes made'
    connection.execute(text('ALTER TABLE max_oauth_login_attempts ADD COLUMN is_new_user boolean NOT NULL DEFAULT false'))
    connection.execute(text('UPDATE alembic_version SET version_num=:new WHERE version_num=:old'),{'new':NEW,'old':OLD})
    return 'applied'

if __name__ == '__main__':
    from core.database import engine
    if '--apply' not in sys.argv:
        with engine.connect() as c:
            print('Current revision:', c.execute(text('SELECT version_num FROM alembic_version')).scalars().all())
    else:
        with engine.begin() as c: result=migrate(c)
        print('MAX signup flag:',result)
