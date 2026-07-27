"""Управление ключами интеграций в ia_admin_settings (ТЗ экран 05)."""
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.config import get_config
from internal_admin.services import get_all_settings, set_setting, write_audit
from internal_admin.services.crypto_secrets import decrypt_secret, encrypt_secret

INTEGRATION_KEYS = {
    "openai",
    "yandex_direct",
    "vk_ads",
    "unisender",
    "telegram",
    "cloudpayments",
    "max_messenger",
}


def _setting_key(integration_id: str) -> str:
    if integration_id not in INTEGRATION_KEYS:
        raise HTTPException(status_code=404, detail="Unknown integration")
    return f"integration_secret_{integration_id}"


def get_integration_secret(db: Session, integration_id: str) -> Optional[str]:
    row_key = _setting_key(integration_id)
    settings = get_all_settings(db)
    enc = settings.get(row_key)
    if not enc:
        return None
    try:
        return decrypt_secret(str(enc))
    except ValueError:
        return None


def set_integration_secret(db: Session, integration_id: str, secret: str, *, staff) -> None:
    row_key = _setting_key(integration_id)
    set_setting(db, row_key, encrypt_secret(secret.strip()), updated_by=staff.id)
    write_audit(
        db,
        staff=staff,
        action="integration_key_updated",
        target_type="integration",
        target_id=integration_id,
        description=f"Обновлён ключ интеграции {integration_id}",
    )


def test_integration(integration_id: str, secret: Optional[str] = None) -> dict[str, Any]:
    cfg = get_config()
    if integration_id == "openai":
        key = secret or cfg.openai.api_key
        if not key:
            return {"ok": False, "detail": "API key not configured"}
        try:
            import httpx

            r = httpx.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {key}"},
                timeout=10.0,
            )
            return {"ok": r.status_code == 200, "status_code": r.status_code}
        except Exception as exc:
            return {"ok": False, "detail": str(exc)}
    if integration_id == "yandex_direct":
        return {"ok": bool(cfg.oauth.yandex_client_id and cfg.oauth.yandex_client_secret)}
    if integration_id == "vk_ads":
        return {"ok": bool(cfg.oauth.vk_client_id and cfg.oauth.vk_client_secret)}
    if integration_id == "telegram":
        return {"ok": bool(cfg.telegram_bot.bot_token)}
    if integration_id == "cloudpayments":
        return {"ok": bool(cfg.cloudpayments.public_id and cfg.cloudpayments.api_secret)}
    if integration_id in {"unisender", "max_messenger"}:
        return {"ok": True, "detail": "No remote ping implemented"}
    raise HTTPException(status_code=404, detail="Unknown integration")
