import base64
import hashlib
import hmac
import logging
import os
from typing import Any, Dict

import httpx

from core.config import get_config

logger = logging.getLogger(__name__)


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
            body = resp.json()
            # CP всегда отвечает HTTP 200, ошибка — в Success:false: без этой проверки
            # неудачная отмена проходила молча и рекуррент продолжал списывать.
            if not body.get("Success"):
                raise RuntimeError(f"CloudPayments cancel failed: {body.get('Message') or body}")
            return body

    @staticmethod
    async def update_subscription(subscription_id: str, **changes: Any) -> Dict[str, Any]:
        """Обновляет сумму/чек будущих рекуррентных списаний.

        CloudPayments официально поддерживает ``subscriptions/update``. Всегда
        проверяем ``Success``: HTTP 200 у API может содержать бизнес-ошибку.
        """
        payload: Dict[str, Any] = {"Id": subscription_id}
        payload.update({key: value for key, value in changes.items() if value is not None})
        headers = {
            "Authorization": CloudPaymentsService._auth_header(),
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{CloudPaymentsService.BASE_URL}/subscriptions/update",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            body = resp.json()
            if not body.get("Success"):
                raise RuntimeError(f"CloudPayments update failed: {body.get('Message') or body}")
            return body

    @staticmethod
    async def find_subscriptions(account_id: str) -> list:
        """Все подписки аккаунта в CP (для отмены рекуррента, когда Id ещё не сохранён у нас)."""
        headers = {
            "Authorization": CloudPaymentsService._auth_header(),
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{CloudPaymentsService.BASE_URL}/subscriptions/find",
                json={"accountId": account_id},
                headers=headers,
            )
            resp.raise_for_status()
            body = resp.json()
            return body.get("Model") or []

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
            # Fail-closed. Раньше здесь стоял `return True`, и стоило секрету
            # пропасть из окружения — вебхук начинал принимать что угодно от кого
            # угодно, то есть выдача тарифа становилась публичным эндпоинтом.
            # Для локальной разработки без секрета есть явный опт-аут.
            if os.getenv("CLOUDPAYMENTS_ALLOW_UNSIGNED_WEBHOOKS", "").strip().lower() in ("1", "true", "yes"):
                logger.warning(
                    "CloudPayments webhook signature check DISABLED "
                    "(CLOUDPAYMENTS_ALLOW_UNSIGNED_WEBHOOKS) — так нельзя в проде"
                )
                return True
            logger.error(
                "CloudPayments webhook rejected: секрет не настроен "
                "(CLOUDPAYMENTS_WEBHOOK_SECRET / CLOUDPAYMENTS_API_SECRET)"
            )
            return False
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

