"""
Обращения с формы «Предложить идея» — письмо на SUPPORT_INBOX_EMAIL (SMTP как у auth).
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from backend_api.services.auth_mail import send_support_idea_email, smtp_delivery_active
from core.config import get_config

logger = logging.getLogger("api.support")

router = APIRouter(prefix="/support", tags=["Support"])


class SupportIdeaIn(BaseModel):
    subject: str = Field(..., min_length=1, max_length=500)
    message: str = Field(..., min_length=1, max_length=20000)
    email: EmailStr


@router.post("/idea")
async def submit_idea(payload: SupportIdeaIn):
    cfg = get_config()
    inbox = (cfg.support.inbox_email or "").strip()
    if not inbox:
        raise HTTPException(
            status_code=503,
            detail="Адрес приёма обращений не настроен (SUPPORT_INBOX_EMAIL).",
        )
    if not smtp_delivery_active():
        raise HTTPException(
            status_code=503,
            detail="Отправка писем отключена или SMTP не настроен (SMTP_ENABLED, SMTP_HOST, SMTP_FROM).",
        )

    ok = await send_support_idea_email(
        inbox_to=inbox,
        subject=payload.subject.strip(),
        message=payload.message.strip(),
        sender_email=str(payload.email).strip(),
    )
    if not ok:
        logger.error("support/idea: send_support_idea_email returned false")
        raise HTTPException(
            status_code=502,
            detail="Не удалось отправить письмо. Проверьте SMTP и попробуйте позже.",
        )

    return {"ok": True, "message": "Идея отправлена"}
