"""
Отправка транзакционных email через UniSender Go API.
Используется для отправки отчётов (PDF-вложение + HTML тело).
Fallback на SMTP если UniSender не настроен.
"""

import asyncio
import base64
import logging
from typing import Optional

import httpx

from core.config import get_config

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    cfg = get_config()
    return bool(cfg.unisender.api_key)


def _send_sync(
    recipients: list[str],
    subject: str,
    html_body: str,
    plain_body: str = "",
    pdf_bytes: Optional[bytes] = None,
    filename: str = "report.pdf",
) -> tuple[bool, Optional[str]]:
    cfg = get_config()
    api_key = cfg.unisender.api_key
    if not api_key:
        return False, "UNISENDER_API_KEY не настроен"

    message: dict = {
        "recipients": [{"email": email} for email in recipients],
        "body": {
            "html": html_body,
            "plaintext": plain_body or subject,
        },
        "subject": subject,
        "from_email": cfg.unisender.from_email,
        "from_name": cfg.unisender.from_name,
    }

    if pdf_bytes:
        encoded = base64.b64encode(pdf_bytes).decode("ascii")
        message["attachments"] = [
            {
                "type": "application/pdf",
                "name": filename,
                "content": encoded,
            }
        ]

    url = f"{cfg.unisender.api_url.rstrip('/')}/email/send.json"

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            url,
            json={"message": message},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-API-KEY": api_key,
            },
        )

    if response.status_code == 200:
        data = response.json()
        status = data.get("status")
        if status == "success":
            job_id = data.get("job_id", "")
            logger.info("UniSender email sent: job_id=%s, to=%s", job_id, recipients)
            return True, None
        else:
            err = data.get("message") or data.get("code") or str(data)
            logger.warning("UniSender send returned status=%s: %s", status, err)
            return False, f"UniSender: {err}"
    else:
        try:
            data = response.json()
            err = data.get("message") or data.get("code") or str(data)
        except Exception:
            err = response.text[:300]
        logger.error("UniSender HTTP %s: %s", response.status_code, err)
        return False, f"UniSender HTTP {response.status_code}: {err}"


async def send_report_email(
    recipients: list[str],
    subject: str,
    html_body: str,
    plain_body: str = "",
    pdf_bytes: Optional[bytes] = None,
    filename: str = "report.pdf",
) -> tuple[bool, Optional[str]]:
    try:
        return await asyncio.to_thread(
            _send_sync, recipients, subject, html_body, plain_body, pdf_bytes, filename,
        )
    except Exception as e:
        logger.exception("UniSender send error: %s", e)
        return False, str(e)
