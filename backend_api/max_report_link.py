"""
Привязка отдельного MAX-бота для отчётов.

Auth MAX bot и reports MAX bot намеренно разделены:
вход в аккаунт не определяет, куда отправлять отчёты.
"""
from __future__ import annotations

import hmac
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend_api.services import max_reports_bot
from core import models, schemas, security
from core.config import get_config
from core.database import get_db


logger = logging.getLogger(__name__)
cfg = get_config()

LINK_TTL_MINUTES = 15
MAX_REPORTS_WEBHOOK_SECRET = (cfg.oauth.max_reports_webhook_secret or "").strip()

link_router = APIRouter(prefix="/auth/max-reports", tags=["MAX reports"])
webhook_router = APIRouter(prefix="/max-reports", tags=["MAX reports webhook"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _attach_target_to_project_schedule(db: Session, token_row, target: models.ReportChatTarget) -> None:
    if not getattr(token_row, "client_id", None) and not getattr(token_row, "folder_id", None):
        return
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


@link_router.post("/link", response_model=schemas.TelegramDeepLinkResponse)
async def create_max_reports_link(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    if not max_reports_bot.is_configured():
        raise HTTPException(status_code=503, detail="MAX-бот для отчётов не настроен на сервере")

    bot_name = await max_reports_bot.resolve_bot_name()
    raw = secrets.token_urlsafe(32)[:64]
    exp = _now() + timedelta(minutes=LINK_TTL_MINUTES)

    db.query(models.MaxReportLinkToken).filter(
        models.MaxReportLinkToken.user_id == current_user.id,
        models.MaxReportLinkToken.consumed_at.is_(None),
        models.MaxReportLinkToken.expires_at > _now(),
    ).delete(synchronize_session=False)

    row = models.MaxReportLinkToken(
        user_id=current_user.id,
        token=raw,
        expires_at=exp,
    )
    db.add(row)
    db.commit()

    return schemas.TelegramDeepLinkResponse(
        deep_link=f"https://max.ru/{bot_name}?start={raw}",
        expires_in_seconds=LINK_TTL_MINUTES * 60,
    )


@webhook_router.post("/webhook")
async def max_reports_webhook(request: Request, db: Session = Depends(get_db)):
    if not MAX_REPORTS_WEBHOOK_SECRET:
        logger.error("MAX_REPORTS_WEBHOOK_SECRET is empty; rejecting webhook")
        raise HTTPException(status_code=503, detail="MAX reports webhook secret is not configured")

    header = request.headers.get("X-Max-Bot-Api-Secret") or ""
    if not hmac.compare_digest(header, MAX_REPORTS_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid MAX reports webhook secret")

    body = await request.json()

    # /link <код> в чате/группе MAX — подключение группового чата для отчётов
    if body.get("update_type") == "message_created":
        msg = body.get("message") or {}
        msg_body = msg.get("body") or {}
        text = str(msg_body.get("text") or "").strip()
        recipient = msg.get("recipient") or {}
        group_chat_id = str(recipient.get("chat_id") or "").strip()
        if text.startswith("/link") and group_chat_id:
            code = text.split(maxsplit=1)[1].strip() if len(text.split(maxsplit=1)) > 1 else ""
            if code and len(code) <= 64:
                row = (
                    db.query(models.MaxReportLinkToken)
                    .filter(
                        models.MaxReportLinkToken.token == code,
                        models.MaxReportLinkToken.consumed_at.is_(None),
                        models.MaxReportLinkToken.expires_at > _now(),
                    )
                    .first()
                )
                if row:
                    chat_title = str((msg.get("recipient") or {}).get("chat_title") or "Чат MAX")[:120]
                    existing = (
                        db.query(models.ReportChatTarget)
                        .filter(
                            models.ReportChatTarget.user_id == row.user_id,
                            models.ReportChatTarget.kind == "max",
                            models.ReportChatTarget.chat_id == group_chat_id,
                        )
                        .first()
                    )
                    target = existing
                    if not target:
                        target = models.ReportChatTarget(
                            user_id=row.user_id, kind="max", chat_id=group_chat_id, title=chat_title,
                        )
                        db.add(target)
                        db.flush()
                    _attach_target_to_project_schedule(db, row, target)
                    row.consumed_at = _now()
                    db.commit()
                    await max_reports_bot.send_message(
                        "✅ Чат подключён: отчёты AdMirra по выбранным правилам будут приходить сюда.",
                        chat_id=group_chat_id,
                    )
                    logger.info("MAX GROUP %s linked to user %s", group_chat_id, row.user_id)
                else:
                    await max_reports_bot.send_message(
                        "Код устарел или уже использован. Сгенерируйте новый в настройках автоотправки AdMirra.",
                        chat_id=group_chat_id,
                    )
        return {"ok": True}

    if body.get("update_type") != "bot_started":
        return {"ok": True}

    payload = str(body.get("payload") or "").strip()
    user_info = body.get("user") if isinstance(body.get("user"), dict) else {}
    max_uid = str(user_info.get("user_id") or "").strip()
    chat_id = str(body.get("chat_id") or "").strip() or None
    username = (user_info.get("username") or "").strip() or None

    if not payload or not max_uid:
        return {"ok": True}

    row = (
        db.query(models.MaxReportLinkToken)
        .filter(
            models.MaxReportLinkToken.token == payload,
            models.MaxReportLinkToken.consumed_at.is_(None),
            models.MaxReportLinkToken.expires_at > _now(),
        )
        .first()
    )
    if not row:
        await max_reports_bot.send_message(
            "Ссылка устарела или уже использована. Запросите новую в личном кабинете AdMirra.",
            chat_id=chat_id,
            user_id=max_uid,
        )
        return {"ok": True}

    user = db.query(models.User).filter(models.User.id == row.user_id).first()
    if not user:
        return {"ok": True}

    user.report_max_chat_id = chat_id
    user.report_max_user_id = max_uid
    user.report_max_username = username
    row.consumed_at = _now()
    db.add(user)
    db.add(row)
    db.commit()

    await max_reports_bot.send_message(
        "MAX привязан. Отчёты из AdMirra будут приходить сюда. Можете вернуться в браузер и отправить отчёт.",
        chat_id=chat_id,
        user_id=max_uid,
    )
    logger.info("MAX reports chat %s linked to user %s", chat_id or max_uid, user.id)
    return {"ok": True}
