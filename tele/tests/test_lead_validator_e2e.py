"""
E2E тесты для Lead Validator API.
Тесты для Telegram, Airtable, и полного процесса валидации.

ВАЖНО: Эти тесты требуют запущенный сервер!

Запуск:
    1. Запустите сервер: python -m lead_validator.standalone
    2. Запустите тесты: python -m pytest tests/test_lead_validator_e2e.py -v
    
Пропуск E2E тестов:
    python -m pytest tests/ -v -m "not integration"
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock
import httpx


# Базовый URL для тестов (сервер должен быть запущен)
BASE_URL = "http://localhost:8000/api"


# Маркер для E2E тестов, требующих запущенный сервер
pytestmark = pytest.mark.integration


class TestHealthCheck:
    """Тесты health check эндпоинта"""

    @pytest.mark.asyncio
    async def test_health_check_returns_ok(self):
        """Health check должен возвращать status ok"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{BASE_URL}/lead/health", timeout=5.0)
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "ok"
                assert data["service"] == "lead_validator"
            except httpx.ConnectError:
                pytest.skip("Server not running - skipping E2E test")


class TestLeadValidation:
    """Тесты валидации лидов"""

    @pytest.mark.asyncio
    async def test_valid_lead_accepted(self):
        """Валидный лид должен быть принят"""
        timestamp = int(time.time()) - 10  # 10 секунд назад
        payload = {
            "phone": "+79991234567",
            "email": "test@example.com",
            "name": "Тест Тестов",
            "timestamp": timestamp
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(f"{BASE_URL}/lead/", json=payload)
                assert response.status_code == 200
                data = response.json()
                # Проверяем структуру ответа
                assert "success" in data
                assert "execution_time_ms" in data
            except httpx.ConnectError:
                pytest.skip("Server not running - skipping E2E test")

    @pytest.mark.asyncio
    async def test_honeypot_triggers_rejection(self):
        """Заполненное honeypot поле должно отклонять лид"""
        payload = {
            "phone": "+79991234567",
            "honeypot": "bot_filled_this"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(f"{BASE_URL}/lead/", json=payload)
                assert response.status_code == 200
                data = response.json()
                assert data["success"] == False
                assert "honeypot" in data.get("rejection_reason", "")
            except httpx.ConnectError:
                pytest.skip("Server not running - skipping E2E test")

    @pytest.mark.asyncio
    async def test_too_fast_form_fill_rejected(self):
        """Слишком быстрое заполнение должно отклоняться"""
        payload = {
            "phone": "+79991234567",
            "timestamp": int(time.time())  # Прямо сейчас (0 секунд)
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(f"{BASE_URL}/lead/", json=payload)
                assert response.status_code == 200
                data = response.json()
                assert data["success"] == False
                assert "too_fast" in data.get("rejection_reason", "")
            except httpx.ConnectError:
                pytest.skip("Server not running - skipping E2E test")

    @pytest.mark.asyncio
    async def test_empty_phone_rejected(self):
        """Пустой телефон должен отклоняться"""
        payload = {"phone": ""}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(f"{BASE_URL}/lead/", json=payload)
                # Может быть 200 с success=False или 422 (validation error)
                if response.status_code == 200:
                    data = response.json()
                    assert data["success"] == False
                else:
                    assert response.status_code == 422
            except httpx.ConnectError:
                pytest.skip("Server not running - skipping E2E test")

    @pytest.mark.asyncio
    async def test_short_phone_rejected(self):
        """Слишком короткий телефон должен отклоняться"""
        timestamp = int(time.time()) - 10
        payload = {
            "phone": "123",
            "timestamp": timestamp
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(f"{BASE_URL}/lead/", json=payload)
                assert response.status_code == 200
                data = response.json()
                assert data["success"] == False
            except httpx.ConnectError:
                pytest.skip("Server not running - skipping E2E test")


class TestTelegramNotifications:
    """Тесты Telegram уведомлений"""

    @pytest.mark.asyncio
    async def test_telegram_test_endpoint(self):
        """Тест эндпоинта проверки Telegram"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{BASE_URL}/lead/test-telegram")
                assert response.status_code == 200
                data = response.json()
                # Проверяем структуру ответа
                assert "ok" in data
            except httpx.ConnectError:
                pytest.skip("Server not running - skipping E2E test")


class TestCaptchaStub:
    """Тесты заглушки CAPTCHA"""

    @pytest.mark.asyncio
    async def test_lead_without_captcha_accepted(self):
        """Лид без CAPTCHA токена должен приниматься (заглушка отключена)"""
        timestamp = int(time.time()) - 10
        payload = {
            "phone": "+79998887766",
            "timestamp": timestamp
            # cf_turnstile_response отсутствует
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(f"{BASE_URL}/lead/", json=payload)
                assert response.status_code == 200
                # Лид не должен быть отклонён из-за CAPTCHA (т.к. выключена)
                data = response.json()
                if data.get("rejection_reason"):
                    assert "captcha" not in data["rejection_reason"]
            except httpx.ConnectError:
                pytest.skip("Server not running - skipping E2E test")


class TestStatisticsEndpoint:
    """Тесты эндпоинта статистики"""

    @pytest.mark.asyncio
    async def test_stats_returns_structure(self):
        """Статистика возвращает правильную структуру"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{BASE_URL}/lead/stats")
                assert response.status_code == 200
                data = response.json()
                assert "date" in data
                assert "total" in data
                assert "by_reason" in data
            except httpx.ConnectError:
                pytest.skip("Server not running - skipping E2E test")


# ============ UNIT ТЕСТЫ (не требуют сервера) ============

# Убираем маркер integration для unit тестов
class TestUnitTurnstileValidator:
    """Unit тесты для Turnstile валидатора"""
    
    pytestmark = []  # Убираем маркер integration

    @pytest.mark.asyncio
    async def test_disabled_turnstile_always_passes(self):
        """Отключённый Turnstile всегда пропускает"""
        from lead_validator.services.turnstile import TurnstileValidator
        
        # Создаём валидатор с отключённым состоянием
        validator = TurnstileValidator()
        validator.enabled = False
        
        is_valid, error = await validator.validate(None)
        assert is_valid == True
        assert error == ""

    @pytest.mark.asyncio
    async def test_missing_token_rejected_when_enabled(self):
        """Отсутствующий токен отклоняется при включённом Turnstile"""
        from lead_validator.services.turnstile import TurnstileValidator
        
        validator = TurnstileValidator()
        validator.enabled = True
        validator.secret_key = "test_secret"
        
        is_valid, error = await validator.validate(None)
        assert is_valid == False
        assert error == "captcha_missing"


class TestUnitTelegramNotifier:
    """Unit тесты для Telegram уведомителя"""
    
    pytestmark = []  # Убираем маркер integration

    @pytest.mark.asyncio
    async def test_disabled_telegram_returns_false(self):
        """Отключённый Telegram возвращает False"""
        from lead_validator.services.telegram import TelegramNotifier
        from lead_validator.schemas import LeadInput
        
        notifier = TelegramNotifier()
        notifier.enabled = False
        
        lead = LeadInput(phone="+79991234567")
        result = await notifier.send_new_lead(lead)
        assert result == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
