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


def build_avito_api_from_integration(
    integration: models.Integration,
    *,
    account_id: Optional[str] = None,
) -> AvitoAdsAPI:
    has_client_credentials = bool(
        integration.platform_client_id and integration.platform_client_secret
    )
    credential_type = "client_credentials" if has_client_credentials else "single_api_key"
    api_kwargs: dict = {
        "credential_type": credential_type,
        "account_id": account_id or integration.account_id,
    }
    if credential_type == "single_api_key":
        api_kwargs["api_key"] = security.decrypt_token(integration.access_token)
    else:
        api_kwargs["client_id"] = security.decrypt_token(integration.platform_client_id)
        api_kwargs["client_secret"] = security.decrypt_token(integration.platform_client_secret)
    return AvitoAdsAPI(**api_kwargs)
