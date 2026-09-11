import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import time
from urllib.parse import urlsplit

import httpx
import pytest
from redis import Redis

from automation import provider_transport as transport


@pytest.fixture
def limiter(monkeypatch):
    url = os.getenv("ISOLATED_REDIS_URL")
    if not url:
        pytest.skip("requires isolated Redis")
    assert os.getenv("WW_TEST") == "1" and urlsplit(url).hostname == "test-redis" and urlsplit(url).path == "/15"
    client = Redis.from_url(url)
    client.flushdb()
    monkeypatch.setenv("RATE_LIMIT_REDIS_URL", url)
    monkeypatch.setenv("DISTRIBUTED_RATE_LIMITS", "true")
    yield client
    client.flushdb()
    client.close()


def test_global_pacing_across_independent_connections(limiter):
    request = httpx.Request("GET", "https://example.invalid", headers={"Authorization": "test-secret"})
    def reserve(_):
        # Independent connections represent separate worker processes.
        client = Redis.from_url(os.environ["ISOLATED_REDIS_URL"])
        try:
            return client.eval(transport.RESERVE, 2, *transport.keys("direct", request), 1000, 1000)
        finally:
            client.close()
    with ThreadPoolExecutor(8) as pool:
        answers = list(pool.map(reserve, range(8)))
    assert sum(x == 0 for x in answers) == 1
    assert all(x > 0 for x in answers if x != 0)
    assert all(b"test-secret" not in key for key in limiter.keys("*"))


@pytest.mark.asyncio
async def test_hook_paces_actual_http_requests(limiter, monkeypatch):
    monkeypatch.setenv("PROVIDER_DIRECT_RPS", "10")
    sent = []
    async def receive(request):
        sent.append(time.monotonic())
        return httpx.Response(200, json={"ok": True})
    async with transport.provider_client("direct", transport=httpx.MockTransport(receive)) as client:
        await asyncio.gather(*(client.get("https://example.invalid") for _ in range(3)))
    assert len(sent) == 3
    assert sent[-1] - sent[0] >= .18


@pytest.mark.asyncio
async def test_redis_failure_never_sends_external_request(limiter, monkeypatch):
    from redis.exceptions import ConnectionError
    class Broken:
        def eval(self, *_):
            raise ConnectionError("unavailable")
    monkeypatch.setattr(transport, "connection", lambda: Broken())
    sent = []
    async def receive(request):
        sent.append(request)
        return httpx.Response(200)
    async with transport.provider_client("direct", transport=httpx.MockTransport(receive)) as client:
        with pytest.raises(transport.RateLimitUnavailable):
            await client.get("https://example.invalid")
    assert sent == []


@pytest.mark.asyncio
async def test_429_cooldown_shared_and_does_not_shorten_existing(limiter):
    request = httpx.Request("GET", "https://example.invalid", headers={"Authorization": "token"})
    await transport.observe("metrica", httpx.Response(429, request=request, headers={"Retry-After": "5"}))
    await transport.observe("metrica", httpx.Response(429, request=request, headers={"Retry-After": "1"}))
    wait = limiter.eval(transport.RESERVE, 2, *transport.keys("metrica", request), 500, 500)
    assert wait > 4000


def test_legacy_client_needs_no_redis(monkeypatch):
    monkeypatch.setenv("DISTRIBUTED_RATE_LIMITS", "false")
    client = transport.provider_client("direct")
    assert client.event_hooks == {"request": [], "response": []}
