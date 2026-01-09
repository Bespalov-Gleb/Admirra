import time
import logging
import functools
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class CacheService:
    """
    A simple in-memory cache service.
    In the future, this can be swapped with Redis without changing the API.
    """
    _cache: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        """
        Get value from cache if it exists and hasn't expired.
        """
        entry = cls._cache.get(key)
        if not entry:
            return None
        
        if time.time() > entry["expires_at"]:
            del cls._cache[key]
            return None
            
        return entry["value"]

    @classmethod
    def set(cls, key: str, value: Any, ttl: int = 600):
        """
        Set value in cache with a TTL (default 10 minutes).
        """
        cls._cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl
        }

    @classmethod
    def clear(cls):
        """
        Clear the entire cache.
        """
        cls._cache.clear()

def cache_response(ttl: int = 600):
    """
    Decorator for caching function responses.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Create a cache key based on function name and arguments
            # Note: We filter out 'db' or 'current_user' from keys to keep them generic for the same data
            cache_args = [str(arg) for arg in args if not hasattr(arg, 'execute')] # Simple check for DB session
            cache_kwargs = {k: str(v) for k, v in kwargs.items() if k not in ["db", "current_user", "background_tasks"]}
            
            key = f"{func.__name__}:{cache_args}:{cache_kwargs}"
            
            cached_val = CacheService.get(key)
            if cached_val is not None:
                logger.info(f"Cache hit for {func.__name__}")
                return cached_val
            
            result = await func(*args, **kwargs)
            CacheService.set(key, result, ttl)
            return result
        return wrapper
    return decorator
