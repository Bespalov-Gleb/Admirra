"""Include response serialization in the project/tree SQL query budget."""
from types import SimpleNamespace

import pytest
import sqlalchemy as sa

from backend_api import clients, folders
from core import models, schemas
from tests.test_durable_work import pg
from tests.test_integration_list_queries import listing


def serialized(rows):
    result = [schemas.ClientResponse.model_validate(row).model_dump(mode='json') for row in rows]
    for row in result:
        row['integrations'].sort(key=lambda item: item['id'])
        for integration in row['integrations']:
            integration['campaigns'].sort(key=lambda item: item['id'])
    return sorted(result, key=lambda row: row['id'])


@pytest.mark.parametrize('size', [1, 13, 20])
def test_same_project_json_without_lazy_queries(listing, monkeypatch, size):
    factory, queries, ids, owner, _ = listing
    permitted = ids[:size]
    monkeypatch.setattr(clients, 'get_accessible_client_ids', lambda *args: permitted)
    with factory() as db:
        queries.clear()
        old = serialized(db.query(models.Client).filter(models.Client.id.in_(permitted)).all())
        assert len(queries) == 1 + size * 2
    with factory() as db:
        queries.clear()
        rows = clients.get_clients(current_user=owner, db=db)
        assert len(queries) == 3
        assert serialized(rows) == old
        assert len(queries) == 3
    assert serialized(rows) == old  # Fully detached, not just cached in session.
    assert 'must-not-leak-token' not in str(old)


@pytest.mark.parametrize('size', [1, 20])
def test_stats_list_has_bounded_queries_including_serialization(listing, monkeypatch, size):
    factory, queries, ids, owner, _ = listing
    monkeypatch.setattr(clients, 'get_accessible_client_ids', lambda *args: ids[:size])
    with factory() as db:
        queries.clear()
        rows = clients.get_clients_with_stats(start_date='2026-09-10', end_date='2026-09-10',
            current_user=owner, db=db)
        result = serialized(rows)
        assert len(result) == size
        assert len(queries) <= 14
    assert serialized(rows) == result


@pytest.mark.parametrize('with_stats', [False, True])
def test_tree_batches_root_and_folder_projects_without_scope_leak(listing, monkeypatch, with_stats):
    factory, queries, ids, owner, stranger = listing
    with factory.begin() as db:
        folder = models.Folder(account_id=owner.id, name='Synthetic folder')
        db.add(folder); db.flush()
        db.execute(sa.update(models.Client).where(models.Client.id.in_(ids[:10])).values(folder_id=folder.id))
    monkeypatch.setattr(folders, 'get_accessible_client_ids', lambda *args: ids[:20])
    monkeypatch.setattr(folders, 'get_team_context', lambda *args: SimpleNamespace(account_id=owner.id, is_owner=True))
    with factory() as db:
        queries.clear()
        result = folders.projects_tree(start_date='2026-09-10', end_date='2026-09-10', with_stats=with_stats,
            current_user=owner, db=db).model_dump(mode='json')
        # One folder total still uses its own fixed set of aggregate queries;
        # its ten child responses must not add twenty lazy relationship reads.
        assert len(queries) <= (26 if with_stats else 5)
        rows = result['root_projects'] + result['folders'][0]['projects']
        assert len(rows) == 20 and {r['id'] for r in rows} == set(map(str, ids[:20]))
        assert all(len(r['integrations'][0]['campaigns']) == 2 for r in rows)
        assert 'Campaign 20-' not in str(result) and 'must-not-leak-token' not in str(result)


def test_real_project_access_still_excludes_other_owner(listing):
    factory, _, ids, owner, stranger = listing
    with factory() as db:
        assert {row['id'] for row in serialized(clients.get_clients(current_user=owner, db=db))} == set(map(str, ids[:20]))
    with factory() as db:
        assert {row['id'] for row in serialized(clients.get_clients(current_user=stranger, db=db))} == {str(ids[-1])}
