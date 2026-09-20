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


@pytest.mark.asyncio
@pytest.mark.parametrize("day,values", [
    ("2026-09-11", [2]), ("not-a-date", [2]), ("2026-9-10", [2]),
    ("2026-09-10", [0.5]), ("2026-09-10", ["NaN"]),
    ("2026-09-10", ["Infinity"]), ("2026-09-10", [None]),
    ("2026-09-10", [True]), ("2026-09-10", []),
])
async def test_wire_response_cannot_hide_invalid_dates_or_round_counts(monkeypatch, day, values):
    real_client = httpx.AsyncClient
    row = {"dimensions": [{"name": day}, {"name": "ad"}], "metrics": values}
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"data": [row, row]}))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: real_client(transport=transport, **kwargs))
    with pytest.raises(ValueError):
        await YandexMetricaAPI("dummy").get_goals_stats("1", "2026-09-10", "2026-09-10", metrics="ym:s:goal1visits")


@pytest.mark.asyncio
async def test_wire_groups_valid_traffic_sources_without_losing_days(monkeypatch):
    real_client = httpx.AsyncClient
    rows = [{"dimensions": [{"name": "2026-09-10"}, {"name": source}], "metrics": [count]}
            for source, count in [("ad", 4), ("other", 3)]]
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"data": rows}))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: real_client(transport=transport, **kwargs))
    result = await YandexMetricaAPI("dummy").get_goals_stats("1", "2026-09-09", "2026-09-10", metrics="ym:s:goal1visits")
    assert result == [{"dimensions": [{"name": "2026-09-09"}], "metrics": [0]},
                      {"dimensions": [{"name": "2026-09-10"}], "metrics": [7]}]
