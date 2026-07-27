"""Шифрование секретов internal_admin (ключи интеграций, TOTP)."""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from core.config import get_config


def _fernet() -> Fernet:
    cfg = get_config()
    raw = (cfg.security.encryption_key or cfg.internal_admin.jwt_secret or "dev-insecure-key").encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    return Fernet(key)


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Invalid encrypted secret") from exc
