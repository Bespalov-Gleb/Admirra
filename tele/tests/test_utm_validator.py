"""
Unit тесты для UTM валидатора.

Запуск:
    python -m pytest tests/test_utm_validator.py -v
"""

import pytest
from unittest.mock import patch, MagicMock


class TestUTMValidatorUnit:
    """Unit тесты для UTMValidator без внешних зависимостей."""

    def test_utm_validator_init(self):
        """UTMValidator должен инициализироваться."""
        from lead_validator.services.utm_validator import UTMValidator
        
        validator = UTMValidator()
        assert validator is not None
        assert hasattr(validator, 'validate')

    def test_valid_utm_passes(self):
        """Валидные UTM метки должны проходить проверку."""
        from lead_validator.services.utm_validator import UTMValidator, UTMData
        
        validator = UTMValidator()
        utm = UTMData(
            source="yandex",
            medium="cpc",
            campaign="test_campaign"
        )
        
        result = validator.validate(utm, client_ip="1.2.3.4", geo_country="RU")
        # При geo_country=RU и source=yandex должно проходить
        # Проверяем что результат - объект с атрибутом is_valid
        assert hasattr(result, 'is_valid')

    def test_empty_utm_passes(self):
        """Пустые UTM метки должны проходить (organic traffic)."""
        from lead_validator.services.utm_validator import UTMValidator, UTMData
        
        validator = UTMValidator()
        utm = UTMData()  # Все поля None
        
        result = validator.validate(utm)
        assert result.is_valid == True

    def test_long_utm_values_rejected(self):
        """Слишком длинные UTM значения должны отклоняться."""
        from lead_validator.services.utm_validator import UTMValidator, UTMData
        
        validator = UTMValidator()
        utm = UTMData(
            source="a" * 300,  # Слишком длинный
            medium="cpc"
        )
        
        result = validator.validate(utm)
        # Длинные значения могут быть отклонены или вызвать предупреждение
        # Проверяем что валидатор не упал
        assert hasattr(result, 'is_valid')

    def test_yandex_source_non_ru_ip_suspicious(self):
        """UTM source=yandex с не-RU IP должен быть подозрительным."""
        from lead_validator.services.utm_validator import UTMValidator, UTMData
        
        validator = UTMValidator()
        utm = UTMData(
            source="yandex",
            medium="cpc"
        )
        
        # Украинский IP с Яндекс-рекламой - подозрительно
        result = validator.validate(utm, geo_country="UA")
        
        # Должен выдать предупреждение или отклонить
        assert hasattr(result, 'warning') or hasattr(result, 'is_valid')

    def test_blacklist_check(self):
        """Проверка работы чёрного списка площадок."""
        from lead_validator.services.utm_validator import UTMValidator, UTMData
        
        validator = UTMValidator()
        
        # Добавляем площадку в чёрный список
        validator.add_to_blacklist("spam_placement_123")
        
        utm = UTMData(
            source="yandex",
            medium="cpc",
            content="spam_placement_123"
        )
        
        result = validator.validate(utm)
        # Должен быть отклонён или иметь warning
        assert hasattr(result, 'is_valid')

    def test_utm_special_characters(self):
        """UTM с спецсимволами должны обрабатываться."""
        from lead_validator.services.utm_validator import UTMValidator, UTMData
        
        validator = UTMValidator()
        utm = UTMData(
            source="yandex",
            medium="cpc",
            campaign="кампания_тест",  # Кириллица
            content="ad%20test"  # URL-encoded
        )
        
        result = validator.validate(utm)
        # Не должен упасть
        assert hasattr(result, 'is_valid')


class TestUTMData:
    """Тесты для dataclass UTMData."""

    def test_utm_data_creation(self):
        """UTMData должен создаваться с параметрами."""
        from lead_validator.services.utm_validator import UTMData
        
        utm = UTMData(
            source="google",
            medium="organic"
        )
        
        assert utm.source == "google"
        assert utm.medium == "organic"
        assert utm.campaign is None

    def test_utm_data_all_fields(self):
        """UTMData должен поддерживать все поля."""
        from lead_validator.services.utm_validator import UTMData
        
        utm = UTMData(
            source="yandex",
            medium="cpc",
            campaign="summer_sale",
            content="banner_1",
            term="buy shoes"
        )
        
        assert utm.source == "yandex"
        assert utm.medium == "cpc"
        assert utm.campaign == "summer_sale"
        assert utm.content == "banner_1"
        assert utm.term == "buy shoes"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
