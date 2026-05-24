"""Приглашение внутренних сотрудников (invite-only, ТЗ v1.0)."""
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core import models, security
from core.config import get_config
from backend_api.auth_helpers import hash_verification_token, verification_expiry
from internal_admin.rbac import STAFF_ROLES, staff_role_label


def _invite_expiry_days() -> int:
    return 7


def invite_staff(
    db: Session,
    *,
    email: str,
    first_name: str | None,
    last_name: str | None,
    role: models.UserRole,
    invited_by: UUID,
    force_client_collision: bool = False,
) -> tuple[models.User, str]:
    email = email.strip().lower()
    invitable = {
        models.UserRole.STAFF_MANAGER,
        models.UserRole.SUPPORT,
        models.UserRole.SEO,
        models.UserRole.DEVELOPER,
    }
    if role not in invitable:
        raise HTTPException(status_code=400, detail="Invalid staff role for invite")

    existing_staff = db.query(models.User).filter(models.User.email == email, models.User.role.in_(STAFF_ROLES)).first()
    if existing_staff:
        raise HTTPException(status_code=400, detail="Staff with this email already exists")

    client_user = db.query(models.User).filter(models.User.email == email, models.User.role == models.UserRole.MANAGER).first()
    if client_user and not force_client_collision:
        raise HTTPException(
            status_code=409,
            detail="This email is used as a client account. Confirm to create staff with the same email.",
        )

    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_verification_token(raw_token)
    placeholder = security.get_password_hash(secrets.token_urlsafe(16))

    user = models.User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        password_hash=placeholder,
        role=role,
        is_active=True,
        email_verified=False,
        email_verification_token_hash=token_hash,
        email_verification_expires_at=verification_expiry(_invite_expiry_days() * 24),
        staff_status=models.StaffStatus.PENDING,
    )
    db.add(user)
    db.flush()
    return user, raw_token


def accept_staff_invite(db: Session, *, token: str, password: str) -> models.User:
    th = hash_verification_token(token.strip())
    user = (
        db.query(models.User)
        .filter(
            models.User.email_verification_token_hash == th,
            models.User.staff_status == models.StaffStatus.PENDING,
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired invite link")
    exp = user.email_verification_expires_at
    if exp and exp.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invite link expired")

    user.password_hash = security.get_password_hash(password)
    user.email_verified = True
    user.staff_status = models.StaffStatus.ACTIVE
    user.email_verification_token_hash = None
    user.email_verification_expires_at = None
    db.add(user)
    return user


def invite_url(raw_token: str) -> str:
    base = get_config().internal_admin.cors_origins.split(",")[0].strip().rstrip("/")
    if not base or base == "*":
        base = get_config().public_domain.frontend_url or "https://admin.admirra.ru"
    return f"{base.rstrip('/')}/invite/{raw_token}"


def deactivate_staff(db: Session, user: models.User) -> None:
    user.staff_status = models.StaffStatus.INACTIVE
    user.is_active = False
    from internal_admin.models import AdminStaffSession

    db.query(AdminStaffSession).filter(AdminStaffSession.staff_user_id == user.id).update(
        {"is_active": False, "revoked_at": datetime.now(timezone.utc)}
    )


def reactivate_staff(db: Session, user: models.User) -> None:
    user.staff_status = models.StaffStatus.ACTIVE
    user.is_active = True
