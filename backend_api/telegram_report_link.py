"""
Привязка Telegram для отчётов: deep link https://t.me/<bot>?start=<token> + webhook.

Настройка webhook (пример):
  curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \\
    -H "Content-Type: application/json" \\
    -d '{"url":"https://<ваш-api>/api/telegram/webhook","secret_token":"<TELEGRAM_WEBHOOK_SECRET>"}'
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core import models, schemas, security
from core.config import get_config
from core.database import get_db

logger = logging.getLogger(__name__)

cfg = get_config()

link_router = APIRouter(prefix="/auth/telegram", tags=["Telegram reports"])
webhook_router = APIRouter(prefix="/telegram", tags=["Telegram webhook"])

LINK_TTL_MINUTES = 15
_cached_bot_username: str | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _resolve_bot_username() -> str:
    global _cached_bot_username
    u = (cfg.telegram_bot.bot_username or "").strip().lstrip("@")
    if u:
        return u
    if _cached_bot_username:
        return _cached_bot_username
    token = (cfg.telegram_bot.bot_token or "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Telegram-бот не настроен (TELEGRAM_BOT_TOKEN)")
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"https://api.telegram.org/bot{token}/getMe")
        data = r.json()
        if not data.get("ok"):
            logger.error("getMe failed: %s", data)
            raise HTTPException(status_code=503, detail="Не удалось получить имя бота из Telegram")
        un = (data.get("result") or {}).get("username") or ""
        if not un:
            raise HTTPException(status_code=503, detail="У бота нет username — укажите TELEGRAM_BOT_USERNAME в .env")
        _cached_bot_username = un
        return un


def _verify_webhook_secret(request: Request) -> None:
    secret = (cfg.telegram_bot.webhook_secret or "").strip()
    if not secret:
        logger.warning("TELEGRAM_WEBHOOK_SECRET пуст — проверка webhook отключена (только для разработки)")
        return
    header = request.headers.get("X-Telegram-Bot-Api-Secret-Token") or ""
    if header != secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")


async def _tg_api(method: str, json_body: dict | None = None) -> dict:
    token = (cfg.telegram_bot.bot_token or "").strip()
    if not token:
        return {"ok": False}
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(
            f"https://api.telegram.org/bot{token}/{method}",
            json=json_body or {},
        )
        try:
            return r.json()
        except Exception:
            return {"ok": False, "description": r.text}


@link_router.post("/link", response_model=schemas.TelegramDeepLinkResponse)
async def create_telegram_link(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    Выдаёт ссылку вида https://t.me/BotName?start=TOKEN — открывает диалог с ботом.
    Параметр start до 64 символов (ограничение Telegram).
    """
    token = (cfg.telegram_bot.bot_token or "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Отправка в Telegram не настроена на сервере")

    username = await _resolve_bot_username()
    raw = secrets.token_urlsafe(32)[:64]

    exp = _now() + timedelta(minutes=LINK_TTL_MINUTES)
    db.query(models.TelegramLinkToken).filter(
        models.TelegramLinkToken.user_id == current_user.id,
        models.TelegramLinkToken.consumed_at.is_(None),
        models.TelegramLinkToken.expires_at > _now(),
    ).delete(synchronize_session=False)

    row = models.TelegramLinkToken(
        user_id=current_user.id,
        token=raw,
        expires_at=exp,
    )
    db.add(row)
    db.commit()

    deep_link = f"https://t.me/{username}?start={raw}"
    return schemas.TelegramDeepLinkResponse(
        deep_link=deep_link,
        expires_in_seconds=LINK_TTL_MINUTES * 60,
    )


@webhook_router.post("/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    _verify_webhook_secret(request)
    body = await request.json()

    message = body.get("message") or body.get("edited_message")
    if not message or "chat" not in message:
        return {"ok": True}

    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()
    if chat_id is None or not text.startswith("/start"):
        return {"ok": True}

    parts = text.split(maxsplit=1)
    payload = parts[1].strip() if len(parts) > 1 else ""
    if not payload:
        await _tg_api(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": "Откройте ссылку из личного кабинета AdMirra, чтобы привязать этот чат для отчётов.",
            },
        )
        return {"ok": True}

    if len(payload) > 64:
        return {"ok": True}

    row = (
        db.query(models.TelegramLinkToken)
        .filter(
            models.TelegramLinkToken.token == payload,
            models.TelegramLinkToken.consumed_at.is_(None),
            models.TelegramLinkToken.expires_at > _now(),
        )
        .first()
    )
    if not row:
        await _tg_api(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": "Ссылка устарела или уже использована. Запросите новую в личном кабинете.",
            },
        )
        return {"ok": True}

    user = db.query(models.User).filter(models.User.id == row.user_id).first()
    if not user:
        return {"ok": True}

    user.report_telegram_chat_id = str(chat_id)
    row.consumed_at = _now()
    db.add(user)
    db.add(row)
    db.commit()

    await _tg_api(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": "✅ Чат привязан. Отчёты из AdMirra будут приходить сюда. Можете вернуться в браузер и отправить отчёт.",
        },
    )
    logger.info("Telegram chat %s linked to user %s", chat_id, user.id)
    return {"ok": True}
