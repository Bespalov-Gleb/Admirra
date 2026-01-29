"""
Проверка наличия телефона в социальных сетях и мессенджерах.

Поддерживаемые методы:
1. VK API (users.search) - бесплатно, но ограниченно
2. Сторонние провайдеры (GetContact, NumBuster) - платные, но более точные

Документация:
- VK API: https://dev.vk.com/ru/method/users.search
- GetContact: https://getcontact.com/api (платный)
- NumBuster: https://numbuster.com/api (платный)
"""

import logging
import re
import httpx
import json
from typing import Optional
from dataclasses import dataclass, asdict
from lead_validator.config import settings
from lead_validator.services.redis_service import redis_service
import os

logger = logging.getLogger("lead_validator.social_checker")


@dataclass
class SocialCheckResult:
    """Результат проверки телефона в соцсетях"""
    phone: str
    has_telegram: Optional[bool] = None  # TG
    has_whatsapp: Optional[bool] = None  # WA
    has_tiktok: Optional[bool] = None  # TT
    has_vk: Optional[bool] = None  # VK
    has_viber: Optional[bool] = None  # Viber
    
    # Дополнительные данные если найдены
    telegram_username: Optional[str] = None
    vk_profile_url: Optional[str] = None
    vk_user_id: Optional[int] = None
    tiktok_username: Optional[str] = None
    
    # Статус проверки
    checked: bool = False
    error: Optional[str] = None
    provider: Optional[str] = None  # Какой провайдер использовался


class SocialChecker:
    """
    Проверка регистрации телефона в социальных сетях.
    
    Поддерживает несколько провайдеров:
    - VK API (бесплатно, ограниченно)
    - GetContact API (платно)
    - NumBuster API (платно)
    """
    
    def __init__(self):
        # VK API настройки
        self.vk_api_token = os.getenv("VK_API_TOKEN", "")  # Service token для VK API (не Ads API)
        self.vk_api_version = "5.131"
        self.vk_enabled = bool(self.vk_api_token)
        
        # GetContact API настройки
        self.getcontact_api_key = os.getenv("GETCONTACT_API_KEY", "")
        self.getcontact_enabled = bool(self.getcontact_api_key)
        
        # NumBuster API настройки
        self.numbuster_api_key = os.getenv("NUMBUSTER_API_KEY", "")
        self.numbuster_enabled = bool(self.numbuster_api_key)
        
        # Общая настройка
        self.enabled = self.vk_enabled or self.getcontact_enabled or self.numbuster_enabled
        
        if not self.enabled:
            logger.debug("Social checker disabled: no API keys configured")
        else:
            providers = []
            if self.vk_enabled:
                providers.append("VK API")
            if self.getcontact_enabled:
                providers.append("GetContact")
            if self.numbuster_enabled:
                providers.append("NumBuster")
            logger.info(f"Social checker enabled with providers: {', '.join(providers)}")
    
    def _normalize_phone(self, phone: str) -> str:
        """Нормализует номер телефона для поиска"""
        # Убираем все нецифровые символы кроме +
        cleaned = re.sub(r"[^\d+]", "", phone)
        
        # Если начинается с +7, заменяем на 7
        if cleaned.startswith("+7"):
            cleaned = "7" + cleaned[2:]
        elif cleaned.startswith("8"):
            cleaned = "7" + cleaned[1:]
        
        return cleaned
    
    async def check_phone(self, phone: str) -> SocialCheckResult:
        """
        Проверяет телефон во всех доступных социальных сетях.
        
        Использует кеширование в Redis для оптимизации повторных запросов.
        
        Args:
            phone: Номер телефона в любом формате
            
        Returns:
            SocialCheckResult с результатами проверки
        """
        result = SocialCheckResult(phone=phone)
        
        if not self.enabled:
            result.error = "Social checker not configured"
            logger.debug(f"Social check skipped for {phone}: not configured")
            return result
        
        normalized_phone = self._normalize_phone(phone)
        
        # Проверяем кеш в Redis (TTL 7 дней)
        cache_key = f"social_check:{normalized_phone}"
        if redis_service.enabled:
            try:
                cached_result = await redis_service._get_cached_result(cache_key)
                if cached_result:
                    logger.debug(f"Social check cache hit for {phone}")
                    # Восстанавливаем результат из кеша
                    result = SocialCheckResult(**cached_result)
                    return result
            except Exception as e:
                logger.debug(f"Failed to check cache: {e}")
        
        # Пробуем разные провайдеры по приоритету
        # 1. VK API (бесплатно, но ограниченно)
        if self.vk_enabled:
            try:
                vk_result = await self._check_vk_api(normalized_phone)
                if vk_result:
                    result.has_vk = vk_result.get("has_vk", False)
                    result.vk_user_id = vk_result.get("user_id")
                    result.vk_profile_url = vk_result.get("profile_url")
                    result.provider = "VK API"
                    result.checked = True
                    logger.debug(f"VK API check for {phone}: found={result.has_vk}")
            except Exception as e:
                logger.warning(f"VK API check failed for {phone}: {e}")
        
        # 2. GetContact API (платно, более точный)
        if self.getcontact_enabled and not result.checked:
            try:
                getcontact_result = await self._check_getcontact(normalized_phone)
                if getcontact_result:
                    result.has_telegram = getcontact_result.get("has_telegram")
                    result.has_whatsapp = getcontact_result.get("has_whatsapp")
                    result.has_viber = getcontact_result.get("has_viber")
                    result.telegram_username = getcontact_result.get("telegram_username")
                    result.provider = "GetContact"
                    result.checked = True
                    logger.debug(f"GetContact check for {phone}: TG={result.has_telegram}, WA={result.has_whatsapp}")
            except Exception as e:
                logger.warning(f"GetContact check failed for {phone}: {e}")
        
        # 3. NumBuster API (платно, альтернатива)
        if self.numbuster_enabled and not result.checked:
            try:
                numbuster_result = await self._check_numbuster(normalized_phone)
                if numbuster_result:
                    result.has_telegram = numbuster_result.get("has_telegram")
                    result.has_whatsapp = numbuster_result.get("has_whatsapp")
                    result.has_tiktok = numbuster_result.get("has_tiktok")
                    result.provider = "NumBuster"
                    result.checked = True
                    logger.debug(f"NumBuster check for {phone}: TG={result.has_telegram}, WA={result.has_whatsapp}")
            except Exception as e:
                logger.warning(f"NumBuster check failed for {phone}: {e}")
        
        if not result.checked:
            result.error = "All providers failed or unavailable"
            logger.debug(f"All social check providers failed for {phone}")
        
        # Сохраняем результат в кеш (TTL 7 дней = 604800 секунд)
        if redis_service.enabled and result.checked:
            try:
                cache_key = f"social_check:{normalized_phone}"
                cache_data = asdict(result)
                await redis_service._cache_result(cache_key, cache_data, ttl=604800)
                logger.debug(f"Cached social check result for {phone}")
            except Exception as e:
                logger.debug(f"Failed to cache result: {e}")
        
        return result
    
    async def _check_vk_api(self, phone: str) -> Optional[dict]:
        """
        Проверка через VK API users.search.
        
        Документация: https://dev.vk.com/ru/method/users.search
        
        Ограничения:
        - Требуется service token или user token
        - Поиск по телефону работает только если номер публичен
        - Может не найти приватные профили
        
        Returns:
            dict с результатами или None при ошибке
        """
        if not self.vk_api_token:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # VK API users.search с параметром phone
                url = "https://api.vk.com/method/users.search"
                params = {
                    "q": phone,
                    "fields": "photo_100,domain",
                    "count": 1,
                    "access_token": self.vk_api_token,
                    "v": self.vk_api_version
                }
                
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if "error" in data:
                        error_code = data["error"].get("error_code")
                        error_msg = data["error"].get("error_msg", "")
                        
                        # Ошибка 5 = Invalid token
                        if error_code == 5:
                            logger.warning("VK API: Invalid token, check VK_API_TOKEN")
                            return None
                        
                        logger.debug(f"VK API error: {error_code} - {error_msg}")
                        return None
                    
                    if "response" in data:
                        items = data["response"].get("items", [])
                        if items:
                            user = items[0]
                            user_id = user.get("id")
                            domain = user.get("domain") or f"id{user_id}"
                            
                            return {
                                "has_vk": True,
                                "user_id": user_id,
                                "profile_url": f"https://vk.com/{domain}"
                            }
                    
                    # Нет результатов - пользователь не найден или профиль приватный
                    return {"has_vk": False}
                
                logger.warning(f"VK API returned status {response.status_code}")
                return None
                
        except httpx.TimeoutException:
            logger.warning(f"VK API timeout for phone {phone}")
            return None
        except Exception as e:
            logger.error(f"VK API check error: {e}")
            return None
    
    async def _check_getcontact(self, phone: str) -> Optional[dict]:
        """
        Проверка через GetContact API.
        
        Документация: https://getcontact.com/api
        
        Требуется:
        - API ключ от GetContact
        - Платный тариф
        
        Returns:
            dict с результатами или None при ошибке
        """
        if not self.getcontact_api_key:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # GetContact API endpoint (пример, нужно уточнить реальный endpoint)
                url = "https://api.getcontact.com/v1/lookup"
                headers = {
                    "Authorization": f"Bearer {self.getcontact_api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "phone": phone
                }
                
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return {
                        "has_telegram": data.get("telegram", False),
                        "has_whatsapp": data.get("whatsapp", False),
                        "has_viber": data.get("viber", False),
                        "telegram_username": data.get("telegram_username")
                    }
                elif response.status_code == 401:
                    logger.warning("GetContact API: Invalid API key")
                    return None
                elif response.status_code == 402:
                    logger.warning("GetContact API: Insufficient funds")
                    return None
                else:
                    logger.warning(f"GetContact API returned status {response.status_code}")
                    return None
                    
        except httpx.TimeoutException:
            logger.warning(f"GetContact API timeout for phone {phone}")
            return None
        except Exception as e:
            logger.error(f"GetContact API check error: {e}")
            return None
    
    async def _check_numbuster(self, phone: str) -> Optional[dict]:
        """
        Проверка через NumBuster API.
        
        Документация: https://numbuster.com/api
        
        Требуется:
        - API ключ от NumBuster
        - Платный тариф
        
        Returns:
            dict с результатами или None при ошибке
        """
        if not self.numbuster_api_key:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # NumBuster API endpoint (пример, нужно уточнить реальный endpoint)
                url = "https://api.numbuster.com/v1/check"
                headers = {
                    "Authorization": f"Bearer {self.numbuster_api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "phone": phone
                }
                
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return {
                        "has_telegram": data.get("telegram", False),
                        "has_whatsapp": data.get("whatsapp", False),
                        "has_tiktok": data.get("tiktok", False)
                    }
                elif response.status_code == 401:
                    logger.warning("NumBuster API: Invalid API key")
                    return None
                elif response.status_code == 402:
                    logger.warning("NumBuster API: Insufficient funds")
                    return None
                else:
                    logger.warning(f"NumBuster API returned status {response.status_code}")
                    return None
                    
        except httpx.TimeoutException:
            logger.warning(f"NumBuster API timeout for phone {phone}")
            return None
        except Exception as e:
            logger.error(f"NumBuster API check error: {e}")
            return None
    
    async def check_telegram(self, phone: str) -> Optional[bool]:
        """
        Проверка регистрации в Telegram.
        
        Возможные методы:
        1. Telegram Bot API (requires user interaction)
        2. Сторонние чекеры (GetContact, NumBuster)
        3. MTProto API (сложная интеграция)
        """
        if not self.enabled:
            return None
        
        result = await self.check_phone(phone)
        return result.has_telegram
    
    async def check_whatsapp(self, phone: str) -> Optional[bool]:
        """
        Проверка регистрации в WhatsApp.
        
        Методы:
        1. WhatsApp Business API (официальный, требует верификации)
        2. Сторонние чекеры (GetContact, NumBuster)
        """
        if not self.enabled:
            return None
        
        result = await self.check_phone(phone)
        return result.has_whatsapp
    
    async def check_vk(self, phone: str) -> Optional[bool]:
        """
        Проверка регистрации в VK.
        
        Методы:
        1. VK API users.search (ограниченный функционал)
        2. Сторонние сервисы
        """
        if not self.enabled:
            return None
        
        result = await self.check_phone(phone)
        return result.has_vk


# Глобальный экземпляр
social_checker = SocialChecker()
