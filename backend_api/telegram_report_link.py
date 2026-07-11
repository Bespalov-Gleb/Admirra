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
import json
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


def _tg_api_base() -> str:
    """База Telegram Bot API. api.telegram.org блокируется с части РФ-хостингов —
    TELEGRAM_API_BASE позволяет ходить через свой прокси (например, старый сервер)."""
    import os
    return (os.getenv("TELEGRAM_API_BASE") or "https://api.telegram.org").rstrip("/")


def _tg_api_verify() -> bool:
    import os
    return (os.getenv("TELEGRAM_API_VERIFY") or "true").strip().lower() not in ("false", "0", "no")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _attach_target_to_project_schedule(db: Session, token_row, target: models.ReportChatTarget) -> None:
    if not getattr(token_row, "client_id", None) and not getattr(token_row, "folder_id", None):
        return
    target.client_id = getattr(token_row, "client_id", None)
    target.folder_id = getattr(token_row, "folder_id", None)
    target.target_type = getattr(token_row, "target_type", None) or "group"
    q = db.query(models.ReportSchedule).filter(models.ReportSchedule.user_id == token_row.user_id)
    if token_row.folder_id:
        q = q.filter(models.ReportSchedule.scope_folder_id == token_row.folder_id)
    else:
        q = q.filter(models.ReportSchedule.scope_client_id == token_row.client_id)
    schedule = q.order_by(models.ReportSchedule.created_at.desc()).first()
    if not schedule:
        schedule = models.ReportSchedule(
            user_id=token_row.user_id,
            scope_client_id=token_row.client_id,
            scope_folder_id=token_row.folder_id,
            enabled=False,
            platform="all",
        )
        db.add(schedule)
    try:
        targets = json.loads(schedule.chat_targets) if schedule.chat_targets else []
    except Exception:
        targets = []
    target_id = str(target.id)
    if target_id not in [str(item) for item in targets]:
        targets.append(target_id)
    schedule.chat_targets = json.dumps(targets)


def _notify_target_linked(db: Session, token_row, target: models.ReportChatTarget) -> None:
    from backend_api.services.notifications import create_notification
    create_notification(
        db, token_row.user_id, "report_recipient_linked",
        "Получатель отчётов подключён",
        body=f"{target.title or 'Telegram-чат'} добавлен к выбранному проекту.",
        meta={
            "client_id": str(token_row.client_id) if token_row.client_id else None,
            "folder_id": str(token_row.folder_id) if token_row.folder_id else None,
            "target_id": str(target.id),
        },
    )


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
    async with httpx.AsyncClient(timeout=15.0, verify=_tg_api_verify()) as client:
        r = await client.get(f"{_tg_api_base()}/bot{token}/getMe")
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
    async with httpx.AsyncClient(timeout=15.0, verify=_tg_api_verify()) as client:
        r = await client.post(
            f"{_tg_api_base()}/bot{token}/{method}",
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
        models.TelegramLinkToken.target_type.is_(None),
        models.TelegramLinkToken.client_id.is_(None),
        models.TelegramLinkToken.folder_id.is_(None),
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
    if chat_id is None:
        return {"ok": True}

    # /link <код> в ГРУППЕ — подключение группового чата для отчётов
    # (бота добавляют в группу СММ-команды и отправляют там код из модалки автоотправки)
    if text.startswith("/link"):
        link_parts = text.split(maxsplit=1)
        # поддерживаем и «/link@BotName код»
        code = link_parts[1].strip() if len(link_parts) > 1 else ""
        if not code or len(code) > 64:
            await _tg_api("sendMessage", {
                "chat_id": chat_id,
                "text": "Отправьте команду в формате: /link КОД (код — в настройках автоотправки AdMirra).",
            })
            return {"ok": True}
        row = (
            db.query(models.TelegramLinkToken)
            .filter(
                models.TelegramLinkToken.token == code,
                models.TelegramLinkToken.consumed_at.is_(None),
                models.TelegramLinkToken.expires_at > _now(),
            )
            .first()
        )
        if not row:
            await _tg_api("sendMessage", {
                "chat_id": chat_id,
                "text": "Код устарел или уже использован. Сгенерируйте новый в настройках автоотправки.",
            })
            return {"ok": True}
        title = chat.get("title") or chat.get("username") or f"Чат {chat_id}"
        if getattr(row, "target_type", None) not in (None, "group"):
            await _tg_api("sendMessage", {"chat_id": chat_id, "text": "Эта ссылка предназначена для личного чата клиента."})
            return {"ok": True}
        existing = (
            db.query(models.ReportChatTarget)
            .filter(
                models.ReportChatTarget.user_id == row.user_id,
                models.ReportChatTarget.kind == "telegram",
                models.ReportChatTarget.chat_id == str(chat_id),
                models.ReportChatTarget.client_id == row.client_id,
                models.ReportChatTarget.folder_id == row.folder_id,
                models.ReportChatTarget.target_type == "group",
            )
            .first()
        )
        target = existing
        if not target:
            target = models.ReportChatTarget(
                user_id=row.user_id, client_id=row.client_id, folder_id=row.folder_id,
                target_type="group", kind="telegram", chat_id=str(chat_id), title=str(title)[:120],
            )
            db.add(target)
            db.flush()
        _attach_target_to_project_schedule(db, row, target)
        _notify_target_linked(db, row, target)
        row.consumed_at = _now()
        db.commit()
        await _tg_api("sendMessage", {
            "chat_id": chat_id,
            "text": f"✅ Группа «{title}» подключена: отчёты AdMirra по выбранным правилам будут приходить сюда.",
        })
        logger.info("Telegram GROUP %s linked to user %s", chat_id, row.user_id)
        return {"ok": True}

    if not text.startswith("/start"):
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

    # /start в группе (deep-link «добавить бота в группу» ?startgroup=КОД) —
    # это подключение ГРУППЫ, а не личного чата
    if str(chat.get("type") or "") in ("group", "supergroup"):
        if getattr(row, "target_type", None) == "client":
            await _tg_api("sendMessage", {"chat_id": chat_id, "text": "Эта ссылка предназначена для личного чата клиента."})
            return {"ok": True}
        title = chat.get("title") or f"Чат {chat_id}"
        exists = (
            db.query(models.ReportChatTarget)
            .filter(
                models.ReportChatTarget.user_id == row.user_id,
                models.ReportChatTarget.kind == "telegram",
                models.ReportChatTarget.chat_id == str(chat_id),
                models.ReportChatTarget.client_id == row.client_id,
                models.ReportChatTarget.folder_id == row.folder_id,
                models.ReportChatTarget.target_type == "group",
            )
            .first()
        )
        target = exists
        if not target:
            target = models.ReportChatTarget(
                user_id=row.user_id, client_id=row.client_id, folder_id=row.folder_id,
                target_type="group", kind="telegram", chat_id=str(chat_id), title=str(title)[:120],
            )
            db.add(target)
            db.flush()
        _attach_target_to_project_schedule(db, row, target)
        _notify_target_linked(db, row, target)
        row.consumed_at = _now()
        db.commit()
        await _tg_api("sendMessage", {
            "chat_id": chat_id,
            "text": f"✅ Группа «{title}» подключена: отчёты AdMirra будут приходить сюда по выбранным правилам.",
        })
        logger.info("Telegram GROUP %s linked (startgroup) to user %s", chat_id, row.user_id)
        return {"ok": True}

    if getattr(row, "target_type", None) == "client" and (row.client_id or row.folder_id):
        sender = message.get("from") or {}
        title = sender.get("username") or " ".join(
            part for part in [sender.get("first_name"), sender.get("last_name")] if part
        ) or f"Клиент {chat_id}"
        target = db.query(models.ReportChatTarget).filter(
            models.ReportChatTarget.user_id == row.user_id,
            models.ReportChatTarget.kind == "telegram",
            models.ReportChatTarget.chat_id == str(chat_id),
            models.ReportChatTarget.client_id == row.client_id,
            models.ReportChatTarget.folder_id == row.folder_id,
            models.ReportChatTarget.target_type == "client",
        ).first()
        if not target:
            target = models.ReportChatTarget(
                user_id=row.user_id, client_id=row.client_id, folder_id=row.folder_id,
                target_type="client", kind="telegram", chat_id=str(chat_id), title=str(title)[:120],
            )
            db.add(target)
            db.flush()
        _attach_target_to_project_schedule(db, row, target)
        _notify_target_linked(db, row, target)
        row.consumed_at = _now()
        db.commit()
        await _tg_api("sendMessage", {"chat_id": chat_id, "text": "✅ Чат подключён к отчётам выбранного проекта AdMirra."})
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
