"""Transport evidence, isolated to one asynchronous send attempt."""
from contextvars import ContextVar
import asyncio
import httpx

outcome = ContextVar("delivery_transport_outcome", default="unknown")


def rejected():
    outcome.set("rejected")


def before_send():
    outcome.set("unknown")


def response_received(response):
    # A 5xx, malformed success or lost response cannot prove non-delivery.
    if 400 <= response.status_code < 500:
        rejected()


def request_failed(exc):
    if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)):
        rejected()


async def in_thread(fn, *args):
    """asyncio copies context INTO a thread, but does not copy changes back."""
    def run():
        try:
            return fn(*args), None, outcome.get()
        except Exception as exc:
            return None, exc, outcome.get()
    result, error, evidence = await asyncio.to_thread(run)
    outcome.set(evidence)
    if error is not None:
        raise error
    return result
