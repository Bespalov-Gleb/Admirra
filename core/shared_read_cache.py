"""Opt-in, scoped JSON read cache with cross-process request coalescing.

Never wrap authorization, billing, report sending, or a mutating endpoint.
Redis is disposable: a cache outage falls back to the original loader; the
independent provider limiter still governs outbound calls. No pickle or secrets
in keys. An expired lock owner cannot overwrite a successor's result.
"""
import asyncio
from functools import lru_cache
import hashlib
import json
import os
import time
import uuid

from redis import Redis
from redis.exceptions import RedisError

from core.runtime import env_bool

RELEASE = "if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) end return 0"
PUBLISH = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[3])
redis.call('DEL', KEYS[1])
return 1
"""


class CacheBusy(RuntimeError):
    """Another process is still loading. Do not return fabricated empty data."""


@lru_cache(maxsize=4)
def _connection(pid, url):
    return Redis.from_url(url, max_connections=16, socket_connect_timeout=.5,
        socket_timeout=.5, retry_on_timeout=False, health_check_interval=30)


def connection():
    url = os.getenv("READ_CACHE_REDIS_URL")
    if not url:
        raise RuntimeError("READ_CACHE_REDIS_URL is required for SHARED_READ_CACHE")
    return _connection(os.getpid(), url)


def cache_key(namespace, scope, params):
    if not scope or not namespace:
        raise ValueError("An explicit authorized scope and namespace are required")
    material = json.dumps([namespace, scope, params], sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "admirra:read:v1:" + hashlib.sha256(material.encode()).hexdigest()


async def remember(namespace, scope, params, loader, *, ttl=60, lease_seconds=180, wait_seconds=150, max_bytes=2_000_000):
    if not env_bool("SHARED_READ_CACHE", False):
        return await loader()
    if ttl < 1 or ttl > 300 or lease_seconds < 1:
        raise ValueError("Read cache lifetime out of range")
    key = cache_key(namespace, scope, params)
    lock = key + ":loading"
    token = uuid.uuid4().hex
    deadline = time.monotonic() + wait_seconds
    client = connection()
    while True:
        try:
            raw = await asyncio.to_thread(client.get, key)
            if raw and len(raw) <= max_bytes:
                try:
                    value = json.loads(raw)
                    if isinstance(value, dict) and "value" in value:
                        return value["value"]
                except (ValueError, TypeError):
                    pass
            owned = await asyncio.to_thread(client.set, lock, token, nx=True, ex=lease_seconds)
        except RedisError:
            return await loader()
        if owned:
            break
        if time.monotonic() >= deadline:
            raise CacheBusy("Данные уже загружаются. Повторите запрос немного позже.")
        await asyncio.sleep(min(.5, max(.01, deadline - time.monotonic())))
    try:
        # A predecessor may have published between our GET and acquiring lock.
        try:
            raw = await asyncio.to_thread(client.get, key)
            if raw and len(raw) <= max_bytes:
                value = json.loads(raw)
                if isinstance(value, dict) and "value" in value:
                    return value["value"]
        except (RedisError, ValueError, TypeError):
            pass
        value = await loader()  # Exceptions and cancellations never populate cache.
        try:
            raw = json.dumps({"value": value}, separators=(",", ":"), allow_nan=False).encode()
            if len(raw) <= max_bytes:
                await asyncio.to_thread(client.eval, PUBLISH, 2, lock, key, token, raw, ttl)
        except (RedisError, ValueError, TypeError):
            pass  # Uncacheable results still go back to their original caller.
        return value
    finally:
        try:
            await asyncio.to_thread(client.eval, RELEASE, 1, lock, token)
        except RedisError:
            pass  # Bounded lease releases a lock after process/cache failure.
