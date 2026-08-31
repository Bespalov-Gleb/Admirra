"""Единая точка вызова LLM для ассистента с маршрутизацией по провайдеру/модели.

Провайдер выбирается в cfg.openrouter.provider:
  • openrouter — всё через OpenAI-совместимый /chat/completions (одна база, слаги).
  • proxyapi   — по семейству модели, т.к. ProxyAPI разделяет провайдеров:
        anthropic (Claude) → /anthropic/v1/messages   (нативный, wire_anthropic)
        openai    (GPT)    → /openai/v1/responses      (Responses, wire_responses)
        google    (Gemini) → /google/v1beta/models/*:streamGenerateContent (wire_google)
        openrouter (Kimi)  → /openrouter/v1/chat/completions (OpenAI-совместимый)

Все пути отдают единый контракт событий, поэтому агент-луп общий:
  {"type":"text","delta":str} | {"type":"reasoning","delta":str}
  {"type":"message","message":{role,content,tool_calls?},"finish_reason","usage"}
"""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, Optional

import httpx

from core.config import get_config

from . import wire_anthropic, wire_google, wire_responses
from .models_catalog import ModelSpec, normalize_effort

logger = logging.getLogger("ai_assistant.llm")
cfg = get_config()


class LLMError(RuntimeError):
    """Ошибка вызова LLM (нет ключа, HTTP-ошибка, битый поток)."""


def is_configured() -> bool:
    return bool((cfg.openrouter.active_key or "").strip())


def _key() -> str:
    key = (cfg.openrouter.active_key or "").strip()
    if not key:
        raise LLMError("Ключ LLM-провайдера не задан — ассистент недоступен")
    return key


def _openai_headers() -> dict[str, str]:
    # Referer/Title нужны только OpenRouter-рейтингам; ProxyAPI их игнорирует.
    return {"HTTP-Referer": cfg.openrouter.referer, "X-Title": cfg.openrouter.title}


def _route(model: ModelSpec) -> tuple[str, str, str]:
    """(protocol, base_url, wire_name) для активного провайдера и модели."""
    o = cfg.openrouter
    if o.provider == "proxyapi":
        if model.family == "anthropic":
            return "anthropic", f"{o.proxyapi_base}/anthropic/v1", model.native_name
        if model.family == "openai":
            return "responses", f"{o.proxyapi_base}/openai/v1", model.native_name
        if model.family == "google":
            return "google", f"{o.proxyapi_base}/google/v1beta", model.native_name
        return "openai_compat", f"{o.proxyapi_base}/openrouter/v1", model.slug
    # provider == openrouter — всё одним контрактом по слагу
    return "openai_compat", o.base_url, model.slug


async def stream_completion(
    *,
    model: ModelSpec,
    effort: Optional[str],
    messages: list[dict],
    tools: Optional[list[dict]] = None,
) -> AsyncGenerator[dict, None]:
    """Один виток запроса к модели со стримингом (маршрутизируется по провайдеру)."""
    eff = normalize_effort(model, effort)
    protocol, base_url, wire_name = _route(model)
    key = _key()
    try:
        if protocol == "anthropic":
            async for ev in wire_anthropic.stream(
                base_url=base_url, api_key=key, headers_extra={}, timeout=cfg.openrouter.request_timeout,
                model_name=wire_name, messages=messages, tools=tools, effort=eff,
            ):
                yield ev
            return
        if protocol == "responses":
            async for ev in wire_responses.stream(
                base_url=base_url, api_key=key, headers_extra=_openai_headers(),
                timeout=cfg.openrouter.request_timeout,
                model_name=wire_name, messages=messages, tools=tools, effort=eff,
            ):
                yield ev
            return
        if protocol == "google":
            async for ev in wire_google.stream(
                base_url=base_url, api_key=key, headers_extra={},
                timeout=cfg.openrouter.request_timeout,
                model_name=wire_name, messages=messages, tools=tools, effort=eff,
            ):
                yield ev
            return
        async for ev in _stream_openai_compat(
            base_url=base_url, key=key, model_slug=wire_name,
            messages=messages, tools=tools, effort=eff,
        ):
            yield ev
    except LLMError:
        raise
    except httpx.HTTPError as exc:
        raise LLMError(f"LLM connection error: {exc}") from exc
    except RuntimeError as exc:
        raise LLMError(str(exc)) from exc


# ── OpenAI-совместимый /chat/completions (Kimi через /openrouter, и провайдер openrouter) ──
def _merge_tool_call_delta(acc: dict[int, dict], deltas: list[dict]) -> None:
    for d in deltas:
        idx = d.get("index", 0)
        slot = acc.setdefault(idx, {"id": None, "type": "function",
                                     "function": {"name": "", "arguments": ""}})
        if d.get("id"):
            slot["id"] = d["id"]
        if d.get("type"):
            slot["type"] = d["type"]
        fn = d.get("function") or {}
        if fn.get("name"):
            slot["function"]["name"] = fn["name"]
        if fn.get("arguments"):
            slot["function"]["arguments"] += fn["arguments"]


async def _stream_openai_compat(
    *, base_url: str, key: str, model_slug: str,
    messages: list[dict], tools: Optional[list[dict]], effort: Optional[str],
) -> AsyncGenerator[dict, None]:
    body: dict[str, Any] = {"model": model_slug, "messages": messages, "stream": True,
                            "stream_options": {"include_usage": True}}
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    if effort and effort != "none":
        body["reasoning"] = {"effort": effort}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", **_openai_headers()}
    url = f"{base_url}/chat/completions"

    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    tool_calls_acc: dict[int, dict] = {}
    finish_reason: Optional[str] = None
    usage: Optional[dict] = None

    async with httpx.AsyncClient(timeout=cfg.openrouter.request_timeout) as client:
        async with client.stream("POST", url, headers=headers, json=body) as resp:
            if resp.status_code >= 400:
                text = (await resp.aread()).decode("utf-8", "replace")
                raise LLMError(f"LLM HTTP {resp.status_code}: {text[:500]}")
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if chunk.get("usage"):
                    usage = chunk["usage"]
                for choice in chunk.get("choices", []) or []:
                    delta = choice.get("delta") or {}
                    if delta.get("content"):
                        content_parts.append(delta["content"])
                        yield {"type": "text", "delta": delta["content"]}
                    if delta.get("reasoning"):
                        reasoning_parts.append(delta["reasoning"])
                        yield {"type": "reasoning", "delta": delta["reasoning"]}
                    if delta.get("tool_calls"):
                        _merge_tool_call_delta(tool_calls_acc, delta["tool_calls"])
                    if choice.get("finish_reason"):
                        finish_reason = choice["finish_reason"]

    message: dict[str, Any] = {"role": "assistant", "content": "".join(content_parts)}
    if tool_calls_acc:
        message["tool_calls"] = [tool_calls_acc[i] for i in sorted(tool_calls_acc)]
    yield {"type": "message", "message": message, "finish_reason": finish_reason,
           "usage": usage, "reasoning_text": "".join(reasoning_parts)}
