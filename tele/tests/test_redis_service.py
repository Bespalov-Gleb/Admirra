"""
Unit тесты для Redis сервиса (дедупликация и rate limiting).

Запуск:
    python -m pytest tests/test_redis_service.py -v
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


class TestRedisServiceUnit:
    """Unit тесты для RedisService."""

    def test_redis_service_init(self):
        """RedisService должен инициализироваться."""
        from lead_validator.services.redis_service import RedisService
        
        service = RedisService()
        assert service is not None
        assert hasattr(service, 'is_duplicate')
        assert hasattr(service, 'mark_phone')
        assert hasattr(service, 'check_rate_limit')

    def test_hash_phone_consistent(self):
        """Хеш телефона должен быть консистентным."""
        from lead_validator.services.redis_service import RedisService
        
        phone = "+79991234567"
        hash1 = RedisService.hash_phone(phone)
        hash2 = RedisService.hash_phone(phone)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex

    def test_hash_phone_normalizes(self):
        """Хеш должен нормализовать телефон (только цифры)."""
        from lead_validator.services.redis_service import RedisService
        
        # Разные форматы одного номера
        phone1 = "+7 (999) 123-45-67"
        phone2 = "79991234567"
        phone3 = "+7-999-123-45-67"
        
        hash1 = RedisService.hash_phone(phone1)
        hash2 = RedisService.hash_phone(phone2)
        hash3 = RedisService.hash_phone(phone3)
        
        assert hash1 == hash2 == hash3

    def test_hash_phone_different_numbers(self):
        """Разные телефоны должны иметь разные хеши."""
        from lead_validator.services.redis_service import RedisService
        
        hash1 = RedisService.hash_phone("+79991234567")
        hash2 = RedisService.hash_phone("+79991234568")
        
        assert hash1 != hash2


class TestRedisServiceDuplication:
    """Тесты дедупликации телефонов."""

    @pytest.mark.asyncio
    async def test_fail_open_when_disabled(self):
        """При отключённом Redis должен пропускать (fail-open)."""
        from lead_validator.services.redis_service import RedisService
        
        service = RedisService()
        service.enabled = False
        service.fail_open = True
        
        # Должен вернуть False (не дубликат) при fail-open
        is_dup = await service.is_duplicate("+79991234567")
        assert is_dup == False

    @pytest.mark.asyncio
    async def test_fail_closed_when_disabled(self):
        """При fail_open=False и отключённом Redis должен блокировать."""
        from lead_validator.services.redis_service import RedisService
        
        service = RedisService()
        service.enabled = False
        service.fail_open = False
        
        # Должен вернуть True (блокировать) при fail-closed
        is_dup = await service.is_duplicate("+79991234567")
        assert is_dup == True

    @pytest.mark.asyncio
    async def test_is_duplicate_with_mock_redis(self):
        """Проверка дубликата через мок Redis."""
        from lead_validator.services.redis_service import RedisService
        
        service = RedisService()
        service.enabled = True
        
        # Мокаем Redis клиент
        mock_client = AsyncMock()
        mock_client.exists = AsyncMock(return_value=1)  # Найден дубликат
        service._client = mock_client
        
        with patch.object(service, '_get_client', return_value=mock_client):
            is_dup = await service.is_duplicate("+79991234567")
            assert is_dup == True

    @pytest.mark.asyncio
    async def test_not_duplicate_with_mock_redis(self):
        """Проверка нового телефона через мок Redis."""
        from lead_validator.services.redis_service import RedisService
        
        service = RedisService()
        service.enabled = True
        
        mock_client = AsyncMock()
        mock_client.exists = AsyncMock(return_value=0)  # Дубликат не найден
        service._client = mock_client
        
        with patch.object(service, '_get_client', return_value=mock_client):
            is_dup = await service.is_duplicate("+79991234567")
            assert is_dup == False


class TestRedisServiceRateLimiting:
    """Тесты rate limiting."""

    @pytest.mark.asyncio
    async def test_rate_limit_fail_open(self):
        """При отключённом Redis rate limit должен пропускать."""
        from lead_validator.services.redis_service import RedisService
        
        service = RedisService()
        service.enabled = False
        service.fail_open = True
        
        allowed = await service.check_rate_limit("1.2.3.4")
        assert allowed == True

    @pytest.mark.asyncio
    async def test_rate_limit_not_exceeded(self):
        """Rate limit не превышен — должен пропустить."""
        from lead_validator.services.redis_service import RedisService
        
        service = RedisService()
        service.enabled = True
        
        mock_client = AsyncMock()
        mock_client.incr = AsyncMock(return_value=1)  # Первый запрос
        mock_client.expire = AsyncMock()
        
        with patch.object(service, '_get_client', return_value=mock_client):
            with patch('lead_validator.services.redis_service.settings') as mock_settings:
                mock_settings.RATE_LIMIT_PER_IP = 10
                mock_settings.RATE_LIMIT_WINDOW_SEC = 3600
                
                allowed = await service.check_rate_limit("1.2.3.4")
                assert allowed == True

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """Rate limit превышен — должен заблокировать."""
        from lead_validator.services.redis_service import RedisService
        
        service = RedisService()
        service.enabled = True
        
        mock_client = AsyncMock()
        mock_client.incr = AsyncMock(return_value=15)  # Превышен лимит (10)
        
        with patch.object(service, '_get_client', return_value=mock_client):
            with patch('lead_validator.services.redis_service.settings') as mock_settings:
                mock_settings.RATE_LIMIT_PER_IP = 10
                mock_settings.RATE_LIMIT_WINDOW_SEC = 3600
                
                allowed = await service.check_rate_limit("1.2.3.4")
                assert allowed == False


class TestRedisServiceMarkPhone:
    """Тесты сохранения телефона."""

    @pytest.mark.asyncio
    async def test_mark_phone_disabled(self):
        """При отключённом Redis mark_phone возвращает False."""
        from lead_validator.services.redis_service import RedisService
        
        service = RedisService()
        service.enabled = False
        
        result = await service.mark_phone("+79991234567")
        assert result == False

    @pytest.mark.asyncio
    async def test_mark_phone_success(self):
        """Успешное сохранение телефона в Redis."""
        from lead_validator.services.redis_service import RedisService
        
        service = RedisService()
        service.enabled = True
        
        mock_client = AsyncMock()
        mock_client.setex = AsyncMock()
        
        with patch.object(service, '_get_client', return_value=mock_client):
            with patch('lead_validator.services.redis_service.settings') as mock_settings:
                mock_settings.PHONE_DUPLICATE_TTL_SEC = 86400
                
                result = await service.mark_phone("+79991234567")
                assert result == True
                mock_client.setex.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
