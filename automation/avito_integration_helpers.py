"""Общие хелперы Avito + Metrika (без импорта backend_api.integrations)."""

from __future__ import annotations

from typing import Optional

from automation.avito_ads import AvitoAdsAPI
from core import models, security


def get_metrika_integration_for_client(db, client_id) -> Optional[models.Integration]:
    for platform in (
        models.IntegrationPlatform.YANDEX_METRIKA,
        models.IntegrationPlatform.YANDEX_DIRECT,
    ):
        integ = (
            db.query(models.Integration)
            .filter(
                models.Integration.client_id == client_id,
                models.Integration.platform == platform,
            )
            .first()
        )
        if integ and integ.access_token:
            return integ
    return None


def metrika_profile_login(integration: models.Integration) -> Optional[str]:
    """Логин Яндекса для ulogin в Метрике (не числовой ID и не домен счётчика)."""
    for candidate in (integration.agency_client_login, integration.account_id):
        if not candidate or str(candidate).lower() in ("unknown", "none", ""):
            continue
        s = str(candidate).strip()
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
