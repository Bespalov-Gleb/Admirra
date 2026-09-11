import asyncio

import pytest
import httpx

from automation.request_queue import APIRequestQueue


class RecordingLimiter:
    def __init__(self):
        self.calls = 0

    async def acquire(self):
        self.calls += 1


@pytest.mark.asyncio
async def test_limiter_follows_job_not_worker():
    queue = APIRequestQueue()
    queue.metrica_limiter = RecordingLimiter()
    queue.direct_limiter = RecordingLimiter()
    queue.vk_limiter = RecordingLimiter()
    await queue.start(num_workers=1)  # First worker used to always use Metrica.
    try:
        async def result():
            return 42
        assert await queue.enqueue("vk", result) == 42
        assert queue.vk_limiter.calls == 1
        assert queue.metrica_limiter.calls == 0
    finally:
        await queue.stop()


@pytest.mark.asyncio
async def test_stop_drains_jobs_before_stopping_consumers():
    queue = APIRequestQueue()
    await queue.start(num_workers=1)
    async def result():
        await asyncio.sleep(0.01)
        return 42
    request = asyncio.create_task(queue.enqueue("vk", result))
    await asyncio.sleep(0)
    await asyncio.wait_for(queue.stop(), timeout=1)
    assert await request == 42


@pytest.mark.asyncio
async def test_shutdown_cancels_hung_request_and_pending_waiters():
    queue = APIRequestQueue()
    await queue.start(num_workers=1)
    async def hang():
        await asyncio.Event().wait()
    tasks = [asyncio.create_task(queue.enqueue("vk", hang)) for _ in range(2)]
    await asyncio.sleep(0)
    await asyncio.wait_for(queue.stop(timeout=0.02), timeout=1)
    results = await asyncio.gather(*tasks, return_exceptions=True)
    assert all(isinstance(result, asyncio.CancelledError) for result in results)
    assert queue._queue.empty()


@pytest.mark.asyncio
async def test_cancelled_caller_does_not_break_worker():
    queue = APIRequestQueue()
    await queue.start(num_workers=1)
    started, finish = asyncio.Event(), asyncio.Event()
    async def slow():
        started.set()
        await finish.wait()
        return 1
    request = asyncio.create_task(queue.enqueue("vk", slow))
    await started.wait()
    request.cancel()
    await asyncio.gather(request, return_exceptions=True)
    finish.set()
    async def fast():
        return 2
    assert await asyncio.wait_for(queue.enqueue("vk", fast), timeout=1) == 2
    await queue.stop()


@pytest.mark.asyncio
async def test_shutdown_during_retry_backoff_cancels_caller():
    queue = APIRequestQueue()
    await queue.start(num_workers=1)
    called = asyncio.Event()
    async def rate_limited():
        called.set()
        response = httpx.Response(429, request=httpx.Request("GET", "https://example.invalid"))
        raise httpx.HTTPStatusError("rate limit", request=response.request, response=response)
    request = asyncio.create_task(queue.enqueue("vk", rate_limited))
    await called.wait()
    await asyncio.wait_for(queue.stop(timeout=0.01), timeout=1)
    result = await asyncio.wait_for(asyncio.gather(request, return_exceptions=True), timeout=1)
    assert isinstance(result[0], asyncio.CancelledError)


@pytest.mark.asyncio
async def test_enqueue_rejected_before_start_and_after_stop():
    queue = APIRequestQueue()
    async def unused():
        raise AssertionError("must not run")
    with pytest.raises(RuntimeError):
        await queue.enqueue("vk", unused)
    await queue.start()
    await queue.stop()
    with pytest.raises(RuntimeError):
        await queue.enqueue("vk", unused)
