"""Impersonation SaaS-пользователя (superadmin + менеджер)."""
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from core import models
from internal_admin.rbac import can_impersonate
from internal_admin.schemas import ImpersonateResponse
from internal_admin.security import create_impersonation_app_token
from internal_admin.services import get_setting, write_audit


def impersonate_saas_user(
    *,
    request: Request,
    staff: models.User,
    db: Session,
    target_user_id: str,
) -> ImpersonateResponse:
    if not can_impersonate(staff):
        raise HTTPException(status_code=403, detail="Impersonation not allowed")
    if not get_setting(db, "support_impersonation_allowed"):
        raise HTTPException(status_code=403, detail="Impersonation disabled in settings")

    target = db.query(models.User).filter(models.User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)

    token = create_impersonation_app_token(target.email, staff.id)
    write_audit(
        db,
        staff=staff,
        action="impersonate_user",
        target_type="user",
        target_id=str(target.id),
        description=f"Вход как пользователь {target.email}",
        ip_address=ip,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return ImpersonateResponse(access_token=token, target_user_id=target.id)
