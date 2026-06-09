"""
Integration tests for sync functionality

Tests cover:
- Integration synchronization with different profiles
- Token refresh handling
- Empty report handling
- Parallel synchronization
- Error scenarios
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session

from automation.sync import sync_integration, sync_data, _update_or_create_stats
from core import models


def _yandex_api_mock(*, stats=None, balance=None, report_side_effect=None):
    mock_api = Mock()
    mock_api.get_balance = AsyncMock(return_value=balance or {"balance": 100.0, "currency": "RUB"})
    if report_side_effect is not None:
        mock_api.get_report = AsyncMock(side_effect=report_side_effect)
    else:
        mock_api.get_report = AsyncMock(return_value=stats if stats is not None else [])
    return mock_api


def _mock_db_for_sync(campaigns=None):
    mock_db = Mock(spec=Session)
    mock_db.query.return_value.filter.return_value.all.return_value = campaigns or []
    return mock_db


def _direct_integration(**overrides):
    mock_integration = Mock()
    mock_integration.id = "test-integration-id"
    mock_integration.platform = models.IntegrationPlatform.YANDEX_DIRECT
    mock_integration.client_id = "test-client"
    mock_integration.access_token = "encrypted_token"
    mock_integration.refresh_token = None
    mock_integration.agency_client_login = "test_login"
    mock_integration.account_id = None
    mock_integration.balance = None
    mock_integration.currency = None
    mock_integration.selected_goals = None
    mock_integration.primary_goal_id = None
    mock_integration.selected_counters = None
    mock_integration.client = None
    mock_integration.sync_status = models.IntegrationSyncStatus.NEVER
    mock_integration.error_message = None
    for key, value in overrides.items():
        setattr(mock_integration, key, value)
    return mock_integration


class TestUpdateOrCreateStats:
    """Test the helper function for updating/creating stats"""

    def test_create_new_stat(self):
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        filters = {"client_id": "test-client", "date": "2024-01-01"}
        data = {"impressions": 1000, "clicks": 50}

        _update_or_create_stats(mock_db, models.YandexStats, filters, data)

        mock_db.add.assert_called_once()

    def test_update_existing_stat(self):
        mock_db = Mock(spec=Session)
        existing_stat = Mock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = existing_stat

        filters = {"client_id": "test-client", "date": "2024-01-01"}
        data = {"impressions": 2000, "clicks": 100}

        _update_or_create_stats(mock_db, models.YandexStats, filters, data)

        assert existing_stat.impressions == 2000
        assert existing_stat.clicks == 100
        mock_db.add.assert_not_called()


class TestSyncIntegration:
    """Test individual integration synchronization"""

    @pytest.mark.asyncio
    async def test_sync_yandex_direct_with_profile(self):
        mock_db = _mock_db_for_sync()
        mock_integration = _direct_integration(agency_client_login="test_login")

        mock_stats = [
            {
                "date": "2024-01-01",
                "campaign_id": "123",
                "campaign_name": "Test Campaign",
                "impressions": 1000,
                "clicks": 50,
                "cost": 100.0,
                "conversions": 5,
            }
        ]

        mock_api = _yandex_api_mock(stats=mock_stats)

        with patch("automation.sync.security.decrypt_token", return_value="decrypted_token"), \
             patch("automation.sync.YandexDirectAPI", return_value=mock_api) as mock_api_class, \
             patch("backend_api.cache_service.CacheService.invalidate_client"):

            await sync_integration(mock_db, mock_integration, "2024-01-01", "2024-01-31")

            mock_api_class.assert_called_with("decrypted_token", client_login="test_login", finance_token=None)
            mock_api.get_report.assert_any_call("2024-01-01", "2024-01-31")
            mock_api.get_balance.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_yandex_direct_without_profile(self):
        """Без профиля sync всё равно стартует с client_login=None."""
        mock_db = _mock_db_for_sync()
        mock_integration = _direct_integration(agency_client_login=None, account_id=None)

        mock_api = _yandex_api_mock(stats=[])

        with patch("automation.sync.security.decrypt_token", return_value="decrypted_token"), \
             patch("automation.sync.YandexDirectAPI", return_value=mock_api) as mock_api_class, \
             patch("backend_api.cache_service.CacheService.invalidate_client"):

            await sync_integration(mock_db, mock_integration, "2024-01-01", "2024-01-31")

            mock_api_class.assert_called_with("decrypted_token", client_login=None, finance_token=None)
            assert mock_integration.sync_status == models.IntegrationSyncStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_sync_with_fallback_to_account_id(self):
        mock_db = _mock_db_for_sync()
        mock_integration = _direct_integration(agency_client_login=None, account_id="fallback_login")

        mock_api = _yandex_api_mock(stats=[])

        with patch("automation.sync.security.decrypt_token", return_value="decrypted_token"), \
             patch("automation.sync.YandexDirectAPI", return_value=mock_api) as mock_api_class, \
             patch("backend_api.cache_service.CacheService.invalidate_client"):

            await sync_integration(mock_db, mock_integration, "2024-01-01", "2024-01-31")

            mock_api_class.assert_called_with("decrypted_token", client_login="fallback_login", finance_token=None)

    @pytest.mark.asyncio
    async def test_sync_with_empty_report(self):
        mock_db = _mock_db_for_sync()
        mock_integration = _direct_integration()

        mock_api = _yandex_api_mock(stats=[])

        with patch("automation.sync.security.decrypt_token", return_value="decrypted_token"), \
             patch("automation.sync.YandexDirectAPI", return_value=mock_api), \
             patch("backend_api.cache_service.CacheService.invalidate_client"):

            await sync_integration(mock_db, mock_integration, "2024-01-01", "2024-01-31")

            assert mock_integration.sync_status == models.IntegrationSyncStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_sync_with_token_refresh(self):
        mock_db = _mock_db_for_sync()
        mock_integration = _direct_integration(
            access_token="encrypted_old_token",
            refresh_token="encrypted_refresh_token",
        )

        mock_api_first = _yandex_api_mock(report_side_effect=PermissionError("401 Unauthorized"))
        mock_api_second = _yandex_api_mock(stats=[])

        with patch("automation.sync.security.decrypt_token") as mock_decrypt, \
             patch("automation.sync.security.encrypt_token", return_value="encrypted_new_token"), \
             patch("automation.sync.YandexDirectAPI", side_effect=[mock_api_first, mock_api_second]) as mock_api_class, \
             patch("backend_api.services.IntegrationService") as mock_service, \
             patch("backend_api.cache_service.CacheService.invalidate_client"):

            mock_decrypt.side_effect = ["old_token", "refresh_token"]
            mock_service.refresh_yandex_token = AsyncMock(return_value={
                "access_token": "new_token",
                "refresh_token": "new_refresh_token",
            })

            await sync_integration(mock_db, mock_integration, "2024-01-01", "2024-01-31")

            mock_service.refresh_yandex_token.assert_called_once()
            assert mock_api_class.call_count == 2

    @pytest.mark.asyncio
    async def test_sync_avito_ads(self):
        mock_db = _mock_db_for_sync()
        mock_integration = Mock()
        mock_integration.id = "test-avito-integration-id"
        mock_integration.platform = models.IntegrationPlatform.AVITO_ADS
        mock_integration.client_id = "test-client"
        mock_integration.access_token = "encrypted_key"
        mock_integration.platform_client_id = None
        mock_integration.platform_client_secret = None
        mock_integration.account_id = "123"
        mock_integration.balance = None
        mock_integration.currency = None
        mock_integration.error_message = None

        mock_campaign = Mock()
        mock_campaign.id = "camp1"
        mock_campaign.external_id = "1001"
        mock_campaign.is_active = True
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_campaign]

        mock_api = Mock()
        mock_api.get_balance = AsyncMock(return_value={"balance": 321.5, "currency": "RUB"})
        mock_api.get_statistics = AsyncMock(return_value=[{
            "campaign_id": "1001",
            "campaign_name": "Avito Campaign",
            "date": "2024-01-01",
            "impressions": 1000,
            "clicks": 40,
            "cost": 200.0,
            "cpc": 5.0,
        }])

        with patch("automation.sync.security.decrypt_token", return_value="decrypted_api_key"), \
             patch("automation.avito_integration_helpers.build_avito_api_from_integration", return_value=mock_api), \
             patch("automation.avito_integration_helpers.get_metrika_integration_for_client", return_value=None), \
             patch("backend_api.cache_service.CacheService.invalidate_client"):
            await sync_integration(mock_db, mock_integration, "2024-01-01", "2024-01-31")
            assert mock_integration.sync_status == models.IntegrationSyncStatus.SUCCESS
            assert mock_api.get_balance.await_count == 1
            assert mock_api.get_statistics.await_count == 1


class TestSyncData:
    """Test parallel synchronization of multiple integrations"""

    @pytest.mark.asyncio
    async def test_parallel_sync_multiple_integrations(self):
        mock_integration1 = Mock()
        mock_integration1.id = "int1"
        mock_integration1.platform = models.IntegrationPlatform.YANDEX_DIRECT

        mock_integration2 = Mock()
        mock_integration2.id = "int2"
        mock_integration2.platform = models.IntegrationPlatform.VK_ADS

        with patch("automation.sync.SessionLocal") as mock_session_local, \
             patch("automation.sync.sync_integration", new_callable=AsyncMock) as mock_sync:

            mock_db = Mock()
            mock_db.query.return_value.all.return_value = [mock_integration1, mock_integration2]
            mock_session_local.return_value = mock_db

            await sync_data(days=7, max_concurrent=2)

            assert mock_sync.call_count == 2

    @pytest.mark.asyncio
    async def test_parallel_sync_handles_individual_failures(self):
        mock_integration1 = Mock()
        mock_integration1.id = "int1"
        mock_integration1.agency_client_login = None
        mock_integration1.account_id = None

        mock_integration2 = Mock()
        mock_integration2.id = "int2"
        mock_integration2.agency_client_login = "test"

        with patch("automation.sync.SessionLocal") as mock_session_local, \
             patch("automation.sync.sync_integration", new_callable=AsyncMock) as mock_sync:

            mock_db = Mock()
            mock_db.query.return_value.all.return_value = [mock_integration1, mock_integration2]
            mock_session_local.return_value = mock_db

            mock_sync.side_effect = [Exception("Sync failed"), None]

            await sync_data(days=7)

            assert mock_sync.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
