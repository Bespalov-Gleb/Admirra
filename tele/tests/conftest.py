"""
Pytest конфигурация для тестов Lead Validator.
Содержит фикстуры и общие настройки.
"""

import pytest
import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def event_loop():
    """Создаём event loop для async тестов."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def valid_phone():
    """Валидный российский мобильный номер."""
    return "+79991234567"


@pytest.fixture
def invalid_phones():
    """Список невалидных телефонов для тестирования."""
    return [
        "",                # Пустой
        "123",             # Слишком короткий
        "abc",             # Буквы
        "1234567890123456",  # Слишком длинный
        "+0000000000",     # Нули
    ]


@pytest.fixture
def valid_lead_data():
    """Валидные данные лида для тестов."""
    import time
    return {
        "phone": "+79991234567",
        "email": "test@example.com",
        "name": "Тест Тестов",
        "timestamp": int(time.time()) - 10  # 10 секунд назад
    }


@pytest.fixture
def bot_lead_data():
    """Данные лида, которые выглядят как бот."""
    return {
        "phone": "+79991234567",
        "honeypot": "bot_filled_this",  # Honeypot заполнен
        "timestamp": 0  # Нереалистичный timestamp
    }


@pytest.fixture
def utm_data_valid():
    """Валидные UTM-метки."""
    return {
        "utm_source": "yandex",
        "utm_medium": "cpc",
        "utm_campaign": "test_campaign",
        "utm_content": "ad_1",
        "utm_term": "keyword"
    }


@pytest.fixture
def utm_data_suspicious():
    """Подозрительные UTM-метки."""
    return {
        "utm_source": "yandex",
        "utm_medium": "cpc",
        "utm_campaign": "test",
        "utm_content": "blacklisted_placement"  # Потенциально в чёрном списке
    }
