"""Explicit additive hotfix migration; never enables the pending DevOps cutover."""
import sqlalchemy as sa
from core.database import engine
from ai.assistant.runs import metadata, runs


def migrate(connection):
    connection.execute(sa.text("SET LOCAL lock_timeout = '5s'"))
    connection.execute(sa.text("SET LOCAL statement_timeout = '30s'"))
    connection.execute(sa.text("SELECT pg_advisory_xact_lock(82491723)"))
    metadata.create_all(connection, checkfirst=True)
    columns = {item["name"] for item in sa.inspect(connection).get_columns(runs.name)}
    if columns != set(runs.c.keys()):
        raise RuntimeError("Assistant request ledger schema mismatch")
    inspector = sa.inspect(connection)
    if ["id"] != inspector.get_pk_constraint(runs.name)["constrained_columns"]:
        raise RuntimeError("Assistant ledger primary key mismatch")
    if not any(item["column_names"] == ["user_id", "request_id"]
               for item in inspector.get_unique_constraints(runs.name)):
        raise RuntimeError("Assistant ledger idempotency constraint missing")


if __name__ == "__main__":
    with engine.begin() as connection:
        migrate(connection)
    print("assistant request ledger ready; existing Alembic revision unchanged")
