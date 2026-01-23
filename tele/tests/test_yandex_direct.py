"""
Unit tests for YandexDirectAPI

Tests cover:
- Initialization with/without client_login
- Campaign fetching
- Report generation with various scenarios
- Error handling
- API Units tracking
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from automation.yandex_direct import YandexDirectAPI


class TestYandexDirectAPIInitialization:
    """Test API initialization scenarios"""
    
    def test_init_with_client_login(self):
        """Test initialization with client_login sets header correctly"""
        api = YandexDirectAPI("test_token", "test_login")
        
        assert api.headers["Client-Login"] == "test_login"
        assert api.client_login == "test_login"
        assert api.headers["Authorization"] == "Bearer test_token"
    
    def test_init_without_client_login(self):
        """Test initialization without client_login"""
        api = YandexDirectAPI("test_token")
        
        assert "Client-Login" not in api.headers
        assert api.client_login is None
        assert api.headers["Authorization"] == "Bearer test_token"
    
    def test_init_with_unknown_client_login(self):
        """Test initialization with 'unknown' client_login is ignored"""
        api = YandexDirectAPI("test_token", "unknown")
        
        assert "Client-Login" not in api.headers
        assert api.client_login is None


class TestYandexDirectAPICampaigns:
    """Test campaign fetching"""
    
    @pytest.mark.asyncio
    async def test_get_campaigns_success(self):
        """Test successful campaign fetching"""
        api = YandexDirectAPI("test_token", "test_login")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "Campaigns": [
                    {"Id": 123, "Name": "Campaign 1", "Status": "ON"},
                    {"Id": 456, "Name": "Campaign 2", "Status": "SUSPENDED"}
                ]
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            campaigns = await api.get_campaigns()
            
            assert len(campaigns) == 2
            assert campaigns[0]["id"] == "123"
            assert campaigns[0]["name"] == "Campaign 1"
            assert campaigns[1]["status"] == "SUSPENDED"
    
    @pytest.mark.asyncio
    async def test_get_campaigns_api_error(self):
        """Test campaign fetching with API error response"""
        api = YandexDirectAPI("test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error": {
                "error_msg": "Invalid token"
            }
        }
        mock_response.text = "Error text"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            with pytest.raises(Exception, match="Invalid token"):
                await api.get_campaigns()
    
    @pytest.mark.asyncio
    async def test_get_campaigns_http_error(self):
        """Test campaign fetching with HTTP error"""
        api = YandexDirectAPI("test_token")
        
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            with pytest.raises(Exception, match="401"):
                await api.get_campaigns()


class TestYandexDirectAPIReports:
    """Test report generation"""
    
    @pytest.mark.asyncio
    async def test_get_report_success(self):
        """Test successful report generation"""
        api = YandexDirectAPI("test_token", "test_login")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Date\tCampaignId\tCampaignName\tImpressions\tClicks\tCost\tConversions\n2024-01-01\t123\tTest Campaign\t1000\t50\t5000000\t10"
        mock_response.headers.get.return_value = "10/10000/9990"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            stats = await api.get_report("2024-01-01", "2024-01-31")
            
            assert len(stats) == 1
            assert stats[0]["campaign_id"] == "123"
            assert stats[0]["impressions"] == 1000
            assert stats[0]["clicks"] == 50
            assert stats[0]["cost"] == 5.0  # Cost is divided by 1000000
            assert stats[0]["conversions"] == 10
    
    @pytest.mark.asyncio
    async def test_get_report_invalid_date_format(self):
        """Test report with invalid date format raises ValueError"""
        api = YandexDirectAPI("test_token")
        
        with pytest.raises(ValueError, match="Invalid date format"):
            await api.get_report("01-01-2024", "31-01-2024")
    
    @pytest.mark.asyncio
    async def test_get_report_date_from_after_date_to(self):
        """Test report with date_from after date_to raises ValueError"""
        api = YandexDirectAPI("test_token")
        
        with pytest.raises(ValueError, match="cannot be after"):
            await api.get_report("2024-01-31", "2024-01-01")
    
    @pytest.mark.asyncio
    async def test_get_report_polling(self):
        """Test report generation with polling (201/202 statuses)"""
        api = YandexDirectAPI("test_token")
        
        mock_response_queued = Mock()
        mock_response_queued.status_code = 201
        mock_response_queued.headers.get.side_effect = lambda x: "5" if x == "Retry-After" else None
        
        mock_response_ready = Mock()
        mock_response_ready.status_code = 200
        mock_response_ready.text = "Date\tCampaignId\tCampaignName\tImpressions\tClicks\tCost\tConversions\n2024-01-01\t123\tTest\t100\t10\t1000000\t5"
        mock_response_ready.headers.get.return_value = "20/10000/9980"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=[mock_response_queued, mock_response_ready]
            )
            with patch('asyncio.sleep', new_callable=AsyncMock):
                stats = await api.get_report("2024-01-01", "2024-01-31")
                
                assert len(stats) == 1
    
    @pytest.mark.asyncio
    async def test_get_report_max_retries_exceeded(self):
        """Test report generation exceeding max retries"""
        api = YandexDirectAPI("test_token")
        
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers.get.side_effect = lambda x: "1" if x == "Retry-After" else None
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            with patch('asyncio.sleep', new_callable=AsyncMock):
                with pytest.raises(TimeoutError, match="Maximum retries"):
                    await api.get_report("2024-01-01", "2024-01-31", max_retries=3)


class TestYandexDirectAPIUnitsTracking:
    """Test API Units tracking and limits"""
    
    def test_parse_units_header(self):
        """Test parsing of Units header"""
        api = YandexDirectAPI("test_token")
        
        api._parse_and_check_units("120/10000/9880")
        
        assert api.units_used == 120
        assert api.units_limit == 10000
        assert api.units_remaining == 9880
    
    def test_parse_units_header_warning_threshold(self):
        """Test warning when approaching units limit"""
        api = YandexDirectAPI("test_token")
        
        # 95% usage should trigger warning
        api._parse_and_check_units("9500/10000/500")
        
        assert api.units_used == 9500
    
    def test_parse_units_header_limit_exceeded(self):
        """Test exception when units limit exceeded"""
        api = YandexDirectAPI("test_token")
        
        with pytest.raises(RuntimeError, match="limit exceeded"):
            api._parse_and_check_units("10000/10000/0")
    
    def test_parse_units_invalid_format(self):
        """Test parsing invalid Units header format"""
        api = YandexDirectAPI("test_token")
        
        # Should not raise exception, just log warning
        api._parse_and_check_units("invalid")
        
        assert api.units_used == 0  # Default value


class TestYandexDirectAPIClients:
    """Test client info fetching"""
    
    @pytest.mark.asyncio
    async def test_get_clients_success(self):
        """Test successful client info fetching"""
        api = YandexDirectAPI("test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "Clients": [
                    {"Login": "user1", "ClientInfo": "Info1"},
                    {"Login": "user2", "ClientInfo": "Info2"}
                ]
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            clients = await api.get_clients()
            
            assert len(clients) == 2
            assert clients[0]["Login"] == "user1"
    
    @pytest.mark.asyncio
    async def test_get_clients_unauthorized(self):
        """Test client fetching with unauthorized error"""
        api = YandexDirectAPI("test_token")
        
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            with pytest.raises(PermissionError, match="Unauthorized"):
                await api.get_clients()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

