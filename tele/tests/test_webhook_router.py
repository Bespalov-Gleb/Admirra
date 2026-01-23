"""
Тесты для webhook эндпоинтов Tilda и Marquiz.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

# Import app
from lead_validator.standalone import app


@pytest.fixture
def client():
    """Test client for the FastAPI app."""
    return TestClient(app)


# ============================================================================
# Tilda Webhook Tests
# ============================================================================

class TestTildaWebhook:
    """Тесты для /webhook/tilda/ эндпоинта."""

    @patch('lead_validator.validators.lead_validator.validate')
    def test_tilda_webhook_basic(self, mock_validate, client):
        """Тест базового webhook от Tilda."""
        # Mock the async validator - need to return a proper awaitable
        from lead_validator.schemas import ValidationResult
        
        async def mock_validate_async(*args, **kwargs):
            return ValidationResult(
                success=True,
                lead_id="test_123",
                execution_time_ms=50.0,
                phone_type="Мобильный",
                phone_provider="МТС",
                phone_region="Москва",
                dadata_qc=0
            )
        
        mock_validate.side_effect = mock_validate_async
        
        response = client.post("/webhook/tilda/", json={
            "name": "Виктор",
            "phone": "+7 (921) 580-71-70",
            "firm": "Toyota RAIZE",
            "cash": "1,3 млн руб",
            "city": "Санкт-петербург",
            "formid": "form1616303501",
            "formname": "Подобрать авто",
            "referer": "https://sakuraat.ru/?utm_source=yandex&utm_medium=adm&utm_campaign=705607755"
        })
        
        assert response.status_code == 200

    @patch('lead_validator.validators.lead_validator.validate')
    def test_tilda_webhook_with_utm_extraction(self, mock_validate, client):
        """Тест извлечения UTM из referer."""
        from lead_validator.webhook_router import extract_utm_from_url
        
        url = "https://sakuraat.ru/?utm_source=yandex&utm_medium=adm&utm_campaign=705607755&utm_content=17476504130|none"
        utm = extract_utm_from_url(url)
        
        assert utm["utm_source"] == "yandex"
        assert utm["utm_medium"] == "adm"
        assert utm["utm_campaign"] == "705607755"
        assert utm["utm_content"] == "17476504130|none"

    def test_tilda_webhook_missing_phone(self, client):
        """Тест webhook без обязательного поля phone."""
        response = client.post("/webhook/tilda/", json={
            "name": "Тест",
            "city": "Москва"
        })
        
        assert response.status_code == 422  # Validation error


# ============================================================================
# Marquiz Webhook Tests
# ============================================================================

class TestMarquizWebhook:
    """Тесты для /webhook/marquiz/ эндпоинта."""

    @patch('lead_validator.validators.lead_validator.validate')
    def test_marquiz_webhook_basic(self, mock_validate, client):
        """Тест базового webhook от Marquiz."""
        from lead_validator.schemas import ValidationResult
        
        async def mock_validate_async(*args, **kwargs):
            return ValidationResult(
                success=True,
                lead_id="test_456",
                execution_time_ms=45.0,
                phone_type="Мобильный",
                phone_provider="Билайн",
                phone_region="Калуга",
                dadata_qc=0
            )
        
        mock_validate.side_effect = mock_validate_async
        
        response = client.post("/webhook/marquiz/", json={
            "name": "Валентин",
            "phone": "+79308466665",
            "email": "shkodin.valentin@mail.ru",
            "location": "Россия, Калуга",
            "leadTimezone": "UTC 3",
            "IP": "95.26.61.74",
            "userAgent": "Mozilla/5.0 (Linux; Android 13)",
            "utm_source": "yandex",
            "utm_medium": "adm",
            "utm_campaign": "704673934",
            "quiz": "Thailand Villa Center / landing 2.0"
        })
        
        assert response.status_code == 200

    @patch('lead_validator.validators.lead_validator.validate')
    def test_marquiz_webhook_utm_from_source_url(self, mock_validate, client):
        """Тест извлечения UTM из source URL когда utm_* поля пусты."""
        from lead_validator.schemas import ValidationResult
        
        async def mock_validate_async(*args, **kwargs):
            return ValidationResult(
                success=True,
                lead_id="test_789",
                execution_time_ms=55.0
            )
        
        mock_validate.side_effect = mock_validate_async
        
        response = client.post("/webhook/marquiz/", json={
            "name": "Тест",
            "phone": "+79001234567",
            "source": "https://mrqz.me/quiz?utm_source=google&utm_medium=cpc"
        })
        
        assert response.status_code == 200

    def test_marquiz_webhook_missing_phone(self, client):
        """Тест webhook без обязательного поля phone."""
        response = client.post("/webhook/marquiz/", json={
            "name": "Тест",
            "email": "test@mail.ru"
        })
        
        assert response.status_code == 422


# ============================================================================
# Helper Function Tests
# ============================================================================

class TestHelperFunctions:
    """Тесты вспомогательных функций."""

    def test_extract_country_from_location(self):
        """Тест извлечения страны из location."""
        from lead_validator.webhook_router import extract_country_from_location
        
        assert extract_country_from_location("Россия, Москва") == "RU"
        assert extract_country_from_location("Россия, Калуга") == "RU"
        assert extract_country_from_location("Украина, Киев") == "UA"
        assert extract_country_from_location("Kazakhstan, Almaty") == "KZ"
        assert extract_country_from_location("Unknown") is None
        assert extract_country_from_location(None) is None

    def test_parse_timezone_offset(self):
        """Тест парсинга timezone."""
        from lead_validator.webhook_router import parse_timezone_offset
        
        assert parse_timezone_offset("UTC 3") == "Europe/Moscow"
        assert parse_timezone_offset("UTC 5") == "Asia/Yekaterinburg"
        assert parse_timezone_offset("UTC 10") == "Asia/Vladivostok"
        assert parse_timezone_offset("UTC+3") == "Europe/Moscow"
        assert parse_timezone_offset(None) is None

    def test_extract_utm_empty_url(self):
        """Тест извлечения UTM из пустого URL."""
        from lead_validator.webhook_router import extract_utm_from_url
        
        utm = extract_utm_from_url("")
        assert utm["utm_source"] is None
        assert utm["utm_medium"] is None
        
        utm = extract_utm_from_url(None)
        assert utm["utm_source"] is None


# ============================================================================
# Webhook Info Endpoint Tests
# ============================================================================

class TestWebhookInfo:
    """Тесты для /webhook/info эндпоинта."""

    def test_webhook_info(self, client):
        """Тест получения информации о webhook URLs."""
        response = client.get("/webhook/info")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "endpoints" in data
        assert "tilda" in data["endpoints"]
        assert "marquiz" in data["endpoints"]
        assert "/webhook/tilda/" in data["endpoints"]["tilda"]
        assert "/webhook/marquiz/" in data["endpoints"]["marquiz"]
        
        assert "tilda_setup" in data
        assert "marquiz_setup" in data
