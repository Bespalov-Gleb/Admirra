"""
Unit тесты для Яндекс.Метрика сервиса (офлайн-конверсии).

Запуск:
    python -m pytest tests/test_metrica_service.py -v
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime


class TestMetricaServiceUnit:
    """Unit тесты для MetricaService."""

    def test_metrica_service_init(self):
        """MetricaService должен инициализироваться."""
        from lead_validator.services.metrica_service import MetricaService
        
        service = MetricaService()
        assert service is not None
        assert hasattr(service, 'send_conversion')
        assert hasattr(service, 'send_quality_lead')
        assert hasattr(service, 'send_spam_lead')
        assert hasattr(service, 'test_connection')


class TestMetricaConversions:
    """Тесты отправки конверсий."""

    @pytest.mark.asyncio
    async def test_send_conversion_disabled(self):
        """При отключённой Метрике конверсии не отправляются."""
        from lead_validator.services.metrica_service import MetricaService
        
        service = MetricaService()
        service.enabled = False
        
        result = await service.send_conversion("client_123", "quality_lead")
        assert result == False

    @pytest.mark.asyncio
    async def test_send_quality_lead_disabled(self):
        """При отключённой Метрике качественный лид не отправляется."""
        from lead_validator.services.metrica_service import MetricaService
        
        service = MetricaService()
        service.enabled = False
        
        result = await service.send_quality_lead("client_123")
        assert result == False

    @pytest.mark.asyncio
    async def test_send_spam_lead_disabled(self):
        """При отключённой Метрике спам лид не отправляется."""
        from lead_validator.services.metrica_service import MetricaService
        
        service = MetricaService()
        service.enabled = False
        
        result = await service.send_spam_lead("client_123")
        assert result == False

    @pytest.mark.asyncio
    async def test_send_conversion_success(self):
        """Успешная отправка конверсии."""
        from lead_validator.services.metrica_service import MetricaService
        
        service = MetricaService()
        service.enabled = True
        service.counter_id = "12345"
        service.oauth_token = "test_token"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 200, "uploading": {"id": 1}}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            result = await service.send_conversion("client_123", "quality_lead")
            assert result == True

    @pytest.mark.asyncio
    async def test_send_conversion_api_error(self):
        """При ошибке API Метрики возвращает False."""
        from lead_validator.services.metrica_service import MetricaService
        
        service = MetricaService()
        service.enabled = True
        service.counter_id = "12345"
        service.oauth_token = "test_token"
        
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            result = await service.send_conversion("client_123", "quality_lead")
            assert result == False


class TestMetricaCSVBuilding:
    """Тесты формирования CSV для загрузки."""

    def test_build_csv_basic(self):
        """CSV должен формироваться корректно."""
        from lead_validator.services.metrica_service import MetricaService
        
        service = MetricaService()
        
        csv = service._build_csv(
            client_id="123456789",
            goal_name="качественный_лид",
            datetime_str="2026-01-20 10:30:00"
        )
        
        assert "ClientId" in csv
        assert "Target" in csv
        assert "DateTime" in csv
        assert "123456789" in csv
        assert "качественный_лид" in csv

    def test_build_csv_with_price(self):
        """CSV с ценой должен включать колонку Price."""
        from lead_validator.services.metrica_service import MetricaService
        
        service = MetricaService()
        
        csv = service._build_csv(
            client_id="123456789",
            goal_name="качественный_лид",
            datetime_str="2026-01-20 10:30:00",
            price=1000.0
        )
        
        assert "Price" in csv
        assert "Currency" in csv
        assert "1000" in csv


class TestMetricaConnection:
    """Тесты проверки подключения к Метрике."""

    @pytest.mark.asyncio
    async def test_connection_disabled(self):
        """При отключённой Метрике test_connection возвращает ошибку."""
        from lead_validator.services.metrica_service import MetricaService
        
        service = MetricaService()
        service.enabled = False
        
        result = await service.test_connection()
        assert "error" in result or result.get("enabled") == False

    @pytest.mark.asyncio
    async def test_connection_success(self):
        """Успешная проверка подключения к Метрике."""
        from lead_validator.services.metrica_service import MetricaService
        
        service = MetricaService()
        service.enabled = True
        service.counter_id = "12345"
        service.oauth_token = "test_token"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "counter": {
                "id": 12345,
                "name": "Test Counter",
                "site": "example.com"
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            result = await service.test_connection()
            assert "error" not in result or result.get("counter") is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
