"""Bounded diagnostics: no customer exports and no provider secrets in responses."""

import asyncio
import os
from types import SimpleNamespace

import httpx
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core import models, security
from core.config import get_config
from core.database import get_db
from internal_admin.deps import require_superadmin
from internal_admin.security import AUDIENCE, decode_admin_token
from lead_validator.services.redis_service import redis_service


# One atomic reservation across replicas; counters contain UUIDs, never phone/email.
_RESERVE = """
local retry_after = 0
for i, key in ipairs(KEYS) do
    if tonumber(redis.call('GET', key) or '0') >= tonumber(ARGV[2*i-1]) then
        retry_after = math.max(retry_after, redis.call('TTL', key), 1)
    end
end
if retry_after > 0 then return -retry_after end
for i, key in ipairs(KEYS) do
    local count = redis.call('INCR', key)
    if count == 1 then redis.call('EXPIRE', key, ARGV[2*i]) end
end
return 1
"""


def diagnostic_user(
    user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Auth SELECT must not keep a SQL connection throughout provider IO."""
    identity = SimpleNamespace(id=user.id)
    db.rollback()
    return identity


def diagnostic_admin(
    request: Request,
    staff: models.User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    if not get_config().internal_admin.enabled:
        raise HTTPException(status_code=404, detail="Not found")
    # python-jose's audience option alone permits a token without an aud claim.
    payload = decode_admin_token(request.headers.get("authorization", "").split(" ", 1)[-1])
    if payload.get("aud") != AUDIENCE:
        raise HTTPException(status_code=401, detail="Admin authentication required")
    identity = SimpleNamespace(id=staff.id)
    db.rollback()
    return identity


async def reserve_check(user_id):
    """Paid checks fail closed when the shared limiter is unavailable."""
    async def reserve():
        client = await redis_service._get_client()
        if client is None:
            raise RuntimeError("Limiter unavailable")
        return await client.eval(
            _RESERVE, 3,
            f"lead:diagnostic:user:{user_id}:minute",
            f"lead:diagnostic:user:{user_id}:day",
            "lead:diagnostic:global:minute",
            10, 60, 100, 86400, 60, 60,
        )
    try:
        allowed = await asyncio.wait_for(reserve(), timeout=2.0)
    except Exception:
        raise HTTPException(status_code=503, detail="Проверка временно недоступна") from None
    if allowed != 1:
        raise HTTPException(status_code=429, detail="Лимит проверок исчерпан",
                            headers={"Retry-After": str(max(1, min(86400, -int(allowed))))})


async def provider_probe(provider: str) -> dict:
    """Read-only health probe. Never return upstream bodies, URLs or exceptions."""
    from lead_validator.services.telegram import telegram_notifier
    from lead_validator.services.metrica_service import metrica_service

    headers = {}
    if provider == "telegram":
        if not telegram_notifier.token:
            return {"ok": False, "error": "not_configured"}
        url = telegram_notifier._get_url("getMe")
    elif provider == "captcha":
        token, folder = os.getenv("YANDEX_IAM_TOKEN"), os.getenv("YANDEX_FOLDER_ID")
        if not token or not folder:
            return {"ok": False, "error": "not_configured"}
        url = "https://smartcaptcha.api.cloud.yandex.net/smartcaptcha/v1/captchas"
        headers = {"Authorization": f"Bearer {token}"}
    elif provider == "metrica":
        if not metrica_service.enabled or not metrica_service.counter_id or not metrica_service.oauth_token:
            return {"ok": False, "error": "not_configured"}
        url = f"{metrica_service.base_url}/counter/{metrica_service.counter_id}"
        headers = {"Authorization": f"OAuth {metrica_service.oauth_token}"}
    else:
        raise ValueError("Unknown diagnostic provider")
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            response = await client.get(url, headers=headers,
                params={"folderId": folder} if provider == "captcha" else None)
            if response.status_code != 200:
                return {"ok": False, "error": "provider_rejected", "status_code": response.status_code}
            body = response.json()
            if not isinstance(body, dict):
                return {"ok": False, "error": "invalid_response"}
            if provider == "telegram":
                return {"ok": body.get("ok") is True, "test_message_sent": False}
            if provider == "captcha":
                resources = body.get("resources")
                return ({"ok": True, "captchas_count": len(resources)} if isinstance(resources, list)
                        else {"ok": False, "error": "invalid_response"})
            return {"ok": isinstance(body.get("counter"), dict)}
    except Exception:
        return {"ok": False, "error": "provider_unavailable"}
