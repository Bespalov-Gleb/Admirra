from datetime import datetime, timedelta, timezone
import uuid

import pytest
import sqlalchemy as sa

from automation import vk_maintenance as work
from automation.work_tables import jobs
from core import models
from tests.test_durable_work import pg


@pytest.fixture
def drafts(pg):
    factory, engine = pg
    models.Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with factory.begin() as db:
        owner = models.User(email="vk-maintenance@example.test", password_hash="synthetic")
        db.add(owner)
        db.flush()
        client = models.Client(name="Synthetic", owner_id=owner.id)
        db.add(client)
        db.flush()
        for i in range(1, 206):
            db.add(models.Integration(id=uuid.UUID(int=i), client_id=client.id,
                platform=models.IntegrationPlatform.VK_ADS, connection_status="awaiting_auth",
                link_created_at=now - timedelta(days=8), link_expires_at=now - timedelta(days=1),
                link_token="synthetic-token", link_token_hash=f"synthetic-{i}"))
    return factory, {"scheduled_at": now.isoformat()}


def test_link_cleanup_is_bounded_replayable_and_keeps_recent_drafts(drafts):
    factory, payload = drafts
    assert work.run_page(factory, payload) == {"scanned": 100, "expired": 100, "removed": 0, "has_next": True}
    assert work.run_page(factory, payload)["expired"] == 0
    for cursor in (100, 200):
        with factory() as db:
            continuation = db.scalar(sa.select(jobs.c.payload).where(
                jobs.c.payload["cursor"].astext == str(uuid.UUID(int=cursor))))
        assert continuation
        work.run_page(factory, continuation)
    with factory() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(models.Integration)) == 205
        assert db.scalar(sa.select(sa.func.count()).select_from(models.Integration).where(
            models.Integration.connection_status == "link_expired", models.Integration.link_token.is_(None),
            models.Integration.link_token_hash.is_(None))) == 205
        assert db.scalar(sa.select(sa.func.count()).select_from(jobs)) == 2


def test_old_drafts_deleted_but_authorized_integrations_preserved(drafts):
    factory, payload = drafts
    with factory.begin() as db:
        for i in (1, 2):
            db.get(models.Integration, uuid.UUID(int=i)).link_created_at = datetime.now(timezone.utc) - timedelta(days=31)
        db.get(models.Integration, uuid.UUID(int=2)).connection_status = "active"
    assert work.run_page(factory, payload)["removed"] == 1
    with factory() as db:
        assert db.get(models.Integration, uuid.UUID(int=1)) is None
        assert db.get(models.Integration, uuid.UUID(int=2)).connection_status == "active"


def test_cleanup_failure_does_not_claim_success_or_commit_partial_expiry(drafts, monkeypatch):
    factory, payload = drafts
    def fail(*_, **__):
        raise RuntimeError("synthetic outbox failure")
    monkeypatch.setattr(work, "submit", fail)
    with pytest.raises(RuntimeError):
        work.run_page(factory, payload)
    with factory() as db:
        assert db.get(models.Integration, uuid.UUID(int=1)).connection_status == "awaiting_auth"
        assert db.scalar(sa.select(sa.func.count()).select_from(jobs)) == 0


def test_cleanup_skips_inflight_oauth_row_and_revisits_next_tick(drafts):
    factory, payload = drafts
    with factory.begin() as callback:
        callback.scalar(sa.select(models.Integration).where(models.Integration.id == uuid.UUID(int=1)).with_for_update())
        assert work.run_page(factory, payload)["scanned"] == 100
        assert callback.get(models.Integration, uuid.UUID(int=1)).connection_status == "awaiting_auth"
    work.run_page(factory, {"scheduled_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()})
    with factory() as db:
        assert db.get(models.Integration, uuid.UUID(int=1)).connection_status == "link_expired"
