"""Менеджер API: /api/manager/*"""
from fastapi import APIRouter, Depends, HTTPException

from core.config import get_config
from internal_admin.routers.manager import router as manager_routes


def require_internal_admin_enabled() -> None:
    if not get_config().internal_admin.enabled:
        raise HTTPException(status_code=404, detail="Internal admin is disabled")


router = APIRouter(
    prefix="/manager",
    tags=["Internal Manager"],
    dependencies=[Depends(require_internal_admin_enabled)],
)
router.include_router(manager_routes)
