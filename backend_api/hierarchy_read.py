"""Detached Direct collection and shared Direct/VK guarded, short SQL apply.

No schema or provider mutation. Client/integration locks use the same order as
ads_sync_work.apply; an intervening sync/config change rejects the late result.
"""
from dataclasses import dataclass, field
from datetime import date
import hashlib
import json
import logging

from fastapi import HTTPException
from sqlalchemy import select

from automation.ads_sync_contract import bounded, identifier, items, number, IncompleteAdsSnapshot
from automation.provider_transport import provider_client
from automation.request_queue import get_api_limiter
from automation.yandex_direct import YandexDirectAPI
from backend_api.attribution_read import _load, _require_read_only, AttributionChanged
from backend_api.read_snapshot import begin_read_snapshot
from core import models, security


TABLES = (models.YandexStats, models.YandexGroups, models.YandexAds)
VK_TABLES = (models.VKStats, models.VKGroups, models.VKBanners)
logger = logging.getLogger(__name__)


def _rows(db, campaign_id, client_id, start, end, tables=TABLES):
    result = {}
    for model in tables:
        query = db.query(*model.__table__.columns).filter(model.campaign_id == campaign_id,
                                                       model.client_id == client_id, model.date <= end)
        if start:
            query = query.filter(model.date >= start)
        result[model] = [dict(row._mapping) for row in query.order_by(model.id).all()]
    return result


def _digest(rows):
    data = [(model.__tablename__, values) for model, values in rows.items()]
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


@dataclass(repr=False)
class Plan:
    contract: object = field(repr=False)
    campaign: object = field(repr=False)
    integration: object = field(repr=False)
    baseline: str
    start: date | None
    end: date
    user_id: object
    need_ads: bool
    need_groups: bool = True


def prepare(db, campaign_id, client_id, start, end, include_ads, user_id,
            *, platform=models.IntegrationPlatform.YANDEX_DIRECT):
    _require_read_only(db)
    if platform not in (models.IntegrationPlatform.YANDEX_DIRECT, models.IntegrationPlatform.VK_ADS):
        raise ValueError("Unsupported hierarchy platform")
    try:
        begin_read_snapshot(db)
        contract = _load(db, [client_id], platform, [campaign_id], user_id)
        groups = list(contract.groups())
        if len(groups) != 1 or len(groups[0][1]) != 1:
            raise AttributionChanged()
        integration, campaigns = groups[0]
        campaign = campaigns[0]
        tables = VK_TABLES if platform == models.IntegrationPlatform.VK_ADS else TABLES
        rows = _rows(db, campaign_id, client_id, start, end, tables)
        return Plan(contract, campaign, integration, _digest(rows), start, end, user_id,
                    bool(include_ads and not rows[tables[2]]),
                    not rows[tables[1]] if platform == models.IntegrationPlatform.VK_ADS else True)
    finally:
        db.rollback()


async def catalog(api, campaign_id, *, ads=False):
    """Strict paginated catalog: errors/truncation are not successful empties."""
    key = "Ads" if ads else "AdGroups"
    urls = (api.ads_url_v501, api.ads_url) if ads else (api.adgroups_url_v501, api.adgroups_url)
    fields = ["Id", "CampaignId", "AdGroupId"] if ads else ["Id", "CampaignId", "Name"]
    async with provider_client("direct") as client:
        for url_index, url in enumerate(urls):
            result, seen, offset = [], set(), 0
            for _ in range(100):
                await get_api_limiter("direct").acquire()
                response = await client.post(url, headers=api.headers, timeout=60,
                    json={"method": "get", "params": {"SelectionCriteria": {"CampaignIds": [int(campaign_id)]},
                          "FieldNames": fields, "Page": {"Limit": 1000, "Offset": offset}}})
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict) or payload.get("error"):
                    if url_index == 0 and offset == 0:
                        break  # Version compatibility, never merge partial pages.
                    raise IncompleteAdsSnapshot("Direct hierarchy catalog error")
                body = payload.get("result")
                page = items(body, key)
                if not page and offset == 0 and url_index == 0:
                    break  # Preserve v501 -> v5 empty-catalog fallback.
                for row in page:
                    entity_id = identifier(row.get("Id"))
                    if identifier(row.get("CampaignId")) != str(campaign_id) or entity_id in seen:
                        raise IncompleteAdsSnapshot("Direct hierarchy catalog scope/duplicate error")
                    seen.add(entity_id)
                    if ads:
                        identifier(row.get("AdGroupId"))
                    result.append(row)
                bounded(result)
                next_offset = body.get("LimitedBy")
                if next_offset is None:
                    return result
                if type(next_offset) is not int or next_offset <= offset or not page:
                    raise IncompleteAdsSnapshot("Direct hierarchy pagination did not advance")
                offset = next_offset
            else:
                raise IncompleteAdsSnapshot("Direct hierarchy catalog page budget exceeded")
    raise IncompleteAdsSnapshot("Direct hierarchy catalog unavailable")


async def collect(plan):
    integration, campaign = plan.integration, plan.campaign
    from backend_api.stats import _selected_yandex_direct_profile
    api = YandexDirectAPI(security.decrypt_token(integration.access_token),
                          client_login=_selected_yandex_direct_profile(integration))
    api.strict_sync = True
    start, end = (plan.start or plan.end).isoformat(), plan.end.isoformat()
    operations = []
    levels = [("campaign", models.YandexStats, None), ("group", models.YandexGroups, "group_id")]
    if plan.need_ads:
        levels.append(("ad", models.YandexAds, "ad_id"))
    for level, model, entity_key in levels:
        rows = bounded(await api.get_report(start, end, level=level, campaign_ids=[int(campaign.external_id)]))
        seen_keys, seen_entities = set(), set()
        for row in rows:
            day = date.fromisoformat(row["date"])
            if not start <= day.isoformat() <= end or identifier(row.get("campaign_id")) != str(campaign.external_id):
                raise IncompleteAdsSnapshot("Direct hierarchy report scope mismatch")
            entity = identifier(row.get(entity_key)) if entity_key else None
            key = (day, entity)
            if key in seen_keys:
                raise IncompleteAdsSnapshot("Direct hierarchy report duplicate")
            seen_keys.add(key); seen_entities.add(entity)
            values = dict(date=day, campaign_name=row.get("campaign_name") or campaign.name,
                cost=number(row.get("cost")), impressions=number(row.get("impressions"), integer=True),
                clicks=number(row.get("clicks"), integer=True), conversions=number(row.get("conversions"), integer=True))
            if entity_key:
                values[entity_key] = entity
                values["group_name"] = row.get("name") if level == "group" else row.get("ad_group_name")
            if level == "ad":
                values["group_id"] = identifier(row.get("group_id"))
            operations.append((model, entity_key, values, False))
        if entity_key:
            for row in await catalog(api, campaign.external_id, ads=level == "ad"):
                entity = str(row["Id"])
                if entity in seen_entities:
                    continue
                values = dict(date=plan.end, campaign_name=campaign.name,
                    impressions=0, clicks=0, cost=0, conversions=0, **{entity_key: entity})
                if level == "group":
                    values["group_name"] = row.get("Name") or f"Группа {entity}"
                else:
                    values["group_id"] = str(row["AdGroupId"])
                operations.append((model, entity_key, values, True))
        bounded(operations)
    return operations


def apply(db, plan, operations):
    _require_read_only(db)
    platform = plan.integration.platform
    tables = VK_TABLES if platform == models.IntegrationPlatform.VK_ADS else TABLES
    try:
        db.rollback()
        # Match sync's lock order. Locks exist only while applying, not in IO.
        db.scalar(select(models.Client).where(models.Client.id == plan.integration.client_id).with_for_update())
        db.scalar(select(models.Integration).where(models.Integration.id == plan.integration.id).with_for_update())
        db.scalar(select(models.Campaign).where(models.Campaign.id == plan.campaign.id).with_for_update())
        current = _load(db, [plan.integration.client_id], platform,
                        [plan.campaign.id], plan.user_id)
        if current != plan.contract or _digest(_rows(db, plan.campaign.id, plan.integration.client_id,
                                                     plan.start, plan.end, tables)) != plan.baseline:
            raise AttributionChanged()
        # One read per table, not one SELECT per row. Natural keys deliberately
        # exclude mutable campaign/group names (renames must not add duplicates).
        existing = {}
        for model in tables:
            rows = db.query(model).filter(model.campaign_id == plan.campaign.id,
                                         model.client_id == plan.integration.client_id, model.date <= plan.end)
            if plan.start:
                rows = rows.filter(model.date >= plan.start)
            entity_key = ("group_id" if model in (models.YandexGroups, models.VKGroups)
                          else "ad_id" if model is models.YandexAds
                          else "banner_id" if model is models.VKBanners else None)
            indexed = {}
            for row in rows:
                key = (row.date, getattr(row, entity_key) if entity_key else None)
                if key in indexed:
                    # Do not guess which pre-existing duplicate is authoritative.
                    raise AttributionChanged()
                indexed[key] = row
            existing[model] = indexed
        for model, entity_key, values, catalog_only in operations:
            key = (values["date"], values.get(entity_key) if entity_key else None)
            row = existing[model].get(key)
            if row is not None and catalog_only:
                continue  # A catalog zero must NEVER erase an existing metric.
            if row is None:
                row = model(client_id=plan.integration.client_id, campaign_id=plan.campaign.id, **values)
                db.add(row)
                existing[model][key] = row
            else:
                for name, value in values.items():
                    setattr(row, name, value)
        db.commit()
    except BaseException:
        db.rollback()
        raise


async def ensure_yandex(db, campaign_id, client_id, start, end, *, include_ads=False, user_id=None):
    if start and start > end:
        raise HTTPException(422, "Некорректный период")
    plan = prepare(db, campaign_id, client_id, start, end, include_ads, user_id)
    if not str(plan.campaign.external_id).isdigit():
        return
    try:
        operations = await collect(plan)
    except Exception as error:
        logger.warning("Direct hierarchy collection failed for campaign %s (%s)",
                       plan.campaign.id, type(error).__name__)
        # No partial writes/zero fallback on timeout, malformed or partial API data.
        raise HTTPException(502, "Не удалось загрузить структуру кампании. Повторите запрос позже.") from None
    apply(db, plan, operations)
