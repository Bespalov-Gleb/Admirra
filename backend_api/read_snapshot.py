"""One PostgreSQL snapshot per SQL-only list/summary HTTP handler.

Call only at the start of a read handler, after the authentication dependency.
Never use inside a write workflow or around external provider IO. Reuse the
request Session/pool slot rather than holding an auth connection plus a second
connection while the pool is saturated. Settings, access scope and all metrics
then see one committed version until the response has been materialized.
"""


def begin_read_snapshot(db):
    if db.get_bind().dialect.name != 'postgresql':
        return False  # SQLite-only unit fixtures keep their native semantics.
    if db.new or db.dirty or db.deleted:
        raise RuntimeError('Read snapshot cannot discard pending changes')
    # Authentication only reads. Release that transaction before changing the
    # isolation level; rollback also expires any ORM objects from the old view.
    db.rollback()
    connection = db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
    connection.exec_driver_sql('SET TRANSACTION READ ONLY')
    connection.execution_options(admirra_read_snapshot=True)
    return True
