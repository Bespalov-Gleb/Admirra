"""
DaData API клиент для валидации телефонов и email.
Использует Clean API для стандартизации и проверки качества.
"""

import asyncio
import json
import logging
import httpx
from typing import Optional
from lead_validator.config import settings
from lead_validator.schemas import DaDataPhoneResponse
from lead_validator.services.redis_service import redis_service

logger = logging.getLogger("lead_validator.dadata")


class DaDataService:
    """
    Асинхронный клиент для работы с DaData Clean API.
    
    Документация: https://dadata.ru/api/clean/phone/
    """
    
    CLEAN_URL = "https://cleaner.dadata.ru/api/v1/clean/phone"
    
    def __init__(self):
        self.api_key = settings.DADATA_API_KEY
        self.secret_key = settings.DADATA_SECRET_KEY
        self.timeout = settings.DADATA_TIMEOUT
        self.cache_ttl = settings.DADATA_CACHE_TTL_SEC
        self.retry_attempts = settings.DADATA_RETRY_ATTEMPTS
        self.retry_backoff = settings.DADATA_RETRY_BACKOFF_SEC
        
    def _get_headers(self) -> dict:
        """Заголовки для авторизации в DaData API"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Token {self.api_key}",
            "X-Secret": self.secret_key
        }

    def _phone_cache_key(self, phone: str) -> str:
        return f"dadata:phone:{redis_service.hash_phone(phone)}"

    def _email_cache_key(self, email: str) -> str:
        return f"dadata:email:{redis_service.hash_email(email)}"

    async def _get_cache(self, key: str) -> Optional[dict]:
        if not redis_service.enabled:
            return None
        client = await redis_service._get_client()
        if client is None:
            return None
        try:
            cached = await client.get(key)
            if cached:
                return json.loads(cached)
        except Exception:
            return None
        return None

    async def _set_cache(self, key: str, data: dict):
        if not redis_service.enabled:
            return
        client = await redis_service._get_client()
        if client is None:
            return
        try:
            await client.setex(key, self.cache_ttl, json.dumps(data))
        except Exception:
            return
    
    async def validate_phone(self, phone: str) -> Optional[DaDataPhoneResponse]:
        """
        Валидация и стандартизация телефона через DaData.
        
        Args:
            phone: Телефон в любом формате
            
        Returns:
            DaDataPhoneResponse с результатом или None при ошибке
            
        Коды качества (qc):
            0 - Телефон распознан уверенно (российский)
            7 - Телефон распознан уверенно (иностранный)
            1 - Распознан с допущениями
            2 - Пустой или мусорный
            3 - Несколько телефонов, распознан первый
        """
        if not self.api_key:
            logger.warning("DaData API key not configured")
            return None

        cache_key = self._phone_cache_key(phone)
        cached = await self._get_cache(cache_key)
        if cached:
            return DaDataPhoneResponse(**cached)

        attempts = max(1, self.retry_attempts + 1)
        for attempt in range(attempts):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.CLEAN_URL,
                        headers=self._get_headers(),
                        json=[phone]
                    )

                    if response.status_code == 200:
                        data = response.json()
                        if data and len(data) > 0:
                            logger.info(
                                f"DaData response for {phone}: qc={data[0].get('qc')}, "
                                f"type={data[0].get('type')}"
                            )
                            await self._set_cache(cache_key, data[0])
                            return DaDataPhoneResponse(**data[0])

                    elif response.status_code == 401:
                        logger.error("DaData auth error: invalid API key or secret")
                        break
                    elif response.status_code == 403:
                        logger.error("DaData error: email not confirmed or insufficient funds")
                        break
                    elif response.status_code == 429:
                        logger.warning("DaData rate limit exceeded")
                    else:
                        logger.error(f"DaData error: {response.status_code} - {response.text}")

            except httpx.TimeoutException:
                logger.warning(f"DaData timeout for phone: {phone}")
            except httpx.RequestError as e:
                logger.error(f"DaData request error: {e}")
            except Exception as e:
                logger.error(f"DaData unexpected error: {e}")

            if attempt < attempts - 1:
                await asyncio.sleep(self.retry_backoff * (attempt + 1))

        return None
    
    async def validate_email(self, email: str) -> Optional[dict]:
        """
        Валидация email через DaData Clean API.
        
        Returns:
            dict с результатом или None при ошибке
            
        Поля ответа:
            - qc: 0=OK, 1=исправлен, 2=мусор, 3=несколько адресов
            - type: PERSONAL, CORPORATE, ROLE, DISPOSABLE
        """
        if not self.api_key:
            logger.warning("DaData API key not configured")
            return None

        cache_key = self._email_cache_key(email)
        cached = await self._get_cache(cache_key)
        if cached:
            return cached

        attempts = max(1, self.retry_attempts + 1)
        for attempt in range(attempts):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        "https://cleaner.dadata.ru/api/v1/clean/email",
                        headers=self._get_headers(),
                        json=[email]
                    )

                    if response.status_code == 200:
                        data = response.json()
                        if data and len(data) > 0:
                            result = data[0]
                            logger.info(
                                f"DaData email response for {email}: "
                                f"qc={result.get('qc')}, type={result.get('type')}"
                            )
                            await self._set_cache(cache_key, result)
                            return result
                    elif response.status_code == 401:
                        logger.error("DaData auth error: invalid API key or secret")
                        break
                    elif response.status_code == 403:
                        logger.error("DaData error: email not confirmed or insufficient funds")
                        break
                    elif response.status_code == 429:
                        logger.warning("DaData rate limit exceeded")

            except httpx.TimeoutException:
                logger.warning(f"DaData timeout for email: {email}")
            except Exception as e:
                logger.error(f"DaData email validation error: {e}")

            if attempt < attempts - 1:
                await asyncio.sleep(self.retry_backoff * (attempt + 1))

        return None
    
    def is_phone_valid(self, dadata_response: DaDataPhoneResponse) -> bool:
        """
        Проверяет, прошёл ли телефон валидацию.
        
        Считаем валидным если:
        - qc = 0 (распознан уверенно, Россия)
        - qc = 7 (распознан уверенно, иностранный)
        """
        return dadata_response.qc in (0, 7)
    
    def is_mobile(self, dadata_response: DaDataPhoneResponse) -> bool:
        """Проверяет, является ли номер мобильным"""
        return dadata_response.type == "Мобильный"
    
    def is_email_valid(self, dadata_response: dict) -> bool:
        """
        Проверяет, прошёл ли email валидацию DaData.
        
        Считаем валидным если qc = 0 или 1 (исправлен).
        qc = 2 (мусор) или 3+ — невалидный.
        
        Args:
            dadata_response: ответ от validate_email()
        """
        qc = dadata_response.get("qc", 2)
        return qc in (0, 1)
    
    def is_email_disposable(self, dadata_response: dict) -> bool:
        """
        Проверяет, является ли email одноразовым (DISPOSABLE).
        
        DaData определяет тип:
        - PERSONAL: Gmail, Mail.ru, Yandex
        - CORPORATE: company.ru
        - ROLE: info@, support@
        - DISPOSABLE: temp-mail, mailinator
        """
        email_type = dadata_response.get("type", "")
        return email_type == "DISPOSABLE"
    
    def get_email_type(self, dadata_response: dict) -> str:
        """Получить тип email: PERSONAL, CORPORATE, ROLE, DISPOSABLE"""
        return dadata_response.get("type", "UNKNOWN")


# Глобальный экземпляр сервиса
dadata_service = DaDataService()


