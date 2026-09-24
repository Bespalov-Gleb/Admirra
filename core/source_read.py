"""Source locks for durable consumers; MVCC for explicitly read-only UI views."""


def lock_sources(db, statement):
    # The marker is connection/transaction scoped, never a Session.info flag
    # that could accidentally survive rollback and weaken a later writer.
    options = db.connection().get_execution_options()
    if options.get("admirra_read_snapshot"):
        if options.get("isolation_level") != "REPEATABLE READ":
            raise RuntimeError("Source snapshot requires repeatable read")
        return statement
    return statement.with_for_update()
