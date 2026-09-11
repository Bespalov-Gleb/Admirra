"""HTML capabilities across API instances, using isolated real PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
import hashlib
import importlib.util
import json
import logging
from pathlib import Path
import subprocess
import sys
import uuid

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from backend_api.reports import public_links as shares
from core import models, security
from core.database import get_db
from core.public_url_logging import PublicURLFilter, redact
from tests.test_durable_work import pg


@pytest.fixture
def shared(pg):
    factory, engine = pg
    models.Base.metadata.create_all(engine)
    spec = importlib.util.spec_from_file_location("public_links_migration", Path(__file__).resolve().parents[1] /
        "alembic/versions/ab7c8d9e0f1a_durable_public_report_links.py")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.begin() as db:
        with Operations.context(MigrationContext.configure(db)):
            migration.upgrade()
    with factory.begin() as db:
        owner = models.User(email="owner@example.test", password_hash="test-only", is_active=True)
        other = models.User(email="other@example.test", password_hash="test-only", is_active=True)
        db.add_all([owner, other])
        db.flush()
        project = models.Client(owner_id=owner.id, name="Synthetic project")
        foreign = models.Client(owner_id=other.id, name="Not yours")
        db.add_all([project, foreign])
        db.flush()
        ids = {"owner": owner.id, "other": other.id, "project": project.id, "foreign": foreign.id}
    return factory, engine, migration, ids


def snapshot():
    return {"summary": {"expenses": 100, "leads": 3}, "top_campaigns": [],
            "client_name": "Synthetic project", "ai_comment": "Already generated",
            "start_date": "2026-09-01", "end_date": "2026-09-10", "generated_at": "2026-09-11 12:00"}


@pytest.mark.parametrize("folder", [None, "synthetic-folder"])
def test_snapshot_scope_is_the_scope_used_for_aggregation(monkeypatch, folder):
    from backend_api.reports import export_service as export
    scope = [uuid.uuid4(), uuid.uuid4()]
    calls = []
    def resolve(*args):
        calls.append("resolve")
        return scope
    def summary(db, ids, *args):
        assert ids is scope
        return {"leads": 3}
    def campaigns(db, ids, *args):
        assert ids is scope
        return []
    monkeypatch.setattr(export.StatsService, "get_effective_client_ids", resolve)
    monkeypatch.setattr(export.StatsService, "resolve_folder_client_ids", resolve)
    monkeypatch.setattr(export.StatsService, "aggregate_summary", summary)
    monkeypatch.setattr(export.StatsService, "get_campaign_stats", campaigns)
    args = (object(), uuid.uuid4(), None, "2026-09-01", "2026-09-10", "")
    legacy = export._get_report_data(*args, folder_id=folder)
    durable = export._get_report_data(*args, folder_id=folder, include_scope=True)
    assert len(legacy) == 6 and durable[:-1] == legacy
    assert durable[-1] is scope
    assert calls == ["resolve", "resolve"]  # exactly once per report, never reconstructed later


def create(shared, **kwargs):
    factory, _, _, ids = shared
    with factory.begin() as db:
        return shares.create(db, kwargs.pop("creator", ids["owner"]), kwargs.pop("scope", [ids["project"]]),
                             kwargs.pop("snapshot", snapshot()), **kwargs)


def test_snapshot_persistent_across_independent_connections_and_process_cache_reset(shared):
    factory, engine, _, ids = shared
    data = snapshot()
    link = create(shared, snapshot=data)
    data["summary"]["leads"] = 999
    from backend_api.reports import export_service
    export_service._report_view_cache.clear()
    with factory() as db:
        schema = db.scalar(sa.text("SELECT current_schema()"))
    other_engine = sa.create_engine(engine.url, connect_args={"options": "-csearch_path=" + schema})
    try:
        with sessionmaker(bind=other_engine)() as db:
            assert shares.read(db, link["token"]) == snapshot()
        with factory() as db:
            stored = dict(db.execute(sa.select(shares.links)).mappings().one())
            assert stored["creator_id"] == ids["owner"]
            assert stored["token_hash"] == hashlib.sha256(link["token"].encode()).hexdigest()
            assert link["token"] not in str(stored)
            assert stored["snapshot_bytes"] == len(shares._encode(snapshot()))
    finally:
        other_engine.dispose()


def test_rollback_publishes_no_capability(shared):
    factory, _, _, ids = shared
    with factory() as db:
        link = shares.create(db, ids["owner"], [ids["project"]], snapshot())
        db.rollback()
    with factory() as db, pytest.raises(shares.LinkUnavailable):
        shares.read(db, link["token"])


@pytest.mark.parametrize("ttl", [0, -1, True, 86401, "60"])
def test_ttl_is_bounded(shared, ttl):
    with pytest.raises(ValueError):
        create(shared, ttl_seconds=ttl)


def test_invalid_unknown_and_expired_tokens_are_opaque(shared):
    factory, _, _, _ = shared
    link = create(shared, ttl_seconds=1)
    with factory() as db:
        for token in ("", "../etc/passwd", "r1_bad", "r1_" + "x" * 10000, "r1_" + "A" * 43):
            with pytest.raises(shares.LinkUnavailable):
                shares.read(db, token)
    with factory.begin() as db:
        db.execute(shares.links.update().values(created_at=sa.func.now() - sa.text("interval '1 day'"),
                                               expires_at=sa.func.now() - sa.text("interval '1 second'")))
    with factory() as db, pytest.raises(shares.LinkUnavailable):
        shares.read(db, link["token"])


def test_revoke_owner_only_and_idempotent(shared):
    factory, _, _, ids = shared
    link = create(shared)
    with factory.begin() as db:
        with pytest.raises(shares.LinkUnavailable):
            shares.revoke(db, uuid.UUID(link["link_id"]), ids["other"])
    for _ in range(2):
        with factory.begin() as db:
            shares.revoke(db, uuid.UUID(link["link_id"]), ids["owner"])
    with factory() as db, pytest.raises(shares.LinkUnavailable):
        shares.read(db, link["token"])


@pytest.mark.parametrize("change", ["disable_creator", "disable_account", "remove_share", "remove_membership", "delete_project", "change_account"])
def test_existing_links_stop_disclosing_after_rights_change(shared, change):
    factory, _, _, ids = shared
    with factory.begin() as db:
        member = models.User(email="member@example.test", password_hash="test-only", is_active=True)
        db.add(member)
        db.flush()
        membership = models.TeamMember(account_id=ids["owner"], user_id=member.id, email=member.email,
            role=models.TeamMemberRole.MEMBER, status=models.TeamMemberStatus.ACTIVE)
        db.add(membership)
        db.flush()
        db.add(models.TeamMemberProject(team_member_id=membership.id, project_id=ids["project"]))
        member_id, membership_id = member.id, membership.id
    link = create(shared, creator=member_id)
    with factory() as db:
        assert shares.read(db, link["token"]) == snapshot()
    with factory.begin() as db:
        if change.startswith("disable"):
            db.execute(sa.update(models.User).where(models.User.id == (member_id if change == "disable_creator" else ids["owner"]))
                       .values(is_active=False))
        elif change == "remove_share":
            db.execute(sa.delete(models.TeamMemberProject).where(models.TeamMemberProject.team_member_id == membership_id))
        elif change == "remove_membership":
            db.execute(sa.delete(models.TeamMember).where(models.TeamMember.id == membership_id))
        elif change == "delete_project":
            db.execute(sa.delete(models.Client).where(models.Client.id == ids["project"]))
        else:
            db.execute(sa.update(models.TeamMember).where(models.TeamMember.id == membership_id).values(account_id=ids["other"]))
    with factory() as db, pytest.raises(shares.LinkUnavailable):
        shares.read(db, link["token"])


def test_scope_cannot_include_foreign_or_empty_projects(shared):
    *_, ids = shared
    with pytest.raises(shares.LinkUnavailable):
        create(shared, scope=[ids["project"], ids["foreign"]])
    with pytest.raises(ValueError):
        create(shared, scope=[])


def test_concurrent_creations_respect_global_per_creator_limit(shared, monkeypatch):
    factory, _, _, _ = shared
    monkeypatch.setattr(shares, "MAX_ACTIVE_LINKS", 2)
    def attempt(_):
        try:
            return create(shared)["link_id"]
        except shares.LinkLimitReached:
            return None
    with ThreadPoolExecutor(6) as pool:
        results = list(pool.map(attempt, range(6)))
    assert sum(value is not None for value in results) == 2
    with factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(shares.links)) == 2


def test_revoke_does_not_allow_unlimited_daily_snapshot_writes(shared, monkeypatch):
    factory, _, _, ids = shared
    monkeypatch.setattr(shares, "MAX_DAILY_LINKS", 1)
    link = create(shared)
    with factory.begin() as db:
        shares.revoke(db, uuid.UUID(link["link_id"]), ids["owner"])
    with pytest.raises(shares.LinkLimitReached):
        create(shared)


def test_normalization_size_bounds_and_integrity(shared, monkeypatch):
    factory, _, _, _ = shared
    data = snapshot() | {"value": Decimal("1.25"), "date": date(2026, 9, 11)}
    link = create(shared, snapshot=data)
    with factory() as db:
        assert shares.read(db, link["token"])["value"] == 1.25
    for data in ({"n": float("nan")}, {"n": float("inf")}, ["not an object"], {"n": object()}):
        with pytest.raises(ValueError):
            create(shared, snapshot=data)
    monkeypatch.setattr(shares, "MAX_SNAPSHOT_BYTES", 100)
    with pytest.raises(ValueError):
        create(shared)
    monkeypatch.setattr(shares, "MAX_SNAPSHOT_BYTES", 1024 * 1024)
    with factory.begin() as db:
        tampered = json.dumps({"tampered": True})
        db.execute(shares.links.update().values(snapshot=tampered, snapshot_bytes=len(tampered.encode())))
    with factory() as db, pytest.raises(shares.SnapshotCorrupt):
        shares.read(db, link["token"])


def test_listing_never_discloses_tokens_or_other_users_and_cursor_is_scoped(shared):
    factory, _, _, ids = shared
    first, second = create(shared), create(shared)
    other = create(shared, creator=ids["other"], scope=[ids["foreign"]])
    with factory() as db:
        page = shares.list_owned(db, ids["owner"], limit=1)
        assert str(page[0]["link_id"]) == second["link_id"]
        assert shares.list_owned(db, ids["owner"], limit=1, before=page[0]["link_id"])[0]["link_id"] == uuid.UUID(first["link_id"])
        assert set(page[0]) == {"link_id", "created_at", "expires_at", "revoked_at"}
        with pytest.raises(shares.LinkUnavailable):
            shares.list_owned(db, ids["owner"], before=uuid.UUID(other["link_id"]))


def test_number_spelling_and_snapshot_survive_fresh_python_processes(shared):
    factory, _, _, _ = shared
    data = snapshot() | {"small": 1e-10, "large": 1e20, "minus_zero": -0.0, "exact": 9007199254740993}
    link = create(shared, snapshot=data)
    with factory() as db:
        schema = db.scalar(sa.text("SELECT current_schema()"))
    script = """
import json, os, sys
import sqlalchemy as sa
from sqlalchemy.orm import Session
from backend_api.reports.public_links import read
args = json.load(sys.stdin)
engine = sa.create_engine(os.environ['ISOLATED_POSTGRES_URL'], connect_args={'options': '-csearch_path=' + args['schema']})
with Session(engine) as db:
    assert read(db, args['token']) == args['expected']
engine.dispose()
print('fresh-process-read: passed')
"""
    for _ in range(2):
        result = subprocess.run([sys.executable, "-c", script], input=json.dumps({"schema": schema,
            "token": link["token"], "expected": data}), text=True, capture_output=True, timeout=20)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip().endswith("fresh-process-read: passed")


def test_deleted_creator_cascades_links(shared):
    factory, _, _, ids = shared
    link = create(shared)
    with factory.begin() as db:
        db.execute(sa.delete(models.Client).where(models.Client.id == ids["project"]))
        db.execute(sa.delete(models.User).where(models.User.id == ids["owner"]))
    with factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(shares.links)) == 0
        with pytest.raises(shares.LinkUnavailable):
            shares.read(db, link["token"])


def test_schema_checks_downgrade_guard_cascade_and_bounded_retention(shared):
    factory, engine, migration, ids = shared
    live = create(shared)
    dead = [create(shared), create(shared)]
    shares.check_schema(engine)
    with engine.begin() as db, Operations.context(MigrationContext.configure(db)):
        with pytest.raises(RuntimeError):
            migration.downgrade()
    with factory.begin() as db:
        db.execute(shares.links.update().where(shares.links.c.id.in_([uuid.UUID(item["link_id"]) for item in dead]))
            .values(created_at=sa.func.now() - sa.text("interval '10 days'"), expires_at=sa.func.now() - sa.text("interval '9 days'")))
        assert shares.prune(db, limit=1) == 1
    with factory.begin() as db:
        assert shares.prune(db) == 1
        assert shares.read(db, live["token"]) == snapshot()
        shares.revoke(db, uuid.UUID(live["link_id"]), ids["owner"])
    with engine.begin() as db, Operations.context(MigrationContext.configure(db)):
        migration.downgrade()
        migration.upgrade()


@pytest.fixture
def api_pair(shared, monkeypatch):
    from backend_api.reports import router as routes
    factory, _, _, ids = shared
    monkeypatch.setenv("DURABLE_REPORT_LINKS", "true")
    monkeypatch.setenv("LEGACY_REPORT_LINK_READS", "false")
    with factory() as db:
        owner = db.get(models.User, ids["owner"])
        db.expunge(owner)
    def database():
        with factory() as db:
            yield db
    def report(*args, **kwargs):
        assert kwargs["include_scope"] is True
        data = snapshot()
        return data["summary"], [], data["client_name"], "", data["start_date"], data["end_date"], [ids["project"]]
    monkeypatch.setattr(routes, "_get_report_data", report)
    def make():
        app = FastAPI()
        app.include_router(routes.router, prefix="/api")
        app.dependency_overrides[get_db] = database
        app.dependency_overrides[security.get_current_user] = lambda: owner
        return TestClient(app)
    with make() as one, make() as two:
        yield one, two, routes


def test_http_two_apis_create_read_revoke_and_rollback_mode(api_pair, monkeypatch):
    one, two, _ = api_pair
    made = one.post("/api/reports/link", json={"start_date": "2026-09-01", "end_date": "2026-09-10", "comment": "<script>alert(1)</script>"})
    assert made.status_code == 200
    assert made.headers["cache-control"] == "no-store, private"
    body = made.json()
    response = two.get(body["url"])
    assert response.status_code == 200
    assert "&lt;script&gt;" in response.text and "<script>alert(1)</script>" not in response.text
    for key, value in shares.PRIVATE_HEADERS.items():
        assert response.headers[key] == value
    monkeypatch.setenv("DURABLE_REPORT_LINKS", "false")
    assert two.get(body["url"]).status_code == 200  # disabling new creation does not break durable reads
    paused = one.post("/api/reports/link", json={"start_date": "2026-09-01", "end_date": "2026-09-10"})
    assert paused.status_code == 503 and "token" not in paused.json()
    assert paused.headers["cache-control"] == "no-store, private"
    listing = one.get("/api/reports/links").json()
    assert body["token"] not in str(listing)
    assert two.delete("/api/reports/links/" + body["link_id"]).status_code == 204
    assert one.get(body["url"]).status_code == 404
    assert one.get("/api/reports/view/legacy-token").status_code == 404


def test_http_database_failure_is_503_not_fake_404_or_legacy_fallback(api_pair, monkeypatch):
    _, two, routes = api_pair
    def unavailable(*args):
        raise sa.exc.OperationalError("secret DSN", {}, Exception("private details"))
    monkeypatch.setattr(shares, "read", unavailable)
    response = two.get("/api/reports/view/r1_" + "A" * 43)
    assert response.status_code == 503
    assert "private" not in response.text and "DSN" not in response.text
    assert response.headers["cache-control"] == "no-store, private"


def test_durable_creation_never_succeeds_before_commit(api_pair, shared, monkeypatch):
    one, _, routes = api_pair
    factory, _, _, _ = shared
    def database():
        with factory() as db:
            def fail():
                raise sa.exc.OperationalError("private", {}, Exception("private"))
            db.commit = fail
            yield db
    one.app.dependency_overrides[get_db] = database
    response = one.post("/api/reports/link", json={"start_date": "2026-09-01", "end_date": "2026-09-10"})
    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store, private"
    assert "token" not in response.json()
    with factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(shares.links)) == 0


def test_public_paths_redacted_in_uvicorn_and_application_records():
    token = "r1_" + "A" * 43
    for url in (f"/api/reports/view/{token}", "/api/reports/file/legacy-uuid", "/api/reports/deliveries/public/secret/pdf"):
        record = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %d',
                                   ("127.0.0.1", "GET", url, "1.1", 200), None)
        PublicURLFilter().filter(record)
        assert "[redacted]" in record.getMessage()
        assert url not in record.getMessage()
        assert record.args[-1] == 200
    assert token not in redact("error " + token)
    assert redact("/api/dashboard/summary") == "/api/dashboard/summary"
