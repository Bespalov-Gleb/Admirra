"""Cross-process API pacing at the HTTP boundary, opt-in during cutover.

Redis failure blocks outbound calls instead of multiplying vendor quotas across
workers. Keys never contain a token, login, URL, or customer payload.
"""
import asyncio
from functools import lru_cache
import hashlib
import os
import time

import httpx
from redis import Redis
from redis.exceptions import RedisError

from core.runtime import env_bool, env_int

RATES = {"direct": 10, "metrica": 2, "vk": 10, "avito": 5}
RESERVE = """
local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000 + tonumber(t[2]) / 1000
local wait = 0
for i, key in ipairs(KEYS) do
    wait = math.max(wait, tonumber(redis.call('GET', key) or '0') - now)
end
if wait > 0 then return math.ceil(wait) end
for i, key in ipairs(KEYS) do
    redis.call('PSETEX', key, math.ceil(tonumber(ARGV[i])) + 1000, now + tonumber(ARGV[i]))
end
return 0
"""
COOLDOWN = """
local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000 + tonumber(t[2]) / 1000
local until_at = math.max(tonumber(redis.call('GET', KEYS[1]) or '0'), now + tonumber(ARGV[1]))
redis.call('PSETEX', KEYS[1], math.ceil(until_at - now) + 1000, until_at)
return 1
"""


class RateLimitUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=8)
def _redis(pid, url):
    return Redis.from_url(url, socket_connect_timeout=2, socket_timeout=2, max_connections=16,
                          retry_on_timeout=False, health_check_interval=30)


def connection():
    url = os.getenv("RATE_LIMIT_REDIS_URL")
    if not url:
        raise RateLimitUnavailable("RATE_LIMIT_REDIS_URL is required for distributed API limits")
    return _redis(os.getpid(), url)


def keys(provider, request):
    credential = request.headers.get("Authorization", "anonymous")
    digest = hashlib.sha256(credential.encode()).hexdigest()
    return [f"admirra:rate:v1:{provider}:global", f"admirra:rate:v1:{provider}:{digest}"]


async def pace(provider, request):
    rate = env_int(f"PROVIDER_{provider.upper()}_RPS", RATES[provider], 1, 100)
    deadline = time.monotonic() + 120
    while True:
        try:
            wait_ms = await asyncio.to_thread(connection().eval, RESERVE, 2, *keys(provider, request),
                                             1000 / rate, 1000 / rate)
        except RedisError:
            raise RateLimitUnavailable("Shared API limiter unavailable; outbound request was not sent") from None
        if wait_ms == 0:
            return
        if time.monotonic() + wait_ms / 1000 > deadline:
            raise RateLimitUnavailable("Shared API limit wait exceeded; retry later")
        await asyncio.sleep(max(0.001, wait_ms / 1000))


async def observe(provider, response):
    if response.status_code != 429:
        return
    try:
        seconds = min(3600, max(1, int(response.headers.get("Retry-After", "60"))))
    except ValueError:
        seconds = 60
    try:
        await asyncio.to_thread(connection().eval, COOLDOWN, 1, keys(provider, response.request)[1], seconds * 1000)
    except RedisError:
        raise RateLimitUnavailable("Cannot share provider cooldown; retry later") from None


def provider_client(provider, **kwargs):
    if provider not in RATES:
        raise ValueError("Unknown API provider")
    if env_bool("DISTRIBUTED_RATE_LIMITS", False):
        hooks = {name: list(items) for name, items in kwargs.pop("event_hooks", {}).items()}
        async def request_hook(request):
            await pace(provider, request)
        async def response_hook(response):
            await observe(provider, response)
        hooks.setdefault("request", []).insert(0, request_hook)
        hooks.setdefault("response", []).insert(0, response_hook)
        kwargs["event_hooks"] = hooks
    return httpx.AsyncClient(**kwargs)
