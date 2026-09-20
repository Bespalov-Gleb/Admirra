"""Permissions on isolated Redis/PostgreSQL; no production data/network."""
import json
import os
from pathlib import Path
import uuid

import pytest
from redis import Redis
from redis.exceptions import ResponseError, AuthenticationError
import sqlalchemy as sa

from ops import private_database, private_firewall, private_redis, service_credentials
from tests.test_durable_work import pg


def test_credentials_are_private_idempotent_and_never_in_acl(tmp_path):
    root = tmp_path / "private"
    private_redis.provision(root)
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    private_redis.provision(root)
    assert before == {p.name: p.read_bytes() for p in root.iterdir()}
    credentials = json.loads((root / "redis-credentials.json").read_text())
    for path in root.glob("*.acl"):
        assert all(password not in path.read_text() for password in credentials.values())
        assert "user default off" in path.read_text()
    for path in root.glob("*.env"):
        assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(RuntimeError, match="differs"):
        private_redis.write_once(root / "redis-worker.env", "different", 0o600)


def test_legacy_credentials_require_explicit_monitor_migration(tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    legacy = {user: "legacy-monitor-migration-" + uuid.uuid4().hex for user in private_redis.LEGACY_USERS}
    private_redis.write_once(root / "redis-credentials.json", json.dumps(legacy), 0o600)

    with pytest.raises(RuntimeError, match="Unexpected credential state"):
        private_redis.provision(root)

    private_redis.provision(root, refresh_acl=True)
    migrated = json.loads((root / "redis-credentials.json").read_text())
    assert set(migrated) == set(private_redis.USERS)
    assert all(migrated[user] == password for user, password in legacy.items())
    assert len(migrated["monitor"]) >= 40

    previous = migrated.copy()
    private_redis.provision(root, rotate_monitor=True)
    rotated = json.loads((root / "redis-credentials.json").read_text())
    assert rotated["monitor"] != previous["monitor"]
    assert all(rotated[user] == password for user, password in previous.items() if user != "monitor")


def test_monitor_acl_has_no_key_scope_or_write_commands():
    passwords = {user: "monitor-acl-test-" + uuid.uuid4().hex for user in private_redis.USERS}
    for content in private_redis.acl_files(passwords).values():
        monitor = next(line for line in content.splitlines() if line.startswith("user monitor "))
        assert "resetkeys" in monitor
        assert " ~" not in monitor
        assert "+set" not in monitor
        assert "+eval" not in monitor


def test_firewall_is_narrow_and_keeps_ssh_web_policy_unchanged():
    for ipv6 in (True, False):
        chains, hooks = private_firewall.rules("10.77.0.2", "10.77.0.1", "eth0", ipv6)
        assert {chain for chain, _ in hooks} == {"INPUT", "DOCKER-USER"}
        assert chains["ADMR-PRIV-IN"][-1] == ["-j", "DROP"]
        assert all("5432,6379,6380" in hook for _, hook in hooks)
        assert all("--ctdir" in hook for chain, hook in hooks if chain == "DOCKER-USER")
        flat = " ".join(" ".join(rule) for entries in chains.values() for rule in entries)
        assert "eth0 -j DROP" in flat
        assert ("10.77.0.1/32" in flat) is not ipv6


def test_hba_preserves_old_clients_and_restricts_only_new_gateway():
    old = "local all all trust\nhost all all all scram-sha-256\n"
    result = private_database.hba_content(old)
    assert result.endswith(old)
    assert result.index("admirra_api,admirra_worker") < result.index("all all 172.18.0.250/32 reject")
    assert private_database.hba_content(result) == result
    with pytest.raises(RuntimeError):
        private_database.hba_content("# BEGIN ADMIRRA PRIVATE GATEWAY\nunexpected\n")


def test_secret_transfer_accepts_only_expected_services_and_destinations():
    password = "x" * 43
    service_credentials.validate("db-worker", f"DATABASE_URL=postgresql://admirra_worker:{password}@10.77.0.1:5432/saas_project\n")
    with pytest.raises(ValueError):
        service_credentials.validate("db-worker", f"DATABASE_URL=postgresql://postgres:{password}@10.77.0.1:5432/saas_project\n")
    passwords = {user: password for user in private_redis.USERS}
    service_credentials.validate("redis-api", private_redis.environments(passwords)["redis-api.env"])
    with pytest.raises(ValueError):
        service_credentials.validate("redis-api", private_redis.environments(passwords)["redis-api.env"].replace("10.77.0.2", "example.org"))


@pytest.fixture
def secured_redis():
    from urllib.parse import urlsplit
    url = os.getenv("ISOLATED_REDIS_URL")
    if not url:
        pytest.skip("isolated Redis required")
    assert os.getenv("WW_TEST") == "1" and urlsplit(url).hostname == "test-redis"
    admin = Redis.from_url(url)
    passwords = {user: "isolated-permissions-test-" + uuid.uuid4().hex for user in private_redis.USERS}
    # Keep the isolated test administrator; production ACL disables default.
    for content in private_redis.acl_files(passwords, db=15).values():
        for line in content.splitlines():
            parts = line.split()
            if parts[1] != "default":
                admin.execute_command("ACL", "SETUSER", *parts[1:])
    def client(user):
        return Redis(host="test-redis", db=0 if user == "health" else 15,
                     username=user, password=passwords[user], socket_timeout=2)
    try:
        yield client, admin
    finally:
        admin.execute_command("ACL", "DELUSER", *passwords)
        for key in admin.scan_iter("admirra:*"):
            admin.delete(key)
        admin.close()


def test_redis_roles_cannot_administer_or_cross_namespaces(secured_redis):
    client, _ = secured_redis
    for user in ("broker_api", "broker_worker", "limiter_api", "limiter_worker", "cache_api", "cache_worker"):
        conn = client(user)
        assert conn.ping()
        for command in (("CONFIG", "GET", "dir"), ("ACL", "LIST"), ("FLUSHALL",), ("KEYS", "*")):
            with pytest.raises(ResponseError):
                conn.execute_command(*command)
        with pytest.raises(ResponseError):
            conn.get("not-admirra:secret")
        conn.close()
    health = client("health")
    assert health.ping()
    with pytest.raises(ResponseError):
        health.get("admirra:task:foo")

    monitor = client("monitor")
    assert monitor.ping()
    assert monitor.info()["redis_version"]
    with pytest.raises(ResponseError):
        monitor.set("admirra:task:forbidden", "value")
    with pytest.raises(ResponseError):
        monitor.get("admirra:task:forbidden")


def test_cache_and_rate_limiter_lua_allowed_but_other_keys_denied(secured_redis):
    from automation.provider_transport import RESERVE
    from core.shared_read_cache import PUBLISH
    client, _ = secured_redis
    limiter = client("limiter_worker")
    assert limiter.eval(RESERVE, 2, "admirra:rate:v1:a", "admirra:rate:v1:b", 100, 100) == 0
    with pytest.raises(ResponseError):
        limiter.set("admirra:task:stolen", "bad")
    cache = client("cache_api")
    cache.set("admirra:read:v1:lock", "owner")
    assert cache.eval(PUBLISH, 2, "admirra:read:v1:lock", "admirra:read:v1:value", "owner", "{}", 60) == 1
    with pytest.raises(ResponseError):
        cache.eval("return redis.call('GET', KEYS[1])", 1, "admirra:task:secret")


def test_kombu_round_trip_with_restricted_broker_user(secured_redis):
    from kombu import Connection, Exchange, Queue
    client, _ = secured_redis
    conn = client("broker_worker")
    credentials = conn.connection_pool.connection_kwargs
    url = "redis://broker_worker:" + credentials["password"] + "@test-redis:6379/15"
    with Connection(url, transport_options={"global_keyprefix": "admirra:task:"}) as broker:
        exchange = Exchange("acceptance", type="direct")
        queue = Queue("acceptance", exchange=exchange, routing_key="acceptance")
        bound = queue(broker)
        bound.declare()
        with broker.Producer(serializer="json") as producer:
            producer.publish({"only": "synthetic"}, exchange=exchange, routing_key="acceptance")
        message = bound.get(no_ack=False)
        assert message.payload == {"only": "synthetic"}
        message.ack()
        bound.delete()


def test_runtime_roles_scram_and_permissions(pg):
    factory, engine = pg
    prefix = "admtest_" + uuid.uuid4().hex[:12]
    password = "synthetic-password-" + uuid.uuid4().hex
    roles = [prefix + suffix for suffix in ("_runtime", "_api", "_worker")]
    with engine.begin() as db:
        schema = db.scalar(sa.text("SELECT current_schema()"))
        owner = db.scalar(sa.text("SELECT current_user"))
        db.execute(sa.text("CREATE TABLE acl_acceptance(id bigserial PRIMARY KEY, value text)"))
    sql = private_database.role_sql("test", schema, owner, {"api": password, "worker": password}, prefix)
    assert password not in sql and "SCRAM-SHA-256" in sql
    try:
        # DBAPI executes PostgreSQL blocks verbatim (not SQLAlchemy bind parsing).
        with engine.connect() as db:
            with db.connection.cursor() as cursor:
                cursor.execute(sql)
            db.commit()
        with engine.connect() as db:
            with db.connection.cursor() as cursor:
                cursor.execute(sql)  # idempotent second pass
            db.commit()
        worker_url = engine.url.set(username=prefix + "_worker", password=password)
        worker = sa.create_engine(worker_url, connect_args={"options": f"-csearch_path={schema}"})
        try:
            with worker.connect() as db:
                assert db.scalar(sa.text("SELECT current_user")) == prefix + "_worker"
                db.execute(sa.text("INSERT INTO acl_acceptance(value) VALUES ('test')"))
                assert db.scalar(sa.text("SELECT count(*) FROM acl_acceptance")) == 1
                db.rollback()
                for forbidden in ("CREATE TABLE forbidden(id int)", "DROP TABLE acl_acceptance", "CREATE ROLE forbidden"):
                    with pytest.raises(sa.exc.DBAPIError):
                        db.execute(sa.text(forbidden))
                    db.rollback()
        finally:
            worker.dispose()
    finally:
        with engine.begin() as db:
            for role in reversed(roles):
                # Only unique test roles, inside test-db; never production.
                if not db.scalar(sa.text("SELECT 1 FROM pg_roles WHERE rolname=:role"), {"role": role}):
                    continue
                db.exec_driver_sql(f'DROP OWNED BY "{role}"')
                db.exec_driver_sql(f'DROP ROLE "{role}"')
