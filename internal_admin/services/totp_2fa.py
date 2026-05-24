"""TOTP 2FA для сотрудников internal_admin (ТЗ v1.0 — добровольно)."""
import hashlib
import secrets
from typing import Optional

import pyotp
from fastapi import HTTPException
from sqlalchemy.orm import Session

from core import models, security
from core.config import get_config
from internal_admin.rbac import is_staff
from internal_admin.services.crypto_secrets import decrypt_secret, encrypt_secret


def _issuer() -> str:
    return "AdMirra Admin"


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=_issuer())


def verify_totp(secret: str, code: str) -> bool:
    if not code or not code.strip().isdigit():
        return False
    return bool(pyotp.TOTP(secret).verify(code.strip(), valid_window=1))


def _hash_recovery_code(code: str) -> str:
    return hashlib.sha256(code.strip().upper().encode()).hexdigest()


def generate_recovery_codes(count: int = 10) -> tuple[list[str], list[str]]:
    plain = [secrets.token_hex(4).upper() for _ in range(count)]
    hashed = [_hash_recovery_code(c) for c in plain]
    return plain, hashed


def consume_recovery_code(user: models.User, code: str) -> bool:
    if not code or not user.staff_recovery_codes_hashed:
        return False
    h = _hash_recovery_code(code)
    remaining = [x for x in user.staff_recovery_codes_hashed if x != h]
    if len(remaining) == len(user.staff_recovery_codes_hashed or []):
        return False
    user.staff_recovery_codes_hashed = remaining
    return True


def begin_enable_2fa(user: models.User) -> dict:
    secret = generate_totp_secret()
    user.staff_totp_pending_secret_encrypted = encrypt_secret(secret)
    return {
        "secret": secret,
        "provisioning_uri": provisioning_uri(secret, user.email),
    }


def confirm_enable_2fa(user: models.User, code: str) -> dict:
    pending = user.staff_totp_pending_secret_encrypted
    if not pending:
        raise HTTPException(status_code=400, detail="2FA setup not started")
    secret = decrypt_secret(pending)
    if not verify_totp(secret, code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    plain_codes, hashed = generate_recovery_codes()
    user.staff_totp_secret_encrypted = encrypt_secret(secret)
    user.staff_totp_pending_secret_encrypted = None
    user.staff_totp_enabled = True
    user.staff_recovery_codes_hashed = hashed
    return {"recovery_codes": plain_codes}


def disable_2fa(user: models.User, *, password: str, code: Optional[str] = None, recovery_code: Optional[str] = None) -> None:
    if not security.verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid password")
    if not user.staff_totp_enabled:
        return
    ok = False
    if code and user.staff_totp_secret_encrypted:
        ok = verify_totp(decrypt_secret(user.staff_totp_secret_encrypted), code)
    if not ok and recovery_code:
        ok = consume_recovery_code(user, recovery_code)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid 2FA code")
    user.staff_totp_enabled = False
    user.staff_totp_secret_encrypted = None
    user.staff_totp_pending_secret_encrypted = None
    user.staff_recovery_codes_hashed = None


def verify_staff_2fa(user: models.User, *, code: Optional[str] = None, recovery_code: Optional[str] = None) -> bool:
    if not user.staff_totp_enabled:
        return True
    if code and user.staff_totp_secret_encrypted:
        if verify_totp(decrypt_secret(user.staff_totp_secret_encrypted), code):
            return True
    if recovery_code:
        return consume_recovery_code(user, recovery_code)
    return False


def staff_2fa_stats(db: Session) -> dict:
    from internal_admin.rbac import STAFF_ROLES

    staff_rows = db.query(models.User).filter(models.User.role.in_(STAFF_ROLES)).all()
    enabled = sum(1 for u in staff_rows if u.staff_totp_enabled)
    return {"enabled_count": enabled, "total_count": len(staff_rows)}
