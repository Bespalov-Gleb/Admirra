"""Nullable MAX attribution expand only; no account backfill or revision change."""
from sqlalchemy import text


def migrate(connection):
    connection.execute(text("SET LOCAL lock_timeout = '2s'"))
    connection.execute(text("SET LOCAL statement_timeout = '10s'"))
    connection.execute(text('SELECT pg_advisory_xact_lock(7920250928)'))
    revisions = connection.execute(text('SELECT version_num FROM alembic_version')).scalars().all()
    assert revisions in (['f68b92a3b4c5'], ['f79ca3b4c5d6'], ['f8ad4b5c6d7e']), 'Unexpected schema revision'
    column = connection.execute(text("SELECT data_type,is_nullable FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='max_oauth_login_attempts' AND column_name='registration_attribution'")).first()
    if column:
        assert tuple(column) == ('json', 'YES'), 'Unexpected column definition'
        return 'already applied'
    connection.execute(text('ALTER TABLE max_oauth_login_attempts ADD COLUMN registration_attribution json NULL'))
    return 'applied'


if __name__ == '__main__':
    import sys
    from core.database import engine
    assert '--apply' in sys.argv, 'Explicit --apply required, using table-owner credentials'
    with engine.begin() as connection:
        print(migrate(connection))
