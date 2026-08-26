"""Клиент OpenAI Responses API (ProxyAPI /openai/v1/responses) для GPT-моделей.

На /chat/completions у GPT-5.6 нельзя одновременно function-tools и
reasoning_effort — документированный путь для «инструменты + размышления» это
Responses API. Здесь перевод нашего OpenAI-chat формата ↔ Responses и разбор его
SSE в общий контракт событий (text / reasoning / message с tool_calls).

Пары вызов/результат в Responses связываются по call_id, поэтому id инструмента
у нас = call_id.
"""
from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Optional

import httpx


def to_tools(openai_tools: Optional[list[dict]]) -> Optional[list[dict]]:
    if not openai_tools:
        return None
    out = []
    for t in openai_tools:
        fn = t.get("function", t)
        out.append({
            "type": "function",
            "name": fn["name"],
            "description": fn.get("description", ""),
            "parameters": fn.get("parameters") or {"type": "object", "properties": {}},
        })
    return out


def to_input(messages: list[dict]) -> tuple[str, list[dict]]:
    """OpenAI-chat messages → (instructions, input items Responses)."""
    instructions: list[str] = []
    items: list[dict] = []
    for m in messages:
        role = m.get("role")
        if role == "system":
            if m.get("content"):
                instructions.append(m["content"])
        elif role == "user":
            items.append({"role": "user", "content": m.get("content") or ""})
        elif role == "tool":
            items.append({"type": "function_call_output",
                          "call_id": m.get("tool_call_id"),
                          "output": m.get("content") or ""})
        elif role == "assistant":
            if m.get("content"):
                items.append({"role": "assistant", "content": m["content"]})
            for call in m.get("tool_calls") or []:
                fn = call.get("function", {})
                items.append({"type": "function_call", "call_id": call.get("id"),
                              "name": fn.get("name"), "arguments": fn.get("arguments") or "{}"})
    return "\n".join(instructions), items


def build_body(*, model_name: str, messages: list[dict], tools: Optional[list[dict]],
               effort: Optional[str]) -> dict[str, Any]:
    instructions, items = to_input(messages)
    body: dict[str, Any] = {"model": model_name, "stream": True, "input": items}
    if instructions:
        body["instructions"] = instructions
    resp_tools = to_tools(tools)
    if resp_tools:
        body["tools"] = resp_tools
        body["tool_choice"] = "auto"
    if effort and effort != "none":
        body["reasoning"] = {"effort": effort}
    return body


async def stream(*, base_url: str, api_key: str, headers_extra: dict, timeout: float,
                 model_name: str, messages: list[dict], tools: Optional[list[dict]],
                 effort: Optional[str]) -> AsyncGenerator[dict, None]:
    body = build_body(model_name=model_name, messages=messages, tools=tools, effort=effort)
    url = f"{base_url}/responses"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", **headers_extra}

    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    # item_id → {"call_id","name","args"}
    tool_slots: dict[str, dict] = {}
    usage: Optional[dict] = None

    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, headers=headers, json=body) as resp:
            if resp.status_code >= 400:
                text = (await resp.aread()).decode("utf-8", "replace")
                raise RuntimeError(f"Responses HTTP {resp.status_code}: {text[:400]}")
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    ev = json.loads(data)
                except json.JSONDecodeError:
                    continue
                etype = ev.get("type", "")
                if etype == "response.output_text.delta":
                    content_parts.append(ev.get("delta", ""))
                    yield {"type": "text", "delta": ev.get("delta", "")}
                elif etype in ("response.reasoning_summary_text.delta", "response.reasoning_text.delta"):
                    reasoning_parts.append(ev.get("delta", ""))
                    yield {"type": "reasoning", "delta": ev.get("delta", "")}
                elif etype == "response.output_item.added":
                    item = ev.get("item", {})
                    if item.get("type") == "function_call":
                        tool_slots[item.get("id")] = {"call_id": item.get("call_id"),
                                                       "name": item.get("name"),
                                                       "args": item.get("arguments") or ""}
                elif etype == "response.function_call_arguments.delta":
                    slot = tool_slots.get(ev.get("item_id"))
                    if slot is not None:
                        slot["args"] += ev.get("delta", "")
                elif etype == "response.function_call_arguments.done":
                    slot = tool_slots.get(ev.get("item_id"))
                    if slot is not None and ev.get("arguments"):
                        slot["args"] = ev["arguments"]
                elif etype == "response.completed":
                    usage = _map_usage((ev.get("response") or {}).get("usage"))
                elif etype == "response.failed":
                    err = (ev.get("response") or {}).get("error")
                    raise RuntimeError(f"Responses failed: {str(err)[:300]}")

    message: dict[str, Any] = {"role": "assistant", "content": "".join(content_parts)}
    if tool_slots:
        message["tool_calls"] = [
            {"id": s["call_id"], "type": "function",
             "function": {"name": s["name"], "arguments": s["args"] or "{}"}}
            for s in tool_slots.values()
        ]
    finish = "tool_calls" if tool_slots else "stop"
    yield {"type": "message", "message": message, "finish_reason": finish,
           "usage": usage, "reasoning_text": "".join(reasoning_parts)}


def _map_usage(u: Optional[dict]) -> Optional[dict]:
    if not u:
        return None
    return {"prompt_tokens": u.get("input_tokens"), "completion_tokens": u.get("output_tokens")}
