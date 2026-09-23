"""Bounded, non-streaming OpenRouter calls for comments (no assistant quota/tools)."""
import os
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace

import httpx

from core.config import get_config


def comment_model() -> str:
    return os.getenv("AI_COMMENT_MODEL", "").strip() or get_config().openrouter.default_model


def require_comment_provider() -> None:
    if not get_config().openrouter.api_key:
        raise ValueError("OPENROUTER_API_KEY не настроен для AI-комментария")


async def create_comment(*, system: str, messages: list, max_tokens: int = 1100,
                         temperature: float = 0.35, json_output: bool = False):
    require_comment_provider()
    cfg = get_config().openrouter
    timeout = max(5, min(55, float(os.getenv("AI_API_TIMEOUT_SECONDS", "50"))))
    payload = {
        "model": comment_model(), "stream": False, "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "system", "content": system}, *messages],
        # Comments have a small output budget; don't spend it on hidden thinking.
        "reasoning": {"enabled": False},
    }
    if json_output:
        payload["response_format"] = {"type": "json_object"}
    # No automatic retry: a timeout does not prove the provider didn't charge.
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            cfg.base_url.rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {cfg.api_key}",
                     "HTTP-Referer": cfg.referer, "X-Title": cfg.title},
            json=payload,
        )
        if response.is_error:
            # Do not log provider bodies (they may echo private context).
            raise RuntimeError(f"OpenRouter comment request failed (HTTP {response.status_code})")
        data = response.json()
    if data.get("error") or not data.get("choices"):
        raise RuntimeError("OpenRouter comment response has no choices")
    choice = data["choices"][0]
    content = (choice.get("message") or {}).get("content")
    if content is not None and not isinstance(content, str):
        raise RuntimeError("OpenRouter comment response has invalid content")
    usage = data.get("usage") or {}
    details = usage.get("prompt_tokens_details") or {}
    # Provider cost is authoritative, including caching and routing. Never use
    # old Byesu per-token prices to estimate a new provider's cost.
    try:
        cost = Decimal(str(usage["cost"])) if usage.get("cost") is not None else None
    except InvalidOperation:
        cost = None
    if cost is not None and (not cost.is_finite() or cost < 0):
        cost = None
    return SimpleNamespace(
        content=[SimpleNamespace(text=content or "")],
        model=data.get("model") or comment_model(), cost_usd=cost,
        stop_reason="max_tokens" if choice.get("finish_reason") == "length" else choice.get("finish_reason"),
        usage=SimpleNamespace(input_tokens=usage.get("prompt_tokens", 0),
                              output_tokens=usage.get("completion_tokens", 0),
                              cache_creation_input_tokens=details.get("cache_write_tokens", 0),
                              cache_read_input_tokens=details.get("cached_tokens", 0)),
    )
