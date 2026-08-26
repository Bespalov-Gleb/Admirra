"""Нативный клиент Anthropic Messages (ProxyAPI /anthropic/v1/messages) для Claude.

Claude 5 не отдаётся в OpenAI-совместимом виде, поэтому здесь перевод нашего
OpenAI-chat формата ↔ Anthropic и разбор его SSE. На выходе — тот же контракт
событий, что и у OpenAI-пути (text / reasoning / message с tool_calls в
OpenAI-форме), поэтому агент-луп остаётся общим.

Размышления Claude 5: thinking={"type":"adaptive"} + output_config={"effort": ...}.
Инструменты: OpenAI function → {name, description, input_schema}.
"""
from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Optional

import httpx

ANTHROPIC_VERSION = "2023-06-01"
MAX_TOKENS = 4096


def to_tools(openai_tools: Optional[list[dict]]) -> Optional[list[dict]]:
    if not openai_tools:
        return None
    out = []
    for t in openai_tools:
        fn = t.get("function", t)
        out.append({
            "name": fn["name"],
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters") or {"type": "object", "properties": {}},
        })
    return out


def to_messages(messages: list[dict]) -> tuple[str, list[dict]]:
    """OpenAI-chat messages → (system, anthropic_messages).

    role=system → в общий system-текст. role=tool → tool_result-блок в user-ходе
    (подряд идущие результаты группируются в один ход)."""
    system_parts: list[str] = []
    out: list[dict] = []
    for m in messages:
        role = m.get("role")
        if role == "system":
            if m.get("content"):
                system_parts.append(m["content"])
            continue
        if role == "tool":
            block = {"type": "tool_result", "tool_use_id": m.get("tool_call_id"),
                     "content": m.get("content") or ""}
            if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list) \
                    and out[-1]["content"] and out[-1]["content"][0].get("type") == "tool_result":
                out[-1]["content"].append(block)
            else:
                out.append({"role": "user", "content": [block]})
            continue
        if role == "user":
            out.append({"role": "user", "content": [{"type": "text", "text": m.get("content") or ""}]})
            continue
        if role == "assistant":
            blocks: list[dict] = []
            if m.get("content"):
                blocks.append({"type": "text", "text": m["content"]})
            for call in m.get("tool_calls") or []:
                fn = call.get("function", {})
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                blocks.append({"type": "tool_use", "id": call.get("id"),
                               "name": fn.get("name"), "input": args})
            if not blocks:
                blocks.append({"type": "text", "text": ""})
            out.append({"role": "assistant", "content": blocks})
    return "\n".join(system_parts), out


def build_body(*, model_name: str, messages: list[dict], tools: Optional[list[dict]],
               effort: Optional[str]) -> dict[str, Any]:
    system, anthro_messages = to_messages(messages)
    body: dict[str, Any] = {
        "model": model_name,
        "max_tokens": MAX_TOKENS,
        "stream": True,
        "messages": anthro_messages,
    }
    if system:
        body["system"] = system
    anthro_tools = to_tools(tools)
    if anthro_tools:
        body["tools"] = anthro_tools
    if effort and effort != "none":
        # Claude 5: адаптивное мышление с уровнем усилия.
        body["thinking"] = {"type": "adaptive"}
        body["output_config"] = {"effort": effort}
    return body


async def stream(*, base_url: str, api_key: str, headers_extra: dict, timeout: float,
                 model_name: str, messages: list[dict], tools: Optional[list[dict]],
                 effort: Optional[str]) -> AsyncGenerator[dict, None]:
    """Стрим Anthropic Messages → унифицированные события ассистента."""
    body = build_body(model_name=model_name, messages=messages, tools=tools, effort=effort)
    url = f"{base_url}/messages"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "anthropic-version": ANTHROPIC_VERSION,
        **headers_extra,
    }

    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    # index → {"id","name","args"} для tool_use блоков
    tool_slots: dict[int, dict] = {}
    stop_reason: Optional[str] = None
    usage: Optional[dict] = None

    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, headers=headers, json=body) as resp:
            if resp.status_code >= 400:
                text = (await resp.aread()).decode("utf-8", "replace")
                raise RuntimeError(f"Anthropic HTTP {resp.status_code}: {text[:400]}")
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if not data:
                    continue
                try:
                    ev = json.loads(data)
                except json.JSONDecodeError:
                    continue
                etype = ev.get("type")
                if etype == "content_block_start":
                    cb = ev.get("content_block", {})
                    if cb.get("type") == "tool_use":
                        tool_slots[ev.get("index", 0)] = {"id": cb.get("id"), "name": cb.get("name"), "args": ""}
                elif etype == "content_block_delta":
                    delta = ev.get("delta", {})
                    dt = delta.get("type")
                    if dt == "text_delta":
                        content_parts.append(delta.get("text", ""))
                        yield {"type": "text", "delta": delta.get("text", "")}
                    elif dt == "thinking_delta":
                        reasoning_parts.append(delta.get("thinking", ""))
                        yield {"type": "reasoning", "delta": delta.get("thinking", "")}
                    elif dt == "input_json_delta":
                        slot = tool_slots.get(ev.get("index", 0))
                        if slot is not None:
                            slot["args"] += delta.get("partial_json", "")
                elif etype == "message_delta":
                    stop_reason = ev.get("delta", {}).get("stop_reason") or stop_reason
                    if ev.get("usage"):
                        usage = ev["usage"]
                elif etype == "message_stop":
                    break
                elif etype == "error":
                    raise RuntimeError(f"Anthropic stream error: {str(ev.get('error'))[:300]}")

    message: dict[str, Any] = {"role": "assistant", "content": "".join(content_parts)}
    if tool_slots:
        message["tool_calls"] = [
            {"id": tool_slots[i]["id"], "type": "function",
             "function": {"name": tool_slots[i]["name"], "arguments": tool_slots[i]["args"] or "{}"}}
            for i in sorted(tool_slots)
        ]
    finish = "tool_calls" if (stop_reason == "tool_use" or tool_slots) else "stop"
    yield {"type": "message", "message": message, "finish_reason": finish,
           "usage": _map_usage(usage), "reasoning_text": "".join(reasoning_parts)}


def _map_usage(u: Optional[dict]) -> Optional[dict]:
    if not u:
        return None
    return {"prompt_tokens": u.get("input_tokens"), "completion_tokens": u.get("output_tokens")}
