"""Superadmin: безопасность и настройки."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from internal_admin.deps import require_superadmin
from internal_admin.models import AdminStaffSession
from internal_admin.schemas import AdminSettingsPatch
from internal_admin.services import get_all_settings, set_setting, write_audit
from internal_admin.services.user_helpers import user_full_name

router = APIRouter(prefix="/security", tags=["Internal Admin Security"])


@router.get("/sessions")
def list_staff_sessions(staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    rows = (
        db.query(AdminStaffSession)
        .filter(AdminStaffSession.is_active.is_(True))
        .order_by(AdminStaffSession.last_seen_at.desc())
        .limit(100)
        .all()
    )
    from core import models

    items = []
    for s in rows:
        user = db.query(models.User).filter(models.User.id == s.staff_user_id).first()
        items.append(
            {
                "id": str(s.id),
                "staff_email": user.email if user else None,
                "staff_name": user_full_name(user) if user else None,
                "role": user.role.value if user else None,
                "ip_address": s.ip_address,
                "city": s.city,
                "user_agent": s.user_agent,
                "last_seen_at": s.last_seen_at,
                "created_at": s.created_at,
            }
        )
    return {"items": items}


@router.post("/sessions/{session_id}/revoke")
def revoke_session(session_id: UUID, staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    row = db.query(AdminStaffSession).filter(AdminStaffSession.id == session_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    row.is_active = False
    row.revoked_at = datetime.now(timezone.utc)
    write_audit(db, staff=staff, action="staff_session_revoked", target_type="session", target_id=str(session_id))
    db.commit()
    return {"ok": True}


settings_router = APIRouter(prefix="/settings", tags=["Internal Admin Settings"])


@settings_router.get("")
def get_settings(staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    from internal_admin.services.totp_2fa import staff_2fa_stats

    data = get_all_settings(db)
    data["team_2fa_stats"] = staff_2fa_stats(db)
    return data


@settings_router.patch("")
def patch_settings(body: AdminSettingsPatch, staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        set_setting(db, key, value, updated_by=staff.id)
    write_audit(db, staff=staff, action="admin_settings_updated", meta=data)
    db.commit()
    return get_all_settings(db)
