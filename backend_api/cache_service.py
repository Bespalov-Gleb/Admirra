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

    @classmethod
    def invalidate_contains(cls, token: str):
        """
        Remove only keys containing a specific token.
        """
        if not token:
            return
        keys = [k for k in cls._cache.keys() if token in k]
        for k in keys:
            cls._cache.pop(k, None)

    @classmethod
    def invalidate_client(cls, client_id: str):
        """
        Remove cache keys related to a specific client_id.
        """
        if not client_id:
            return
        cls.invalidate_contains(str(client_id))

def cache_response(ttl: int = 600, skip_cache_when=None):
    """
    Decorator for caching function responses.
    skip_cache_when: callable(result) -> bool; if True, result is not cached (e.g. empty list).
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            import json
            clean_kwargs = {k: v for k, v in kwargs.items() if k not in ["db", "current_user", "background_tasks"]}
            try:
                params_str = json.dumps(clean_kwargs, sort_keys=True, default=str)
            except:
                params_str = str(clean_kwargs)
            key = f"{func.__name__}:{params_str}"
            cached_val = CacheService.get(key)
            if cached_val is not None:
                print(f"DEBUG: CACHE HIT for {func.__name__} - key: {key[:100]}...")
                logger.info(f"Cache hit for {func.__name__}")
                return cached_val
            print(f"DEBUG: CACHE MISS for {func.__name__} - key: {key[:100]}...")
            result = await func(*args, **kwargs)
            if skip_cache_when is None or not skip_cache_when(result):
                CacheService.set(key, result, ttl)
            return result
        return wrapper
    return decorator
