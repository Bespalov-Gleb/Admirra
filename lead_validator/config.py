"""
Конфигурация Lead Validator.
Все секреты загружаются из переменных окружения.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List
from dotenv import load_dotenv

# Загружаем .env файл
load_dotenv()


def _get_env(key: str, default: str = "") -> str:
    """Получить переменную окружения с fallback на default."""
    return os.getenv(key, default)


def _get_env_bool(key: str, default: bool = False) -> bool:
    """Получить boolean переменную окружения."""
    return os.getenv(key, str(default)).lower() in ("true", "1", "yes")


def _get_env_int(key: str, default: int = 0) -> int:
    """Получить int переменную окружения."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def _get_env_float(key: str, default: float = 0.0) -> float:
    """Получить float переменную окружения."""
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


@dataclass
class LeadValidatorSettings:
    """
    Настройки модуля валидации лидов.
    Все значения загружаются из переменных окружения.
    """
    
    # DaData API для валидации телефонов и email
    DADATA_API_KEY: str = ""
    DADATA_SECRET_KEY: str = ""
    DADATA_TIMEOUT: float = 5.0
    
    # Redis для дедупликации и rate limiting
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_ENABLED: bool = False
    
    # Telegram бот для уведомлений
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_ENABLED: bool = False
    
    # Airtable для логирования
    AIRTABLE_API_KEY: Optional[str] = None
    AIRTABLE_BASE_ID: Optional[str] = None
    AIRTABLE_TABLE_NAME: str = "rejected_leads"
    
    # CAPTCHA (Yandex SmartCaptcha)
    SMARTCAPTCHA_CLIENT_KEY: Optional[str] = None
    SMARTCAPTCHA_SERVER_KEY: Optional[str] = None
    SMARTCAPTCHA_ENABLED: bool = False
    
    # Антибот настройки
    MIN_FORM_FILL_TIME_SEC: int = 3
    MAX_FORM_FILL_TIME_SEC: int = 3600
    JS_TOKEN_ENABLED: bool = True  # Проверка JavaScript-токена
    
    # Rate Limiting
    RATE_LIMIT_PER_IP: int = 10
    RATE_LIMIT_WINDOW_SEC: int = 3600
    
    # Rate Limiting по телефону (Уровень 3 по ТЗ)
    RATE_LIMIT_PER_PHONE_PER_HOUR: int = 5  # Максимум 5 заявок в час с одного номера
    RATE_LIMIT_PHONE_WINDOW_SEC: int = 3600  # Окно 1 час
    
    # Дедупликация
    PHONE_DUPLICATE_TTL_SEC: int = 86400
    
    # Fail-open режим (пропускать при недоступности внешних сервисов)
    FAIL_OPEN_MODE: bool = True
    
    # Яндекс.Метрика (офлайн-конверсии)
    METRICA_COUNTER_ID: Optional[str] = None
    METRICA_OAUTH_TOKEN: Optional[str] = None
    METRICA_ENABLED: bool = False
    
    # UTM валидация (Уровень 6)
    UTM_VALIDATION_ENABLED: bool = True
    UTM_BLACKLISTED_PLACEMENTS: List[str] = field(default_factory=list)
    
    # MX-запись email (проверка существования почтового сервера)
    MX_CHECK_ENABLED: bool = True
    
    # Проверка соцсетей
    # VK API (бесплатно, но ограниченно)
    VK_API_TOKEN: str = ""  # Service token для VK API (не Ads API)
    
    # GetContact API (платно)
    GETCONTACT_API_KEY: str = ""
    
    # NumBuster API (платно)
    NUMBUSTER_API_KEY: str = ""
    
    # Спам-номера (Уровень 5)
    SPRAVPORTAL_API_KEY: str = ""  # SpravPortal WhoCalls API
    KASPERSKY_API_KEY: str = ""  # Kaspersky Who Calls API
    
    # Bitrix24 CRM (Уровень 3)
    BITRIX24_WEBHOOK_URL: str = ""  # Webhook URL для доступа к API
    
    # Автоматические оповещения (Уровень 8)
    ALERT_THRESHOLD_PERCENT: float = 50.0  # Порог для алерта (% мусора)
    ALERT_LOOKBACK_DAYS: int = 7  # Период анализа (дней)
    ALERT_MIN_LEADS: int = 5  # Минимальное кол-во заявок для алерта
    
    # Динамический чёрный список площадок (Уровень 8)
    PLACEMENT_BLACKLIST_THRESHOLD: float = 70.0  # Порог для добавления в чёрный список (% мусора)
    PLACEMENT_BLACKLIST_MIN_LEADS: int = 10  # Минимальное кол-во заявок
    PLACEMENT_BLACKLIST_TTL_DAYS: int = 21  # Время жизни в чёрном списке (дней)
    
    def __post_init__(self):
        """Загрузка значений из переменных окружения."""
        # DaData
        self.DADATA_API_KEY = _get_env("DADATA_API_KEY")
        self.DADATA_SECRET_KEY = _get_env("DADATA_SECRET_KEY")
        self.DADATA_TIMEOUT = _get_env_float("DADATA_TIMEOUT", 5.0)
        
        # Redis
        self.REDIS_URL = _get_env("REDIS_URL", "redis://localhost:6379")
        self.REDIS_ENABLED = _get_env_bool("REDIS_ENABLED", False)
        
        # Telegram
        self.TELEGRAM_BOT_TOKEN = _get_env("TELEGRAM_BOT_TOKEN")
        self.TELEGRAM_CHAT_ID = _get_env("TELEGRAM_CHAT_ID")
        self.TELEGRAM_ENABLED = _get_env_bool("TELEGRAM_ENABLED", False)
        
        # Airtable
        self.AIRTABLE_API_KEY = _get_env("AIRTABLE_API_KEY") or None
        self.AIRTABLE_BASE_ID = _get_env("AIRTABLE_BASE_ID") or None
        self.AIRTABLE_TABLE_NAME = _get_env("AIRTABLE_TABLE_NAME", "rejected_leads")
        
        # CAPTCHA (Yandex SmartCaptcha)
        self.SMARTCAPTCHA_CLIENT_KEY = _get_env("SMARTCAPTCHA_CLIENT_KEY") or None
        self.SMARTCAPTCHA_SERVER_KEY = _get_env("SMARTCAPTCHA_SERVER_KEY") or None
        self.SMARTCAPTCHA_ENABLED = _get_env_bool("SMARTCAPTCHA_ENABLED", False)
        
        # Антибот
        self.MIN_FORM_FILL_TIME_SEC = _get_env_int("MIN_FORM_FILL_TIME_SEC", 3)
        self.MAX_FORM_FILL_TIME_SEC = _get_env_int("MAX_FORM_FILL_TIME_SEC", 3600)
        self.JS_TOKEN_ENABLED = _get_env_bool("JS_TOKEN_ENABLED", True)
        
        # Rate Limiting
        self.RATE_LIMIT_PER_IP = _get_env_int("RATE_LIMIT_PER_IP", 10)
        self.RATE_LIMIT_WINDOW_SEC = _get_env_int("RATE_LIMIT_WINDOW_SEC", 3600)
        self.RATE_LIMIT_PER_PHONE_PER_HOUR = _get_env_int("RATE_LIMIT_PER_PHONE_PER_HOUR", 5)
        self.RATE_LIMIT_PHONE_WINDOW_SEC = _get_env_int("RATE_LIMIT_PHONE_WINDOW_SEC", 3600)
        
        # Дедупликация
        self.PHONE_DUPLICATE_TTL_SEC = _get_env_int("PHONE_DUPLICATE_TTL_SEC", 86400)
        
        # Fail-open
        self.FAIL_OPEN_MODE = _get_env_bool("FAIL_OPEN_MODE", True)
        
        # Яндекс.Метрика
        self.METRICA_COUNTER_ID = _get_env("METRICA_COUNTER_ID") or None
        self.METRICA_OAUTH_TOKEN = _get_env("METRICA_OAUTH_TOKEN") or None
        self.METRICA_ENABLED = _get_env_bool("METRICA_ENABLED", False)
        
        # UTM валидация
        self.UTM_VALIDATION_ENABLED = _get_env_bool("UTM_VALIDATION_ENABLED", True)
        # Чёрный список площадок (через запятую)
        blacklist_str = _get_env("UTM_BLACKLISTED_PLACEMENTS", "")
        self.UTM_BLACKLISTED_PLACEMENTS = [
            p.strip() for p in blacklist_str.split(",") if p.strip()
        ]
        
        # MX-запись
        self.MX_CHECK_ENABLED = _get_env_bool("MX_CHECK_ENABLED", True)
        
        # Проверка соцсетей
        self.VK_API_TOKEN = _get_env("VK_API_TOKEN", "")
        self.GETCONTACT_API_KEY = _get_env("GETCONTACT_API_KEY", "")
        self.NUMBUSTER_API_KEY = _get_env("NUMBUSTER_API_KEY", "")
        
        # Спам-номера
        self.SPRAVPORTAL_API_KEY = _get_env("SPRAVPORTAL_API_KEY", "")
        self.KASPERSKY_API_KEY = _get_env("KASPERSKY_API_KEY", "")
        
        # Bitrix24 CRM
        self.BITRIX24_WEBHOOK_URL = _get_env("BITRIX24_WEBHOOK_URL", "")
        
        # Автоматические оповещения
        self.ALERT_THRESHOLD_PERCENT = _get_env_float("ALERT_THRESHOLD_PERCENT", 50.0)
        self.ALERT_LOOKBACK_DAYS = _get_env_int("ALERT_LOOKBACK_DAYS", 7)
        self.ALERT_MIN_LEADS = _get_env_int("ALERT_MIN_LEADS", 5)
        
        # Динамический чёрный список площадок
        self.PLACEMENT_BLACKLIST_THRESHOLD = _get_env_float("PLACEMENT_BLACKLIST_THRESHOLD", 70.0)
        self.PLACEMENT_BLACKLIST_MIN_LEADS = _get_env_int("PLACEMENT_BLACKLIST_MIN_LEADS", 10)
        self.PLACEMENT_BLACKLIST_TTL_DAYS = _get_env_int("PLACEMENT_BLACKLIST_TTL_DAYS", 21)


# Глобальный экземпляр настроек
settings = LeadValidatorSettings()

