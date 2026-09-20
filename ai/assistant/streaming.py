"""Bounded SSE handoff: slow/disconnected clients cannot orphan an agent."""
import asyncio
from contextlib import aclosing, suppress
import logging

logger = logging.getLogger(__name__)


async def stream_events(events, *, heartbeat_seconds=12.0, max_pending=32):
    queue = asyncio.Queue(maxsize=max_pending)
    done = object()

    async def produce():
        try:
            async with aclosing(events):
                async for event in events:
                    await queue.put(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # Provider exceptions may include URLs, credentials or payloads.
            logger.error("Assistant stream failed (%s)", type(exc).__name__)
            await queue.put({"type": "error", "error": "Не удалось завершить ответ. Попробуйте ещё раз."})
        # Never block on a full queue from a cancellation/finally handler.
        await queue.put(done)

    producer = asyncio.create_task(produce())
    try:
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=heartbeat_seconds)
            except asyncio.TimeoutError:
                yield None  # SSE keepalive comment, not a business event.
                continue
            if item is done:
                break
            yield item
    finally:
        if not producer.done():
            producer.cancel()
        with suppress(asyncio.CancelledError):
            await producer

