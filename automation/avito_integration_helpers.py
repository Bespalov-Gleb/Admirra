"""Общие хелперы Avito + Metrika (без импорта backend_api.integrations)."""

from __future__ import annotations

from typing import Optional

from automation.avito_ads import AvitoAdsAPI
from core import models, security


def avito_metrika_access_token(integration: models.Integration) -> Optional[str]:
    """Return the Avito-specific Metrika token, never a project-wide fallback."""
    token = getattr(integration, "metrika_access_token", None)
    return security.decrypt_token(token) if token else None


def avito_metrika_profile_login(integration: models.Integration) -> Optional[str]:
    """Yandex login used as ``ulogin`` for this Avito-specific grant."""
    candidate = getattr(integration, "metrika_account_id", None)
    if not candidate:
        return None
    value = str(candidate).strip()
    if not value or value.lower() in {"unknown", "none", "null"}:
        return None
    return value


def metrika_profile_login(integration: models.Integration) -> Optional[str]:
    """Логин Яндекса для ulogin в Метрике (не числовой ID и не домен счётчика)."""
    for candidate in (integration.agency_client_login, integration.account_id):
        if not candidate or str(candidate).lower() in ("unknown", "none", ""):
            continue
        s = str(candidate).strip()
        if s.lower().startswith("porg-"):
            continue
        if s.isdigit():
            continue
        # В account_id иногда ошибочно сохраняют site счётчика (например facebook.tim).
        if "." in s and "@" not in s:
            continue
        return s
    return None


def build_avito_api_from_integration(
    integration: models.Integration,
    *,
    account_id: Optional[str] = None,
) -> AvitoAdsAPI:
    if not (integration.platform_client_id and integration.platform_client_secret):
        raise ValueError("Для Avito Ads нужны Client ID и Client Secret")
    return AvitoAdsAPI(
        credential_type="client_credentials",
        client_id=security.decrypt_token(integration.platform_client_id),
        client_secret=security.decrypt_token(integration.platform_client_secret),
        account_id=account_id or integration.account_id,
    )
