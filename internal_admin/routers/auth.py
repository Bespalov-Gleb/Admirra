"""Аутентификация внутренней админки."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core.database import get_db
from core import models, security
from internal_admin.deps import get_current_staff, require_superadmin
from internal_admin.models import AdminStaffSession
from internal_admin.rbac import is_staff, staff_role_label, is_superadmin, can_access_manager, can_access_seo
from internal_admin.schemas import (
    AdminLoginRequest,
    AdminTokenResponse,
    AdminMeResponse,
    ImpersonateResponse,
    StaffInviteAccept,
)
from internal_admin.security import (
    create_admin_access_token,
    create_mfa_challenge_token,
    decode_mfa_challenge_token,
    hash_session_token,
    new_session_token,
)
from internal_admin.services.totp_2fa import verify_staff_2fa
from internal_admin.services import write_audit, get_setting
from internal_admin.services.user_helpers import user_full_name

router = APIRouter(prefix="/auth", tags=["Internal Admin Auth"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _complete_admin_login(user: models.User, request: Request, db: Session) -> AdminTokenResponse:
    raw_session = new_session_token()
    session = AdminStaffSession(
        staff_user_id=user.id,
        session_token_hash=hash_session_token(raw_session),
        ip_address=_client_ip(request),
        user_agent=(request.headers.get("user-agent") or "")[:500],
    )
    db.add(session)
    user.last_login_at = datetime.now(timezone.utc)
    write_audit(
        db,
        staff=user,
        action="admin_login",
        description="Вход во внутреннюю админку",
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()

    token = create_admin_access_token(user.id, user.email, user.role.value, session_id=str(session.id))
    return AdminTokenResponse(
        access_token=token,
        role=user.role.value,
        full_name=user_full_name(user),
    )


@router.post("/login", response_model=AdminTokenResponse)
def admin_login(body: AdminLoginRequest, request: Request, db: Session = Depends(get_db)):
    if body.mfa_token:
        from uuid import UUID

        payload = decode_mfa_challenge_token(body.mfa_token)
        user = db.query(models.User).filter(models.User.id == UUID(str(payload.get("uid")))).first()
        if not user or user.email != payload.get("sub"):
            raise HTTPException(status_code=401, detail="Invalid MFA session")
        if not verify_staff_2fa(user, code=body.totp_code, recovery_code=body.recovery_code):
            raise HTTPException(status_code=401, detail="Invalid 2FA code")
        if not user.is_active or not is_staff(user):
            raise HTTPException(status_code=403, detail="Staff account unavailable")
        return _complete_admin_login(user, request, db)

    user = db.query(models.User).filter(models.User.email == body.email.lower()).first()
    if not user or not security.verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account blocked")
    if not is_staff(user):
        raise HTTPException(status_code=403, detail="Not an internal staff account")

    if user.staff_totp_enabled:
        if body.totp_code or body.recovery_code:
            if not verify_staff_2fa(user, code=body.totp_code, recovery_code=body.recovery_code):
                raise HTTPException(status_code=401, detail="Invalid 2FA code")
            db.commit()
            return _complete_admin_login(user, request, db)
        mfa = create_mfa_challenge_token(user.id, user.email)
        return AdminTokenResponse(requires_2fa=True, mfa_token=mfa)

    return _complete_admin_login(user, request, db)


@router.get("/me", response_model=AdminMeResponse)
def admin_me(staff: models.User = Depends(get_current_staff)):
    return AdminMeResponse(
        id=staff.id,
        email=staff.email,
        role=staff.role.value,
        role_label=staff_role_label(staff.role),
        full_name=user_full_name(staff),
        permissions={
            "superadmin": is_superadmin(staff),
            "manager": can_access_manager(staff) and not is_superadmin(staff),
            "seo": can_access_seo(staff),
        },
    )


@router.post("/invite/accept")
def accept_staff_invite(body: StaffInviteAccept, db: Session = Depends(get_db)):
    from internal_admin.services.staff_invite import accept_staff_invite as do_accept

    user = do_accept(db, token=body.token, password=body.password)
    db.commit()
    token = create_admin_access_token(user.id, user.email, user.role.value)
    return AdminTokenResponse(
        access_token=token,
        role=user.role.value,
        full_name=user_full_name(user),
    )


@router.post("/logout")
def admin_logout(
    request: Request,
    staff: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    sid = getattr(request.state, "admin_session_id", None)
    if sid:
        row = db.query(AdminStaffSession).filter(AdminStaffSession.id == sid).first()
        if row:
            row.is_active = False
            row.revoked_at = datetime.now(timezone.utc)
    write_audit(db, staff=staff, action="admin_logout", description="Выход из админки")
    db.commit()
    return {"ok": True}


@router.post("/users/{user_id}/impersonate", response_model=ImpersonateResponse)
def impersonate_user(
    user_id: str,
    request: Request,
    staff: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    from internal_admin.services.impersonate import impersonate_saas_user

    return impersonate_saas_user(request=request, staff=staff, db=db, target_user_id=user_id)
