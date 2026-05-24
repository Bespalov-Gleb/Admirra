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
from unittest.mock import Mock, patch, AsyncMock

from automation.yandex_direct import YandexDirectAPI


def _http_response(
    *,
    status_code: int = 200,
    json_data=None,
    text: str = "",
    headers: dict | None = None,
):
    """Mock httpx response with request metadata used by YandexDirectAPI logging."""
    response = Mock()
    response.status_code = status_code
    response.text = text
    response.headers = headers or {}
    response.json = Mock(return_value=json_data if json_data is not None else {})

    request = Mock()
    request.method = "POST"
    request.url = "https://api.direct.yandex.com/json/v5/campaigns"
    request.headers = {}
    response.request = request
    return response


def _campaign_payload(campaigns: list[dict]) -> dict:
    return {"result": {"Campaigns": campaigns}}


def _sample_campaign(campaign_id: int, name: str, status: str = "ON") -> dict:
    return {
        "Id": campaign_id,
        "Name": name,
        "Status": status,
        "State": status,
        "StatusPayment": "ALLOWED",
        "Type": "TEXT_CAMPAIGN",
    }


class TestYandexDirectAPIInitialization:
    """Test API initialization scenarios"""

    def test_init_with_client_login(self):
        api = YandexDirectAPI("test_token", "test_login")

        assert api.headers["Client-Login"] == "test_login"
        assert api.client_login == "test_login"
        assert api.headers["Authorization"] == "Bearer test_token"

    def test_init_without_client_login(self):
        api = YandexDirectAPI("test_token")

        assert "Client-Login" not in api.headers
        assert api.client_login is None
        assert api.headers["Authorization"] == "Bearer test_token"

    def test_init_with_unknown_client_login(self):
        """Caller may pass unknown; __init__ sets header as-is (sync filters before call)."""
        api = YandexDirectAPI("test_token", "unknown")

        assert api.headers["Client-Login"] == "unknown"
        assert api.client_login == "unknown"


class TestYandexDirectAPICampaigns:
    """Test campaign fetching"""

    @pytest.mark.asyncio
    async def test_get_campaigns_success(self):
        api = YandexDirectAPI("test_token", "test_login")

        mock_response = _http_response(
            json_data=_campaign_payload([
                _sample_campaign(123, "Campaign 1", "ON"),
                _sample_campaign(456, "Campaign 2", "SUSPENDED"),
            ]),
            headers={"Units": "10/10000/9990"},
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            campaigns = await api.get_campaigns()

            assert len(campaigns) == 2
            assert campaigns[0]["id"] == "123"
            assert campaigns[0]["name"] == "Campaign 1"
            assert campaigns[1]["status"] == "SUSPENDED"

    @pytest.mark.asyncio
    async def test_get_campaigns_api_error(self):
        api = YandexDirectAPI("test_token")

        mock_response = _http_response(
            json_data={"error": {"error_msg": "Invalid token"}},
            text="Error text",
        )

        with patch("httpx.AsyncClient") as mock_client, patch.object(
            api,
            "get_campaigns_from_reports",
            new_callable=AsyncMock,
            return_value=[],
        ):
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(Exception, match="Invalid token"):
                await api.get_campaigns()

    @pytest.mark.asyncio
    async def test_get_campaigns_http_error(self):
        api = YandexDirectAPI("test_token")

        mock_response = _http_response(status_code=401, text="Unauthorized")

        with patch("httpx.AsyncClient") as mock_client, patch.object(
            api,
            "get_campaigns_from_reports",
            new_callable=AsyncMock,
            return_value=[],
        ):
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(Exception, match="401"):
                await api.get_campaigns()


class TestYandexDirectAPIReports:
    """Test report generation"""

    @pytest.mark.asyncio
    async def test_get_report_success(self):
        api = YandexDirectAPI("test_token", "test_login")

        mock_response = _http_response(
            text="Date\tCampaignId\tCampaignName\tImpressions\tClicks\tCost\tConversions\n2024-01-01\t123\tTest Campaign\t1000\t50\t5000000\t10",
            headers={"Units": "10/10000/9990"},
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            stats = await api.get_report("2024-01-01", "2024-01-31")

            assert len(stats) == 1
            assert stats[0]["campaign_id"] == "123"
            assert stats[0]["impressions"] == 1000
            assert stats[0]["clicks"] == 50
            assert stats[0]["cost"] == 5.0
            assert stats[0]["conversions"] == 10

    @pytest.mark.asyncio
    async def test_get_report_invalid_date_format(self):
        api = YandexDirectAPI("test_token")

        with pytest.raises(ValueError, match="Invalid date format"):
            await api.get_report("01-01-2024", "31-01-2024")

    @pytest.mark.asyncio
    async def test_get_report_date_from_after_date_to(self):
        api = YandexDirectAPI("test_token")

        with pytest.raises(ValueError, match="cannot be after"):
            await api.get_report("2024-01-31", "2024-01-01")

    @pytest.mark.asyncio
    async def test_get_report_polling(self):
        api = YandexDirectAPI("test_token")

        mock_response_queued = _http_response(status_code=201, headers={"Retry-After": "5"})
        mock_response_ready = _http_response(
            text="Date\tCampaignId\tCampaignName\tImpressions\tClicks\tCost\tConversions\n2024-01-01\t123\tTest\t100\t10\t1000000\t5",
            headers={"Units": "20/10000/9980"},
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=[mock_response_queued, mock_response_ready]
            )
            with patch("asyncio.sleep", new_callable=AsyncMock):
                stats = await api.get_report("2024-01-01", "2024-01-31")

                assert len(stats) == 1

    @pytest.mark.asyncio
    async def test_get_report_max_retries_exceeded(self):
        api = YandexDirectAPI("test_token")

        mock_response = _http_response(status_code=201, headers={"Retry-After": "1"})

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(TimeoutError, match="Maximum retries"):
                    await api.get_report("2024-01-01", "2024-01-31", max_retries=3)


class TestYandexDirectAPIUnitsTracking:
    """Test API Units tracking and limits"""

    def test_parse_units_header(self):
        api = YandexDirectAPI("test_token")

        api._parse_and_check_units("120/10000/9880")

        assert api.units_used == 120
        assert api.units_limit == 10000
        assert api.units_remaining == 9880

    def test_parse_units_header_warning_threshold(self):
        api = YandexDirectAPI("test_token")
        api._parse_and_check_units("9500/10000/500")
        assert api.units_used == 9500

    def test_parse_units_header_limit_exceeded(self):
        api = YandexDirectAPI("test_token")

        with pytest.raises(RuntimeError, match="limit exceeded"):
            api._parse_and_check_units("10000/10000/0")

    def test_parse_units_invalid_format(self):
        api = YandexDirectAPI("test_token")
        api._parse_and_check_units("invalid")
        assert api.units_used == 0


class TestYandexDirectAPIClients:
    """Test client info fetching"""

    @pytest.mark.asyncio
    async def test_get_clients_success(self):
        api = YandexDirectAPI("test_token")

        mock_response = _http_response(
            json_data={
                "result": {
                    "Clients": [
                        {"Login": "user1", "ClientInfo": "Info1"},
                        {"Login": "user2", "ClientInfo": "Info2"},
                    ]
                }
            }
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            clients = await api.get_clients()

            assert len(clients) == 2
            assert clients[0]["Login"] == "user1"

    @pytest.mark.asyncio
    async def test_get_clients_unauthorized(self):
        api = YandexDirectAPI("test_token")

        mock_response = _http_response(status_code=401, text="Unauthorized")

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(PermissionError, match="Unauthorized"):
                await api.get_clients()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
