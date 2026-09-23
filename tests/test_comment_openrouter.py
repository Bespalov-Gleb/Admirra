import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from ai import comment_llm as llm
from ai import report_generator as reports


@pytest.fixture
def provider(monkeypatch):
    cfg = SimpleNamespace(api_key="synthetic-test-key", base_url="http://test-gateway/api/v1/",
                          default_model="test/model", referer="https://example.test", title="Test")
    monkeypatch.setattr(llm, "get_config", lambda: SimpleNamespace(openrouter=cfg))
    monkeypatch.delenv("AI_COMMENT_MODEL", raising=False)
    return cfg


def mock_transport(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(llm.httpx, "AsyncClient", lambda **kwargs: original(
        **kwargs, transport=httpx.MockTransport(handler)))


@pytest.mark.asyncio
async def test_comment_uses_gateway_json_and_actual_cost(provider, monkeypatch):
    def handler(request):
        assert str(request.url) == "http://test-gateway/api/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer synthetic-test-key"
        body = json.loads(request.content)
        assert body["model"] == "test/model"
        assert body["messages"] == [{"role": "system", "content": "rules"}, {"role": "user", "content": "context"}]
        assert body["response_format"] == {"type": "json_object"}
        assert body["reasoning"] == {"enabled": False}
        assert "tools" not in body
        return httpx.Response(200, json={"model": "test/resolved", "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20, "cost": 0.00012, "prompt_tokens_details": {"cached_tokens": 50}}})
    mock_transport(monkeypatch, handler)
    response = await llm.create_comment(system="rules", messages=[{"role": "user", "content": "context"}], json_output=True)
    assert response.content[0].text == "{}"
    assert response.cost_usd == Decimal("0.00012")
    assert response.model == "test/resolved"
    assert reports._response_usage(response) == (100, 20, 0, 50)


@pytest.mark.asyncio
async def test_no_cost_is_unknown_not_old_provider_estimate(provider, monkeypatch):
    monkeypatch.setenv("AI_INPUT_COST_PER_MILLION_USD", "9999")
    mock_transport(monkeypatch, lambda r: httpx.Response(200, json={"choices": [{"message": {"content": None}, "finish_reason": "length"}]}))
    response = await llm.create_comment(system="rules", messages=[])
    assert response.cost_usd is None
    assert response.stop_reason == "max_tokens"
    assert response.content[0].text == ""


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 402, 429, 502])
async def test_errors_not_retried_or_echoed(provider, monkeypatch, status):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(status, text="PRIVATE MODEL CONTEXT")
    mock_transport(monkeypatch, handler)
    with pytest.raises(RuntimeError, match=f"HTTP {status}") as exc:
        await llm.create_comment(system="rules", messages=[])
    assert "PRIVATE" not in str(exc.value)
    assert len(requests) == 1


def test_explicit_model_and_required_openrouter_key(provider, monkeypatch):
    monkeypatch.setenv("AI_COMMENT_MODEL", "test/comment-model")
    assert llm.comment_model() == "test/comment-model"
    provider.api_key = ""
    monkeypatch.setenv("OPENAI_API_KEY", "legacy-key-must-not-be-used")
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        llm.require_comment_provider()


@pytest.mark.asyncio
async def test_dashboard_timeout_falls_back_without_retry(provider, monkeypatch):
    call = AsyncMock(side_effect=httpx.ReadTimeout("test timeout"))
    monkeypatch.setattr(reports, "create_comment", call)
    monkeypatch.setattr(reports, "_log_comment_generation", lambda *a, **kw: None)
    monkeypatch.setattr(reports, "_fallback_dashboard_comment", lambda context: "safe fallback")
    result = await reports._generate_dashboard_comment(None, [], None, None, "2026-09-01", "2026-09-07", "vk", _context={})
    assert result == "safe fallback"
    call.assert_awaited_once()


def test_worker_receives_openrouter_but_not_proxy_credentials():
    from ops.prepare_worker_runtime import select
    selected = select({"SECRET_KEY": "test", "ENCRYPTION_KEY": "test", "OPENROUTER_API_KEY": "test",
        "OPENROUTER_BASE_URL": "http://private-gateway/api/v1", "AI_COMMENT_MODEL": "test/model", "PROXYAPI_KEY": "unused"})
    assert "OPENROUTER_API_KEY" in selected
    assert "AI_COMMENT_MODEL" in selected
    assert "PROXYAPI_KEY" not in selected


def test_comment_log_uses_provider_model_and_cost(provider, monkeypatch):
    import uuid
    from datetime import date
    rows = []
    db = SimpleNamespace(add=rows.append, commit=lambda: None, rollback=lambda: None)
    monkeypatch.setattr(reports, "data_fingerprint", lambda *a: "test")
    monkeypatch.setenv("AI_INPUT_COST_PER_MILLION_USD", "9999")
    response = SimpleNamespace(model="actual/model", cost_usd=Decimal("0.00012"), usage=SimpleNamespace(input_tokens=100, output_tokens=20))
    reports._log_comment_generation(db, [uuid.uuid4()], date(2026, 9, 1), date(2026, 9, 7), "test", {}, "refresh", response=response)
    assert len(rows) == 1
    assert rows[0].model == "actual/model"
    assert rows[0].cost_usd == Decimal("0.00012")
    assert rows[0].cost_rub is None
