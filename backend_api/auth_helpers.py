"""Хэши токенов подтверждения почты и OTP входа."""
import hashlib
import hmac
import secrets
import string
from datetime import datetime, timedelta, timezone
from core.config import get_config

SECRET_KEY = get_config().security.secret_key


def hash_verification_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def hash_login_otp(code: str) -> str:
    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        code.strip().encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_login_otp(code: str, otp_hash: str) -> bool:
    try:
        return hmac.compare_digest(hash_login_otp(code), otp_hash)
    except Exception:
        return False


def generate_email_verification_raw_token() -> str:
    return secrets.token_urlsafe(32)


def generate_otp_digits() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(6))


def mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        return f"{local[0]}***@{domain}" if local else f"***@{domain}"
    return f"{local[0]}***{local[-1]}@{domain}"


def utcnow():
    return datetime.now(timezone.utc)


def verification_expiry(hours: int = 48):
    return utcnow() + timedelta(hours=hours)


def otp_expiry_minutes(minutes: int = 10):
    return utcnow() + timedelta(minutes=minutes)
