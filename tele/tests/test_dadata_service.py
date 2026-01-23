"""
Unit тесты для DaData сервиса.

Запуск:
    python -m pytest tests/test_dadata_service.py -v
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


class TestDaDataServiceUnit:
    """Unit тесты для DaDataService с моками."""

    def test_dadata_service_init(self):
        """DaDataService должен инициализироваться."""
        from lead_validator.services.dadata import DaDataService
        
        service = DaDataService()
        assert service is not None
        assert hasattr(service, 'validate_phone')
        assert hasattr(service, 'validate_email')

    def test_headers_contain_auth(self):
        """Заголовки должны содержать авторизацию."""
        from lead_validator.services.dadata import DaDataService
        
        service = DaDataService()
        headers = service._get_headers()
        
        assert "Authorization" in headers
        assert "X-Secret" in headers
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"

    def test_is_phone_valid_qc_0(self):
        """qc=0 должен считаться валидным."""
        from lead_validator.services.dadata import DaDataService
        from lead_validator.schemas import DaDataPhoneResponse
        
        service = DaDataService()
        response = DaDataPhoneResponse(
            source="+79991234567",
            qc=0,
            type="Мобильный"
        )
        
        assert service.is_phone_valid(response) == True

    def test_is_phone_valid_qc_7(self):
        """qc=7 (иностранный) должен считаться валидным."""
        from lead_validator.services.dadata import DaDataService
        from lead_validator.schemas import DaDataPhoneResponse
        
        service = DaDataService()
        response = DaDataPhoneResponse(
            source="+1234567890",
            qc=7,
            type="Мобильный"
        )
        
        assert service.is_phone_valid(response) == True

    def test_is_phone_invalid_qc_2(self):
        """qc=2 (мусор) должен быть невалидным."""
        from lead_validator.services.dadata import DaDataService
        from lead_validator.schemas import DaDataPhoneResponse
        
        service = DaDataService()
        response = DaDataPhoneResponse(
            source="абракадабра",
            qc=2,
            type=None
        )
        
        assert service.is_phone_valid(response) == False

    def test_is_mobile_true(self):
        """Мобильный номер должен определяться."""
        from lead_validator.services.dadata import DaDataService
        from lead_validator.schemas import DaDataPhoneResponse
        
        service = DaDataService()
        response = DaDataPhoneResponse(
            source="+79991234567",
            qc=0,
            type="Мобильный"
        )
        
        assert service.is_mobile(response) == True

    def test_is_mobile_false(self):
        """Стационарный номер не должен быть мобильным."""
        from lead_validator.services.dadata import DaDataService
        from lead_validator.schemas import DaDataPhoneResponse
        
        service = DaDataService()
        response = DaDataPhoneResponse(
            source="+74951234567",
            qc=0,
            type="Стационарный"
        )
        
        assert service.is_mobile(response) == False

    @pytest.mark.asyncio
    async def test_validate_phone_success(self):
        """Успешная валидация телефона через API (мок)."""
        from lead_validator.services.dadata import DaDataService
        
        service = DaDataService()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{
            "source": "+79991234567",
            "type": "Мобильный",
            "phone": "+7 999 123-45-67",
            "country_code": "7",
            "city_code": "999",
            "number": "1234567",
            "extension": None,
            "provider": "МТС",
            "country": "Россия",
            "region": "Москва",
            "city": None,
            "timezone": "UTC+3",
            "qc_conflict": 0,
            "qc": 0
        }]
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            result = await service.validate_phone("+79991234567")
            
            assert result is not None
            assert result.qc == 0
            assert result.type == "Мобильный"

    @pytest.mark.asyncio
    async def test_validate_phone_timeout(self):
        """Timeout при запросе к API должен возвращать None."""
        from lead_validator.services.dadata import DaDataService
        import httpx
        
        service = DaDataService()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            result = await service.validate_phone("+79991234567")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_validate_phone_auth_error(self):
        """Ошибка авторизации (401) должна возвращать None."""
        from lead_validator.services.dadata import DaDataService
        
        service = DaDataService()
        
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            result = await service.validate_phone("+79991234567")
            
            assert result is None


class TestDaDataPhoneResponse:
    """Тесты для DaDataPhoneResponse схемы."""

    def test_minimal_response(self):
        """Минимальный ответ должен создаваться."""
        from lead_validator.schemas import DaDataPhoneResponse
        
        response = DaDataPhoneResponse(source="+79991234567")
        
        assert response.source == "+79991234567"
        assert response.qc == 1  # default

    def test_full_response(self):
        """Полный ответ со всеми полями."""
        from lead_validator.schemas import DaDataPhoneResponse
        
        response = DaDataPhoneResponse(
            source="+79991234567",
            type="Мобильный",
            phone="+7 999 123-45-67",
            country_code="7",
            city_code="999",
            number="1234567",
            extension=None,
            provider="МТС",
            country="Россия",
            region="Москва",
            city=None,
            timezone="UTC+3",
            qc_conflict=0,
            qc=0
        )
        
        assert response.type == "Мобильный"
        assert response.provider == "МТС"
        assert response.qc == 0


class TestDaDataEmailValidation:
    """Тесты валидации email через DaData."""

    def test_is_email_valid_qc_0(self):
        """Email с qc=0 валиден."""
        from lead_validator.services.dadata import DaDataService
        
        service = DaDataService()
        response = {"qc": 0, "type": "PERSONAL"}
        
        assert service.is_email_valid(response) == True

    def test_is_email_valid_qc_1(self):
        """Email с qc=1 (исправлен) валиден."""
        from lead_validator.services.dadata import DaDataService
        
        service = DaDataService()
        response = {"qc": 1, "type": "CORPORATE"}
        
        assert service.is_email_valid(response) == True

    def test_is_email_invalid_qc_2(self):
        """Email с qc=2 (мусор) невалиден."""
        from lead_validator.services.dadata import DaDataService
        
        service = DaDataService()
        response = {"qc": 2, "type": None}
        
        assert service.is_email_valid(response) == False

    def test_is_email_disposable_true(self):
        """Email типа DISPOSABLE определяется как одноразовый."""
        from lead_validator.services.dadata import DaDataService
        
        service = DaDataService()
        response = {"qc": 0, "type": "DISPOSABLE"}
        
        assert service.is_email_disposable(response) == True

    def test_is_email_disposable_false(self):
        """Email типа PERSONAL не одноразовый."""
        from lead_validator.services.dadata import DaDataService
        
        service = DaDataService()
        response = {"qc": 0, "type": "PERSONAL"}
        
        assert service.is_email_disposable(response) == False

    def test_get_email_type(self):
        """Получение типа email."""
        from lead_validator.services.dadata import DaDataService
        
        service = DaDataService()
        
        assert service.get_email_type({"type": "PERSONAL"}) == "PERSONAL"
        assert service.get_email_type({"type": "CORPORATE"}) == "CORPORATE"
        assert service.get_email_type({"type": "ROLE"}) == "ROLE"
        assert service.get_email_type({"type": "DISPOSABLE"}) == "DISPOSABLE"
        assert service.get_email_type({}) == "UNKNOWN"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

