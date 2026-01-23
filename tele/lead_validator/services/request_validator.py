"""
Проверка User-Agent и Referer для антибот-фильтрации.

Уровень 1 по ТЗ:
- User-Agent: блокировка curl, python-requests, PostmanRuntime
- Referer: проверка откуда пришёл пользователь
"""

import logging
import re
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger("lead_validator.request_validator")


# Подозрительные User-Agent паттерны (боты, скрипты)
SUSPICIOUS_USER_AGENTS = [
    "curl",
    "python-requests",
    "python-urllib",
    "wget",
    "postmanruntime",
    "insomnia",
    "httpie",
    "axios",
    "node-fetch",
    "go-http-client",
    "java/",
    "okhttp",
    "apache-httpclient",
    "libwww-perl",
    "scrapy",
    "bot",
    "crawler",
    "spider",
    "headless",
    "phantomjs",
    "selenium",
    "puppeteer",
    "playwright",
]

# User-Agent которые точно боты (полное совпадение или пустой)
BLOCKED_USER_AGENTS = [
    "",
    "-",
    "Mozilla/5.0",  # Только базовый без деталей - подозрительно
]


@dataclass
class RequestValidationResult:
    """Результат проверки запроса."""
    is_valid: bool
    rejection_reason: Optional[str] = None
    warning: Optional[str] = None
    user_agent_suspicious: bool = False
    referer_suspicious: bool = False


class RequestValidator:
    """
    Проверка HTTP-заголовков запроса на признаки бота.
    
    Проверяет:
    - User-Agent на подозрительные паттерны
    - Referer на соответствие ожидаемым доменам
    """
    
    def __init__(self):
        # Разрешённые домены для referer (можно настроить через env)
        self.allowed_referer_domains: list = []
        self.strict_referer_check = False  # Если True - отклонять при пустом referer
        
    def validate(
        self, 
        user_agent: Optional[str] = None,
        referer: Optional[str] = None,
        expected_domains: Optional[list] = None
    ) -> RequestValidationResult:
        """
        Проверить заголовки запроса.
        
        Args:
            user_agent: Заголовок User-Agent
            referer: Заголовок Referer
            expected_domains: Список разрешённых доменов для referer
            
        Returns:
            RequestValidationResult с результатом проверки
        """
        result = RequestValidationResult(is_valid=True)
        
        # === Проверка User-Agent ===
        ua_check = self._check_user_agent(user_agent)
        if ua_check:
            result.is_valid = False
            result.rejection_reason = ua_check
            result.user_agent_suspicious = True
            return result
        
        # === Проверка Referer ===
        referer_check = self._check_referer(referer, expected_domains)
        if referer_check:
            if self.strict_referer_check:
                result.is_valid = False
                result.rejection_reason = referer_check
            else:
                result.warning = referer_check
            result.referer_suspicious = True
        
        return result
    
    def _check_user_agent(self, user_agent: Optional[str]) -> Optional[str]:
        """
        Проверить User-Agent на подозрительные паттерны.
        
        Returns:
            Причина отклонения или None если OK
        """
        if user_agent is None:
            logger.info("Empty User-Agent detected")
            return "user_agent_empty"
        
        ua_lower = user_agent.lower().strip()
        
        # Пустой или минимальный User-Agent
        if ua_lower in ["", "-", "mozilla/5.0"]:
            logger.info(f"Blocked User-Agent: '{user_agent}'")
            return "user_agent_blocked"
        
        # Проверка на подозрительные паттерны
        for pattern in SUSPICIOUS_USER_AGENTS:
            if pattern in ua_lower:
                logger.info(f"Suspicious User-Agent pattern '{pattern}' in: {user_agent}")
                return f"user_agent_suspicious:{pattern}"
        
        # Слишком короткий User-Agent (обычно > 30 символов у браузеров)
        if len(user_agent) < 20:
            logger.info(f"Too short User-Agent: {user_agent}")
            return "user_agent_too_short"
        
        return None
    
    def _check_referer(
        self, 
        referer: Optional[str],
        expected_domains: Optional[list] = None
    ) -> Optional[str]:
        """
        Проверить Referer на соответствие ожиданиям.
        
        Returns:
            Предупреждение или причина отклонения, None если OK
        """
        # Пустой referer - подозрительно, но не критично
        if not referer:
            logger.debug("Empty Referer header")
            return "referer_empty"
        
        # Извлекаем домен из referer
        domain_match = re.search(r'https?://([^/]+)', referer.lower())
        if not domain_match:
            logger.info(f"Invalid Referer format: {referer}")
            return "referer_invalid_format"
        
        domain = domain_match.group(1)
        
        # Если указаны ожидаемые домены - проверяем
        domains_to_check = expected_domains or self.allowed_referer_domains
        if domains_to_check:
            domain_ok = any(
                allowed in domain 
                for allowed in domains_to_check
            )
            if not domain_ok:
                logger.info(f"Referer domain not in allowed list: {domain}")
                return f"referer_domain_not_allowed:{domain}"
        
        return None
    
    def add_allowed_domain(self, domain: str):
        """Добавить домен в список разрешённых для referer."""
        if domain not in self.allowed_referer_domains:
            self.allowed_referer_domains.append(domain.lower())
            logger.info(f"Added allowed referer domain: {domain}")


# Глобальный экземпляр
request_validator = RequestValidator()
