"""Current sync contracts: explicit ORM-shaped fixtures and async API methods."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, call
import uuid

import pytest
from sqlalchemy.orm import Session

from automation import sync
from core import models


@pytest.mark.parametrize("exists", [False, True])
def test_update_or_create_stats(exists):
    db = Mock(spec=Session)
    row = SimpleNamespace(impressions=1, clicks=1) if exists else None
    db.query.return_value.filter_by.return_value.first.return_value = row
    sync._update_or_create_stats(db, models.YandexStats, {"client_id": uuid.uuid4()}, {"impressions": 2000, "clicks": 100})
    if exists:
        assert (row.impressions, row.clicks) == (2000, 100)
        db.add.assert_not_called()
    else:
        added = db.add.call_args.args[0]
        assert (added.impressions, added.clicks) == (2000, 100)


@pytest.fixture
def direct(monkeypatch):
    db = MagicMock(spec=Session)
    db.query.return_value.filter.return_value.all.return_value = []
    integration = SimpleNamespace(
        id=uuid.uuid4(), client_id=uuid.uuid4(), platform=models.IntegrationPlatform.YANDEX_DIRECT,
        client=SimpleNamespace(status=models.ClientStatus.ACTIVE, owner=None), is_agency=True,
        access_token="encrypted-old", refresh_token=None, agency_client_login="agency-client", account_id="account",
        balance=None, currency=None, selected_goals=None, primary_goal_id=None, selected_counters=None,
    )
    api = SimpleNamespace(get_campaigns=AsyncMock(return_value=[]), get_balance=AsyncMock(return_value=None),
                          get_report=AsyncMock(return_value=[]), get_campaign_strategies=AsyncMock(return_value={}))
    constructor = Mock(return_value=api)
    monkeypatch.setattr(sync, "YandexDirectAPI", constructor)
    monkeypatch.setattr(sync.security, "decrypt_token", lambda _: "decrypted")
    monkeypatch.setattr(sync.security, "encrypt_token", lambda value: "encrypted:" + value)
    monkeypatch.setattr(sync, "log_event", lambda *_: None)
    monkeypatch.setattr("backend_api.cache_service.CacheService.invalidate_client", lambda *_: None)
    return db, integration, api, constructor


@pytest.mark.asyncio
@pytest.mark.parametrize("agency,login,account,expected", [
    (True, "agency-client", "account", "agency-client"),
    (True, None, "fallback", "fallback"),
    (False, "stale-agency-alias", "personal", "personal"),
    (False, None, None, None),
])
async def test_direct_profile_selection_and_empty_success(direct, agency, login, account, expected):
    db, integration, api, constructor = direct
    integration.is_agency, integration.agency_client_login, integration.account_id = agency, login, account
    await sync.sync_integration(db, integration, "2026-09-01", "2026-09-10")
    constructor.assert_called_once_with("decrypted", client_login=expected, finance_token=None)
    api.get_report.assert_has_awaits([
        call("2026-09-01", "2026-09-10"), call("2026-09-01", "2026-09-10", level="group"),
        call("2026-09-01", "2026-09-10", level="keyword"),
    ])
    assert integration.sync_status == models.IntegrationSyncStatus.SUCCESS
    assert integration.last_sync_at is not None


@pytest.mark.asyncio
async def test_direct_refreshes_token_and_preserves_profile(direct, monkeypatch):
    db, integration, api, constructor = direct
    integration.refresh_token = "encrypted-refresh"
    api.get_report.side_effect = [RuntimeError("401 Unauthorized"), [], [], []]
    refresh = AsyncMock(return_value={"access_token": "new", "refresh_token": "new-refresh"})
    monkeypatch.setattr("backend_api.services.IntegrationService.refresh_yandex_token", refresh)
    monkeypatch.setattr(sync, "_yandex_app_credentials", lambda _: ("app-id", "app-secret"))
    await sync.sync_integration(db, integration, "2026-09-01", "2026-09-10")
    refresh.assert_awaited_once_with("decrypted", "app-id", "app-secret")
    assert integration.access_token == "encrypted:new"
    assert integration.refresh_token == "encrypted:new-refresh"
    assert constructor.call_args == call("new", client_login="agency-client")
    assert integration.sync_status == models.IntegrationSyncStatus.SUCCESS


@pytest.mark.asyncio
async def test_missing_token_does_not_call_provider(direct):
    db, integration, api, constructor = direct
    integration.access_token = None
    with pytest.raises(ValueError, match="токен"):
        await sync.sync_integration(db, integration, "2026-09-01", "2026-09-10")
    constructor.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("empty", [True, False])
async def test_required_goals_failure_cannot_advance_success_watermark(direct, monkeypatch, empty):
    from datetime import datetime
    db, integration, api, _ = direct
    integration.selected_goals, integration.selected_counters = '["1"]', '["123"]'
    integration.refresh_token = "encrypted-refresh"
    integration.client.owner_id = None
    previous = datetime(2026, 8, 1)
    integration.last_sync_at = previous
    if not empty:
        api.get_report.side_effect = [[{"campaign_id": "42"}], [], []]
    goals = AsyncMock(side_effect=RuntimeError("401 Unauthorized sensitive-provider-body"))
    refresh = AsyncMock()
    detector = Mock()
    monkeypatch.setattr(sync, "_sync_metrika_goals_for_direct", goals)
    monkeypatch.setattr(sync, "_bulk_upsert_stats_by_key", Mock())
    monkeypatch.setattr(sync, "_run_detector_after_sync", detector)
    monkeypatch.setattr("backend_api.services.IntegrationService.refresh_yandex_token", refresh)
    with pytest.raises(sync.RequiredSyncSourceFailed):
        await sync.sync_integration(db, integration, "2026-09-01", "2026-09-10")
    assert integration.sync_status == models.IntegrationSyncStatus.FAILED
    assert integration.last_sync_at == previous
    assert "sensitive-provider-body" not in integration.error_message
    goals.assert_awaited_once()
    refresh.assert_not_awaited()  # A Metrika failure is not a Direct token retry.
    detector.assert_not_called()


@pytest.mark.asyncio
async def test_goals_use_refreshed_direct_token(direct, monkeypatch):
    db, integration, api, _ = direct
    integration.selected_goals, integration.selected_counters = '["1"]', '["123"]'
    integration.refresh_token = "encrypted-refresh"
    api.get_report.side_effect = [RuntimeError("401 Unauthorized"), [], [], []]
    monkeypatch.setattr("backend_api.services.IntegrationService.refresh_yandex_token",
                        AsyncMock(return_value={"access_token": "new"}))
    monkeypatch.setattr(sync, "_yandex_app_credentials", lambda _: ("id", "secret"))
    goals = AsyncMock()
    monkeypatch.setattr(sync, "_sync_metrika_goals_for_direct", goals)
    await sync.sync_integration(db, integration, "2026-09-01", "2026-09-10")
    assert goals.await_args.args[4] == "new"
    assert integration.sync_status == models.IntegrationSyncStatus.SUCCESS


@pytest.mark.asyncio
@pytest.mark.parametrize("fail_first", [False, True])
async def test_parallel_sync_uses_isolated_sessions_and_continues(direct, monkeypatch, fail_first):
    _, integration, _, _ = direct
    other = SimpleNamespace(id=uuid.uuid4())
    listing, first, second = (MagicMock(spec=Session) for _ in range(3))
    listing.query.return_value.join.return_value.filter.return_value.all.return_value = [(integration.id,), (other.id,)]
    listing.query.return_value.filter.return_value.all.return_value = [(integration.client_id,)]
    first.query.return_value.join.return_value.filter.return_value.first.return_value = integration
    second.query.return_value.join.return_value.filter.return_value.first.return_value = other
    sessions = Mock(side_effect=[listing, first, second])
    execute = AsyncMock(side_effect=[RuntimeError("provider failed") if fail_first else None, None])
    monkeypatch.setattr(sync, "SessionLocal", sessions)
    monkeypatch.setattr(sync, "sync_integration", execute)
    monkeypatch.setattr(sync, "run_post_sync_reports", Mock())
    await sync.sync_data(days=7, max_concurrent=2)
    assert execute.await_count == 2
    assert [args.args[0] for args in execute.await_args_list] == [first, second]
    if fail_first:
        first.rollback.assert_called_once()
        first.commit.assert_not_called()
    else:
        first.commit.assert_called_once()
    second.commit.assert_called_once()
    for session in (listing, first, second):
        session.close.assert_called_once()
