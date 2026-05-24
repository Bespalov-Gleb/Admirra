"""Superadmin: сотрудники (ТЗ — invite-only, без закрепления клиентов)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.database import get_db
from core import models
from internal_admin.deps import require_superadmin
from internal_admin.models import AdminStaffSession
from internal_admin.rbac import STAFF_ROLES, staff_role_label
from internal_admin.schemas import StaffInviteCreate, StaffRoleUpdate
from internal_admin.services import write_audit
from internal_admin.services.staff_invite import (
    deactivate_staff,
    invite_staff,
    invite_url,
    reactivate_staff,
)
from internal_admin.services.user_helpers import user_full_name

router = APIRouter(prefix="/staff", tags=["Internal Admin Staff"])


def _staff_status(user: models.User) -> str:
    if user.staff_status:
        return user.staff_status.value
    return "active" if user.is_active else "inactive"


@router.get("")
def list_staff(staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    rows = db.query(models.User).filter(models.User.role.in_(STAFF_ROLES)).order_by(models.User.email).all()
    items = []
    for u in rows:
        sessions = (
            db.query(func.count(AdminStaffSession.id))
            .filter(AdminStaffSession.staff_user_id == u.id, AdminStaffSession.is_active.is_(True))
            .scalar()
            or 0
        )
        items.append(
            {
                "user_id": str(u.id),
                "email": u.email,
                "full_name": user_full_name(u),
                "role": u.role.value,
                "role_label": staff_role_label(u.role),
                "status": _staff_status(u),
                "active_sessions": int(sessions),
                "is_active": bool(u.is_active),
            }
        )
    return {"items": items}


@router.post("/invite")
async def staff_invite(body: StaffInviteCreate, staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    try:
        role = models.UserRole(body.role.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")
    user, raw = invite_staff(
        db,
        email=body.email,
        first_name=body.first_name,
        last_name=body.last_name,
        role=role,
        invited_by=staff.id,
        force_client_collision=body.force_client_collision,
    )
    write_audit(
        db,
        staff=staff,
        action="staff_invited",
        target_type="staff",
        target_id=str(user.id),
        meta={"email": user.email, "role": role.value},
    )
    db.commit()
    url = invite_url(raw)
    email_sent = False
    from backend_api.services.auth_mail import send_staff_invite_email, smtp_delivery_active

    if smtp_delivery_active():
        email_sent = await send_staff_invite_email(user.email, url, staff_role_label(role))
    return {"ok": True, "user_id": str(user.id), "invite_url": url, "email_sent": email_sent}


@router.post("/{user_id}/resend-invite")
async def staff_resend_invite(user_id: UUID, staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id, models.User.role.in_(STAFF_ROLES)).first()
    if not user or user.staff_status != models.StaffStatus.PENDING:
        raise HTTPException(status_code=400, detail="Staff not in pending state")
    from backend_api.auth_helpers import generate_email_verification_raw_token, hash_verification_token, verification_expiry

    raw = generate_email_verification_raw_token()
    user.email_verification_token_hash = hash_verification_token(raw)
    user.email_verification_expires_at = verification_expiry(7 * 24)
    write_audit(db, staff=staff, action="staff_invite_resent", target_type="staff", target_id=str(user_id))
    db.commit()
    url = invite_url(raw)
    email_sent = False
    from backend_api.services.auth_mail import send_staff_invite_email, smtp_delivery_active

    if smtp_delivery_active():
        email_sent = await send_staff_invite_email(user.email, url, staff_role_label(user.role))
    return {"ok": True, "invite_url": url, "email_sent": email_sent}


@router.post("/{user_id}/deactivate")
def staff_deactivate(user_id: UUID, staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id, models.User.role.in_(STAFF_ROLES)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Staff not found")
    deactivate_staff(db, user)
    write_audit(db, staff=staff, action="staff_deactivated", target_type="staff", target_id=str(user_id))
    db.commit()
    return {"ok": True}


@router.post("/{user_id}/reactivate")
def staff_reactivate(user_id: UUID, staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id, models.User.role.in_(STAFF_ROLES)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Staff not found")
    reactivate_staff(db, user)
    write_audit(db, staff=staff, action="staff_reactivated", target_type="staff", target_id=str(user_id))
    db.commit()
    return {"ok": True}


@router.patch("/{user_id}/role")
def update_staff_role(
    user_id: UUID,
    body: StaffRoleUpdate,
    staff=Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or user.role not in STAFF_ROLES:
        raise HTTPException(status_code=404, detail="Staff user not found")
    try:
        new_role = models.UserRole(body.role.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")
    if new_role not in STAFF_ROLES:
        raise HTTPException(status_code=400, detail="Role must be internal staff role")
    old = user.role.value
    user.role = new_role
    write_audit(
        db,
        staff=staff,
        action="staff_role_changed",
        target_type="staff",
        target_id=str(user_id),
        meta={"old_role": old, "new_role": new_role.value},
    )
    db.commit()
    return {"ok": True, "role": new_role.value}
