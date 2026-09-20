"""An agency cannot evade its worker quota by using different projects."""
import pytest
import sqlalchemy as sa

from automation import durable_sync, work_ledger
from automation.work_tables import jobs
from core import models
from tests.test_durable_work import pg


@pytest.mark.parametrize("kind", ["sync", "goals"])
def test_projects_of_same_owner_share_quota_and_other_owner_can_run(pg, monkeypatch, kind):
    factory, engine = pg
    models.Base.metadata.create_all(engine)
    monkeypatch.setattr(durable_sync, "SessionLocal", factory)
    monkeypatch.setenv("SYNC_GLOBAL_CONCURRENCY", "4")
    monkeypatch.setenv("SYNC_TENANT_CONCURRENCY", "2")
    with factory.begin() as db:
        owners = [models.User(email=f"quota-{i}@example.test", password_hash="synthetic") for i in range(2)]
        db.add_all(owners)
        db.flush()
        integrations = []
        for index in range(4):
            project = models.Client(name=f"Project {index}", owner_id=owners[index // 3].id)
            db.add(project)
            db.flush()
            integration = models.Integration(client_id=project.id,
                platform=models.IntegrationPlatform.YANDEX_DIRECT)
            db.add(integration)
            db.flush()
            integrations.append(integration.id)
        owner_ids = [str(owner.id) for owner in owners]
    for integration_id in integrations:
        if kind == "sync":
            durable_sync.enqueue(integration_id, days=3, force_full=False, trigger="manual")
        else:
            durable_sync.enqueue_goals(integration_id, "2026-09-01", "2026-09-02")
    with factory.begin() as db:
        entries = {row.resource: row for row in db.execute(sa.select(jobs)).mappings()}
        ordered = [entries[f"integration:{i}"] for i in integrations]
        assert [row.tenant for row in ordered] == [owner_ids[0]] * 3 + [owner_ids[1]]
        assert work_ledger.claim(db, ordered[0].id)
        assert work_ledger.claim(db, ordered[1].id)
        assert work_ledger.claim(db, ordered[2].id) is None
        assert work_ledger.claim(db, ordered[3].id)
