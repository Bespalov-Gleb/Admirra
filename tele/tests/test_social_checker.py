"""
Unit тесты для социального чекера (ТГ, WA, ВК).

Запуск:
    python -m pytest tests/test_social_checker.py -v
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


class TestSocialCheckerUnit:
    """Unit тесты для SocialChecker."""

    def test_social_checker_init(self):
        """SocialChecker должен инициализироваться."""
        from lead_validator.services.social_checker import SocialChecker
        
        checker = SocialChecker()
        assert checker is not None
        assert hasattr(checker, 'check_phone')
        assert hasattr(checker, 'check_telegram')
        assert hasattr(checker, 'check_whatsapp')
        assert hasattr(checker, 'check_vk')

    def test_social_checker_disabled_by_default(self):
        """SocialChecker должен быть отключён по умолчанию (заглушка)."""
        from lead_validator.services.social_checker import SocialChecker
        
        checker = SocialChecker()
        assert checker.enabled == False


class TestSocialCheckResult:
    """Тесты для SocialCheckResult dataclass."""

    def test_social_check_result_creation(self):
        """SocialCheckResult должен создаваться."""
        from lead_validator.services.social_checker import SocialCheckResult
        
        result = SocialCheckResult(phone="+79991234567")
        
        assert result.phone == "+79991234567"
        assert result.has_telegram is None
        assert result.has_whatsapp is None
        assert result.has_viber is None
        assert result.has_vk is None
        assert result.checked == False

    def test_social_check_result_with_data(self):
        """SocialCheckResult с данными о соцсетях."""
        from lead_validator.services.social_checker import SocialCheckResult
        
        result = SocialCheckResult(
            phone="+79991234567",
            has_telegram=True,
            has_whatsapp=True,
            has_viber=False,
            has_vk=True,
            telegram_username="@testuser",
            vk_profile_url="https://vk.com/id123",
            checked=True
        )
        
        assert result.has_telegram == True
        assert result.telegram_username == "@testuser"
        assert result.checked == True


class TestSocialCheckerAsync:
    """Async тесты для SocialChecker."""

    @pytest.mark.asyncio
    async def test_check_phone_disabled(self):
        """При отключённом чекере возвращает пустой результат."""
        from lead_validator.services.social_checker import SocialChecker
        
        checker = SocialChecker()
        checker.enabled = False
        
        result = await checker.check_phone("+79991234567")
        
        assert result.phone == "+79991234567"
        assert result.checked == False
        assert result.error is not None  # Должна быть причина

    @pytest.mark.asyncio
    async def test_check_telegram_disabled(self):
        """При отключённом чекере Telegram возвращает None."""
        from lead_validator.services.social_checker import SocialChecker
        
        checker = SocialChecker()
        checker.enabled = False
        
        result = await checker.check_telegram("+79991234567")
        assert result is None

    @pytest.mark.asyncio
    async def test_check_whatsapp_disabled(self):
        """При отключённом чекере WhatsApp возвращает None."""
        from lead_validator.services.social_checker import SocialChecker
        
        checker = SocialChecker()
        checker.enabled = False
        
        result = await checker.check_whatsapp("+79991234567")
        assert result is None

    @pytest.mark.asyncio
    async def test_check_vk_disabled(self):
        """При отключённом чекере VK возвращает None."""
        from lead_validator.services.social_checker import SocialChecker
        
        checker = SocialChecker()
        checker.enabled = False
        
        result = await checker.check_vk("+79991234567")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
