#!/usr/bin/env python3
"""
Проверка интеграции CloudPayments без реальной оплаты.

1) api-test — GET https://api.cloudpayments.ru/test (Basic: Public ID + API Secret).
2) webhook-send — POST тестового уведомления на ваш /api/billing/cloudpayments/webhook
   с подписью Content-HMAC (HMAC-SHA256 + base64), как в доке CP.

Запуск из каталога trafic_agent:
  python -m scripts.test_cloudpayments api-test
  python -m scripts.test_cloudpayments webhook-send --account-id <UUID пользователя>

Переменные .env: CLOUDPAYMENTS_PUBLIC_ID, CLOUDPAYMENTS_API_SECRET,
опционально CLOUDPAYMENTS_WEBHOOK_SECRET (для подписи; иначе берётся API Secret).
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

from core.config import get_config


def _webhook_signing_secret() -> str:
    cfg = get_config().cloudpayments
    return (cfg.webhook_secret or cfg.api_secret or "").strip()


def content_hmac(raw_body: bytes, secret: str) -> str:
    """Подпись уведомления CP: base64(HMAC-SHA256(body, secret))."""
    return base64.b64encode(
        hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    ).decode("ascii")


def cmd_api_test() -> None:
    cfg = get_config()
    if not cfg.cloudpayments.public_id or not cfg.cloudpayments.api_secret:
        print("Укажите CLOUDPAYMENTS_PUBLIC_ID и CLOUDPAYMENTS_API_SECRET в .env")
        sys.exit(1)
    token = base64.b64encode(
        f"{cfg.cloudpayments.public_id}:{cfg.cloudpayments.api_secret}".encode("utf-8")
    ).decode("ascii")
    url = "https://api.cloudpayments.ru/test"
    r = httpx.get(url, headers={"Authorization": f"Basic {token}"}, timeout=30.0)
    print(f"HTTP {r.status_code}")
    print(r.text)
    if r.status_code != 200:
        sys.exit(1)


def cmd_webhook_send(args: argparse.Namespace) -> None:
    get_config()
    secret = _webhook_signing_secret()
    payload: dict = {
        "TransactionId": int(args.transaction_id),
        "AccountId": str(args.account_id).strip(),
        "Success": True,
        "JsonData": {"plan_code": args.plan},
    }
    if args.subscription_id:
        payload["SubscriptionId"] = str(args.subscription_id)

    if args.event == "pay":
        payload["Type"] = "Pay"
        payload["Success"] = True
    elif args.event == "fail":
        payload["Type"] = "Fail"
        payload["Success"] = False
    elif args.event == "recurrent":
        payload["Type"] = "Recurrent"
        payload["Success"] = True
    elif args.event == "cancel":
        payload["Type"] = "Cancel"
        payload["Success"] = True
    else:
        payload["Type"] = ""
        payload["Success"] = True

    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}

    if args.no_sign and args.sign:
        print("Укажите только один из флагов: --sign или --no-sign")
        sys.exit(2)
    if args.no_sign:
        need_sign = False
    elif args.sign:
        need_sign = True
    else:
        need_sign = bool(secret)

    if need_sign:
        if not secret:
            print(
                "Для подписи нужен CLOUDPAYMENTS_WEBHOOK_SECRET или CLOUDPAYMENTS_API_SECRET в .env"
            )
            sys.exit(1)
        headers["Content-HMAC"] = content_hmac(body, secret)

    r = httpx.post(args.url.rstrip("/"), content=body, headers=headers, timeout=30.0)
    print(f"HTTP {r.status_code}")
    print(r.text)
    if r.status_code not in (200, 201):
        sys.exit(1)


def cmd_sign_demo(args: argparse.Namespace) -> None:
    """Локально: показать Content-HMAC для строки тела (как у CP)."""
    get_config()
    secret = _webhook_signing_secret()
    if not secret:
        print("Нужен CLOUDPAYMENTS_WEBHOOK_SECRET или CLOUDPAYMENTS_API_SECRET")
        sys.exit(1)
    raw = args.body.encode("utf-8")
    print(content_hmac(raw, secret))


def main() -> None:
    parser = argparse.ArgumentParser(description="Тесты CloudPayments")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_test = sub.add_parser("api-test", help="GET /test к API CloudPayments")
    p_test.set_defaults(func=lambda _: cmd_api_test())

    p_wh = sub.add_parser("webhook-send", help="POST тестового webhook на бэкенд")
    p_wh.add_argument(
        "--url",
        default="http://127.0.0.1:8000/api/billing/cloudpayments/webhook",
        help="Полный URL эндпоинта webhook",
    )
    p_wh.add_argument(
        "--account-id",
        required=True,
        help="UUID пользователя (AccountId в CP = id в БД)",
    )
    p_wh.add_argument(
        "--plan",
        default="start",
        choices=["start", "basic", "standard"],
        help="plan_code в JsonData",
    )
    p_wh.add_argument(
        "--event",
        default="pay",
        choices=["pay", "fail", "recurrent", "cancel", "minimal"],
        help="Тип уведомления (minimal — пустой Type, как часть сценариев)",
    )
    p_wh.add_argument("--transaction-id", default="999999001", help="TransactionId в JSON")
    p_wh.add_argument("--subscription-id", default="", help="SubscriptionId (опционально)")
    p_wh.add_argument(
        "--sign",
        action="store_true",
        help="Обязательно отправить Content-HMAC (нужен секрет в .env)",
    )
    p_wh.add_argument(
        "--no-sign",
        action="store_true",
        help="Не отправлять подпись (для dev, если проверка отключена)",
    )

    p_wh.set_defaults(func=cmd_webhook_send)

    p_sig = sub.add_parser("sign-demo", help="Вывести Content-HMAC для произвольного UTF-8 тела")
    p_sig.add_argument("body", help='Строка тела, например \'{"AccountId":"..."}\'')
    p_sig.set_defaults(func=cmd_sign_demo)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
