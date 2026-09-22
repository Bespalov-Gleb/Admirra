"""SQL-only requirements shared by report consumers. Caller owns transaction.

Locks are deliberately client -> integration in stable order, as in writers.
Authorization belongs to the caller; do not accept arbitrary IDs from requests.
"""
import json

import sqlalchemy as sa
from core import models, sync_coverage


class DataNotReady(RuntimeError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__("Данные отчёта ещё не готовы. Обновите данные или подготовьте отчёт через согласование.")


def requirements(db, ids, start, end):
    ids = sorted(set(ids), key=str)
    if not ids or len(ids) > 200:
        raise DataNotReady("scope_unavailable_or_too_large")
    clients = list(db.scalars(sa.select(models.Client).where(models.Client.id.in_(ids))
        .order_by(models.Client.id).execution_options(populate_existing=True).with_for_update()))
    if len(clients) != len(ids) or any(c.status != models.ClientStatus.ACTIVE for c in clients):
        raise DataNotReady("scope_unavailable")
    integrations = list(db.scalars(sa.select(models.Integration).where(models.Integration.client_id.in_(ids))
        .order_by(models.Integration.id).limit(513).execution_options(populate_existing=True).with_for_update()))
    if len(integrations) > 512:
        raise DataNotReady("source_limit")
    owners = {c.id: c for c in clients}
    required = []
    for integration in integrations:
        platform = integration.platform
        if platform == models.IntegrationPlatform.YANDEX_METRIKA and not str(integration.account_id).isdigit():
            continue  # OAuth login link, not a statistical counter.
        stages = ["metrika_goals"] if platform == models.IntegrationPlatform.YANDEX_METRIKA else ["campaigns"]
        if platform not in {models.IntegrationPlatform.YANDEX_DIRECT, models.IntegrationPlatform.VK_ADS,
                            models.IntegrationPlatform.AVITO_ADS, models.IntegrationPlatform.YANDEX_METRIKA}:
            raise DataNotReady("unsupported_source")
        if platform in {models.IntegrationPlatform.YANDEX_DIRECT, models.IntegrationPlatform.AVITO_ADS}:
            try:
                selected = json.loads(integration.selected_goals or "[]")
            except (TypeError, ValueError):
                raise DataNotReady("invalid_goal_settings") from None
            if not isinstance(selected, list):
                raise DataNotReady("invalid_goal_settings")
            if selected or integration.primary_goal_id:
                stages.append("metrika_goals")
        client = owners[integration.client_id]
        required.append(dict(integration_id=str(integration.id), client_id=str(client.id), owner_id=str(client.owner_id),
            stages=stages, settings=sync_coverage.settings_digest(integration, client),
            date_from=start.isoformat(), date_to=end.isoformat()))
    if {row["client_id"] for row in required} != {str(value) for value in ids}:
        raise DataNotReady("no_statistical_sources")
    return required
