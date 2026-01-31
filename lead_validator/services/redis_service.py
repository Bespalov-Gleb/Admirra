"""
Redis сервис для дедупликации и rate limiting.
Поддерживает fail-open режим при недоступности Redis.
"""

import logging
import hashlib
from typing import Optional
from lead_validator.config import settings

logger = logging.getLogger("lead_validator.redis")

# Redis импортируется опционально для fail-open
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis package not installed, Redis features disabled")


class RedisService:
    """
    Redis операции для дедупликации телефонов и rate limiting по IP.
    
    Fail-open режим: если Redis недоступен и FAIL_OPEN_MODE=True,
    операции возвращают "успех" (не блокируют лиды).
    """
    
    def __init__(self):
        self.enabled = settings.REDIS_ENABLED and REDIS_AVAILABLE
        self.fail_open = settings.FAIL_OPEN_MODE
        self._client: Optional[redis.Redis] = None
        
    async def _get_client(self) -> Optional[redis.Redis]:
        """Получить или создать Redis клиент"""
        if not self.enabled:
            return None
            
        if self._client is None:
            try:
                self._client = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
                # Проверяем подключение
                await self._client.ping()
                logger.info("Redis connected successfully")
            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                self._client = None
                
        return self._client
    
    @staticmethod
    def hash_phone(phone: str) -> str:
        """
        Создаёт SHA256 хеш телефона для хранения в Redis.
        Хеш нужен чтобы не хранить телефоны в открытом виде.
        """
        # Нормализуем: только цифры
        digits_only = "".join(filter(str.isdigit, phone))
        return hashlib.sha256(digits_only.encode()).hexdigest()
    
    async def is_duplicate(self, phone: str) -> bool:
        """
        Проверяет, есть ли телефон в базе дубликатов.
        
        Returns:
            True если дубликат найден
            False если это новый телефон или Redis недоступен (fail-open)
        """
        client = await self._get_client()
        if client is None:
            if self.fail_open:
                return False  # Пропускаем при недоступности Redis
            return True  # Блокируем при недоступности Redis
            
        try:
            phone_hash = self.hash_phone(phone)
            key = f"lead:phone:{phone_hash}"
            exists = await client.exists(key)
            
            if exists:
                logger.info(f"Duplicate phone detected: {phone_hash[:16]}...")
            return bool(exists)
            
        except Exception as e:
            logger.error(f"Redis is_duplicate error: {e}")
            return not self.fail_open
    
    async def mark_phone(self, phone: str) -> bool:
        """
        Сохраняет хеш телефона в Redis с TTL.
        
        Returns:
            True если успешно сохранено
        """
        client = await self._get_client()
        if client is None:
            return False
            
        try:
            phone_hash = self.hash_phone(phone)
            key = f"lead:phone:{phone_hash}"
            ttl = settings.PHONE_DUPLICATE_TTL_SEC
            
            await client.setex(key, ttl, "1")
            logger.debug(f"Phone marked: {phone_hash[:16]}... TTL={ttl}s")
            return True
            
        except Exception as e:
            logger.error(f"Redis mark_phone error: {e}")
            return False
    
    async def check_rate_limit(self, ip: str) -> bool:
        """
        Проверяет rate limit по IP.
        
        Returns:
            True если лимит НЕ превышен (можно продолжать)
            False если лимит превышен
        """
        client = await self._get_client()
        if client is None:
            return self.fail_open  # True = пропускаем, False = блокируем
            
        try:
            key = f"lead:rate:{ip}"
            window = settings.RATE_LIMIT_WINDOW_SEC
            limit = settings.RATE_LIMIT_PER_IP
            
            # Увеличиваем счётчик
            current = await client.incr(key)
            
            # При первом запросе устанавливаем TTL
            if current == 1:
                await client.expire(key, window)
                
            if current > limit:
                logger.warning(f"Rate limit exceeded for IP: {ip} ({current}/{limit})")
                return False
                
            logger.debug(f"Rate limit check for {ip}: {current}/{limit}")
            return True
            
        except Exception as e:
            logger.error(f"Redis rate_limit error: {e}")
            return self.fail_open
    
    @staticmethod
    def hash_email(email: str) -> str:
        """
        Создаёт SHA256 хеш email для хранения в Redis.
        Нормализует: lowercase, удаление пробелов.
        """
        normalized = email.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    async def is_email_duplicate(self, email: str) -> bool:
        """
        Проверяет, есть ли email в базе дубликатов.
        
        Returns:
            True если дубликат найден
            False если это новый email или Redis недоступен (fail-open)
        """
        if not email:
            return False
            
        client = await self._get_client()
        if client is None:
            if self.fail_open:
                return False
            return True
            
        try:
            email_hash = self.hash_email(email)
            key = f"lead:email:{email_hash}"
            exists = await client.exists(key)
            
            if exists:
                logger.info(f"Duplicate email detected: {email_hash[:16]}...")
            return bool(exists)
            
        except Exception as e:
            logger.error(f"Redis is_email_duplicate error: {e}")
            return not self.fail_open
    
    async def mark_email(self, email: str) -> bool:
        """
        Сохраняет хеш email в Redis с TTL.
        
        Returns:
            True если успешно сохранено
        """
        if not email:
            return False
            
        client = await self._get_client()
        if client is None:
            return False
            
        try:
            email_hash = self.hash_email(email)
            key = f"lead:email:{email_hash}"
            ttl = settings.PHONE_DUPLICATE_TTL_SEC  # Используем тот же TTL
            
            await client.setex(key, ttl, "1")
            logger.debug(f"Email marked: {email_hash[:16]}... TTL={ttl}s")
            return True
            
        except Exception as e:
            logger.error(f"Redis mark_email error: {e}")
            return False
    
    async def check_phone_rate_limit(self, phone: str) -> bool:
        """
        Проверяет rate limit по телефону (Уровень 3 по ТЗ).
        Одна заявка в сутки — нормально. Пять заявок за час — накрутка или бот.
        
        Args:
            phone: Номер телефона
            
        Returns:
            True если лимит НЕ превышен (можно продолжать)
            False если лимит превышен
        """
        client = await self._get_client()
        if client is None:
            return self.fail_open  # True = пропускаем, False = блокируем
            
        try:
            phone_hash = self.hash_phone(phone)
            key = f"lead:rate:phone:{phone_hash}"
            window = settings.RATE_LIMIT_PHONE_WINDOW_SEC
            limit = settings.RATE_LIMIT_PER_PHONE_PER_HOUR
            
            # Увеличиваем счётчик
            current = await client.incr(key)
            
            # При первом запросе устанавливаем TTL
            if current == 1:
                await client.expire(key, window)
                
            if current > limit:
                logger.warning(f"Phone rate limit exceeded: {phone_hash[:16]}... ({current}/{limit} per hour)")
                return False
                
            logger.debug(f"Phone rate limit check: {phone_hash[:16]}... {current}/{limit}")
            return True
            
        except Exception as e:
            logger.error(f"Redis phone_rate_limit error: {e}")
            return self.fail_open
    
    async def _get_cached_result(self, key: str) -> Optional[dict]:
        """
        Получить закешированный результат из Redis.
        
        Args:
            key: Ключ кеша
            
        Returns:
            dict с данными или None если не найдено
        """
        if not self.enabled:
            return None
        
        client = await self._get_client()
        if client is None:
            return None
        
        try:
            import json
            cached = await client.get(key)
            if cached:
                return json.loads(cached)
            return None
        except Exception as e:
            logger.debug(f"Redis get cache error: {e}")
            return None
    
    async def _cache_result(self, key: str, data: dict, ttl: int = 604800):
        """
        Сохранить результат в кеш Redis.
        
        Args:
            key: Ключ кеша
            data: Данные для кеширования (должны быть JSON-сериализуемы)
            ttl: Время жизни в секундах (по умолчанию 7 дней)
        """
        if not self.enabled:
            return
        
        client = await self._get_client()
        if client is None:
            return
        
        try:
            import json
            json_data = json.dumps(data, default=str)  # default=str для datetime и других типов
            await client.setex(key, ttl, json_data)
            logger.debug(f"Cached result for key {key} with TTL {ttl}s")
        except Exception as e:
            logger.debug(f"Redis cache error: {e}")
    
    async def close(self):
        """Закрыть соединение с Redis"""
        if self._client:
            await self._client.close()
            self._client = None


# Глобальный экземпляр
redis_service = RedisService()

