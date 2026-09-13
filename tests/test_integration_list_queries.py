from types import SimpleNamespace
import uuid

import pytest
import sqlalchemy as sa

from backend_api import integrations
from core import models, schemas
from tests.test_durable_work import pg


@pytest.fixture
def listing(pg):
    factory, engine = pg
    models.Base.metadata.create_all(engine)
    with factory.begin() as db:
        owner = models.User(email="integration-owner@example.test", password_hash="synthetic")
        stranger = models.User(email="integration-other@example.test", password_hash="synthetic")
        db.add_all([owner, stranger])
        db.flush()
        ids = []
        for i in range(21):
            project = models.Client(owner_id=owner.id if i < 20 else stranger.id, name=f"Synthetic {i}")
            db.add(project)
            db.flush()
            integration = models.Integration(client_id=project.id, platform=models.IntegrationPlatform.VK_ADS,
                access_token="must-not-leak-token", selected_goals='["1"]', selected_counters='["a"]')
            db.add(integration)
            db.flush()
            db.add_all([models.Campaign(integration_id=integration.id, external_id=f"{i}-{j}",
                name=f"Campaign {i}-{j}", is_active=True, vk_goal_action_id="lead") for j in range(2)])
            ids.append(project.id)
        owner_id, stranger_id = owner.id, stranger.id
    statements = []
    def counted(conn, cursor, statement, params, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)
    sa.event.listen(engine, "before_cursor_execute", counted)
    try:
        yield factory, statements, ids, SimpleNamespace(id=owner_id), SimpleNamespace(id=stranger_id)
    finally:
        sa.event.remove(engine, "before_cursor_execute", counted)


def serialized(rows):
    result = [schemas.IntegrationResponse.model_validate(row).model_dump(mode="json") for row in rows]
    for row in result:
        row["campaigns"].sort(key=lambda campaign: campaign["id"])
    return sorted(result, key=lambda row: row["id"])


@pytest.mark.parametrize("size", [1, 13, 20])
def test_two_queries_replace_n_plus_one_with_identical_json(listing, monkeypatch, size):
    factory, statements, ids, owner, _ = listing
    permitted = ids[:size]
    monkeypatch.setattr(integrations, "get_accessible_client_ids", lambda *args: permitted)
    with factory() as db:
        statements.clear()
        old = serialized(db.query(models.Integration).join(models.Client)
            .filter(models.Integration.client_id.in_(permitted)).all())
        assert len(statements) == 1 + 2 * size
    with factory() as db:
        statements.clear()
        rows = integrations.get_integrations(current_user=owner, db=db)
        assert len(statements) == 2
        # Serialization is part of the budget; no hidden lazy SQL after handler.
        current = serialized(rows)
        assert len(statements) == 2
    assert serialized(rows) == current == old  # detached response is complete
    assert all("access_token" not in row for row in current)
    assert all(len(row["campaigns"]) == 2 and row["client_name"] for row in current)


def test_real_access_resolution_excludes_other_owner_and_campaigns(listing):
    factory, statements, ids, owner, stranger = listing
    with factory() as db:
        statements.clear()
        rows = serialized(integrations.get_integrations(current_user=owner, db=db))
        assert len(rows) == 20
        assert {row["client_id"] for row in rows} == set(map(str, ids[:20]))
        assert len(statements) == 6  # four unchanged access queries + two data queries
        assert "Campaign 20-" not in str(rows)
        assert "must-not-leak-token" not in str(rows)
    with factory() as db:
        assert len(serialized(integrations.get_integrations(current_user=stranger, db=db))) == 1


@pytest.mark.parametrize("foreign", [False, True])
def test_project_filter_does_not_broaden_access(listing, foreign):
    factory, _, ids, owner, _ = listing
    with factory() as db:
        rows = serialized(integrations.get_integrations(client_id=str(ids[-1] if foreign else ids[0]),
            current_user=owner, db=db))
    assert len(rows) == (0 if foreign else 1)


def test_folder_scope_is_intersected_with_access_not_trusted(listing, monkeypatch):
    from backend_api.stats_service import StatsService
    factory, _, ids, owner, _ = listing
    monkeypatch.setattr(StatsService, "resolve_folder_client_ids", lambda *args: [ids[0], ids[-1]])
    with factory() as db:
        rows = serialized(integrations.get_integrations(folder_id=str(uuid.uuid4()), current_user=owner, db=db))
    assert [row["client_id"] for row in rows] == [str(ids[0])]


def test_empty_access_never_loads_relationships(listing, monkeypatch):
    factory, statements, _, owner, _ = listing
    monkeypatch.setattr(integrations, "get_accessible_client_ids", lambda *args: [])
    with factory() as db:
        statements.clear()
        assert integrations.get_integrations(current_user=owner, db=db) == []
        assert not statements
