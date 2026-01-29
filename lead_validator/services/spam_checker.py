"""
Проверка телефонов на спам-номера (Уровень 5 по ТЗ).

Поддерживает:
- Внешние API (SpravPortal WhoCalls, Kaspersky Who Calls)
- Собственный чёрный список (Redis)
- Белый список (номера из CRM как действующие клиенты)
"""

import logging
import httpx
from typing import Optional, Dict, Any
from dataclasses import dataclass
from lead_validator.config import settings
from lead_validator.services.redis_service import redis_service

logger = logging.getLogger("lead_validator.spam_checker")


@dataclass
class SpamCheckResult:
    """Результат проверки на спам."""
    is_spam: bool = False
    is_whitelisted: bool = False
    category: Optional[str] = None  # spam, fraud, advertising, normal
    source: Optional[str] = None  # spravportal, kaspersky, blacklist, whitelist
    reason: Optional[str] = None


class SpamChecker:
    """
    Проверка телефонов на спам через внешние API и локальные списки.
    
    Порядок проверки:
    1. Белый список (если номер в белом списке - пропускаем)
    2. Чёрный список (если номер в чёрном списке - отклоняем)
    3. Внешние API (SpravPortal, Kaspersky)
    """
    
    def __init__(self):
        self.spravportal_enabled = bool(settings.SPRAVPORTAL_API_KEY)
        self.kaspersky_enabled = bool(settings.KASPERSKY_API_KEY)
        
    async def check_phone(self, phone: str) -> SpamCheckResult:
        """
        Проверить телефон на спам.
        
        Args:
            phone: Номер телефона
            
        Returns:
            SpamCheckResult с результатом проверки
        """
        result = SpamCheckResult()
        
        # 1. Проверка белого списка
        is_whitelisted = await self._check_whitelist(phone)
        if is_whitelisted:
            result.is_whitelisted = True
            result.source = "whitelist"
            logger.debug(f"Phone {phone[:10]}... is whitelisted")
            return result
        
        # 2. Проверка чёрного списка
        is_blacklisted = await self._check_blacklist(phone)
        if is_blacklisted:
            result.is_spam = True
            result.category = "spam"
            result.source = "blacklist"
            result.reason = "phone_in_blacklist"
            logger.info(f"Phone {phone[:10]}... is in blacklist")
            return result
        
        # 3. Проверка через внешние API (если включены)
        if self.spravportal_enabled:
            try:
                spravportal_result = await self._check_spravportal(phone)
                if spravportal_result.is_spam:
                    result.is_spam = True
                    result.category = spravportal_result.category
                    result.source = "spravportal"
                    result.reason = spravportal_result.reason
                    logger.info(f"SpravPortal marked {phone[:10]}... as {spravportal_result.category}")
                    return result
            except Exception as e:
                logger.warning(f"SpravPortal check failed for {phone[:10]}...: {e}")
        
        if self.kaspersky_enabled:
            try:
                kaspersky_result = await self._check_kaspersky(phone)
                if kaspersky_result.is_spam:
                    result.is_spam = True
                    result.category = kaspersky_result.category
                    result.source = "kaspersky"
                    result.reason = kaspersky_result.reason
                    logger.info(f"Kaspersky marked {phone[:10]}... as {kaspersky_result.category}")
                    return result
            except Exception as e:
                logger.warning(f"Kaspersky check failed for {phone[:10]}...: {e}")
        
        # Номер не является спамом
        return result
    
    async def _check_whitelist(self, phone: str) -> bool:
        """
        Проверить номер в белом списке.
        
        Белый список хранится в Redis с ключом: whitelist:phone:{hash}
        """
        client = await redis_service._get_client()
        if client is None:
            return False
        
        try:
            phone_hash = redis_service.hash_phone(phone)
            key = f"whitelist:phone:{phone_hash}"
            exists = await client.exists(key)
            return bool(exists)
        except Exception as e:
            logger.error(f"Redis whitelist check error: {e}")
            return False
    
    async def _check_blacklist(self, phone: str) -> bool:
        """
        Проверить номер в чёрном списке.
        
        Чёрный список хранится в Redis с ключом: blacklist:phone:{hash}
        """
        client = await redis_service._get_client()
        if client is None:
            return False
        
        try:
            phone_hash = redis_service.hash_phone(phone)
            key = f"blacklist:phone:{phone_hash}"
            exists = await client.exists(key)
            return bool(exists)
        except Exception as e:
            logger.error(f"Redis blacklist check error: {e}")
            return False
    
    async def _check_spravportal(self, phone: str) -> SpamCheckResult:
        """
        Проверка через SpravPortal WhoCalls API.
        
        Документация: https://spravportal.ru/api/who-calls
        """
        result = SpamCheckResult()
        
        try:
            # Нормализуем телефон (только цифры)
            digits_only = "".join(filter(str.isdigit, phone))
            if not digits_only or len(digits_only) < 10:
                return result
            
            url = "https://api.spravportal.ru/who-calls/check"
            headers = {
                "Authorization": f"Bearer {settings.SPRAVPORTAL_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {"phone": digits_only}
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    category = data.get("category", "").lower()
                    
                    # Категории: spam, fraud, advertising, normal
                    if category in ("spam", "fraud", "advertising"):
                        result.is_spam = True
                        result.category = category
                        result.reason = f"spravportal_{category}"
                elif response.status_code == 404:
                    # Номер не найден в базе - считаем нормальным
                    pass
                else:
                    logger.warning(f"SpravPortal API returned {response.status_code}: {response.text[:200]}")
                    
        except httpx.TimeoutException:
            logger.warning(f"SpravPortal API timeout for {phone[:10]}...")
        except Exception as e:
            logger.error(f"SpravPortal API error: {e}")
        
        return result
    
    async def _check_kaspersky(self, phone: str) -> SpamCheckResult:
        """
        Проверка через Kaspersky Who Calls API.
        
        Документация: https://who-calls.ru/api
        """
        result = SpamCheckResult()
        
        try:
            # Нормализуем телефон (только цифры)
            digits_only = "".join(filter(str.isdigit, phone))
            if not digits_only or len(digits_only) < 10:
                return result
            
            url = "https://api.who-calls.ru/v1/check"
            headers = {
                "X-API-Key": settings.KASPERSKY_API_KEY,
                "Content-Type": "application/json"
            }
            payload = {"phone": digits_only}
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    category = data.get("type", "").lower()
                    
                    # Категории могут отличаться, нужно уточнить в документации
                    if category in ("spam", "fraud", "scam", "advertising"):
                        result.is_spam = True
                        result.category = category
                        result.reason = f"kaspersky_{category}"
                elif response.status_code == 404:
                    # Номер не найден в базе - считаем нормальным
                    pass
                else:
                    logger.warning(f"Kaspersky API returned {response.status_code}: {response.text[:200]}")
                    
        except httpx.TimeoutException:
            logger.warning(f"Kaspersky API timeout for {phone[:10]}...")
        except Exception as e:
            logger.error(f"Kaspersky API error: {e}")
        
        return result
    
    async def add_to_blacklist(self, phone: str, reason: Optional[str] = None) -> bool:
        """
        Добавить номер в чёрный список.
        
        Args:
            phone: Номер телефона
            reason: Причина добавления (опционально)
            
        Returns:
            True если успешно добавлено
        """
        client = await redis_service._get_client()
        if client is None:
            return False
        
        try:
            phone_hash = redis_service.hash_phone(phone)
            key = f"blacklist:phone:{phone_hash}"
            # Храним бессрочно (или можно установить TTL)
            value = reason or "manual_add"
            await client.set(key, value)
            logger.info(f"Added phone {phone_hash[:16]}... to blacklist")
            return True
        except Exception as e:
            logger.error(f"Failed to add phone to blacklist: {e}")
            return False
    
    async def add_to_whitelist(self, phone: str) -> bool:
        """
        Добавить номер в белый список.
        
        Args:
            phone: Номер телефона
            
        Returns:
            True если успешно добавлено
        """
        client = await redis_service._get_client()
        if client is None:
            return False
        
        try:
            phone_hash = redis_service.hash_phone(phone)
            key = f"whitelist:phone:{phone_hash}"
            # Храним бессрочно
            await client.set(key, "1")
            logger.info(f"Added phone {phone_hash[:16]}... to whitelist")
            return True
        except Exception as e:
            logger.error(f"Failed to add phone to whitelist: {e}")
            return False


# Глобальный экземпляр
spam_checker = SpamChecker()

