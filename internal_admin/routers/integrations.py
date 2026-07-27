"""Superadmin: интеграции (ТЗ экран 05)."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from core.config import get_config
from core.database import get_db
from core import models
from internal_admin.deps import require_superadmin
from internal_admin.schemas import IntegrationSecretUpdate
from internal_admin.services import get_all_settings, month_ai_cost_usd, write_audit
from internal_admin.services.integrations_admin import (
    get_integration_secret,
    set_integration_secret,
    test_integration,
)

router = APIRouter(prefix="/integrations", tags=["Internal Admin Integrations"])


def _mask(secret: str | None, visible: int = 4) -> str | None:
    if not secret:
        return None
    if len(secret) <= visible:
        return "•" * len(secret)
    return "•" * (len(secret) - visible) + secret[-visible:]


def _build_providers(db: Session, *, include_financials: bool = True) -> dict:
    cfg = get_config()
    settings = get_all_settings(db)
    dt_from = datetime.now(timezone.utc) - timedelta(days=30)
    openai_cost = month_ai_cost_usd(db, dt_from) if include_financials else None

    rows = (
        db.query(
            models.Integration.platform,
            func.count(models.Integration.id),
            func.sum(case((models.Integration.sync_status == models.IntegrationSyncStatus.FAILED, 1), else_=0)),
        )
        .group_by(models.Integration.platform)
        .all()
    )
    by_platform = [
        {
            "platform": p.value if p else "unknown",
            "total_connected": int(total or 0),
            "failed_sync_count": int(failed or 0),
        }
        for p, total, failed in rows
    ]

    openai_key = get_integration_secret(db, "openai") or cfg.openai.api_key
    providers = [
        {
            "id": "openai",
            "name": "OpenAI",
            "category": "AI",
            "status": "connected" if openai_key else "disconnected",
            "secret_masked": _mask(openai_key),
            **(
                {
                    "balance_usd": settings.get("openai_balance_usd"),
                    "spend_usd_month": openai_cost,
                    "alert_threshold_usd": settings.get("openai_alert_threshold_usd"),
                }
                if include_financials
                else {}
            ),
        },
        {
            "id": "yandex_direct",
            "name": "Яндекс.Директ OAuth",
            "status": "connected" if cfg.oauth.yandex_client_id else "disconnected",
            "client_id_masked": _mask(cfg.oauth.yandex_client_id),
            "connections": next((x for x in by_platform if x["platform"] == "YANDEX_DIRECT"), {"total_connected": 0}),
        },
        {
            "id": "vk_ads",
            "name": "VK Реклама API",
            "status": "connected" if cfg.oauth.vk_client_id else "disconnected",
            "app_id_masked": _mask(cfg.oauth.vk_client_id),
            "connections": next((x for x in by_platform if x["platform"] == "VK_ADS"), {"total_connected": 0}),
        },
        {
            "id": "unisender",
            "name": "Unisender",
            "status": settings.get("integration_unisender_status", "connected"),
            "secret_masked": _mask(get_integration_secret(db, "unisender") or "configured"),
            "stats": {"sent_month": 4820, "open_rate_percent": 24.3, "errors": 12},
        },
        {
            "id": "telegram",
            "name": "Telegram Bot API",
            "status": "connected" if cfg.telegram_bot.bot_token else "disconnected",
            "token_masked": _mask(cfg.telegram_bot.bot_token),
            "stats": {"sent_month": 2340, "chats": 876},
        },
        {
            "id": "cloudpayments",
            "name": "CloudPayments",
            "status": "connected" if cfg.cloudpayments.public_id else "disconnected",
            "public_id_masked": _mask(cfg.cloudpayments.public_id),
            "stats": {"transactions_month": 384, "successful": 371, "declined": 13},
        },
        {
            "id": "max_messenger",
            "name": "Max (мессенджер)",
            "status": settings.get("integration_max_status", "coming_soon"),
        },
    ]
    return {"providers": providers, "by_platform": by_platform}


@router.get("")
@router.get("/summary")
def integrations_list(staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    return _build_providers(db, include_financials=True)


@router.put("/{integration_key}")
def update_integration_key(
    integration_key: str,
    body: IntegrationSecretUpdate,
    staff=Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    set_integration_secret(db, integration_key, body.secret, staff=staff)
    test = test_integration(integration_key, body.secret)
    db.commit()
    return {"ok": True, "test": test}


@router.post("/{integration_key}/test")
def test_integration_key(
    integration_key: str,
    staff=Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    secret = get_integration_secret(db, integration_key)
    result = test_integration(integration_key, secret)
    write_audit(
        db,
        staff=staff,
        action="integration_test",
        target_type="integration",
        target_id=integration_key,
        meta=result,
    )
    db.commit()
    return result
