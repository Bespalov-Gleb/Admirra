"""Публичные эндпоинты staff auth: /api/auth/* (ТЗ v1.0)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from internal_admin.deps import get_current_staff
from internal_admin.schemas import StaffInviteAccept, AdminTokenResponse
from internal_admin.security import create_admin_access_token
from internal_admin.services.user_helpers import user_full_name
from internal_admin.schemas import (
    TwoFactorDisableRequest,
    TwoFactorEnableResponse,
    TwoFactorVerifyRequest,
)
from internal_admin.services.totp_2fa import (
    begin_enable_2fa,
    confirm_enable_2fa,
    disable_2fa,
    verify_staff_2fa,
)
from core import models

router = APIRouter(prefix="/auth", tags=["Internal Staff Auth Public"])


@router.post("/invite/accept", response_model=AdminTokenResponse)
def accept_invite_public(body: StaffInviteAccept, db: Session = Depends(get_db)):
    from internal_admin.services.staff_invite import accept_staff_invite

    user = accept_staff_invite(db, token=body.token, password=body.password)
    db.commit()
    token = create_admin_access_token(user.id, user.email, user.role.value)
    return AdminTokenResponse(
        access_token=token,
        role=user.role.value,
        full_name=user_full_name(user),
    )


@router.post("/2fa/enable", response_model=TwoFactorEnableResponse)
def enable_2fa(staff: models.User = Depends(get_current_staff), db: Session = Depends(get_db)):
    data = begin_enable_2fa(staff)
    db.commit()
    return TwoFactorEnableResponse(
        secret=data["secret"],
        provisioning_uri=data["provisioning_uri"],
    )


@router.post("/2fa/verify")
def verify_2fa(
    body: TwoFactorVerifyRequest,
    staff: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    if body.setup_confirm:
        codes = confirm_enable_2fa(staff, body.code or "")
        db.commit()
        return {"ok": True, "recovery_codes": codes["recovery_codes"]}
    if not verify_staff_2fa(staff, code=body.code, recovery_code=body.recovery_code):
        raise HTTPException(status_code=400, detail="Invalid 2FA code")
    db.commit()
    return {"ok": True}


@router.post("/2fa/disable")
def disable_2fa_endpoint(
    body: TwoFactorDisableRequest,
    staff: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    disable_2fa(staff, password=body.password, code=body.code, recovery_code=body.recovery_code)
    db.commit()
    return {"ok": True}
