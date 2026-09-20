import asyncio
import unittest

from ai.assistant.streaming import stream_events


class StreamingTests(unittest.IsolatedAsyncioTestCase):
    async def test_order_and_normal_completion(self):
        async def agent():
            for index in range(5):
                yield {"type": "text", "delta": str(index)}
        result = [event async for event in stream_events(agent(), max_pending=2)]
        self.assertEqual([event["delta"] for event in result], list("01234"))

    async def test_disconnect_closes_blocked_producer(self):
        closed = asyncio.Event()
        produced = []
        async def agent():
            try:
                for index in range(1000):
                    produced.append(index)
                    yield {"type": "text", "delta": str(index)}
            finally:
                closed.set()
        stream = stream_events(agent(), max_pending=2)
        await anext(stream)
        # Let the queue fill; a slow reader must apply backpressure.
        for _ in range(5):
            await asyncio.sleep(0)
        self.assertLessEqual(len(produced), 4)
        await asyncio.wait_for(stream.aclose(), timeout=1)
        self.assertTrue(closed.is_set())

    async def test_heartbeat_and_cancel_during_provider_wait(self):
        closed = asyncio.Event()
        async def agent():
            try:
                await asyncio.Event().wait()
                yield {"type": "done"}
            finally:
                closed.set()
        stream = stream_events(agent(), heartbeat_seconds=0.01)
        self.assertIsNone(await asyncio.wait_for(anext(stream), timeout=1))
        await asyncio.wait_for(stream.aclose(), timeout=1)
        self.assertTrue(closed.is_set())

    async def test_provider_exception_is_not_exposed(self):
        async def agent():
            raise RuntimeError("token=SECRET; private request body")
            yield
        with self.assertLogs("ai.assistant.streaming", level="ERROR") as logs:
            result = [event async for event in stream_events(agent())]
        self.assertEqual(result[0]["type"], "error")
        self.assertNotIn("SECRET", str(result) + str(logs.output))
