"""Read-only DB acceptance and expiring Redis test keys; no business handlers."""
import argparse
import json
import os
import uuid
from urllib.parse import urlsplit


def database():
    import psycopg2
    from psycopg2.extensions import parse_dsn
    dsn = os.environ["DATABASE_URL"]
    args = parse_dsn(dsn)
    if args.get("host") != "10.77.0.1" or args.get("user") not in {"admirra_api", "admirra_worker"}:
        raise RuntimeError("Unexpected DB target")
    with psycopg2.connect(dsn, connect_timeout=5, application_name="admirra-infra-readonly-probe",
                         options="-cdefault_transaction_read_only=on -cstatement_timeout=5000") as db:
        with db.cursor() as cursor:
            cursor.execute("""SELECT current_user,
              has_schema_privilege(current_user,'public','CREATE'),
              has_table_privilege(current_user,'public.clients','SELECT'),
              has_table_privilege(current_user,'public.clients','UPDATE'),
              has_table_privilege(current_user,'public.alembic_version','UPDATE')""")
            user, create_schema, read_data, update_data, change_version = cursor.fetchone()
            assert not create_schema and read_data and update_data and not change_version
    forbidden = {**args, "user": "postgres", "password": "deliberately-invalid-probe", "connect_timeout": 5}
    try:
        psycopg2.connect(**forbidden).close()
    except psycopg2.OperationalError as exc:
        if "pg_hba.conf rejects" not in str(exc):
            raise RuntimeError("Expected explicit HBA rejection, not just password rejection") from None
    else:
        raise RuntimeError("Privileged gateway login unexpectedly accepted")
    return {"role": user, "readonly_probe": "passed", "ddl": "denied", "postgres_gateway_login": "denied"}


def redis_services():
    from redis import Redis
    from redis.exceptions import ResponseError, AuthenticationError
    results = {}
    for key, namespace in (("CELERY_BROKER_URL", "admirra:task:"),
                            ("RATE_LIMIT_REDIS_URL", "admirra:rate:v1:"),
                            ("READ_CACHE_REDIS_URL", "admirra:read:v1:")):
        url = os.environ[key]
        parts = urlsplit(url)
        if parts.hostname not in {"10.77.0.2", "broker", "cache"}:
            raise RuntimeError("Unexpected Redis target")
        client = Redis.from_url(url, socket_connect_timeout=3, socket_timeout=3)
        assert client.ping()
        # New random probe key; no real queue/cache/rate-limit keys are touched.
        probe = namespace + "infrastructure-probe:" + uuid.uuid4().hex
        if key == "RATE_LIMIT_REDIS_URL":
            client.psetex(probe, 1000, "ok")
        else:
            client.set(probe, "ok", ex=1)
        assert client.get(probe) == b"ok"
        for forbidden in (("CONFIG", "GET", "dir"), ("GET", "outside-namespace:probe")):
            try:
                client.execute_command(*forbidden)
            except ResponseError:
                pass
            else:
                raise RuntimeError("Redis ACL unexpectedly permitted a forbidden operation")
        anonymous = Redis(host=parts.hostname, port=parts.port, socket_connect_timeout=3, socket_timeout=3)
        try:
            anonymous.ping()
        except AuthenticationError:
            pass
        else:
            raise RuntimeError("Redis accepted an unauthenticated connection")
        finally:
            anonymous.close()
            client.close()
        results[key] = "authenticated; namespace/admin/anonymous restrictions passed"
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("service", choices=("database", "redis"))
    args = parser.parse_args()
    try:
        result = database() if args.service == "database" else redis_services()
    except Exception as exc:
        # Do not emit DSNs/passwords, even in failure traceback.
        raise SystemExit("Private infrastructure probe failed: " + type(exc).__name__) from None
    print(json.dumps(result))


if __name__ == "__main__":
    main()
