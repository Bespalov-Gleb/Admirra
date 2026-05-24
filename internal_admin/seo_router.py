"""SEO API: /api/seo/* (отдельно от суперадминки, ТЗ v1.0)."""
from fastapi import APIRouter, Depends, HTTPException

from core.config import get_config
from internal_admin.routers.seo import router as seo_routes


def require_internal_admin_enabled() -> None:
    if not get_config().internal_admin.enabled:
        raise HTTPException(status_code=404, detail="Internal admin is disabled")


router = APIRouter(
    prefix="/seo",
    tags=["Internal SEO"],
    dependencies=[Depends(require_internal_admin_enabled)],
)
router.include_router(seo_routes)
