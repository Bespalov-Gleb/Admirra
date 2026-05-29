"""
Обращения с формы «Предложить идею» — письмо на SUPPORT_INBOX_EMAIL (SMTP как у auth).
"""

import logging
import re
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Form, UploadFile, File

from backend_api.services.auth_mail import send_support_idea_email, smtp_delivery_active
from core.config import get_config

logger = logging.getLogger("api.support")

router = APIRouter(prefix="/support", tags=["Support"])

_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')

MAX_ATTACHMENT_FILES = 5
MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024  # 5 MB per file


@router.post("/idea")
async def submit_idea(
    subject: str = Form(..., min_length=1, max_length=500),
    message: str = Form(..., min_length=1, max_length=20000),
    email: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
):
    if not _EMAIL_RE.match(email.strip()):
        raise HTTPException(status_code=422, detail="Некорректный формат email.")

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

    # Read and validate attachments
    attachments = []
    if files:
        real_files = [f for f in files if f and f.filename]
        if len(real_files) > MAX_ATTACHMENT_FILES:
            raise HTTPException(
                status_code=400,
                detail=f"Максимум {MAX_ATTACHMENT_FILES} файлов.",
            )
        for f in real_files:
            content = await f.read()
            if len(content) > MAX_ATTACHMENT_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"Файл «{f.filename}» превышает 5 МБ.",
                )
            ct = f.content_type or "application/octet-stream"
            attachments.append((f.filename, ct, content))

    ok = await send_support_idea_email(
        inbox_to=inbox,
        subject=subject.strip(),
        message=message.strip(),
        sender_email=email.strip(),
        attachments=attachments,
    )
    if not ok:
        logger.error("support/idea: send_support_idea_email returned false")
        raise HTTPException(
            status_code=502,
            detail="Не удалось отправить письмо. Проверьте SMTP и попробуйте позже.",
        )

    return {"ok": True, "message": "Идея отправлена"}
