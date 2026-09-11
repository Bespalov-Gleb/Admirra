import httpx
import pytest
from automation.yandex_metrica import YandexMetricaAPI


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 401, 403, 500, 503])
async def test_http_failure_is_not_empty_statistics(monkeypatch, status):
    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(status, json={"error": "test"}))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: real_client(transport=transport, **kwargs))
    with pytest.raises(httpx.HTTPStatusError):
        await YandexMetricaAPI("dummy").get_goals_stats("1", "2026-09-10", "2026-09-10")


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [{}, {"data": None}, {"data": [], "total_rows": 1001}])
async def test_malformed_or_truncated_success_is_rejected(monkeypatch, payload):
    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: real_client(transport=transport, **kwargs))
    with pytest.raises(ValueError):
        await YandexMetricaAPI("dummy").get_goals_stats("1", "2026-09-10", "2026-09-10")
