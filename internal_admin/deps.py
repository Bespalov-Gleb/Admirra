"""FastAPI dependencies для internal_admin."""
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from core.database import get_db
from core import models
from internal_admin.rbac import STAFF_ROLES, is_superadmin, can_access_manager, can_access_seo
from internal_admin.security import decode_admin_token

_bearer = HTTPBearer(auto_error=False)


def get_current_staff(
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> models.User:
    if not auth or not auth.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin authentication required")
    payload = decode_admin_token(auth.credentials)
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Staff user not found or inactive")
    if user.role not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Not an internal staff account")
    if user.role in STAFF_ROLES:
        if user.staff_status == models.StaffStatus.INACTIVE:
            raise HTTPException(status_code=403, detail="Staff account deactivated")
        if user.staff_status == models.StaffStatus.PENDING:
            raise HTTPException(status_code=403, detail="Staff invite not accepted yet")
    request.state.admin_session_id = payload.get("sid")
    return user


def require_superadmin(staff: models.User = Depends(get_current_staff)) -> models.User:
    if not is_superadmin(staff):
        raise HTTPException(status_code=403, detail="Superadmin only")
    return staff


def require_manager(staff: models.User = Depends(get_current_staff)) -> models.User:
    if not can_access_manager(staff):
        raise HTTPException(status_code=403, detail="Manager access required")
    return staff


def require_seo(staff: models.User = Depends(get_current_staff)) -> models.User:
    if not can_access_seo(staff):
        raise HTTPException(status_code=403, detail="SEO access required")
    return staff
