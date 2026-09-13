"""Two bounded read-only pg_stat_statements snapshots, never query text.

Use an existing diagnostic DATABASE_URL with pg_read_all_stats and access to
pg_control_system. Never installs/resets statistics or changes server settings.
"""
import argparse
import hashlib
import json
import math
import os
import time

import sqlalchemy as sa
from sqlalchemy.pool import NullPool

COUNTERS = ("calls", "total_exec_time", "rows", "shared_blks_hit", "shared_blks_read", "temp_blks_written")
MAX_ENTRIES = 10000


class SampleUnavailable(ValueError):
    pass


def capture(engine):
    if engine.dialect.name != "postgresql":
        raise SampleUnavailable("PostgreSQL required")
    with engine.connect() as conn, conn.begin():
        conn.execute(sa.text("SET TRANSACTION READ ONLY"))
        conn.execute(sa.text("SET LOCAL statement_timeout = '3000ms'"))
        conn.execute(sa.text("SET LOCAL lock_timeout = '1000ms'"))
        conn.execute(sa.text("SET LOCAL search_path = pg_catalog"))
        meta = conn.execute(sa.text("""
            SELECT n.nspname, e.extversion, pg_postmaster_start_time() AS server_start,
                   current_setting('server_version_num') AS server_version,
                   (SELECT oid FROM pg_database WHERE datname=current_database()) AS database_oid,
                   (current_setting('is_superuser')='on' OR
                       pg_has_role(current_user, 'pg_read_all_stats', 'MEMBER')) AS visible,
                   (SELECT system_identifier::text FROM pg_control_system()) AS system_id
            FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace
            WHERE e.extname='pg_stat_statements'
        """)).mappings().one_or_none()
        if meta is None or not meta["visible"]:
            raise SampleUnavailable("Statistics extension or full diagnostic visibility unavailable")
        schema = conn.dialect.identifier_preparer.quote_schema(meta["nspname"])
        info_sql = sa.text(f"SELECT stats_reset, dealloc FROM {schema}.pg_stat_statements_info")
        before = dict(conn.execute(info_sql).mappings().one())
        started = time.monotonic()
        rows = [dict(row) for row in conn.execute(sa.text(f"""
            SELECT userid::bigint AS db_role_oid, queryid, toplevel, {', '.join(COUNTERS)}
            FROM {schema}.pg_stat_statements(false)
            WHERE dbid=:database_oid ORDER BY userid, queryid, toplevel LIMIT :limit
        """), {"database_oid": meta["database_oid"], "limit": MAX_ENTRIES + 1}).mappings()]
        ended = time.monotonic()
        after = dict(conn.execute(info_sql).mappings().one())
        observed = str(conn.scalar(sa.text("SELECT clock_timestamp()")))
        if before != after or len(rows) > MAX_ENTRIES:
            raise SampleUnavailable("Statistics changed during collection or exceeded row cap")
    identity = hashlib.sha256(f"{meta['system_id']}:{meta['database_oid']}".encode()).hexdigest()
    return {"identity": identity, "server_start": str(meta["server_start"]),
        "server_version": meta["server_version"], "extension_version": meta["extversion"],
        "reset": str(after["stats_reset"]), "dealloc": after["dealloc"],
        "observed_at": observed, "monotonic_at": (started + ended) / 2,
        "collection_seconds": ended - started, "rows": rows}


def indexed(rows):
    if len(rows) > MAX_ENTRIES:
        raise SampleUnavailable("Too many statement entries")
    result = {}
    for row in rows:
        key = (row["db_role_oid"], row["queryid"], row["toplevel"])
        if key[1] is None or key in result:
            raise SampleUnavailable("Missing or duplicate statement identity")
        for name in COUNTERS:
            value = row[name]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise SampleUnavailable("Invalid statement counter")
        result[key] = row
    return result


def difference(first, second):
    for field in ("identity", "server_start", "server_version", "extension_version", "reset", "dealloc"):
        if first[field] != second[field]:
            raise SampleUnavailable("Restart, reset, eviction or incompatible source; repeat measurement")
    elapsed = second["monotonic_at"] - first["monotonic_at"]
    if not math.isfinite(elapsed) or elapsed <= 0:
        raise SampleUnavailable("Invalid sampling interval")
    old, new = indexed(first["rows"]), indexed(second["rows"])
    if old.keys() - new.keys():
        raise SampleUnavailable("Statement entries disappeared; repeat measurement")
    changes = []
    for key, row in new.items():
        previous = old.get(key, {})
        delta = {name: row[name] - previous.get(name, 0) for name in COUNTERS}
        if any(value < 0 for value in delta.values()):
            raise SampleUnavailable("Statement counters decreased; possible targeted reset")
        if not delta["calls"]:
            if any(delta.values()):
                raise SampleUnavailable("Inconsistent counters; repeat measurement")
            continue
        changes.append({"db_role_oid": key[0], "queryid": key[1], "toplevel": key[2],
            "new_entry": key not in old, **delta,
            "mean_exec_ms": round(delta["total_exec_time"] / delta["calls"], 3)})
    # Only top-level calls are summed: nested calls would count execution twice.
    top = [row for row in changes if row["toplevel"]]
    calls = sum(row["calls"] for row in top)
    return {"format_version": 1, "read_only": True, "query_text_included": False,
        "load_accepted": False, "sample_valid": True,
        "from": first["observed_at"], "to": second["observed_at"], "interval_seconds": round(elapsed, 3),
        "collection_seconds": [first["collection_seconds"], second["collection_seconds"]],
        "completed_top_level_calls": calls, "completed_sql_calls_per_second": round(calls / elapsed, 3),
        "top_level_exec_ms": round(sum(row["total_exec_time"] for row in top), 3),
        "changed_statement_entries": len(changes), "nested_entries": len(changes) - len(top),
        "top": sorted(top, key=lambda row: (-row["total_exec_time"], row["queryid"], row["db_role_oid"]))[:20],
        "limitations": ["Includes diagnostic SQL; SQL call rate is not HTTP RPS or CPU utilization",
            "Completed statements can have started before the sample; failed/in-flight work is not fully represented",
            "Concurrent targeted resets may be undetectable if counters already surpassed their earlier values",
            "Short ambient observation is not a representative peak/load test"]}


def sample(engine, seconds=15, *, sleep=time.sleep):
    if isinstance(seconds, bool) or not isinstance(seconds, int) or not 1 <= seconds <= 30:
        raise SampleUnavailable("Sampling wait must be 1..30 seconds")
    first = capture(engine)
    sleep(seconds)  # No checked-out SQL connection while waiting.
    return difference(first, capture(engine))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, default=15, choices=range(1, 31))
    args = parser.parse_args()
    engine = None
    try:
        engine = sa.create_engine(os.environ["DATABASE_URL"], poolclass=NullPool,
            connect_args={"connect_timeout": 5}, echo=False)
        print(json.dumps(sample(engine, args.seconds), indent=2, sort_keys=True))
    except Exception:
        raise SystemExit("Statement sample unavailable; check permissions/extension or repeat after reset, without printing credentials") from None
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
