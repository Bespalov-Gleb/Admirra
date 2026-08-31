"""Нативный клиент Google Gemini (ProxyAPI /google/v1beta) для Gemini-моделей.

Gemini отдаётся только в собственном формате (contents/systemInstruction/
functionDeclarations), поэтому здесь перевод нашего OpenAI-chat формата ↔ Gemini
и разбор его SSE (streamGenerateContent?alt=sse). На выходе — тот же контракт
событий, что и у остальных путей (text / reasoning / message с tool_calls в
OpenAI-форме), поэтому агент-луп остаётся общим.

Размышления Gemini: generationConfig.thinkingConfig (thinkingBudget + includeThoughts).
Инструменты: OpenAI function → functionDeclarations. Подписи мыслей Gemini 3
(thoughtSignature) сохраняются в tool_call (_gts) и возвращаются модели в следующем
ходе, иначе function-calling с включённым мышлением деградирует.
"""
from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Optional

import httpx

# Ключи JSON Schema, которые понимает Gemini (OpenAPI-подмножество).
_SCHEMA_KEYS = ("type", "description", "enum", "items", "properties", "required", "nullable", "format")

# effort → бюджет размышлений (в токенах); 24576 — потолок flash-линейки.
_THINKING_BUDGET = {"low": 2048, "medium": 8192, "high": 24576}


def _clean_schema(schema: Any) -> Any:
    """Рекурсивно оставляет только поддерживаемые Gemini ключи JSON Schema."""
    if not isinstance(schema, dict):
        return schema
    out: dict[str, Any] = {}
    for k in _SCHEMA_KEYS:
        if k not in schema:
            continue
        v = schema[k]
        if k == "properties" and isinstance(v, dict):
            out[k] = {pk: _clean_schema(pv) for pk, pv in v.items()}
        elif k == "items":
            out[k] = _clean_schema(v)
        else:
            out[k] = v
    return out


def to_tools(openai_tools: Optional[list[dict]]) -> Optional[list[dict]]:
    if not openai_tools:
        return None
    decls: list[dict] = []
    for t in openai_tools:
        fn = t.get("function", t)
        decl: dict[str, Any] = {"name": fn["name"], "description": fn.get("description", "")}
        params = _clean_schema(fn.get("parameters") or {})
        # Gemini не принимает object без свойств — тогда параметры опускаем.
        if params.get("properties"):
            decl["parameters"] = params
        decls.append(decl)
    return [{"functionDeclarations": decls}]


def _response_obj(content: str) -> dict:
    """Строка результата инструмента → объект для functionResponse.response."""
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    return {"result": content}


def to_contents(messages: list[dict]) -> tuple[Optional[dict], list[dict]]:
    """OpenAI-chat messages → (systemInstruction, contents).

    role=system → systemInstruction. role=tool → functionResponse в user-ходе
    (подряд идущие результаты группируются). assistant.tool_calls → functionCall."""
    system_parts: list[str] = []
    contents: list[dict] = []
    for m in messages:
        role = m.get("role")
        if role == "system":
            if m.get("content"):
                system_parts.append(m["content"])
            continue
        if role == "tool":
            fr: dict[str, Any] = {"name": m.get("name") or "",
                                  "response": _response_obj(m.get("content") or "")}
            if m.get("tool_call_id"):     # эхо id вызова — матчинг при parallel tools
                fr["id"] = m["tool_call_id"]
            part = {"functionResponse": fr}
            # Группируем подряд идущие результаты в один user-ход (parallel tools).
            if contents and contents[-1]["role"] == "user" and contents[-1]["parts"] \
                    and "functionResponse" in contents[-1]["parts"][0]:
                contents[-1]["parts"].append(part)
            else:
                contents.append({"role": "user", "parts": [part]})
            continue
        if role == "user":
            contents.append({"role": "user", "parts": [{"text": m.get("content") or ""}]})
            continue
        if role == "assistant":
            parts: list[dict] = []
            if m.get("content"):
                parts.append({"text": m["content"]})
            for call in m.get("tool_calls") or []:
                fn = call.get("function", {})
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                fc_part: dict[str, Any] = {"functionCall": {"name": fn.get("name"), "args": args}}
                if call.get("_gts"):          # подпись мысли Gemini 3 — вернуть модели
                    fc_part["thoughtSignature"] = call["_gts"]
                parts.append(fc_part)
            if not parts:
                parts.append({"text": ""})
            contents.append({"role": "model", "parts": parts})
    system = {"parts": [{"text": "\n".join(system_parts)}]} if system_parts else None
    return system, contents


def build_body(*, messages: list[dict], tools: Optional[list[dict]],
               effort: Optional[str]) -> dict[str, Any]:
    system, contents = to_contents(messages)
    body: dict[str, Any] = {"contents": contents}
    if system:
        body["systemInstruction"] = system
    gtools = to_tools(tools)
    if gtools:
        body["tools"] = gtools
    # thinkingConfig шлём только при явном уровне: budget=0 некоторые flash отвергают.
    if effort and effort != "none":
        body["generationConfig"] = {
            "thinkingConfig": {"thinkingBudget": _THINKING_BUDGET.get(effort, 8192),
                               "includeThoughts": True},
        }
    return body


async def stream(*, base_url: str, api_key: str, headers_extra: dict, timeout: float,
                 model_name: str, messages: list[dict], tools: Optional[list[dict]],
                 effort: Optional[str]) -> AsyncGenerator[dict, None]:
    """Стрим Gemini streamGenerateContent → унифицированные события ассистента."""
    body = build_body(messages=messages, tools=tools, effort=effort)
    url = f"{base_url}/models/{model_name}:streamGenerateContent?alt=sse"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        **headers_extra,
    }

    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    tool_calls: list[dict] = []
    finish_reason: Optional[str] = None
    usage: Optional[dict] = None

    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, headers=headers, json=body) as resp:
            if resp.status_code >= 400:
                text = (await resp.aread()).decode("utf-8", "replace")
                raise RuntimeError(f"Gemini HTTP {resp.status_code}: {text[:400]}")
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if not data:
                    continue
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if chunk.get("usageMetadata"):
                    usage = chunk["usageMetadata"]
                for cand in chunk.get("candidates", []) or []:
                    for part in (cand.get("content") or {}).get("parts", []) or []:
                        if "functionCall" in part:
                            fc = part["functionCall"]
                            call: dict[str, Any] = {
                                "id": fc.get("id") or f"call_{len(tool_calls)}",
                                "type": "function",
                                "function": {"name": fc.get("name"),
                                             "arguments": json.dumps(fc.get("args") or {}, ensure_ascii=False)},
                            }
                            if part.get("thoughtSignature"):
                                call["_gts"] = part["thoughtSignature"]
                            tool_calls.append(call)
                        elif "text" in part:
                            if part.get("thought"):
                                reasoning_parts.append(part["text"])
                                yield {"type": "reasoning", "delta": part["text"]}
                            else:
                                content_parts.append(part["text"])
                                yield {"type": "text", "delta": part["text"]}
                    if cand.get("finishReason"):
                        finish_reason = cand["finishReason"]

    message: dict[str, Any] = {"role": "assistant", "content": "".join(content_parts)}
    if tool_calls:
        message["tool_calls"] = tool_calls
    finish = "tool_calls" if tool_calls else (finish_reason or "stop")
    yield {"type": "message", "message": message, "finish_reason": finish,
           "usage": _map_usage(usage), "reasoning_text": "".join(reasoning_parts)}


def _map_usage(u: Optional[dict]) -> Optional[dict]:
    if not u:
        return None
    return {"prompt_tokens": u.get("promptTokenCount"),
            "completion_tokens": u.get("candidatesTokenCount")}
