"""Bounded PostgreSQL inventory. No business rows, query text or mutations.

DATABASE_URL is read from the process environment, never a CLI argument/output.
Counters are cumulative observations, not current throughput or tuning advice.
"""
import json
import os

import sqlalchemy as sa
from sqlalchemy.pool import NullPool


TABLES = ("clients", "integrations", "campaigns", "yandex_stats", "vk_stats", "avito_stats",
    "metrika_goals", "yandex_keywords", "yandex_groups", "background_jobs", "background_outbox",
    "report_deliveries", "report_route_attempts", "stored_artifacts")

QUERIES = {
    "database": """
        SELECT clock_timestamp() AS observed_at, pg_postmaster_start_time() AS server_started_at,
               current_setting('server_version_num')::integer AS version_num,
               current_setting('transaction_read_only') AS transaction_read_only,
               current_setting('statement_timeout') AS statement_timeout,
               current_setting('lock_timeout') AS lock_timeout,
               (current_setting('is_superuser')='on' OR
                   pg_has_role(current_user, 'pg_read_all_stats', 'MEMBER')) AS all_activity_visible,
               pg_database_size(datid) AS size_bytes, stats_reset,
               xact_commit, xact_rollback, blks_read, blks_hit, temp_bytes, deadlocks,
               EXISTS (SELECT 1 FROM pg_extension WHERE extname='pg_stat_statements') AS statements_installed
        FROM pg_stat_database WHERE datname = current_database()
    """,
    "activity": """
        SELECT count(*) AS connections,
               count(*) FILTER (WHERE state='active') AS active,
               count(*) FILTER (WHERE state='idle') AS idle,
               count(*) FILTER (WHERE state LIKE 'idle in transaction%') AS idle_in_transaction,
               count(*) FILTER (WHERE state IS NULL) AS state_unavailable,
               count(*) FILTER (WHERE cardinality(pg_blocking_pids(pid)) > 0) AS blocked,
               max(EXTRACT(epoch FROM clock_timestamp()-xact_start)) AS oldest_transaction_seconds,
               max(EXTRACT(epoch FROM clock_timestamp()-xact_start))
                   FILTER (WHERE state LIKE 'idle in transaction%') AS oldest_idle_transaction_seconds
        FROM pg_stat_activity WHERE datname=current_database() AND pid <> pg_backend_pid()
    """,
    "tables": """
        SELECT relname AS table_name, n_live_tup, n_dead_tup, seq_scan, seq_tup_read,
               idx_scan, n_tup_ins, n_tup_upd, n_tup_del, n_tup_hot_upd,
               last_autovacuum, last_autoanalyze, last_vacuum, last_analyze,
               autovacuum_count, autoanalyze_count, pg_total_relation_size(relid) AS total_bytes,
               pg_relation_size(relid) AS heap_bytes, pg_indexes_size(relid) AS indexes_bytes,
               (SELECT reloptions FROM pg_class WHERE oid=relid) AS storage_options
        FROM pg_stat_user_tables WHERE schemaname=:schema AND relname=ANY(:tables)
        ORDER BY pg_total_relation_size(relid) DESC, relname LIMIT 32
    """,
    "indexes": """
        SELECT s.relname AS table_name, s.indexrelname AS index_name,
               i.indisvalid AS valid, i.indisready AS ready, i.indisunique AS unique_index,
               s.idx_scan, s.idx_tup_read, s.idx_tup_fetch, pg_relation_size(s.indexrelid) AS size_bytes
        FROM pg_stat_user_indexes s JOIN pg_index i ON i.indexrelid=s.indexrelid
        WHERE s.schemaname=:schema AND s.relname=ANY(:tables)
        ORDER BY s.relname, s.indexrelname LIMIT 256
    """,
}


def collect(engine, *, schema="public"):
    if engine.dialect.name != "postgresql":
        raise ValueError("PostgreSQL is required")
    # Parameters are bound, including schema. No untrusted SQL/identifiers.
    with engine.connect() as conn, conn.begin():
        conn.execute(sa.text("SET TRANSACTION READ ONLY"))
        conn.execute(sa.text("SET LOCAL statement_timeout = '3000ms'"))
        conn.execute(sa.text("SET LOCAL lock_timeout = '1000ms'"))
        conn.execute(sa.text("SET LOCAL search_path = pg_catalog"))
        sections = {name: [dict(row) for row in conn.execute(sa.text(query),
            {"schema": schema, "tables": list(TABLES)}).mappings()] for name, query in QUERIES.items()}
    return {"format_version": 1, "read_only": True, "load_accepted": False,
        "counter_semantics": "cumulative_since_stats_reset_not_current_rps",
        "business_rows_read": False, "query_text_included": False,
        "truncation_possible": len(sections["tables"]) == 32 or len(sections["indexes"]) == 256,
        "catalog_row_limits": {"tables": 32, "indexes": 256}, **sections}


def main():
    engine = None
    try:
        dsn = os.environ["DATABASE_URL"]
        engine = sa.create_engine(dsn, poolclass=NullPool, connect_args={"connect_timeout": 5}, echo=False)
        result = collect(engine)
        print(json.dumps(result, default=str, indent=2, sort_keys=True))
    except Exception:
        # Driver/SQL errors may contain connection details; never echo them.
        raise SystemExit("Read-only DB audit failed; inspect connectivity/permissions privately") from None
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
