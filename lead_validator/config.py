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
    DADATA_CACHE_TTL_SEC: int = 86400
    DADATA_RETRY_ATTEMPTS: int = 2
    DADATA_RETRY_BACKOFF_SEC: float = 0.5
    
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
    
    # CAPTCHA провайдеры (по приоритету)
    # 1. Cloudflare Turnstile (рекомендуется, бесплатно)
    TURNSTILE_SITE_KEY: Optional[str] = None  # Для фронтенда
    TURNSTILE_SECRET_KEY: Optional[str] = None  # Для бэкенда
    
    # 2. Google reCAPTCHA v2/v3
    RECAPTCHA_SITE_KEY: Optional[str] = None  # Для фронтенда
    RECAPTCHA_SECRET_KEY: Optional[str] = None  # Для бэкенда
    RECAPTCHA_MIN_SCORE: float = 0.5  # Минимальный score для v3 (0.0-1.0)
    
    # 3. Yandex SmartCaptcha (запасной вариант)
    SMARTCAPTCHA_CLIENT_KEY: Optional[str] = None  # Для фронтенда
    SMARTCAPTCHA_SERVER_KEY: Optional[str] = None  # Для бэкенда
    
    # Отключить проверку CAPTCHA (true/false). Если false — капча не проверяется
    CAPTCHA_ENABLED: bool = True
    
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
    # ВАЖНО: users.search требует пользовательский OAuth-токен! Сервисный ключ (service token)
    # выдаёт ошибку 1051. Получить токен: OAuth Implicit Flow, scope=offline
    VK_API_TOKEN: str = ""  # User OAuth token (ключ доступа пользователя), не сервисный
    
    # GetContact API (платно, коммерческий)
    GETCONTACT_API_KEY: str = ""
    GETCONTACT_API_URL: str = ""
    
    # GetContact неофициальное (имя по телефону для VK). Токен и AES из приложения.
    GETCONTACT_UNOFFICIAL_TOKEN: str = ""
    GETCONTACT_UNOFFICIAL_AES_KEY: str = ""
    
    # NumBuster API (платно)
    NUMBUSTER_API_KEY: str = ""
    NUMBUSTER_API_URL: str = ""
    
    # InfoTrackPeople API (единый чек по телефону -> Telegram/VK, через socials[])
    INFOTRACKPEOPLE_API_KEY: str = ""
    # По докам: POST /public-api/data/search, auth через x-api-key
    INFOTRACKPEOPLE_API_URL: str = "https://datatech.work/public-api/data/search"
    # Логировать сырой ответ ITP (осторожно: может содержать персональные данные)
    INFOTRACKPEOPLE_LOG_RAW: bool = False

    # Telegram проверка через Telethon (api_id, api_hash, путь к .session)
    TELEGRAM_CHECKER_API_ID: str = ""
    TELEGRAM_CHECKER_API_HASH: str = ""
    TELEGRAM_CHECKER_SESSION: str = ""
    
    # Спам-номера (Уровень 5)
    SPRAVPORTAL_API_KEY: str = ""  # SpravPortal WhoCalls API
    KASPERSKY_API_KEY: str = ""  # Kaspersky Who Calls API
    CALLFILTER_API_KEY: str = ""  # Callfilter API (free tier)
    
    # Bitrix24 CRM (Уровень 3)
    BITRIX24_WEBHOOK_URL: str = ""  # Webhook URL для доступа к API

    # Госуслуги (внешний провайдер)
    GOSUSLUGI_API_URL: str = ""
    GOSUSLUGI_API_KEY: str = ""
    GOSUSLUGI_TIMEOUT: float = 5.0

    # Email уведомления
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_USE_TLS: bool = True
    
    # Автоматические оповещения (Уровень 8)
    ALERT_THRESHOLD_PERCENT: float = 50.0  # Порог для алерта (% мусора)
    ALERT_LOOKBACK_DAYS: int = 7  # Период анализа (дней)
    ALERT_MIN_LEADS: int = 5  # Минимальное кол-во заявок для алерта
    
    # Динамический чёрный список площадок (Уровень 8)
    PLACEMENT_BLACKLIST_THRESHOLD: float = 70.0  # Порог для добавления в чёрный список (% мусора)
    PLACEMENT_BLACKLIST_MIN_LEADS: int = 10  # Минимальное кол-во заявок
    PLACEMENT_BLACKLIST_TTL_DAYS: int = 21  # Время жизни в чёрном списке (дней)

    # Lead scoring: веса сигналов и пороги tier
    LEAD_SCORE_WEIGHT_MOBILE: int = 20
    LEAD_SCORE_WEIGHT_DADATA_QC_GOOD: int = 15
    LEAD_SCORE_WEIGHT_TELEGRAM: int = 20
    LEAD_SCORE_WEIGHT_WHATSAPP: int = 15
    LEAD_SCORE_WEIGHT_VK: int = 15
    LEAD_SCORE_WEIGHT_VIBER: int = 10
    LEAD_SCORE_WEIGHT_TIKTOK: int = 10
    LEAD_SCORE_WEIGHT_GOSUSLUGI: int = 25
    LEAD_SCORE_WEIGHT_NAME_MATCH_GOSUSLUGI: int = 10
    LEAD_SCORE_TIER_HIGH_MIN: int = 70
    LEAD_SCORE_TIER_MEDIUM_MIN: int = 40

    # Lead scoring: веса сигналов и пороги tier
    LEAD_SCORE_WEIGHT_MOBILE: int = 20
    LEAD_SCORE_WEIGHT_DADATA_QC_GOOD: int = 15
    LEAD_SCORE_WEIGHT_TELEGRAM: int = 20
    LEAD_SCORE_WEIGHT_WHATSAPP: int = 15
    LEAD_SCORE_WEIGHT_VK: int = 15
    LEAD_SCORE_WEIGHT_VIBER: int = 10
    LEAD_SCORE_WEIGHT_TIKTOK: int = 10
    LEAD_SCORE_WEIGHT_GOSUSLUGI: int = 25
    LEAD_SCORE_WEIGHT_NAME_MATCH_GOSUSLUGI: int = 10
    LEAD_SCORE_TIER_HIGH_MIN: int = 70
    LEAD_SCORE_TIER_MEDIUM_MIN: int = 40
    
    def __post_init__(self):
        """Загрузка значений из переменных окружения."""
        # DaData
        self.DADATA_API_KEY = _get_env("DADATA_API_KEY")
        self.DADATA_SECRET_KEY = _get_env("DADATA_SECRET_KEY")
        self.DADATA_TIMEOUT = _get_env_float("DADATA_TIMEOUT", 5.0)
        self.DADATA_CACHE_TTL_SEC = _get_env_int("DADATA_CACHE_TTL_SEC", 86400)
        self.DADATA_RETRY_ATTEMPTS = _get_env_int("DADATA_RETRY_ATTEMPTS", 2)
        self.DADATA_RETRY_BACKOFF_SEC = _get_env_float("DADATA_RETRY_BACKOFF_SEC", 0.5)
        
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
        # CAPTCHA
        self.TURNSTILE_SITE_KEY = _get_env("TURNSTILE_SITE_KEY") or None
        self.TURNSTILE_SECRET_KEY = _get_env("TURNSTILE_SECRET_KEY") or None
        self.RECAPTCHA_SITE_KEY = _get_env("RECAPTCHA_SITE_KEY") or None
        self.RECAPTCHA_SECRET_KEY = _get_env("RECAPTCHA_SECRET_KEY") or None
        self.RECAPTCHA_MIN_SCORE = _get_env_float("RECAPTCHA_MIN_SCORE", 0.5)
        self.SMARTCAPTCHA_CLIENT_KEY = _get_env("SMARTCAPTCHA_CLIENT_KEY") or None
        self.SMARTCAPTCHA_SERVER_KEY = _get_env("SMARTCAPTCHA_SERVER_KEY") or None
        self.CAPTCHA_ENABLED = _get_env_bool("CAPTCHA_ENABLED", True)
        
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
        self.GETCONTACT_API_URL = _get_env("GETCONTACT_API_URL", "")
        self.GETCONTACT_UNOFFICIAL_TOKEN = _get_env("GETCONTACT_UNOFFICIAL_TOKEN", "")
        self.GETCONTACT_UNOFFICIAL_AES_KEY = _get_env("GETCONTACT_UNOFFICIAL_AES_KEY", "")
        self.NUMBUSTER_API_KEY = _get_env("NUMBUSTER_API_KEY", "")
        self.NUMBUSTER_API_URL = _get_env("NUMBUSTER_API_URL", "")
        self.INFOTRACKPEOPLE_API_KEY = _get_env("INFOTRACKPEOPLE_API_KEY", "")
        self.INFOTRACKPEOPLE_API_URL = _get_env(
            "INFOTRACKPEOPLE_API_URL",
            "https://datatech.work/public-api/data/search",
        )
        self.INFOTRACKPEOPLE_LOG_RAW = _get_env_bool("INFOTRACKPEOPLE_LOG_RAW", False)
        self.TELEGRAM_CHECKER_API_ID = _get_env("TELEGRAM_CHECKER_API_ID", "")
        self.TELEGRAM_CHECKER_API_HASH = _get_env("TELEGRAM_CHECKER_API_HASH", "")
        self.TELEGRAM_CHECKER_SESSION = _get_env("TELEGRAM_CHECKER_SESSION", "")
        
        # Спам-номера
        self.SPRAVPORTAL_API_KEY = _get_env("SPRAVPORTAL_API_KEY", "")
        self.KASPERSKY_API_KEY = _get_env("KASPERSKY_API_KEY", "")
        self.CALLFILTER_API_KEY = _get_env("CALLFILTER_API_KEY", "")
        
        # Bitrix24 CRM
        self.BITRIX24_WEBHOOK_URL = _get_env("BITRIX24_WEBHOOK_URL", "")

        # Госуслуги
        self.GOSUSLUGI_API_URL = _get_env("GOSUSLUGI_API_URL", "")
        self.GOSUSLUGI_API_KEY = _get_env("GOSUSLUGI_API_KEY", "")
        self.GOSUSLUGI_TIMEOUT = _get_env_float("GOSUSLUGI_TIMEOUT", 5.0)

        # Email
        self.SMTP_HOST = _get_env("SMTP_HOST", "")
        self.SMTP_PORT = _get_env_int("SMTP_PORT", 587)
        self.SMTP_USER = _get_env("SMTP_USER", "")
        self.SMTP_PASSWORD = _get_env("SMTP_PASSWORD", "")
        self.SMTP_FROM = _get_env("SMTP_FROM", "")
        self.SMTP_USE_TLS = _get_env_bool("SMTP_USE_TLS", True)
        
        # Автоматические оповещения
        self.ALERT_THRESHOLD_PERCENT = _get_env_float("ALERT_THRESHOLD_PERCENT", 50.0)
        self.ALERT_LOOKBACK_DAYS = _get_env_int("ALERT_LOOKBACK_DAYS", 7)
        self.ALERT_MIN_LEADS = _get_env_int("ALERT_MIN_LEADS", 5)
        
        # Динамический чёрный список площадок
        self.PLACEMENT_BLACKLIST_THRESHOLD = _get_env_float("PLACEMENT_BLACKLIST_THRESHOLD", 70.0)
        self.PLACEMENT_BLACKLIST_MIN_LEADS = _get_env_int("PLACEMENT_BLACKLIST_MIN_LEADS", 10)
        self.PLACEMENT_BLACKLIST_TTL_DAYS = _get_env_int("PLACEMENT_BLACKLIST_TTL_DAYS", 21)

        # Lead scoring
        self.LEAD_SCORE_WEIGHT_MOBILE = _get_env_int("LEAD_SCORE_WEIGHT_MOBILE", 20)
        self.LEAD_SCORE_WEIGHT_DADATA_QC_GOOD = _get_env_int("LEAD_SCORE_WEIGHT_DADATA_QC_GOOD", 15)
        self.LEAD_SCORE_WEIGHT_TELEGRAM = _get_env_int("LEAD_SCORE_WEIGHT_TELEGRAM", 20)
        self.LEAD_SCORE_WEIGHT_WHATSAPP = _get_env_int("LEAD_SCORE_WEIGHT_WHATSAPP", 15)
        self.LEAD_SCORE_WEIGHT_VK = _get_env_int("LEAD_SCORE_WEIGHT_VK", 15)
        self.LEAD_SCORE_WEIGHT_VIBER = _get_env_int("LEAD_SCORE_WEIGHT_VIBER", 10)
        self.LEAD_SCORE_WEIGHT_TIKTOK = _get_env_int("LEAD_SCORE_WEIGHT_TIKTOK", 10)
        self.LEAD_SCORE_WEIGHT_GOSUSLUGI = _get_env_int("LEAD_SCORE_WEIGHT_GOSUSLUGI", 25)
        self.LEAD_SCORE_WEIGHT_NAME_MATCH_GOSUSLUGI = _get_env_int("LEAD_SCORE_WEIGHT_NAME_MATCH_GOSUSLUGI", 10)
        self.LEAD_SCORE_TIER_HIGH_MIN = _get_env_int("LEAD_SCORE_TIER_HIGH_MIN", 70)
        self.LEAD_SCORE_TIER_MEDIUM_MIN = _get_env_int("LEAD_SCORE_TIER_MEDIUM_MIN", 40)

        # Lead scoring
        self.LEAD_SCORE_WEIGHT_MOBILE = _get_env_int("LEAD_SCORE_WEIGHT_MOBILE", 20)
        self.LEAD_SCORE_WEIGHT_DADATA_QC_GOOD = _get_env_int("LEAD_SCORE_WEIGHT_DADATA_QC_GOOD", 15)
        self.LEAD_SCORE_WEIGHT_TELEGRAM = _get_env_int("LEAD_SCORE_WEIGHT_TELEGRAM", 20)
        self.LEAD_SCORE_WEIGHT_WHATSAPP = _get_env_int("LEAD_SCORE_WEIGHT_WHATSAPP", 15)
        self.LEAD_SCORE_WEIGHT_VK = _get_env_int("LEAD_SCORE_WEIGHT_VK", 15)
        self.LEAD_SCORE_WEIGHT_VIBER = _get_env_int("LEAD_SCORE_WEIGHT_VIBER", 10)
        self.LEAD_SCORE_WEIGHT_TIKTOK = _get_env_int("LEAD_SCORE_WEIGHT_TIKTOK", 10)
        self.LEAD_SCORE_WEIGHT_GOSUSLUGI = _get_env_int("LEAD_SCORE_WEIGHT_GOSUSLUGI", 25)
        self.LEAD_SCORE_WEIGHT_NAME_MATCH_GOSUSLUGI = _get_env_int("LEAD_SCORE_WEIGHT_NAME_MATCH_GOSUSLUGI", 10)
        self.LEAD_SCORE_TIER_HIGH_MIN = _get_env_int("LEAD_SCORE_TIER_HIGH_MIN", 70)
        self.LEAD_SCORE_TIER_MEDIUM_MIN = _get_env_int("LEAD_SCORE_TIER_MEDIUM_MIN", 40)


# Глобальный экземпляр настроек
settings = LeadValidatorSettings()

