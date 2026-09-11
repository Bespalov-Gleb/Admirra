"""Real isolated PostgreSQL + filesystem, transaction gaps and cleanup fences."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import hashlib
import importlib.util
from io import BytesIO
from pathlib import Path
import uuid

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
import sqlalchemy as sa

from core import models
from core.artifact_storage import LocalObjects, ObjectMissing, StorageUnavailable
from backend_api import artifact_ledger as ledger
from backend_api.artifact_workflow import persist, cleanup
from backend_api.reports.public_links import LinkUnavailable
from tests.test_durable_work import pg


@pytest.fixture
def artifacts(pg, tmp_path):
    factory, engine = pg
    models.Base.metadata.create_all(engine)
    spec = importlib.util.spec_from_file_location("artifact_migration", Path(__file__).resolve().parents[1] /
        "alembic/versions/bc8d9e0f1a2b_artifact_lifecycle.py")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.begin() as db, Operations.context(MigrationContext.configure(db)):
        migration.upgrade()
    with factory.begin() as db:
        owner = models.User(email="artifact-owner@example.test", password_hash="test", is_active=True)
        other = models.User(email="artifact-other@example.test", password_hash="test", is_active=True)
        db.add_all([owner, other])
        db.flush()
        project = models.Client(owner_id=owner.id, name="Synthetic")
        db.add(project)
        db.flush()
        delivery = models.ReportDelivery(user_id=owner.id, client_id=project.id,
            start_date=date(2026, 9, 1), end_date=date(2026, 9, 10))
        db.add(delivery)
        db.flush()
        ids = dict(owner=owner.id, other=other.id, project=project.id, delivery=delivery.id)
    root = tmp_path / "objects"
    root.mkdir()
    store = LocalObjects(root)
    try:
        yield factory, engine, store, ids, migration
    finally:
        store.close()


DATA = b"a fixed report snapshot"
DIGEST = hashlib.sha256(DATA).hexdigest()


def reserve(factory, ids, key="one"):
    with factory.begin() as db:
        return ledger.reserve(db, ids["owner"], [ids["project"]], "report_pdf", len(DATA), DIGEST, key)


def save(artifacts, key="one", storage=None):
    factory, _, store, ids, _ = artifacts
    return persist(factory, storage or store, ids["owner"], [ids["project"]], "report_pdf", BytesIO(DATA), key)


def expire(db, id, state="uploading"):
    if state == "ready":
        values = dict(created_at=sa.func.now() - sa.text("interval '4 days'"), expires_at=sa.func.now() - sa.text("interval '1 day'"))
    else:
        values = dict(lease_until=sa.func.now() - sa.text("interval '1 minute'"))
    db.execute(ledger.artifacts.update().where(ledger.artifacts.c.id == id).values(**values))


def test_workflow_releases_sql_connection_during_storage_io(artifacts):
    factory, engine, store, ids, _ = artifacts
    class Observed:
        def put(self, info, chunks):
            assert engine.pool.checkedout() == 0
            with factory() as db:
                assert db.scalar(sa.select(ledger.artifacts.c.state).where(ledger.artifacts.c.id == uuid.UUID(info.key))) == "uploading"
            return store.put(info, chunks)
        def stat(self, key):
            assert engine.pool.checkedout() == 0
            return store.stat(key)
    first = save(artifacts, storage=Observed())
    second = save(artifacts, storage=Observed())
    assert first["id"] == second["id"] and second["state"] == "ready"
    with store.open(str(first["id"]), expected=ledger.descriptor(first)) as (stream, _):
        assert stream.read() == DATA


def test_unknown_storage_result_retry_is_same_immutable_object(artifacts):
    factory, _, store, ids, _ = artifacts
    class LostReply:
        def put(self, info, chunks):
            store.put(info, chunks)
            raise StorageUnavailable()
    with pytest.raises(StorageUnavailable):
        save(artifacts, storage=LostReply())
    first = reserve(factory, ids)
    assert first["state"] == "uploading"
    with factory() as db, pytest.raises(LinkUnavailable):
        ledger.create_link(db, first["id"], ids["owner"])
    retry = save(artifacts)
    assert retry["id"] == first["id"] and retry["state"] == "ready"


def test_idempotency_key_cannot_change_bytes_scope_or_owner(artifacts):
    factory, _, _, ids, _ = artifacts
    first = save(artifacts)
    with factory.begin() as db, pytest.raises(ledger.ArtifactConflict):
        ledger.reserve(db, ids["owner"], [ids["project"]], "report_pdf", 1, "a" * 64, "one")
    with factory.begin() as db, pytest.raises(LinkUnavailable):
        ledger.reserve(db, ids["other"], [ids["project"]], "report_pdf", len(DATA), DIGEST, "one")
    with factory() as db, pytest.raises(LinkUnavailable):
        ledger.owned(db, first["id"], ids["other"])


def test_concurrent_reservations_and_account_pending_quota(artifacts):
    factory, _, _, ids, _ = artifacts
    with ThreadPoolExecutor(6) as pool:
        same = list(pool.map(lambda _: reserve(factory, ids), range(6)))
    assert len({row["id"] for row in same}) == 1
    def attempt(i):
        try:
            return reserve(factory, ids, str(i))["id"]
        except ledger.ArtifactLimit:
            return None
    with ThreadPoolExecutor(6) as pool:
        results = list(pool.map(attempt, range(12)))
    assert sum(value is not None for value in results) == 7


def test_cleanup_fences_expired_upload_and_recovery_is_idempotent(artifacts):
    factory, _, store, ids, _ = artifacts
    old = reserve(factory, ids)
    store.put(ledger.descriptor(old), [DATA])
    with factory.begin() as db:
        expire(db, old["id"])
        deletion = ledger.claim_cleanup(db)[0]
    with factory.begin() as db, pytest.raises(ledger.ArtifactConflict):
        ledger.finalize(db, old["id"], ids["owner"], old["generation"], ledger.descriptor(old))
    store.delete(str(old["id"]))
    # Death after remote tombstone, before metadata commit; expired cleanup resumes.
    with factory.begin() as db:
        expire(db, old["id"])
    assert cleanup(factory, store) == 1
    with factory() as db:
        assert db.scalar(sa.select(ledger.artifacts.c.state).where(ledger.artifacts.c.id == old["id"])) == "deleted"
    with factory.begin() as db, pytest.raises(ledger.ArtifactConflict):
        ledger.finish_cleanup(db, old["id"], deletion["generation"])
    with pytest.raises(ObjectMissing):
        store.stat(str(old["id"]))


def test_renewed_upload_generation_rejects_old_finalizer(artifacts):
    factory, _, _, ids, _ = artifacts
    old = reserve(factory, ids)
    with factory.begin() as db:
        expire(db, old["id"])
    current = reserve(factory, ids)
    assert current["generation"] == old["generation"] + 1
    with factory.begin() as db, pytest.raises(ledger.ArtifactConflict):
        ledger.finalize(db, old["id"], ids["owner"], old["generation"], ledger.descriptor(old))
    assert save(artifacts)["state"] == "ready"


def test_report_refs_and_active_links_pin_objects_and_close_after_revoke(artifacts):
    factory, _, store, ids, _ = artifacts
    report, shared, orphan = (save(artifacts, key) for key in ("report", "shared", "orphan"))
    with factory.begin() as db:
        ledger.attach_report(db, ids["delivery"], ids["owner"], "pdf", report["id"], DIGEST)
        link = ledger.create_link(db, shared["id"], ids["owner"])
        for row in (report, shared, orphan):
            expire(db, row["id"], "ready")
    assert cleanup(factory, store) == 1
    with factory() as db:
        assert ledger.linked_report(db, ids["delivery"], ids["owner"], "pdf", DIGEST)["id"] == report["id"]
        assert ledger.linked_report(db, ids["delivery"], ids["owner"], "pdf", "b" * 64) is None
        assert ledger.resolve_link(db, link["token"])["id"] == shared["id"]
        stored = db.execute(sa.select(ledger.file_links)).mappings().one()
        assert link["token"] not in str(stored)
    with factory.begin() as db:
        ledger.revoke_link(db, uuid.UUID(link["link_id"]), ids["owner"])
    assert cleanup(factory, store) == 1
    with factory() as db, pytest.raises(LinkUnavailable):
        ledger.resolve_link(db, link["token"])
    assert store.stat(str(report["id"])) == ledger.descriptor(report)


def test_rights_revoked_after_upload_prevent_publication(artifacts):
    factory, _, store, ids, _ = artifacts
    class RevokeAfterPut:
        def put(self, info, chunks):
            result = store.put(info, chunks)
            with factory.begin() as db:
                db.execute(sa.update(models.User).where(models.User.id == ids["owner"]).values(is_active=False))
            return result
    with pytest.raises(LinkUnavailable):
        save(artifacts, storage=RevokeAfterPut())
    with factory() as db:
        assert db.scalar(sa.select(ledger.artifacts.c.state)) == "uploading"


def test_public_capability_rechecks_rights_and_revoke_is_owner_only(artifacts):
    factory, _, _, ids, _ = artifacts
    row = save(artifacts)
    with factory.begin() as db:
        link = ledger.create_link(db, row["id"], ids["owner"])
    with factory.begin() as db, pytest.raises(LinkUnavailable):
        ledger.revoke_link(db, uuid.UUID(link["link_id"]), ids["other"])
    with factory.begin() as db:
        db.execute(sa.update(models.User).where(models.User.id == ids["owner"]).values(is_active=False))
    with factory() as db, pytest.raises(LinkUnavailable):
        ledger.resolve_link(db, link["token"])
    with factory.begin() as db:
        ledger.revoke_link(db, uuid.UUID(link["link_id"]), ids["owner"])


def test_cleanup_claim_prevents_late_report_attachment(artifacts):
    factory, _, _, ids, _ = artifacts
    row = save(artifacts)
    with factory.begin() as db:
        expire(db, row["id"], "ready")
    with factory.begin() as db:
        assert len(ledger.claim_cleanup(db)) == 1
    with factory.begin() as db, pytest.raises(LinkUnavailable):
        ledger.attach_report(db, ids["delivery"], ids["owner"], "pdf", row["id"], DIGEST)


def test_migration_guard_and_missing_artifact_not_false_idempotent_success(artifacts):
    factory, engine, store, ids, migration = artifacts
    row = save(artifacts)
    ledger.check_schema(engine)
    with engine.begin() as db, Operations.context(MigrationContext.configure(db)), pytest.raises(RuntimeError):
        migration.downgrade()
    store.delete(str(row["id"]))
    with pytest.raises(StorageUnavailable):
        save(artifacts)
