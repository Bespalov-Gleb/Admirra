"""
Unit тесты для валидатора качества данных (email, имена).

Запуск:
    python -m pytest tests/test_data_quality.py -v
"""

import pytest


class TestDisposableEmailValidator:
    """Тесты проверки одноразовых email."""

    def test_data_quality_validator_init(self):
        """DataQualityValidator должен инициализироваться."""
        from lead_validator.services.data_quality import DataQualityValidator
        
        validator = DataQualityValidator()
        assert validator is not None
        assert len(validator.disposable_domains) > 50

    def test_mailinator_rejected(self):
        """Mailinator email должен отклоняться."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_email_domain("test@mailinator.com")
        assert result.is_valid == False
        assert "disposable" in result.rejection_reason

    def test_tempmail_rejected(self):
        """Tempmail email должен отклоняться."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_email_domain("user@tempmail.com")
        assert result.is_valid == False

    def test_guerrillamail_rejected(self):
        """Guerrillamail email должен отклоняться."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_email_domain("spam@guerrillamail.com")
        assert result.is_valid == False

    def test_yopmail_rejected(self):
        """Yopmail email должен отклоняться."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_email_domain("temp@yopmail.com")
        assert result.is_valid == False

    def test_10minutemail_rejected(self):
        """10minutemail email должен отклоняться."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_email_domain("throw@10minutemail.com")
        assert result.is_valid == False

    def test_gmail_accepted(self):
        """Gmail email должен приниматься."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_email_domain("user@gmail.com")
        assert result.is_valid == True

    def test_yandex_accepted(self):
        """Yandex email должен приниматься."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_email_domain("user@yandex.ru")
        assert result.is_valid == True

    def test_corporate_email_accepted(self):
        """Корпоративный email должен приниматься."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_email_domain("info@company.ru")
        assert result.is_valid == True

    def test_empty_email_accepted(self):
        """Пустой email должен приниматься (необязательное поле)."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_email_domain(None)
        assert result.is_valid == True


class TestGarbageNameValidator:
    """Тесты проверки мусорных имён."""

    def test_test_name_rejected(self):
        """Имя 'test' должно отклоняться."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_name("test")
        assert result.is_valid == False
        assert "garbage" in result.rejection_reason

    def test_asdf_rejected(self):
        """Имя 'asdf' должно отклоняться."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_name("asdf")
        assert result.is_valid == False

    def test_qwerty_rejected(self):
        """Имя 'qwerty' должно отклоняться."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_name("qwerty")
        assert result.is_valid == False

    def test_тест_rejected(self):
        """Имя 'тест' должно отклоняться."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_name("тест")
        assert result.is_valid == False

    def test_йцукен_rejected(self):
        """Имя 'йцукен' должно отклоняться."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_name("йцукен")
        assert result.is_valid == False

    def test_xxx_rejected(self):
        """Имя 'xxx' должно отклоняться."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_name("xxx")
        assert result.is_valid == False

    def test_aaa_rejected(self):
        """Имя 'aaa' должно отклоняться."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_name("aaa")
        assert result.is_valid == False

    def test_vasya_pupkin_rejected(self):
        """Имя 'Вася Пупкин' должно отклоняться."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_name("вася пупкин")
        assert result.is_valid == False

    def test_normal_name_accepted(self):
        """Нормальное имя должно приниматься."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_name("Александр")
        assert result.is_valid == True

    def test_normal_name_maria_accepted(self):
        """Имя 'Мария' должно приниматься."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_name("Мария")
        assert result.is_valid == True

    def test_name_with_double_letters_accepted(self):
        """Имя 'Анна' с двойными буквами должно приниматься."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_name("Анна")
        assert result.is_valid == True

    def test_short_name_rejected(self):
        """Слишком короткое имя должно отклоняться."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_name("А")
        assert result.is_valid == False
        assert "short" in result.rejection_reason

    def test_empty_name_accepted(self):
        """Пустое имя должно приниматься (может быть необязательным)."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_name(None)
        assert result.is_valid == True

    def test_repeating_chars_rejected(self):
        """Имена с повторяющимися символами ааааа должны отклоняться."""
        from lead_validator.services.data_quality import data_quality_validator
        
        result = data_quality_validator.validate_name("ааааа")
        assert result.is_valid == False


class TestAddToLists:
    """Тесты добавления в списки."""

    def test_add_disposable_domain(self):
        """Добавление домена в чёрный список."""
        from lead_validator.services.data_quality import DataQualityValidator
        
        validator = DataQualityValidator()
        validator.add_disposable_domain("badmail.test")
        
        assert "badmail.test" in validator.disposable_domains

    def test_add_garbage_name(self):
        """Добавление имени в стоп-лист."""
        from lead_validator.services.data_quality import DataQualityValidator
        
        validator = DataQualityValidator()
        validator.add_garbage_name("badname")
        
        assert "badname" in validator.garbage_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
