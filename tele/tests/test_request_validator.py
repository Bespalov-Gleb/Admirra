"""
Unit тесты для валидатора User-Agent и Referer.

Запуск:
    python -m pytest tests/test_request_validator.py -v
"""

import pytest
from unittest.mock import patch


class TestRequestValidatorUnit:
    """Unit тесты для RequestValidator."""

    def test_request_validator_init(self):
        """RequestValidator должен инициализироваться."""
        from lead_validator.services.request_validator import RequestValidator
        
        validator = RequestValidator()
        assert validator is not None
        assert hasattr(validator, 'validate')

    def test_empty_user_agent_rejected(self):
        """Пустой User-Agent должен отклоняться."""
        from lead_validator.services.request_validator import request_validator
        
        result = request_validator.validate(user_agent=None)
        assert result.is_valid == False
        assert "user_agent" in result.rejection_reason

    def test_curl_user_agent_rejected(self):
        """curl User-Agent должен отклоняться."""
        from lead_validator.services.request_validator import request_validator
        
        result = request_validator.validate(user_agent="curl/7.68.0")
        assert result.is_valid == False
        assert "suspicious" in result.rejection_reason

    def test_python_requests_rejected(self):
        """python-requests User-Agent должен отклоняться."""
        from lead_validator.services.request_validator import request_validator
        
        result = request_validator.validate(user_agent="python-requests/2.25.1")
        assert result.is_valid == False
        assert "suspicious" in result.rejection_reason

    def test_postman_rejected(self):
        """Postman User-Agent должен отклоняться."""
        from lead_validator.services.request_validator import request_validator
        
        result = request_validator.validate(user_agent="PostmanRuntime/7.28.4")
        assert result.is_valid == False
        assert "suspicious" in result.rejection_reason

    def test_valid_chrome_user_agent_accepted(self):
        """Нормальный Chrome User-Agent должен приниматься."""
        from lead_validator.services.request_validator import request_validator
        
        chrome_ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        result = request_validator.validate(user_agent=chrome_ua)
        assert result.is_valid == True

    def test_valid_firefox_user_agent_accepted(self):
        """Нормальный Firefox User-Agent должен приниматься."""
        from lead_validator.services.request_validator import request_validator
        
        firefox_ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) "
            "Gecko/20100101 Firefox/89.0"
        )
        result = request_validator.validate(user_agent=firefox_ua)
        assert result.is_valid == True

    def test_short_user_agent_rejected(self):
        """Слишком короткий User-Agent должен отклоняться."""
        from lead_validator.services.request_validator import request_validator
        
        result = request_validator.validate(user_agent="Mozilla/5.0")
        assert result.is_valid == False


class TestRefererValidation:
    """Тесты проверки Referer."""

    def test_empty_referer_warning(self):
        """Пустой Referer должен давать warning, но не отклонять."""
        from lead_validator.services.request_validator import RequestValidator
        
        validator = RequestValidator()
        validator.strict_referer_check = False  # Нестрогий режим
        
        chrome_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0"
        result = validator.validate(user_agent=chrome_ua, referer=None)
        
        # Должен пройти, но с warning
        assert result.is_valid == True
        assert result.referer_suspicious == True

    def test_valid_referer_accepted(self):
        """Валидный Referer должен приниматься."""
        from lead_validator.services.request_validator import RequestValidator
        
        validator = RequestValidator()
        validator.allowed_referer_domains = ["example.com", "mysite.ru"]
        
        chrome_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0"
        result = validator.validate(
            user_agent=chrome_ua, 
            referer="https://mysite.ru/landing-page"
        )
        
        assert result.is_valid == True

    def test_foreign_referer_warning(self):
        """Чужой домен в Referer должен давать warning."""
        from lead_validator.services.request_validator import RequestValidator
        
        validator = RequestValidator()
        validator.allowed_referer_domains = ["example.com"]
        validator.strict_referer_check = False
        
        chrome_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0"
        result = validator.validate(
            user_agent=chrome_ua, 
            referer="https://other-site.com/page"
        )
        
        assert result.referer_suspicious == True


class TestAddAllowedDomain:
    """Тесты добавления разрешённых доменов."""

    def test_add_allowed_domain(self):
        """Добавление домена в список разрешённых."""
        from lead_validator.services.request_validator import RequestValidator
        
        validator = RequestValidator()
        validator.add_allowed_domain("example.com")
        
        assert "example.com" in validator.allowed_referer_domains


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
