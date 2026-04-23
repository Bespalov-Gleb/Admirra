"""
Отправка email уведомлений о новых лидах.
"""

import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import List, Dict, Any, Optional

from lead_validator.config import settings

logger = logging.getLogger("lead_validator.email_sender")


class EmailSender:
    """
    Отправка email через SMTP.
    """

    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_addr = settings.SMTP_FROM or settings.SMTP_USER
        self.use_tls = settings.SMTP_USE_TLS

        self.enabled = bool(self.host and self.from_addr)
        if not self.enabled:
            logger.info("Email sender disabled: SMTP settings not configured")

    def _build_message(self, recipients: List[str], payload: Dict[str, Any]) -> EmailMessage:
        subject = f"Новая заявка: {payload.get('phone')}"
        lines = [
            "Новая заявка из телефонии:",
            "",
            f"Телефон: {payload.get('phone')}",
            f"Имя: {payload.get('name') or '-'}",
            f"Фамилия: {payload.get('surname') or '-'}",
            f"Email: {payload.get('email') or '-'}",
            f"Статус: {payload.get('status') or '-'}",
            f"Оператор: {payload.get('phone_provider') or '-'}",
            f"Регион: {payload.get('phone_region') or '-'}",
            "",
            "UTM:",
            f"utm_source: {payload.get('utm_source') or '-'}",
            f"utm_campaign: {payload.get('utm_campaign') or '-'}",
            "",
            f"Создано: {payload.get('created_at') or '-'}",
        ]

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(recipients)
        msg.set_content("\n".join(lines))
        return msg

    def _send_sync(self, recipients: List[str], payload: Dict[str, Any]) -> bool:
        if not self.enabled:
            return False
        if not recipients:
            return False

        msg = self._build_message(recipients, payload)

        with smtplib.SMTP(self.host, self.port, timeout=10) as server:
            if self.use_tls:
                server.starttls()
            if self.user and self.password:
                server.login(self.user, self.password)
            server.send_message(msg)
        return True

    async def send_lead_notification(self, recipients: List[str], payload: Dict[str, Any]) -> bool:
        try:
            return await asyncio.to_thread(self._send_sync, recipients, payload)
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False

    def _send_report_sync(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        pdf_bytes: Optional[bytes] = None,
        filename: str = "report.pdf",
    ) -> bool:
        """Синхронная отправка отчёта с опциональным вложением PDF."""
        if not self.enabled or not recipients:
            return False
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(recipients)
        msg.set_content(body)
        if pdf_bytes:
            msg.add_attachment(
                pdf_bytes,
                maintype="application",
                subtype="pdf",
                filename=filename,
            )
        with smtplib.SMTP(self.host, self.port, timeout=30) as server:
            if self.use_tls:
                server.starttls()
            if self.user and self.password:
                server.login(self.user, self.password)
            server.send_message(msg)
        return True

    async def send_report_email(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        pdf_bytes: Optional[bytes] = None,
        filename: str = "report.pdf",
    ) -> tuple[bool, Optional[str]]:
        """
        Отправка отчёта на email с опциональным вложением PDF.
        Возвращает (success, error_message).
        """
        try:
            ok = await asyncio.to_thread(
                self._send_report_sync,
                recipients,
                subject,
                body,
                pdf_bytes,
                filename,
            )
            return (ok, None)
        except smtplib.SMTPAuthenticationError as e:
            err = str(e)
            if "535" in err or "authentication failed" in err.lower():
                hint = " Для Gmail используйте App Password (https://myaccount.google.com/apppasswords), не обычный пароль."
            else:
                hint = ""
            logger.error(f"Report email send failed: {e}")
            return (False, f"Ошибка аутентификации SMTP.{hint}")
        except Exception as e:
            logger.error(f"Report email send failed: {e}")
            return (False, str(e))


email_sender = EmailSender()

