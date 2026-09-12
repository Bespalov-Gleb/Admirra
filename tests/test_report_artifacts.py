"""Shared report HTTP bridge: exact snapshots, rollback and disconnect safety."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from io import BytesIO
import logging
from types import SimpleNamespace
import uuid

import anyio
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
import sqlalchemy as sa
from starlette.requests import ClientDisconnect

from backend_api import artifact_ledger as ledger, artifact_response
from backend_api.reports import artifacts as reports, export_service
from core import models, security
from core.artifact_storage import LocalObjects, ObjectInfo
from core.database import get_db
from core.public_url_logging import PublicURLFilter
from tests.test_artifact_ledger import artifacts
from tests.test_durable_work import pg

PDF = b"%PDF synthetic frozen report"
PNG = b"\x89PNG synthetic frozen image"


@pytest.fixture
def snapshots(artifacts, monkeypatch, tmp_path):
    factory, engine, store, ids, _ = artifacts
    with factory.begin() as db:
        delivery = db.get(models.ReportDelivery, ids["delivery"])
        delivery.pdf_snapshot, delivery.png_snapshot = PDF, PNG
        delivery.snapshot_data = {"frozen": "unchanged"}
        delivery.public_token = "legacy-fixed-capability"
        delivery.public_expires_at = datetime.now(timezone.utc) + timedelta(days=20)
    def storage():
        assert engine.pool.checkedout() == 0
        return LocalObjects(tmp_path / "objects")
    monkeypatch.setattr(artifact_response, "from_environment", storage)
    monkeypatch.setattr("core.artifact_client.from_environment", storage)
    monkeypatch.setenv("SHARED_REPORT_ARTIFACTS", "true")
    return artifacts


@pytest.fixture
def apis(snapshots):
    from backend_api.reports import router as routes
    factory, _, _, ids, _ = snapshots
    owner = SimpleNamespace(id=ids["owner"])
    def database():
        with factory() as db:
            yield db
    def make():
        app = FastAPI()
        app.include_router(routes.router, prefix="/api")
        app.dependency_overrides[get_db] = database
        app.dependency_overrides[security.get_current_user] = lambda: owner
        return TestClient(app)
    with make() as one, make() as two:
        yield one, two


def test_copy_idempotent_preserves_original_snapshot_and_token(snapshots):
    factory, engine, store, ids, _ = snapshots
    class Observed:
        def put(self, info, chunks):
            assert engine.pool.checkedout() == 0
            return store.put(info, chunks)
        def stat(self, key):
            assert engine.pool.checkedout() == 0
            return store.stat(key)
    for _ in range(2):
        assert reports.copy_delivery(factory, Observed(), ids["delivery"])["formats"] == ["pdf", "png"]
    with factory() as db:
        delivery = db.get(models.ReportDelivery, ids["delivery"])
        assert (delivery.pdf_snapshot, delivery.png_snapshot) == (PDF, PNG)
        assert delivery.snapshot_data == {"frozen": "unchanged"}
        assert delivery.public_token == "legacy-fixed-capability"
        assert db.scalar(sa.select(sa.func.count()).select_from(ledger.artifacts)) == 2
        assert db.scalar(sa.select(sa.func.count()).select_from(ledger.references)) == 2


def test_revision_changed_during_copy_never_attaches_stale_snapshot(snapshots):
    factory, _, store, ids, _ = snapshots
    class Changed:
        def put(self, info, chunks):
            result = store.put(info, chunks)
            with factory.begin() as db:
                db.get(models.ReportDelivery, ids["delivery"]).pdf_snapshot = b"new revision"
            return result
    with pytest.raises(ledger.ArtifactConflict):
        reports.copy_delivery(factory, Changed(), ids["delivery"])
    with factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(ledger.references)) == 0
        assert db.get(models.ReportDelivery, ids["delivery"]).pdf_snapshot == b"new revision"


def test_legacy_aggregate_without_historical_scope_is_not_guessed(snapshots):
    factory, _, store, ids, _ = snapshots
    with factory.begin() as db:
        db.get(models.ReportDelivery, ids["delivery"]).client_id = None
    with pytest.raises(ValueError, match="historical scope"):
        reports.copy_delivery(factory, store, ids["delivery"])
    with factory.begin() as db:
        db.get(models.ReportDelivery, ids["delivery"]).snapshot_data = {"_scope_client_ids": [str(ids["project"])]}
    assert reports.copy_delivery(factory, store, ids["delivery"])["formats"] == ["pdf", "png"]


def test_legacy_urls_cross_api_exact_bytes_and_feature_rollback(snapshots, apis, monkeypatch):
    factory, _, store, ids, _ = snapshots
    one, two = apis
    paths = [("/api/reports/deliveries/public/legacy-fixed-capability/pdf", PDF),
             (f'/api/reports/deliveries/{ids["delivery"]}/snapshot.pdf', PDF),
             (f'/api/reports/deliveries/{ids["delivery"]}/snapshot.png', PNG)]
    for path, data in paths:
        assert one.get(path).content == data
    reports.copy_delivery(factory, store, ids["delivery"])
    for path, data in paths:
        response = two.get(path)
        assert response.status_code == 200 and response.content == data
        assert response.headers["cache-control"] == "no-store, private"
        assert int(response.headers["content-length"]) == len(data)
    monkeypatch.setenv("SHARED_REPORT_ARTIFACTS", "false")
    assert one.get(paths[0][0]).content == PDF


def test_changed_draft_does_not_reuse_old_binding(snapshots, apis):
    factory, _, store, ids, _ = snapshots
    reports.copy_delivery(factory, store, ids["delivery"])
    with factory.begin() as db:
        db.get(models.ReportDelivery, ids["delivery"]).pdf_snapshot = b"new exact bytes"
    response = apis[1].get(f'/api/reports/deliveries/{ids["delivery"]}/snapshot.pdf')
    assert response.status_code == 200 and response.content == b"new exact bytes"


def test_valid_binding_storage_failure_is_503_not_legacy_fallback(snapshots, apis):
    factory, _, store, ids, _ = snapshots
    reports.copy_delivery(factory, store, ids["delivery"])
    with factory() as db:
        id = db.scalar(sa.select(ledger.references.c.artifact_id).where(ledger.references.c.format == "pdf"))
    store.delete(str(id))
    response = apis[0].get("/api/reports/deliveries/public/legacy-fixed-capability/pdf")
    assert response.status_code == 503 and PDF not in response.content


def test_shared_snapshot_rechecks_current_owner_access(snapshots, apis):
    factory, _, store, ids, _ = snapshots
    reports.copy_delivery(factory, store, ids["delivery"])
    with factory.begin() as db:
        db.get(models.User, ids["owner"]).is_active = False
    response = apis[1].get("/api/reports/deliveries/public/legacy-fixed-capability/pdf")
    assert response.status_code == 404


def test_durable_file_link_survives_cache_reset_flags_and_revoke(snapshots, apis, monkeypatch):
    factory, _, _, ids, _ = snapshots
    monkeypatch.setenv("DURABLE_REPORT_FILES", "true")
    token = export_service.save_report_for_link("pdf", PDF, "2026-09-01", "2026-09-10",
        db_factory=factory, user_id=ids["owner"], scope_ids=[ids["project"]], request_key="synthetic")
    assert token.startswith("f1_")
    export_service._report_file_cache.clear()
    path = "/api/reports/file/" + token
    assert apis[0].get(path).content == PDF
    monkeypatch.setenv("DURABLE_REPORT_FILES", "false")
    monkeypatch.setenv("LEGACY_REPORT_LINK_READS", "false")
    assert apis[1].get(path).content == PDF
    with factory() as db:
        link = db.execute(sa.select(ledger.file_links)).mappings().one()
        assert token not in str(link)
    listing = apis[0].get("/api/reports/file-links").json()["items"]
    assert listing[0]["link_id"] == str(link["id"])
    assert set(listing[0]) == {"link_id", "created_at", "expires_at", "revoked_at"}
    assert apis[1].get("/api/reports/file-links", params={"before": str(link["id"])}).json()["items"] == []
    with factory() as db:
        assert ledger.list_links(db, ids["other"]) == []
    assert apis[0].delete(f'/api/reports/file-links/{link["id"]}').status_code == 204
    assert apis[1].get(path).status_code == 404


@pytest.mark.parametrize("metadata", [{}, {"scope_ids": []}, {"format_type": "html"}, {"ttl_seconds": 86401}])
def test_file_link_rejects_invalid_contract_before_storage(monkeypatch, metadata):
    monkeypatch.setenv("DURABLE_REPORT_FILES", "true")
    monkeypatch.setattr("core.artifact_client.from_environment", lambda: pytest.fail("must validate before IO"))
    args = dict(format_type="pdf", file_bytes=PDF, start_date="a", end_date="b")
    if metadata:
        args.update(db_factory=object(), user_id=uuid.uuid4(), scope_ids=[uuid.uuid4()])
        args.update(metadata)
    with pytest.raises(ValueError):
        export_service.save_report_for_link(**args)


def test_response_disconnect_and_cancel_release_storage_and_capacity():
    for mode in ("disconnect", "cancel"):
        events = []
        class Storage:
            @contextmanager
            def open(self, *args, **kwargs):
                events.append("open")
                with BytesIO(b"abc") as stream:
                    try:
                        yield stream, None
                    finally:
                        events.append("closed stream")
            def close(self):
                events.append("closed client")
        info = ObjectInfo(str(uuid.uuid4()), 3, "a" * 64)
        response = artifact_response.ArtifactResponse(info, "application/pdf", "report.pdf", storage_factory=Storage)
        assert not events  # no resources allocated for a response that is never sent
        async def run():
            async def receive():
                await anyio.sleep_forever()
            with anyio.CancelScope() as cancel:
                async def send(message):
                    if message["type"] == "http.response.body":
                        if mode == "disconnect":
                            raise OSError("client disconnected")
                        cancel.cancel()
                        await anyio.sleep(0)
                if mode == "disconnect":
                    with pytest.raises(ClientDisconnect):
                        await response({"type": "http", "asgi": {"spec_version": "2.4"}}, receive, send)
                else:
                    await response({"type": "http", "asgi": {"spec_version": "2.4"}}, receive, send)
        anyio.run(run)
        assert events == ["open", "closed stream", "closed client"]
        assert artifact_response._downloads.acquire(False)
        assert artifact_response._downloads.acquire(False)
        artifact_response._downloads.release()
        artifact_response._downloads.release()


def test_response_busy_rejects_before_open():
    info = ObjectInfo(str(uuid.uuid4()), 1, "a" * 64)
    response = artifact_response.ArtifactResponse(info, "application/pdf", "report.pdf",
        storage_factory=lambda: pytest.fail("must not open a third download"))
    artifact_response._downloads.acquire()
    artifact_response._downloads.acquire()
    sent = []
    async def send(message):
        sent.append(message)
    try:
        anyio.run(response, {"type": "http"}, None, send)
    finally:
        artifact_response._downloads.release()
        artifact_response._downloads.release()
    assert sent[0]["status"] == 503


def test_file_capabilities_redacted_in_log_args():
    token = "f1_" + "a" * 43
    record = logging.LogRecord("api", logging.INFO, __file__, 1, "file %s", (token,), None)
    PublicURLFilter().filter(record)
    assert token not in record.getMessage()


def test_migration_inventory_is_read_only_and_does_not_create_metadata(snapshots):
    from ops.migrate_report_artifacts import inventory
    factory, _, _, _, _ = snapshots
    assert inventory(factory) == {"deliveries": 1, "frozen_pdfs": 1, "scope_candidates": 1,
                                  "pdf_bytes": len(PDF), "png_bytes": len(PNG)}
    with factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(ledger.artifacts)) == 0


def test_migration_cli_never_defaults_to_bulk_apply():
    from ops.migrate_report_artifacts import arguments
    assert arguments([]).apply is False
    id = str(uuid.uuid4())
    for argv in (["--apply"], ["--delivery-id", id], ["--apply"] + ["--delivery-id", id] * 21):
        with pytest.raises(SystemExit):
            arguments(argv)
    assert arguments(["--apply", "--delivery-id", id]).delivery_id == [uuid.UUID(id)]


def test_pdf_builder_freezes_exact_aggregation_scope(monkeypatch):
    from backend_api.reports import pdf_service
    scope = [uuid.uuid4(), uuid.uuid4()]
    calls = []
    def resolve(*args):
        calls.append("scope")
        return scope
    def summary(db, ids, *args):
        assert ids is scope
        return {"leads": 3}
    def campaigns(db, ids, *args):
        assert ids is scope
        return []
    monkeypatch.setattr(pdf_service.StatsService, "get_effective_client_ids", resolve)
    monkeypatch.setattr(pdf_service.StatsService, "aggregate_summary", summary)
    monkeypatch.setattr(pdf_service.StatsService, "get_campaign_stats", campaigns)
    raw, data = pdf_service.generate_report_pdf(object(), uuid.uuid4(), None, "2026-09-01", "2026-09-10",
        sections=["kpi"], render_pdf=False, return_data=True)
    assert raw == b"" and data["_scope_client_ids"] == [str(id) for id in scope]
    assert calls == ["scope"]
