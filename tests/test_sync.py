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
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from automation.sync import sync_integration, sync_data, _update_or_create_stats
from core import models


class TestUpdateOrCreateStats:
    """Test the helper function for updating/creating stats"""
    
    def test_create_new_stat(self):
        """Test creating a new stat record"""
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        filters = {"client_id": "test-client", "date": "2024-01-01"}
        data = {"impressions": 1000, "clicks": 50}
        
        _update_or_create_stats(mock_db, models.YandexStats, filters, data)
        
        mock_db.add.assert_called_once()
    
    def test_update_existing_stat(self):
        """Test updating an existing stat record"""
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
        """Test syncing Yandex Direct with agency_client_login set"""
        mock_db = Mock(spec=Session)
        
        # Create mock integration
        mock_integration = Mock()
        mock_integration.id = "test-integration-id"
        mock_integration.platform = models.IntegrationPlatform.YANDEX_DIRECT
        mock_integration.client_id = "test-client"
        mock_integration.access_token = "encrypted_token"
        mock_integration.agency_client_login = "test_login"
        mock_integration.refresh_token = None
        
        # Mock campaign
        mock_campaign = Mock()
        mock_campaign.id = "campaign-id"
        mock_campaign.name = "Test Campaign"
        mock_campaign.is_active = True
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_campaign
        
        # Mock API responses
        mock_stats = [
            {
                "date": "2024-01-01",
                "campaign_id": "123",
                "campaign_name": "Test Campaign",
                "impressions": 1000,
                "clicks": 50,
                "cost": 100.0,
                "conversions": 5
            }
        ]
        
        with patch('automation.sync.security.decrypt_token', return_value="decrypted_token"), \
             patch('automation.sync.YandexDirectAPI') as mock_api_class:
            
            mock_api = Mock()
            mock_api.get_report = AsyncMock(return_value=mock_stats)
            mock_api_class.return_value = mock_api
            
            await sync_integration(mock_db, mock_integration, "2024-01-01", "2024-01-31")
            
            # Verify API was initialized with client_login
            mock_api_class.assert_called_with("decrypted_token", "test_login")
            
            # Verify report was fetched
            mock_api.get_report.assert_called_once_with("2024-01-01", "2024-01-31")
    
    @pytest.mark.asyncio
    async def test_sync_yandex_direct_without_profile(self):
        """Test syncing Yandex Direct without agency_client_login (should fail)"""
        mock_db = Mock(spec=Session)
        
        mock_integration = Mock()
        mock_integration.id = "test-integration-id"
        mock_integration.platform = models.IntegrationPlatform.YANDEX_DIRECT
        mock_integration.access_token = "encrypted_token"
        mock_integration.agency_client_login = None
        mock_integration.account_id = None  # Neither set
        
        with patch('automation.sync.security.decrypt_token', return_value="decrypted_token"):
            # Should return early without syncing
            await sync_integration(mock_db, mock_integration, "2024-01-01", "2024-01-31")
            
            # Verify status was set to FAILED
            assert mock_integration.sync_status == models.SyncStatus.FAILED
            assert "Profile not selected" in mock_integration.sync_error
    
    @pytest.mark.asyncio
    async def test_sync_with_fallback_to_account_id(self):
        """Test syncing with fallback to account_id when agency_client_login is not set"""
        mock_db = Mock(spec=Session)
        
        mock_integration = Mock()
        mock_integration.id = "test-integration-id"
        mock_integration.platform = models.IntegrationPlatform.YANDEX_DIRECT
        mock_integration.client_id = "test-client"
        mock_integration.access_token = "encrypted_token"
        mock_integration.agency_client_login = None
        mock_integration.account_id = "fallback_login"
        mock_integration.refresh_token = None
        
        mock_campaign = Mock()
        mock_campaign.id = "campaign-id"
        mock_campaign.is_active = True
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_campaign
        
        with patch('automation.sync.security.decrypt_token', return_value="decrypted_token"), \
             patch('automation.sync.YandexDirectAPI') as mock_api_class:
            
            mock_api = Mock()
            mock_api.get_report = AsyncMock(return_value=[])
            mock_api_class.return_value = mock_api
            
            await sync_integration(mock_db, mock_integration, "2024-01-01", "2024-01-31")
            
            # Verify API was initialized with fallback account_id
            mock_api_class.assert_called_with("decrypted_token", "fallback_login")
    
    @pytest.mark.asyncio
    async def test_sync_with_empty_report(self):
        """Test syncing when API returns empty report"""
        mock_db = Mock(spec=Session)
        
        mock_integration = Mock()
        mock_integration.id = "test-integration-id"
        mock_integration.platform = models.IntegrationPlatform.YANDEX_DIRECT
        mock_integration.access_token = "encrypted_token"
        mock_integration.agency_client_login = "test_login"
        mock_integration.refresh_token = None
        
        with patch('automation.sync.security.decrypt_token', return_value="decrypted_token"), \
             patch('automation.sync.YandexDirectAPI') as mock_api_class:
            
            mock_api = Mock()
            mock_api.get_report = AsyncMock(return_value=[])  # Empty report
            mock_api_class.return_value = mock_api
            
            await sync_integration(mock_db, mock_integration, "2024-01-01", "2024-01-31")
            
            # Verify sync completed successfully even with empty report
            assert mock_integration.sync_status == models.SyncStatus.SUCCESS
    
    @pytest.mark.asyncio
    async def test_sync_with_token_refresh(self):
        """Test syncing with automatic token refresh on 401 error"""
        mock_db = Mock(spec=Session)
        
        mock_integration = Mock()
        mock_integration.id = "test-integration-id"
        mock_integration.platform = models.IntegrationPlatform.YANDEX_DIRECT
        mock_integration.client_id = "test-client"
        mock_integration.access_token = "encrypted_old_token"
        mock_integration.agency_client_login = "test_login"
        mock_integration.refresh_token = "encrypted_refresh_token"
        
        mock_campaign = Mock()
        mock_campaign.id = "campaign-id"
        mock_campaign.is_active = True
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_campaign
        
        with patch('automation.sync.security.decrypt_token') as mock_decrypt, \
             patch('automation.sync.security.encrypt_token') as mock_encrypt, \
             patch('automation.sync.YandexDirectAPI') as mock_api_class, \
             patch('automation.sync.IntegrationService') as mock_service:
            
            mock_decrypt.side_effect = ["old_token", "refresh_token"]
            mock_encrypt.return_value = "encrypted_new_token"
            
            # First API call fails with 401
            mock_api_first = Mock()
            mock_api_first.get_report = AsyncMock(side_effect=Exception("401 Unauthorized"))
            
            # Second API call succeeds
            mock_api_second = Mock()
            mock_api_second.get_report = AsyncMock(return_value=[])
            
            mock_api_class.side_effect = [mock_api_first, mock_api_second]
            
            # Mock token refresh
            mock_service.refresh_yandex_token = AsyncMock(return_value={
                "access_token": "new_token",
                "refresh_token": "new_refresh_token"
            })
            
            await sync_integration(mock_db, mock_integration, "2024-01-01", "2024-01-31")
            
            # Verify token was refreshed
            mock_service.refresh_yandex_token.assert_called_once()


class TestSyncData:
    """Test parallel synchronization of multiple integrations"""
    
    @pytest.mark.asyncio
    async def test_parallel_sync_multiple_integrations(self):
        """Test parallel synchronization of multiple integrations"""
        mock_integration1 = Mock()
        mock_integration1.id = "int1"
        mock_integration1.platform = models.IntegrationPlatform.YANDEX_DIRECT
        
        mock_integration2 = Mock()
        mock_integration2.id = "int2"
        mock_integration2.platform = models.IntegrationPlatform.VK_ADS
        
        with patch('automation.sync.SessionLocal') as mock_session_local, \
             patch('automation.sync.sync_integration', new_callable=AsyncMock) as mock_sync:
            
            mock_db = Mock()
            mock_db.query.return_value.all.return_value = [mock_integration1, mock_integration2]
            mock_session_local.return_value = mock_db
            
            await sync_data(days=7, max_concurrent=2)
            
            # Verify both integrations were synced
            assert mock_sync.call_count == 2
    
    @pytest.mark.asyncio
    async def test_parallel_sync_handles_individual_failures(self):
        """Test that parallel sync continues even if one integration fails"""
        mock_integration1 = Mock()
        mock_integration1.id = "int1"
        mock_integration1.agency_client_login = None
        mock_integration1.account_id = None
        
        mock_integration2 = Mock()
        mock_integration2.id = "int2"
        mock_integration2.agency_client_login = "test"
        
        with patch('automation.sync.SessionLocal') as mock_session_local, \
             patch('automation.sync.sync_integration', new_callable=AsyncMock) as mock_sync:
            
            mock_db = Mock()
            mock_db.query.return_value.all.return_value = [mock_integration1, mock_integration2]
            mock_session_local.return_value = mock_db
            
            # First sync fails, second succeeds
            mock_sync.side_effect = [Exception("Sync failed"), None]
            
            # Should not raise exception
            await sync_data(days=7)
            
            # Verify both were attempted
            assert mock_sync.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

