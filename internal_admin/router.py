"""Суперадмин API: /api/admin/*"""
from fastapi import APIRouter, Depends, HTTPException

from core.config import get_config
from internal_admin.routers.auth import router as auth_router
from internal_admin.routers.dashboard import router as dashboard_router
from internal_admin.routers.users import router as users_router
from internal_admin.routers.ai_limits import router as ai_limits_router
from internal_admin.routers.staff import router as staff_router
from internal_admin.routers.activity import router as activity_router
from internal_admin.routers.integrations import router as integrations_router
from internal_admin.routers.security_settings import router as security_router, settings_router
from internal_admin.routers.events import router as events_router
from internal_admin.routers.sessions_audit import sessions_router, audit_router


def require_internal_admin_enabled() -> None:
    if not get_config().internal_admin.enabled:
        raise HTTPException(status_code=404, detail="Internal admin is disabled")


router = APIRouter(
    prefix="/admin",
    tags=["Internal Admin"],
    dependencies=[Depends(require_internal_admin_enabled)],
)

router.include_router(auth_router)
router.include_router(dashboard_router)
router.include_router(users_router)
router.include_router(ai_limits_router)
router.include_router(staff_router)
router.include_router(activity_router)
router.include_router(integrations_router)
router.include_router(security_router)
router.include_router(settings_router)
router.include_router(events_router)
router.include_router(sessions_router)
router.include_router(audit_router)
