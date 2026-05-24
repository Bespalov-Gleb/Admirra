"""JWT и сессии внутренней админки (отдельный audience)."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from jose import JWTError, jwt
from fastapi import HTTPException, status

from core.config import get_config

AUDIENCE = "internal_admin"
MFA_AUDIENCE = "internal_admin_mfa"


def _admin_cfg():
    return get_config().internal_admin


def create_admin_access_token(user_id: UUID, email: str, role: str, session_id: Optional[str] = None) -> str:
    cfg = _admin_cfg()
    expire = datetime.now(timezone.utc) + timedelta(minutes=cfg.jwt_expire_minutes)
    payload = {
        "sub": email,
        "uid": str(user_id),
        "role": role,
        "aud": AUDIENCE,
        "exp": expire,
    }
    if session_id:
        payload["sid"] = session_id
    return jwt.encode(payload, cfg.jwt_secret, algorithm="HS256")


def decode_admin_token(token: str) -> dict[str, Any]:
    cfg = _admin_cfg()
    try:
        payload = jwt.decode(token, cfg.jwt_secret, algorithms=["HS256"], audience=AUDIENCE)
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def hash_session_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def create_mfa_challenge_token(user_id: UUID, email: str) -> str:
    cfg = _admin_cfg()
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    payload = {
        "sub": email,
        "uid": str(user_id),
        "aud": MFA_AUDIENCE,
        "exp": expire,
    }
    return jwt.encode(payload, cfg.jwt_secret, algorithm="HS256")


def decode_mfa_challenge_token(token: str) -> dict[str, Any]:
    cfg = _admin_cfg()
    try:
        return jwt.decode(token, cfg.jwt_secret, algorithms=["HS256"], audience=MFA_AUDIENCE)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA challenge",
        ) from exc


def create_impersonation_app_token(target_email: str, staff_id: UUID) -> str:
    """JWT для основного приложения (вход «как пользователь»). ТЗ: ~30 мин."""
    from core import security

    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {
        "sub": target_email,
        "impersonated_by": str(staff_id),
        "impersonation": True,
        "exp": expire,
    }
    return jwt.encode(payload, security.SECRET_KEY, algorithm=security.ALGORITHM)
