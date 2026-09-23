"""VK hierarchy: detached provider collection followed by one guarded apply."""
from datetime import date
import logging

from fastapi import HTTPException

from automation.ads_sync_contract import IncompleteAdsSnapshot, bounded, identifier, number
from automation.vk_ads import VKAdsAPI
from automation.vk_hierarchy_contract import catalog, statistics
from backend_api.hierarchy_read import prepare, apply
from core import models, security

logger = logging.getLogger(__name__)


async def collect(plan):
    integration, campaign = plan.integration, plan.campaign
    token = security.decrypt_token(integration.access_token)
    api = VKAdsAPI(token)
    kind = await api.detect_token_kind()
    if kind not in ("personal", "agency", "manager"):
        raise IncompleteAdsSnapshot("VK token scope could not be determined")
    if kind != "personal" and not integration.account_id:
        raise IncompleteAdsSnapshot("VK delegated account scope is missing")
    # Reuse the same API object/throttle across detection and data requests.
    api.send_client_id = kind != "personal"
    api.account_id = integration.account_id if api.send_client_id else None
    api.cabinet_id = integration.account_id
    groups = {}
    for row in await catalog(api, [campaign.external_id]):
        key = identifier(row.get("id"))
        if key in groups or identifier(row.get("ad_plan_id")) != str(campaign.external_id):
            raise IncompleteAdsSnapshot("VK group parent/duplicate mismatch")
        groups[key] = row.get("name") or f"Группа {key}"
    operations = []
    start, end = (plan.start or plan.end).isoformat(), plan.end.isoformat()

    async def level_rows(level, model, entity_key, metadata):
        seen, reported = set(), set()
        for row in bounded(await statistics(api, level, list(metadata), start, end)):
            entity = identifier(row.get("object_id"))
            day = date.fromisoformat(row["date"])
            key = (day, entity)
            if entity not in metadata or not start <= day.isoformat() <= end or key in seen:
                raise IncompleteAdsSnapshot("VK hierarchy statistic scope/duplicate mismatch")
            seen.add(key); reported.add(entity)
            values = dict(date=day, campaign_name=campaign.name, **metadata[entity], **{entity_key: entity},
                cost=number(row.get("cost")), clicks=number(row.get("clicks"), integer=True),
                impressions=number(row.get("impressions"), integer=True),
                conversions=number(row.get("conversions"), integer=True))
            operations.append((model, entity_key, values, False))
        for entity, meta in metadata.items():
            if entity not in reported:
                values = dict(date=plan.end, campaign_name=campaign.name, **meta, **{entity_key: entity},
                              cost=0, clicks=0, impressions=0, conversions=0)
                operations.append((model, entity_key, values, True))
        bounded(operations)

    if plan.need_groups and groups:
        await level_rows("ad_groups", models.VKGroups, "group_id",
                         {key: dict(group_name=name) for key, name in groups.items()})
    if plan.need_ads and groups:
        banners = {}
        for row in await catalog(api, list(groups), banners=True):
            key, group = identifier(row.get("id")), identifier(row.get("ad_group_id"))
            if key in banners or group not in groups:
                raise IncompleteAdsSnapshot("VK banner parent/duplicate mismatch")
            banners[key] = dict(group_id=group, group_name=groups[group],
                                banner_name=row.get("name") or f"Объявление {key}")
        if banners:
            await level_rows("banners", models.VKBanners, "banner_id", banners)
    return operations


async def ensure_vk(db, campaign_id, client_id, start, end, *, include_ads=False, user_id=None):
    if start and start > end:
        raise HTTPException(422, "Некорректный период")
    plan = prepare(db, campaign_id, client_id, start, end, include_ads, user_id,
                   platform=models.IntegrationPlatform.VK_ADS)
    # Preserve the existing per-slice lazy-cache policy. A row is NOT a proof
    # of complete historical coverage; explicit coverage tracking is separate.
    if not plan.need_groups and not plan.need_ads:
        return
    try:
        identifier(plan.campaign.external_id)
        operations = await collect(plan)
    except Exception as error:
        logger.warning("VK hierarchy collection failed for campaign %s (%s)",
                       plan.campaign.id, type(error).__name__)
        raise HTTPException(502, "Не удалось загрузить структуру кампании. Повторите запрос позже.") from None
    apply(db, plan, operations)
