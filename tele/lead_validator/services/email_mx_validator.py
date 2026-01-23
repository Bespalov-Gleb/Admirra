"""
Проверка MX-записей email домена и валидация timezone браузера.

Уровень 2 и 7 по ТЗ:
- MX-записи: проверка существования почтового сервера
- Timezone: сравнение часового пояса браузера с ожидаемым для IP
"""

import logging
import dns.resolver
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger("lead_validator.email_mx")


# Маппинг часовых поясов на регионы России
TIMEZONE_TO_REGION = {
    "Europe/Moscow": "RU",
    "Europe/Kaliningrad": "RU",
    "Europe/Samara": "RU",
    "Europe/Volgograd": "RU",
    "Asia/Yekaterinburg": "RU",
    "Asia/Omsk": "RU",
    "Asia/Novosibirsk": "RU",
    "Asia/Krasnoyarsk": "RU",
    "Asia/Irkutsk": "RU",
    "Asia/Yakutsk": "RU",
    "Asia/Vladivostok": "RU",
    "Asia/Magadan": "RU",
    "Asia/Kamchatka": "RU",
    "Asia/Sakhalin": "RU",
}

# Часовые пояса Москвы и близких регионов
MOSCOW_TIMEZONES = {"Europe/Moscow", "Europe/Volgograd", "Europe/Samara"}


@dataclass
class MXCheckResult:
    """Результат проверки MX-записей."""
    has_mx: bool
    mx_records: list
    error: Optional[str] = None


@dataclass
class TimezoneCheckResult:
    """Результат проверки timezone."""
    is_valid: bool
    is_suspicious: bool = False
    warning: Optional[str] = None
    browser_tz: Optional[str] = None
    expected_country: Optional[str] = None


class EmailMXValidator:
    """
    Проверка MX-записей email домена.
    
    Если у домена нет MX-записей — почтового сервера не существует,
    значит email невалидный.
    """
    
    def __init__(self):
        self.timeout = 5.0  # секунд на DNS запрос
        self.cache = {}  # Простой кэш для повторных запросов
        
    def check_mx(self, email: str) -> MXCheckResult:
        """
        Проверить наличие MX-записей для домена email.
        
        Args:
            email: Email адрес
            
        Returns:
            MXCheckResult
        """
        if not email or "@" not in email:
            return MXCheckResult(
                has_mx=False,
                mx_records=[],
                error="invalid_email_format"
            )
        
        domain = email.split("@")[-1].lower().strip()
        
        # Проверяем кэш
        if domain in self.cache:
            return self.cache[domain]
        
        try:
            # Запрашиваем MX-записи
            resolver = dns.resolver.Resolver()
            resolver.timeout = self.timeout
            resolver.lifetime = self.timeout
            
            mx_records = resolver.resolve(domain, 'MX')
            records = [str(r.exchange).rstrip('.') for r in mx_records]
            
            result = MXCheckResult(
                has_mx=len(records) > 0,
                mx_records=records
            )
            
            logger.info(f"MX records for {domain}: {records[:3]}")
            
        except dns.resolver.NXDOMAIN:
            logger.info(f"Domain not found: {domain}")
            result = MXCheckResult(
                has_mx=False,
                mx_records=[],
                error="domain_not_found"
            )
            
        except dns.resolver.NoAnswer:
            logger.info(f"No MX records for: {domain}")
            result = MXCheckResult(
                has_mx=False,
                mx_records=[],
                error="no_mx_records"
            )
            
        except dns.resolver.Timeout:
            logger.warning(f"DNS timeout for: {domain}")
            result = MXCheckResult(
                has_mx=True,  # Fail-open: при timeout пропускаем
                mx_records=[],
                error="dns_timeout"
            )
            
        except Exception as e:
            logger.error(f"MX check error for {domain}: {e}")
            result = MXCheckResult(
                has_mx=True,  # Fail-open
                mx_records=[],
                error=str(e)
            )
        
        # Кэшируем результат
        self.cache[domain] = result
        return result
    
    def has_valid_mx(self, email: str) -> bool:
        """
        Быстрая проверка: есть ли у email валидные MX-записи.
        
        Returns:
            True если MX есть или при ошибке (fail-open)
        """
        result = self.check_mx(email)
        return result.has_mx


class TimezoneValidator:
    """
    Проверка соответствия timezone браузера и IP.
    
    Если IP московский, а timezone показывает Токио — подозрительно.
    """
    
    def validate(
        self,
        browser_timezone: Optional[str],
        ip_country: Optional[str] = None,
        ip_city: Optional[str] = None
    ) -> TimezoneCheckResult:
        """
        Проверить timezone браузера.
        
        Args:
            browser_timezone: Timezone браузера (Intl.DateTimeFormat)
            ip_country: Страна по IP (например "RU", "US")
            ip_city: Город по IP (опционально)
            
        Returns:
            TimezoneCheckResult
        """
        if not browser_timezone:
            return TimezoneCheckResult(
                is_valid=True,  # Пропускаем если не передан
                warning="timezone_not_provided"
            )
        
        # Определяем ожидаемый регион по timezone
        expected_country = TIMEZONE_TO_REGION.get(browser_timezone)
        
        result = TimezoneCheckResult(
            is_valid=True,
            browser_tz=browser_timezone,
            expected_country=expected_country
        )
        
        # Если IP-страна известна — сравниваем
        if ip_country and expected_country:
            if ip_country != expected_country:
                result.is_suspicious = True
                result.warning = f"timezone_mismatch:{browser_timezone}_vs_{ip_country}"
                logger.warning(
                    f"Timezone mismatch: browser={browser_timezone}, "
                    f"expected={expected_country}, ip_country={ip_country}"
                )
        
        # Если timezone не российский, но IP российский — подозрительно
        if ip_country == "RU" and browser_timezone not in TIMEZONE_TO_REGION:
            result.is_suspicious = True
            result.warning = f"non_russian_timezone:{browser_timezone}"
            logger.warning(f"Non-Russian timezone from Russian IP: {browser_timezone}")
        
        # Если timezone азиатский/американский, но IP московский
        if ip_city and "Moscow" in ip_city:
            if browser_timezone not in MOSCOW_TIMEZONES:
                if browser_timezone.startswith("Asia/") and browser_timezone not in TIMEZONE_TO_REGION:
                    result.is_suspicious = True
                    result.warning = f"suspicious_timezone_for_moscow:{browser_timezone}"
        
        return result
    
    def is_timezone_russian(self, timezone: str) -> bool:
        """Проверить, является ли timezone российским."""
        return timezone in TIMEZONE_TO_REGION


# Глобальные экземпляры
email_mx_validator = EmailMXValidator()
timezone_validator = TimezoneValidator()
