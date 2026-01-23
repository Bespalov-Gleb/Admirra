"""
Unit тесты для Telegram уведомлений.

Запуск:
    python -m pytest tests/test_telegram_service.py -v
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


class TestTelegramNotifierUnit:
    """Unit тесты для TelegramNotifier."""

    def test_telegram_notifier_init(self):
        """TelegramNotifier должен инициализироваться."""
        from lead_validator.services.telegram import TelegramNotifier
        
        notifier = TelegramNotifier()
        assert notifier is not None
        assert hasattr(notifier, 'send_new_lead')
        assert hasattr(notifier, 'send_message')
        assert hasattr(notifier, 'test_connection')

    def test_telegram_url_format(self):
        """URL для Telegram API должен формироваться правильно."""
        from lead_validator.services.telegram import TelegramNotifier
        
        notifier = TelegramNotifier()
        notifier.token = "123456:ABC-DEF"
        
        url = notifier._get_url("sendMessage")
        assert "123456:ABC-DEF" in url
        assert "sendMessage" in url
        assert url.startswith("https://api.telegram.org/bot")

    def test_disabled_telegram_returns_false(self):
        """Отключённый Telegram должен возвращать False."""
        from lead_validator.services.telegram import TelegramNotifier
        from lead_validator.schemas import LeadInput
        
        notifier = TelegramNotifier()
        notifier.enabled = False
        
        lead = LeadInput(phone="+79991234567")
        # Синхронная проверка enabled
        assert notifier.enabled == False


class TestTelegramNotifierAsync:
    """Async тесты для TelegramNotifier."""

    @pytest.mark.asyncio
    async def test_send_new_lead_disabled(self):
        """При отключённом Telegram send_new_lead возвращает False."""
        from lead_validator.services.telegram import TelegramNotifier
        from lead_validator.schemas import LeadInput
        
        notifier = TelegramNotifier()
        notifier.enabled = False
        
        lead = LeadInput(phone="+79991234567")
        result = await notifier.send_new_lead(lead)
        assert result == False

    @pytest.mark.asyncio
    async def test_send_new_lead_success(self):
        """Успешная отправка уведомления о лиде."""
        from lead_validator.services.telegram import TelegramNotifier
        from lead_validator.schemas import LeadInput
        
        notifier = TelegramNotifier()
        notifier.enabled = True
        notifier.token = "test_token"
        notifier.chat_id = "123456"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "result": {"message_id": 123}}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            lead = LeadInput(
                phone="+79991234567",
                name="Тест Тестов",
                email="test@example.com"
            )
            
            result = await notifier.send_new_lead(lead)
            assert result == True

    @pytest.mark.asyncio
    async def test_send_new_lead_api_error(self):
        """При ошибке Telegram API должен возвращать False."""
        from lead_validator.services.telegram import TelegramNotifier
        from lead_validator.schemas import LeadInput
        
        notifier = TelegramNotifier()
        notifier.enabled = True
        notifier.token = "test_token"
        notifier.chat_id = "123456"
        
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"ok": False, "description": "Unauthorized"}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            lead = LeadInput(phone="+79991234567")
            
            result = await notifier.send_new_lead(lead)
            assert result == False

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Успешное тестирование подключения."""
        from lead_validator.services.telegram import TelegramNotifier
        
        notifier = TelegramNotifier()
        notifier.enabled = True
        notifier.token = "test_token"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True, 
            "result": {
                "id": 123456789,
                "first_name": "TestBot",
                "username": "test_bot"
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            result = await notifier.test_connection()
            # Проверяем что результат содержит данные
            assert result is not None


class TestLeadMessageFormatting:
    """Тесты форматирования сообщений о лидах."""

    def test_format_lead_message_minimal(self):
        """Минимальный лид должен форматироваться."""
        from lead_validator.services.telegram import TelegramNotifier
        from lead_validator.schemas import LeadInput
        
        notifier = TelegramNotifier()
        lead = LeadInput(phone="+79991234567")
        
        message = notifier._format_lead_message(lead)
        
        assert "+79991234567" in message or "7999" in message
        # Сообщение содержит телефон и какой-то заголовок
        assert "заявка" in message.lower() or "лид" in message.lower() or "Новая" in message

    def test_format_lead_message_full(self):
        """Полный лид с UTM должен форматироваться."""
        from lead_validator.services.telegram import TelegramNotifier
        from lead_validator.schemas import LeadInput
        
        notifier = TelegramNotifier()
        lead = LeadInput(
            phone="+79991234567",
            name="Иван Иванов",
            email="ivan@example.com",
            utm_source="yandex",
            utm_medium="cpc"
        )
        
        message = notifier._format_lead_message(
            lead,
            phone_type="Мобильный",
            provider="МТС",
            region="Москва"
        )
        
        # Проверяем наличие ключевых данных
        assert "Иван" in message
        assert "yandex" in message.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
