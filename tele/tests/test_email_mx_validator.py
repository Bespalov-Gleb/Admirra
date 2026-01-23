"""
Unit тесты для email MX-валидатора и timezone-валидатора.

Запуск:
    python -m pytest tests/test_email_mx_validator.py -v
"""

import pytest


class TestEmailMXValidator:
    """Тесты проверки MX-записей."""

    def test_mx_validator_init(self):
        """MX-валидатор должен инициализироваться."""
        from lead_validator.services.email_mx_validator import EmailMXValidator
        
        validator = EmailMXValidator()
        assert validator is not None
        assert hasattr(validator, 'check_mx')
        assert hasattr(validator, 'has_valid_mx')

    def test_gmail_has_mx(self):
        """Gmail должен иметь MX-записи."""
        from lead_validator.services.email_mx_validator import email_mx_validator
        
        result = email_mx_validator.check_mx("test@gmail.com")
        assert result.has_mx == True
        assert len(result.mx_records) > 0

    def test_yandex_has_mx(self):
        """Yandex должен иметь MX-записи."""
        from lead_validator.services.email_mx_validator import email_mx_validator
        
        result = email_mx_validator.check_mx("test@yandex.ru")
        assert result.has_mx == True

    def test_mailru_has_mx(self):
        """Mail.ru должен иметь MX-записи."""
        from lead_validator.services.email_mx_validator import email_mx_validator
        
        result = email_mx_validator.check_mx("test@mail.ru")
        assert result.has_mx == True

    def test_nonexistent_domain_no_mx(self):
        """Несуществующий домен не должен иметь MX."""
        from lead_validator.services.email_mx_validator import email_mx_validator
        
        result = email_mx_validator.check_mx("test@thisdomaindoesnotexist12345.xyz")
        assert result.has_mx == False
        assert result.error is not None

    def test_invalid_email_format(self):
        """Невалидный формат email."""
        from lead_validator.services.email_mx_validator import email_mx_validator
        
        result = email_mx_validator.check_mx("not-an-email")
        assert result.has_mx == False
        assert result.error == "invalid_email_format"

    def test_empty_email(self):
        """Пустой email."""
        from lead_validator.services.email_mx_validator import email_mx_validator
        
        result = email_mx_validator.check_mx("")
        assert result.has_mx == False

    def test_has_valid_mx_helper(self):
        """Проверка helper метода has_valid_mx."""
        from lead_validator.services.email_mx_validator import email_mx_validator
        
        assert email_mx_validator.has_valid_mx("test@gmail.com") == True
        assert email_mx_validator.has_valid_mx("test@nonexistent12345.xyz") == False

    def test_mx_cache(self):
        """Результаты должны кэшироваться."""
        from lead_validator.services.email_mx_validator import EmailMXValidator
        
        validator = EmailMXValidator()
        
        # Первый запрос
        result1 = validator.check_mx("test@gmail.com")
        
        # Второй запрос — из кэша
        result2 = validator.check_mx("test@gmail.com")
        
        assert result1.mx_records == result2.mx_records


class TestTimezoneValidator:
    """Тесты валидации timezone браузера."""

    def test_timezone_validator_init(self):
        """Timezone-валидатор должен инициализироваться."""
        from lead_validator.services.email_mx_validator import TimezoneValidator
        
        validator = TimezoneValidator()
        assert validator is not None
        assert hasattr(validator, 'validate')

    def test_moscow_timezone_ru_ip(self):
        """Московский timezone с российским IP — OK."""
        from lead_validator.services.email_mx_validator import timezone_validator
        
        result = timezone_validator.validate(
            browser_timezone="Europe/Moscow",
            ip_country="RU"
        )
        
        assert result.is_valid == True
        assert result.is_suspicious == False

    def test_tokyo_timezone_ru_ip(self):
        """Токийский timezone с российским IP — подозрительно."""
        from lead_validator.services.email_mx_validator import timezone_validator
        
        result = timezone_validator.validate(
            browser_timezone="Asia/Tokyo",
            ip_country="RU"
        )
        
        assert result.is_suspicious == True
        assert result.warning is not None

    def test_empty_timezone(self):
        """Пустой timezone — пропускаем."""
        from lead_validator.services.email_mx_validator import timezone_validator
        
        result = timezone_validator.validate(
            browser_timezone=None,
            ip_country="RU"
        )
        
        assert result.is_valid == True

    def test_russian_timezone_list(self):
        """Все российские timezone должны определяться."""
        from lead_validator.services.email_mx_validator import timezone_validator
        
        russian_tz = [
            "Europe/Moscow", "Europe/Kaliningrad", 
            "Asia/Yekaterinburg", "Asia/Vladivostok"
        ]
        
        for tz in russian_tz:
            assert timezone_validator.is_timezone_russian(tz) == True

    def test_foreign_timezone_not_russian(self):
        """Иностранные timezone не должны быть российскими."""
        from lead_validator.services.email_mx_validator import timezone_validator
        
        foreign_tz = ["America/New_York", "Europe/London", "Asia/Tokyo"]
        
        for tz in foreign_tz:
            assert timezone_validator.is_timezone_russian(tz) == False


class TestEmailDeduplicationRedis:
    """Тесты дедупликации email в Redis."""

    def test_hash_email_consistent(self):
        """Хеш email должен быть консистентным."""
        from lead_validator.services.redis_service import RedisService
        
        email = "Test@Example.COM"
        hash1 = RedisService.hash_email(email)
        hash2 = RedisService.hash_email(email)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex

    def test_hash_email_normalizes(self):
        """Хеш должен нормализовать email."""
        from lead_validator.services.redis_service import RedisService
        
        # Разные регистры одного email
        email1 = "User@Gmail.com"
        email2 = "user@gmail.com"
        email3 = "USER@GMAIL.COM"
        
        hash1 = RedisService.hash_email(email1)
        hash2 = RedisService.hash_email(email2)
        hash3 = RedisService.hash_email(email3)
        
        assert hash1 == hash2 == hash3

    def test_hash_email_different_emails(self):
        """Разные email должны иметь разные хеши."""
        from lead_validator.services.redis_service import RedisService
        
        hash1 = RedisService.hash_email("user1@gmail.com")
        hash2 = RedisService.hash_email("user2@gmail.com")
        
        assert hash1 != hash2

    @pytest.mark.asyncio
    async def test_email_duplicate_disabled(self):
        """При отключённом Redis дубликаты не определяются (fail-open)."""
        from lead_validator.services.redis_service import RedisService
        
        service = RedisService()
        service.enabled = False
        service.fail_open = True
        
        result = await service.is_email_duplicate("test@example.com")
        assert result == False

    @pytest.mark.asyncio
    async def test_mark_email_disabled(self):
        """При отключённом Redis mark_email возвращает False."""
        from lead_validator.services.redis_service import RedisService
        
        service = RedisService()
        service.enabled = False
        
        result = await service.mark_email("test@example.com")
        assert result == False

    @pytest.mark.asyncio
    async def test_empty_email_not_duplicate(self):
        """Пустой email не должен считаться дубликатом."""
        from lead_validator.services.redis_service import RedisService
        
        service = RedisService()
        
        result = await service.is_email_duplicate("")
        assert result == False
        
        result = await service.is_email_duplicate(None)
        assert result == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
