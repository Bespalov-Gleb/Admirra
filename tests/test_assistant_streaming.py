import asyncio
import unittest
import pytest

from ai.assistant.streaming import stream_events


@pytest.mark.asyncio
@pytest.mark.parametrize('protocol', ['anthropic', 'responses', 'google', 'openai_compat'])
async def test_llm_wrapper_closes_selected_wire_on_disconnect(monkeypatch, protocol):
    from ai.assistant import llm
    closed = asyncio.Event()
    async def wire(**kwargs):
        try:
            yield {'type': 'text', 'delta': 'First'}
            await asyncio.Event().wait()
        finally:
            closed.set()
    monkeypatch.setattr(llm, '_route', lambda model: (protocol, 'https://unused.invalid', 'synthetic'))
    monkeypatch.setattr(llm, '_key', lambda: 'synthetic')
    monkeypatch.setattr(llm, 'normalize_effort', lambda *args: None)
    monkeypatch.setattr(llm.runs, 'before_provider', lambda: None)
    monkeypatch.setattr(llm.runs, 'record_usage', lambda *args, **kwargs: None)
    if protocol == 'openai_compat':
        monkeypatch.setattr(llm, '_stream_openai_compat', wire)
    else:
        monkeypatch.setattr(getattr(llm, 'wire_' + protocol), 'stream', wire)
    stream = llm.stream_completion(model=None, effort=None, messages=[])
    assert (await anext(stream))['type'] == 'text'
    await stream.aclose()
    assert closed.is_set()


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
