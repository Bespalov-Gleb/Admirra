import base64
import hashlib
import hmac
from typing import Any, Dict

import httpx

from core.config import get_config


class CloudPaymentsService:
    BASE_URL = "https://api.cloudpayments.ru"

    @staticmethod
    def _auth_header() -> str:
        cfg = get_config().cloudpayments
        pair = f"{cfg.public_id}:{cfg.api_secret}".encode("utf-8")
        return "Basic " + base64.b64encode(pair).decode("utf-8")

    @staticmethod
    async def create_subscription(payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = {
            "Authorization": CloudPaymentsService._auth_header(),
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{CloudPaymentsService.BASE_URL}/subscriptions/create",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    async def cancel_subscription(subscription_id: str) -> Dict[str, Any]:
        headers = {
            "Authorization": CloudPaymentsService._auth_header(),
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{CloudPaymentsService.BASE_URL}/subscriptions/cancel",
                json={"Id": subscription_id},
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def validate_webhook_signature(raw_body: bytes, signature: str | None) -> bool:
        """
        См. https://developers.cloudpayments.ru/#proverka-uvedomleniy :
        HMAC-SHA256 от тела POST (UTF-8), ключ — API Secret; значение в заголовке в base64.
        CLOUDPAYMENTS_WEBHOOK_SECRET если задан — используется как ключ; иначе CLOUDPAYMENTS_API_SECRET.
        """
        cfg = get_config().cloudpayments
        secret = (cfg.webhook_secret or cfg.api_secret or "").strip()
        if not secret:
            return True
        if not signature:
            return False
        sig_clean = signature.strip()
        expected_b64 = base64.b64encode(
            hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
        ).decode("ascii")
        if hmac.compare_digest(expected_b64, sig_clean):
            return True
        # Обратная совместимость: если в заголовке случайно передали hex
        expected_hex = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_hex.lower(), sig_clean.lower())

