import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
from urllib.parse import urlsplit

import httpx
import pytest
from redis import Redis
from redis.exceptions import ConnectionError

from core import shared_read_cache as cache


@pytest.fixture
def shared(monkeypatch):
    url = os.getenv("ISOLATED_REDIS_URL")
    if not url:
        pytest.skip("requires isolated Redis")
    assert os.getenv("WW_TEST") == "1" and urlsplit(url).hostname == "test-redis" and urlsplit(url).path == "/15"
    client = Redis.from_url(url)
    client.flushdb()
    monkeypatch.setenv("SHARED_READ_CACHE", "true")
    monkeypatch.setenv("READ_CACHE_REDIS_URL", url)
    yield client
    client.flushdb()
    client.close()


def test_coalesces_across_independent_loops_and_connections(shared):
    url = os.getenv("ISOLATED_REDIS_URL")
    async def request():
        async def load():
            client = Redis.from_url(url)
            try:
                client.incr("loads")
            finally:
                client.close()
            await asyncio.sleep(.1)
            return {"leads": 34}
        return await cache.remember("stats", ["user-one", "client-one"], {"period": "week"}, load)
    with ThreadPoolExecutor(8) as pool:
        responses = list(pool.map(lambda _: asyncio.run(request()), range(8)))
    assert responses == [{"leads": 34}] * 8
    assert int(shared.get("loads")) == 1


@pytest.mark.asyncio
async def test_scope_period_goals_and_credentials_do_not_mix(shared):
    calls = []
    async def load():
        calls.append(1)
        return len(calls)
    for user, params in [("one", [1]), ("two", [1]), ("one", [2])]:
        await cache.remember("goals", user, params, load)
    assert await cache.remember("goals", "one", [1], load) == 1
    assert len(calls) == 3
    assert all(b"one" not in key for key in shared.keys("admirra:*"))


@pytest.mark.asyncio
async def test_exception_not_cached_and_lock_released(shared):
    async def failed(): raise ValueError("API failed")
    with pytest.raises(ValueError):
        await cache.remember("data", "owner", [], failed)
    assert shared.keys("admirra:*") == []
    async def good(): return []  # A VALID empty response is cacheable.
    assert await cache.remember("data", "owner", [], good) == []
    assert await cache.remember("data", "owner", [], failed) == []


@pytest.mark.asyncio
async def test_redis_outage_falls_back_to_loader(shared, monkeypatch):
    class Broken:
        def get(self, *args): raise ConnectionError("test")
    monkeypatch.setattr(cache, "connection", lambda: Broken())
    async def load(): return {"fresh": True}
    assert await cache.remember("data", "owner", [], load) == {"fresh": True}


def test_expired_owner_cannot_publish_or_unlock_successor(shared):
    key = cache.cache_key("data", "owner", [])
    lock = key + ":loading"
    shared.set(lock, "new-owner", ex=10)
    assert shared.eval(cache.PUBLISH, 2, lock, key, "old-owner", '{"value":"old"}', 60) == 0
    assert shared.eval(cache.RELEASE, 1, lock, "old-owner") == 0
    assert shared.get(lock) == b"new-owner"
    assert shared.eval(cache.PUBLISH, 2, lock, key, "new-owner", '{"value":"new"}', 60) == 1
    assert shared.ttl(key) in (59, 60)


@pytest.mark.asyncio
async def test_cancellation_releases_lock(shared):
    started = asyncio.Event()
    async def load():
        started.set()
        await asyncio.sleep(10)
    task = asyncio.create_task(cache.remember("data", "owner", [], load))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError): await task
    assert shared.keys("admirra:*") == []


@pytest.mark.asyncio
async def test_busy_result_is_not_fabricated_empty_data(shared):
    key = cache.cache_key("data", "owner", [])
    shared.set(key + ":loading", "some-other-loader", ex=5)
    async def load(): raise AssertionError("must not send parallel duplicate")
    with pytest.raises(cache.CacheBusy):
        await cache.remember("data", "owner", [], load, wait_seconds=.01)


@pytest.mark.asyncio
async def test_large_or_corrupt_values_do_not_break_fresh_read(shared):
    key = cache.cache_key("data", "owner", [])
    shared.set(key, "not JSON", ex=60)
    async def load(): return "x" * 100
    assert await cache.remember("data", "owner", [], load, max_bytes=10) == "x" * 100
    assert shared.get(key) == b"not JSON"


@pytest.mark.asyncio
async def test_metrika_integration_cache_and_token_rotation(shared, monkeypatch):
    from automation import yandex_metrica as metrica
    count = 0
    async def receive(request):
        nonlocal count
        count += 1
        return httpx.Response(200, json={"data": [{"dimensions": [{"name": "Campaign"}], "metrics": [34]}], "total_rows": 1})
    monkeypatch.setattr(metrica, "provider_client", lambda *a, **kw: httpx.AsyncClient(transport=httpx.MockTransport(receive)))
    async def query(token="secret-token", goal="1"):
        return await metrica.YandexMetricaAPI(token).get_conversions_by_dimension("counter", "2026-09-01", "2026-09-07", [goal], "campaign")
    assert (await query())[0]["conversions"] == 34
    await query()
    assert count == 1
    await query("new-token")
    await query(goal="2")
    assert count == 3
    assert all(b"secret-token" not in k and b"counter" not in k for k in shared.keys("*"))


@pytest.mark.asyncio
@pytest.mark.parametrize("status,payload", [(503, {}), (200, {}), (200, {"data": [], "total_rows": 1}),
    (200, {"data": [{}]}), (200, {"data": [{"metrics": ["NaN"], "dimensions": []}]})])
async def test_metrika_bad_results_are_not_cached_as_zero(shared, monkeypatch, status, payload):
    from automation import yandex_metrica as metrica
    monkeypatch.setattr(metrica, "provider_client", lambda *a, **kw:
        httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(status, json=payload))))
    with pytest.raises((httpx.HTTPStatusError, ValueError)):
        await metrica.YandexMetricaAPI("test").get_conversions_by_dimension("1", "2026-09-01", "2026-09-07", ["1"], "campaign")
    assert shared.keys("admirra:*") == []
