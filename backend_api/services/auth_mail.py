"""
Письма для подтверждения регистрации и OTP при входе (SMTP из env).
"""

import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Optional
from core.config import get_config

logger = logging.getLogger("api.auth_mail")


def smtp_enabled() -> bool:
    """false — не пытаемся слать письма (временно при проблемах с сетью/SMTP). По умолчанию true."""
    cfg = get_config()
    return cfg.smtp.enabled


def smtp_delivery_active() -> bool:
    """Письма реально отправляются: SMTP включён и заданы host/from."""
    return smtp_enabled() and is_configured()


def _smtp_config():
    cfg = get_config()
    host = cfg.smtp.host
    port = cfg.smtp.port
    user = cfg.smtp.user
    password = cfg.smtp.password
    from_addr = cfg.smtp.from_addr
    use_tls = cfg.smtp.use_tls
    return host, port, user, password, from_addr, use_tls


def is_configured() -> bool:
    host, _, _, _, from_addr, _ = _smtp_config()
    return bool(host and from_addr)


def _send_sync(to_email: str, subject: str, body_text: str) -> bool:
    if not smtp_enabled():
        logger.warning("Auth email skipped: SMTP_ENABLED=false")
        return False
    if not is_configured():
        logger.warning("Auth email skipped: SMTP not configured")
        return False
    host, port, user, password, from_addr, use_tls = _smtp_config()
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.set_content(body_text)
    with smtplib.SMTP(host, port, timeout=15) as server:
        if use_tls:
            server.starttls()
        if user and password:
            server.login(user, password)
        server.send_message(msg)
    return True


async def send_verification_link_email(to_email: str, verify_url: str) -> bool:
    subject = "Подтвердите регистрацию — AdMirra"
    body = (
        f"Здравствуйте!\n\n"
        f"Для подтверждения email перейдите по ссылке:\n{verify_url}\n\n"
        f"Если вы не регистрировались, проигнорируйте это письмо.\n"
    )
    try:
        return await asyncio.to_thread(_send_sync, to_email, subject, body)
    except Exception as e:
        logger.exception("send_verification_link_email failed: %s", e)
        return False


async def send_login_otp_email(to_email: str, code: str) -> bool:
    subject = "Код входа — AdMirra"
    body = (
        f"Ваш код для входа: {code}\n\n"
        f"Код действителен несколько минут. Никому его не сообщайте.\n"
    )
    try:
        return await asyncio.to_thread(_send_sync, to_email, subject, body)
    except Exception as e:
        logger.exception("send_login_otp_email failed: %s", e)
        return False
