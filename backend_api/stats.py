from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from core.database import get_db
from core import models, schemas, security
from datetime import datetime, timedelta, date
from typing import List, Optional
import uuid
from time import monotonic
from backend_api.stats_service import StatsService
from backend_api.top_ads_service import get_top_ads_with_images
import csv
import io
from fastapi.responses import StreamingResponse
import json
import logging
from automation.sync import sync_integration, sync_metrika_goals_background
from automation.vk_goal_action_mapping import get_vk_goal_action_name_ru
from automation.yandex_direct import YandexDirectAPI
from backend_api.sync_jobs import enqueue_sync_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# Дедупликация ensure_data_synced: не запускать повторный sync для интеграции в течение 30 сек
_sync_last_started: dict = {}
_sync_cooldown_sec = 30
_metrika_counter_goals_cache: dict = {}
_metrika_counter_goals_ttl_sec = 600


def _clean_yandex_profile_login(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned or cleaned.lower() in {"unknown", "none", "null"}:
        return None
    return cleaned


def _selected_yandex_direct_profile(integration: models.Integration) -> Optional[str]:
    if getattr(integration, "is_agency", False):
        profile = integration.agency_client_login or integration.account_id
    else:
        profile = integration.account_id
    return _clean_yandex_profile_login(profile)


def _json_list_safe(value) -> List[str]:
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
        if isinstance(parsed, (list, tuple)):
            return [str(item) for item in parsed if str(item).strip()]
    except Exception:
        pass
    return []


def _normalize_direct_name(value) -> str:
    return str(value or "").replace("\xa0", " ").strip().lower()


def _chunks(items: List[str], size: int):
    for index in range(0, len(items), size):
        yield items[index:index + size]


async def _get_metrika_counter_goal_ids(api, integration_id: uuid.UUID, counter_id: str) -> set:
    cache_key = (str(integration_id), str(counter_id))
    cached = _metrika_counter_goals_cache.get(cache_key)
    now = monotonic()
    if cached and now - cached["ts"] < _metrika_counter_goals_ttl_sec:
        return cached["goal_ids"]

    counter_goals = await api.get_counter_goals(str(counter_id))
    goal_ids = {str(goal.get("id")) for goal in (counter_goals or []) if goal.get("id")}
    _metrika_counter_goals_cache[cache_key] = {"ts": now, "goal_ids": goal_ids}
    return goal_ids


def _metrika_integration_goal_context(integration: models.Integration) -> tuple[List[str], List[str]]:
    counters = _json_list_safe(integration.selected_counters)
    goals = _json_list_safe(integration.selected_goals)
    if integration.primary_goal_id and str(integration.primary_goal_id) not in goals:
        goals.append(str(integration.primary_goal_id))
    return counters, goals


def _avito_utm_source(integration: models.Integration) -> str:
    source = str(getattr(integration, "utm_source", None) or "").strip()
    return source or "avito-ads"


def _metrika_utm_source_filter(source: str) -> str:
    safe_source = str(source or "avito-ads").replace("\\", "\\\\").replace("'", "\\'")
    return f"ym:s:UTMSource=='{safe_source}'"


async def _metrika_drill_conv_map(
    integration: models.Integration,
    campaign: models.Campaign,
    level: str,
    d_start: Optional[date],
    d_end: date,
) -> tuple[dict, bool]:
    """
    Exact Yandex leads for drill-down from Metrika selected goals.
    DirectBannerGroup.id matches Yandex AdGroupId; DirectBanner.name is M-<ad_id>.
    DirectClickOrder.id does not match Direct CampaignId, so campaign scope is by name.
    """
    counters, goals = _metrika_integration_goal_context(integration)
    if not counters or not goals:
        return {}, False

    try:
        access_token = security.decrypt_token(integration.access_token)
    except Exception:
        return {}, False

    from automation.yandex_metrica import YandexMetricaAPI

    api = YandexMetricaAPI(access_token, client_login=_selected_yandex_direct_profile(integration))
    date_from = (d_start or d_end).strftime("%Y-%m-%d")
    date_to = d_end.strftime("%Y-%m-%d")
    target_campaign = _normalize_direct_name(campaign.name)
    dimension = (
        "ym:s:<attribution>DirectBannerGroup"
        if level == "campaign"
        else "ym:s:<attribution>DirectBanner"
    )

    conv_map: dict = {}
    goals_available = False
    for counter in counters:
        try:
            available_goal_ids = await _get_metrika_counter_goal_ids(api, integration.id, str(counter))
        except Exception as err:
            logger.warning("Metrika drilldown goals fetch failed for counter %s: %s", counter, err)
            continue

        counter_goal_ids = [goal_id for goal_id in goals if goal_id in available_goal_ids]
        if not counter_goal_ids:
            continue

        goals_available = True
        for goals_batch in _chunks(counter_goal_ids, 20):
            rows = await api.get_conversions_by_dimension(
                counter_id=str(counter),
                date_from=date_from,
                date_to=date_to,
                goal_ids=goals_batch,
                dimension=dimension,
                extra_dimension="ym:s:<attribution>DirectClickOrder",
            )
            for row in rows:
                dimensions = row.get("dimensions") or []
                if len(dimensions) < 2:
                    continue
                campaign_dim = dimensions[0] or {}
                entity_dim = dimensions[1] or {}
                if _normalize_direct_name(campaign_dim.get("name")) != target_campaign:
                    continue

                if level == "campaign":
                    key = str(entity_dim.get("id") or "").strip()
                else:
                    key = str(entity_dim.get("name") or "").strip()
                    if key.upper().startswith("M-"):
                        key = key[2:]
                if key:
                    conv_map[key] = conv_map.get(key, 0.0) + float(row.get("conversions") or 0)

    return conv_map, goals_available


async def _avito_metrika_utm_conv_maps(
    db: Session,
    integration: models.Integration,
    d_start: Optional[date],
    d_end: date,
) -> tuple[dict, dict, bool]:
    """
    Exact Avito leads from Metrika selected goals.
    Avito Ads stats API has spend/views/clicks only; leads come from Metrika
    with UTM tags:
    - utm_source = integration.utm_source, default avito-ads
    - utm_campaign = Avito campaign id
    - utm_content = Avito creative/ad id
    """
    counters, goals = _metrika_integration_goal_context(integration)
    if not counters or not goals:
        return {}, {}, False

    try:
        from automation.avito_integration_helpers import (
            get_metrika_integration_for_client,
            metrika_profile_login,
        )

        metrika_integration = get_metrika_integration_for_client(db, integration.client_id)
        if not metrika_integration:
            return {}, {}, False
        access_token = security.decrypt_token(metrika_integration.access_token)
        selected_profile = metrika_profile_login(metrika_integration)
    except Exception:
        return {}, {}, False

    from automation.yandex_metrica import YandexMetricaAPI

    api = YandexMetricaAPI(access_token, client_login=selected_profile)
    date_from = (d_start or d_end).strftime("%Y-%m-%d")
    date_to = d_end.strftime("%Y-%m-%d")
    filters = _metrika_utm_source_filter(_avito_utm_source(integration))
    campaign_map: dict = {}
    creative_map: dict = {}
    goals_available = False

    for counter in counters:
        try:
            available_goal_ids = await _get_metrika_counter_goal_ids(api, integration.id, str(counter))
        except Exception as err:
            logger.warning("Avito Metrika goals fetch failed for counter %s: %s", counter, err)
            continue

        counter_goal_ids = [goal_id for goal_id in goals if goal_id in available_goal_ids]
        if not counter_goal_ids:
            continue

        goals_available = True
        for goals_batch in _chunks(counter_goal_ids, 20):
            rows = await api.get_conversions_by_dimension(
                counter_id=str(counter),
                date_from=date_from,
                date_to=date_to,
                goal_ids=goals_batch,
                dimension="ym:s:UTMCampaign",
                filters=filters,
            )
            for row in rows:
                dimensions = row.get("dimensions") or []
                if not dimensions:
                    continue
                key = str((dimensions[0] or {}).get("name") or "").strip()
                if key:
                    campaign_map[key] = campaign_map.get(key, 0.0) + float(row.get("conversions") or 0)

            rows = await api.get_conversions_by_dimension(
                counter_id=str(counter),
                date_from=date_from,
                date_to=date_to,
                goal_ids=goals_batch,
                dimension="ym:s:UTMContent",
                filters=filters,
            )
            for row in rows:
                dimensions = row.get("dimensions") or []
                if not dimensions:
                    continue
                key = str((dimensions[0] or {}).get("name") or "").strip()
                if key:
                    creative_map[key] = creative_map.get(key, 0.0) + float(row.get("conversions") or 0)

    return campaign_map, creative_map, goals_available


async def _metrika_campaign_conv_map(
    integration: models.Integration,
    d_start: Optional[date],
    d_end: date,
) -> tuple[dict, bool]:
    counters, goals = _metrika_integration_goal_context(integration)
    if not counters or not goals:
        return {}, False

    try:
        access_token = security.decrypt_token(integration.access_token)
    except Exception:
        return {}, False

    from automation.yandex_metrica import YandexMetricaAPI

    api = YandexMetricaAPI(access_token, client_login=_selected_yandex_direct_profile(integration))
    date_from = (d_start or d_end).strftime("%Y-%m-%d")
    date_to = d_end.strftime("%Y-%m-%d")

    conv_map: dict = {}
    goals_available = False
    for counter in counters:
        try:
            available_goal_ids = await _get_metrika_counter_goal_ids(api, integration.id, str(counter))
        except Exception as err:
            logger.warning("Metrika campaign goals fetch failed for counter %s: %s", counter, err)
            continue

        counter_goal_ids = [goal_id for goal_id in goals if goal_id in available_goal_ids]
        if not counter_goal_ids:
            continue

        goals_available = True
        for goals_batch in _chunks(counter_goal_ids, 20):
            rows = await api.get_conversions_by_dimension(
                counter_id=str(counter),
                date_from=date_from,
                date_to=date_to,
                goal_ids=goals_batch,
                dimension="ym:s:<attribution>DirectClickOrder",
            )
            for row in rows:
                dimensions = row.get("dimensions") or []
                if not dimensions:
                    continue
                key = _normalize_direct_name((dimensions[0] or {}).get("name"))
                if key:
                    conv_map[key] = conv_map.get(key, 0.0) + float(row.get("conversions") or 0)

    return conv_map, goals_available


async def _build_yandex_campaign_conversion_overrides(
    db: Session,
    client_ids: List[uuid.UUID],
    d_start: Optional[date],
    d_end: date,
    campaign_ids: Optional[List[uuid.UUID]] = None,
) -> dict:
    campaign_q = (
        db.query(models.Campaign)
        .join(models.Integration, models.Campaign.integration_id == models.Integration.id)
        .filter(
            models.Integration.client_id.in_(client_ids),
            models.Integration.platform == models.IntegrationPlatform.YANDEX_DIRECT,
        )
    )
    if campaign_ids:
        campaign_q = campaign_q.filter(models.Campaign.id.in_(campaign_ids))

    campaigns = campaign_q.all()
    campaigns_by_integration: dict = {}
    for campaign in campaigns:
        if campaign.integration:
            campaigns_by_integration.setdefault(campaign.integration.id, []).append(campaign)

    overrides: dict = {}
    for grouped_campaigns in campaigns_by_integration.values():
        integration = grouped_campaigns[0].integration
        conv_map, available = await _metrika_campaign_conv_map(integration, d_start, d_end)
        if not available:
            continue

        name_counts: dict = {}
        for campaign in grouped_campaigns:
            key = _normalize_direct_name(campaign.name)
            name_counts[key] = name_counts.get(key, 0) + 1

        for campaign in grouped_campaigns:
            key = _normalize_direct_name(campaign.name)
            if name_counts.get(key, 0) == 1:
                overrides[str(campaign.id)] = int(round(conv_map.get(key, 0)))
    return overrides


async def _build_avito_campaign_conversion_overrides(
    db: Session,
    client_ids: List[uuid.UUID],
    d_start: Optional[date],
    d_end: date,
    campaign_ids: Optional[List[uuid.UUID]] = None,
) -> dict:
    integration_q = db.query(models.Integration).filter(
        models.Integration.client_id.in_(client_ids),
        models.Integration.platform == models.IntegrationPlatform.AVITO_ADS,
    )
    if campaign_ids:
        integration_q = integration_q.join(models.Campaign).filter(models.Campaign.id.in_(campaign_ids))

    overrides: dict = {}
    for integration in integration_q.distinct().all():
        campaign_map, _, available = await _avito_metrika_utm_conv_maps(db, integration, d_start, d_end)
        if not available:
            continue
        for external_id, conversions in campaign_map.items():
            overrides[str(external_id)] = int(round(float(conversions or 0)))
    return overrides


async def _ensure_yandex_hierarchy_rows_for_campaign(
    db: Session,
    campaign: models.Campaign,
    d_start: Optional[date],
    d_end: date,
    *,
    include_ads: bool = False,
) -> None:
    """
    Lazy-load Yandex drill-down catalog rows for a single campaign and period.
    Direct reports remain the source for metrics, but Campaigns/AdGroups/Ads
    services are needed to show real children that have zero report rows in the
    selected period.
    """
    if not campaign or not campaign.integration:
        return
    if campaign.integration.platform != models.IntegrationPlatform.YANDEX_DIRECT:
        return
    if not campaign.external_id or not str(campaign.external_id).isdigit():
        return

    integration = campaign.integration
    selected_profile = _selected_yandex_direct_profile(integration)

    try:
        access_token = security.decrypt_token(integration.access_token)
        api = YandexDirectAPI(access_token, client_login=selected_profile)
    except Exception as err:
        logger.warning("Failed to initialize Yandex drilldown catalog for campaign %s: %s", campaign.id, err)
        return

    date_from = (d_start or d_end).strftime("%Y-%m-%d")
    date_to = d_end.strftime("%Y-%m-%d")
    catalog_row_date = d_end
    known_group_ids = set()

    try:
        campaign_rows = await api.get_report(
            date_from,
            date_to,
            level="campaign",
            campaign_ids=[int(campaign.external_id)],
        )
    except Exception as err:
        logger.warning("Failed to lazy-load Yandex campaign report for campaign %s: %s", campaign.id, err)
        campaign_rows = []

    for row in campaign_rows:
        row_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
        filters = {
            "client_id": integration.client_id,
            "campaign_id": campaign.id,
            "date": row_date,
        }
        existing = db.query(models.YandexStats).filter_by(**filters).first()
        data = {
            "campaign_name": row.get("campaign_name") or campaign.name,
            "impressions": row.get("impressions", 0),
            "clicks": row.get("clicks", 0),
            "cost": row.get("cost", 0),
            "conversions": row.get("conversions", 0),
        }
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
        else:
            db.add(models.YandexStats(**filters, **data))

    try:
        group_rows = await api.get_report(
            date_from,
            date_to,
            level="group",
            campaign_ids=[int(campaign.external_id)],
        )
    except Exception as err:
        logger.warning("Failed to lazy-load Yandex group report for campaign %s: %s", campaign.id, err)
        group_rows = []

    for row in group_rows:
        group_id = str(row.get("group_id") or "").strip()
        if not group_id:
            continue
        known_group_ids.add(group_id)
        row_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
        filters = {
            "client_id": integration.client_id,
            "campaign_id": campaign.id,
            "date": row_date,
            "campaign_name": row.get("campaign_name") or campaign.name,
            "group_id": group_id,
        }
        existing = db.query(models.YandexGroups).filter_by(**filters).first()
        data = {
            "group_name": row.get("name") or f"Группа {group_id}",
            "impressions": row.get("impressions", 0),
            "clicks": row.get("clicks", 0),
            "cost": row.get("cost", 0),
            "conversions": row.get("conversions", 0),
        }
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
        else:
            db.add(models.YandexGroups(**filters, **data))

    try:
        groups = await api.get_ad_groups_for_campaigns([int(campaign.external_id)])
        for group in groups:
            group_id = str(group.get("Id") or "").strip()
            if not group_id or group_id in known_group_ids:
                continue
            filters = {
                "client_id": integration.client_id,
                "campaign_id": campaign.id,
                "date": catalog_row_date,
                "campaign_name": campaign.name,
                "group_id": group_id,
            }
            existing = db.query(models.YandexGroups).filter_by(**filters).first()
            data = {
                "group_name": group.get("Name") or f"Группа {group_id}",
                "impressions": 0,
                "clicks": 0,
                "cost": 0,
                "conversions": 0,
            }
            if existing:
                for key, value in data.items():
                    setattr(existing, key, value)
            else:
                db.add(models.YandexGroups(**filters, **data))
    except Exception as err:
        logger.warning("Failed to lazy-load Yandex group catalog for campaign %s: %s", campaign.id, err)

    if not include_ads:
        db.commit()
        return

    ad_exists_q = db.query(models.YandexAds.id).filter(
        models.YandexAds.campaign_id == campaign.id,
        models.YandexAds.date <= d_end,
    )
    if d_start:
        ad_exists_q = ad_exists_q.filter(models.YandexAds.date >= d_start)
    if ad_exists_q.first():
        db.commit()
        return

    try:
        rows = await api.get_report(
            date_from,
            date_to,
            level="ad",
            campaign_ids=[int(campaign.external_id)],
        )
    except Exception as err:
        logger.warning("Failed to lazy-load Yandex ad report for campaign %s: %s", campaign.id, err)
        rows = []

    known_ad_ids = set()
    for row in rows:
        ad_id = row.get("ad_id")
        if not ad_id:
            continue
        known_ad_ids.add(str(ad_id))
        row_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
        filters = {
            "client_id": integration.client_id,
            "campaign_id": campaign.id,
            "date": row_date,
            "campaign_name": row.get("campaign_name") or campaign.name,
            "group_id": row.get("group_id"),
            "ad_id": str(ad_id),
        }
        existing = db.query(models.YandexAds).filter_by(**filters).first()
        data = {
            "group_name": row.get("ad_group_name"),
            "impressions": row.get("impressions", 0),
            "clicks": row.get("clicks", 0),
            "cost": row.get("cost", 0),
            "conversions": row.get("conversions", 0),
        }
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
        else:
            db.add(models.YandexAds(**filters, **data))

    try:
        ads = await api.get_ads_with_titles_and_images(campaign_ids=[int(campaign.external_id)])
        for ad in ads:
            ad_id = str(ad.get("Id") or "").strip()
            if not ad_id or ad_id in known_ad_ids:
                continue
            group_id = str(ad.get("AdGroupId") or "").strip() or None
            filters = {
                "client_id": integration.client_id,
                "campaign_id": campaign.id,
                "date": catalog_row_date,
                "campaign_name": campaign.name,
                "group_id": group_id,
                "ad_id": ad_id,
            }
            existing = db.query(models.YandexAds).filter_by(**filters).first()
            data = {
                "group_name": None,
                "impressions": 0,
                "clicks": 0,
                "cost": 0,
                "conversions": 0,
            }
            if existing:
                for key, value in data.items():
                    setattr(existing, key, value)
            else:
                db.add(models.YandexAds(**filters, **data))
    except Exception as err:
        logger.warning("Failed to lazy-load Yandex ad catalog for campaign %s: %s", campaign.id, err)

    db.commit()


def check_data_availability(
    db: Session,
    client_ids: List[uuid.UUID],
    d_start: date,
    d_end: date,
    platform: str = "all",
    campaign_ids: Optional[List[uuid.UUID]] = None
) -> bool:
    """
    Проверяет наличие данных в БД за указанный период.
    Возвращает True, если данные есть, False - если данных нет или период выходит за рамки сохраненных данных.
    """
    try:
        # Проверяем наличие данных для Yandex Direct
        if platform in ["all", "yandex"]:
            y_query = db.query(func.count(models.YandexStats.id)).join(
                models.Campaign, models.YandexStats.campaign_id == models.Campaign.id
            ).filter(
                models.YandexStats.client_id.in_(client_ids),
                models.YandexStats.date >= d_start,
                models.YandexStats.date <= d_end
            )
            if campaign_ids:
                y_query = y_query.filter(models.Campaign.id.in_(campaign_ids))
            y_count = y_query.scalar() or 0
            
            if y_count > 0:
                # Проверяем, что данные покрывают весь запрошенный период
                # Проверяем минимальную и максимальную даты в БД
                y_date_range = db.query(
                    func.min(models.YandexStats.date).label('min_date'),
                    func.max(models.YandexStats.date).label('max_date')
                ).join(
                    models.Campaign, models.YandexStats.campaign_id == models.Campaign.id
                ).filter(
                    models.YandexStats.client_id.in_(client_ids),
                    models.YandexStats.date >= d_start,
                    models.YandexStats.date <= d_end
                )
                if campaign_ids:
                    y_date_range = y_date_range.filter(models.Campaign.id.in_(campaign_ids))
                date_range = y_date_range.first()
                
                if date_range and date_range.min_date and date_range.max_date:
                    # Если минимальная дата в БД больше запрошенной начальной даты - данных не хватает
                    if date_range.min_date > d_start:
                        logger.info(f"⚠️ Data gap detected: DB min_date={date_range.min_date}, requested start={d_start}")
                        return False
                    # Если максимальная дата в БД меньше запрошенной конечной даты - данных не хватает
                    if date_range.max_date < d_end:
                        logger.info(f"⚠️ Data gap detected: DB max_date={date_range.max_date}, requested end={d_end}")
                        return False
                    return True
        
        if platform in ["all", "avito"]:
            a_query = db.query(func.count(models.AvitoStats.id)).join(
                models.Campaign, models.AvitoStats.campaign_id == models.Campaign.id
            ).filter(
                models.AvitoStats.client_id.in_(client_ids),
                models.AvitoStats.date >= d_start,
                models.AvitoStats.date <= d_end
            )
            if campaign_ids:
                a_query = a_query.filter(models.Campaign.id.in_(campaign_ids))
            a_count = a_query.scalar() or 0
            if a_count > 0:
                a_date_range = db.query(
                    func.min(models.AvitoStats.date).label('min_date'),
                    func.max(models.AvitoStats.date).label('max_date')
                ).join(
                    models.Campaign, models.AvitoStats.campaign_id == models.Campaign.id
                ).filter(
                    models.AvitoStats.client_id.in_(client_ids),
                    models.AvitoStats.date >= d_start,
                    models.AvitoStats.date <= d_end
                )
                if campaign_ids:
                    a_date_range = a_date_range.filter(models.Campaign.id.in_(campaign_ids))
                date_range = a_date_range.first()
                if date_range and date_range.min_date and date_range.max_date:
                    if date_range.min_date > d_start:
                        return False
                    if date_range.max_date < d_end:
                        return False
                    return True

        # Проверяем наличие данных для VK Ads
        if platform in ["all", "vk"]:
            v_query = db.query(func.count(models.VKStats.id)).join(
                models.Campaign, models.VKStats.campaign_id == models.Campaign.id
            ).filter(
                models.VKStats.client_id.in_(client_ids),
                models.VKStats.date >= d_start,
                models.VKStats.date <= d_end
            )
            if campaign_ids:
                v_query = v_query.filter(models.Campaign.id.in_(campaign_ids))
            v_count = v_query.scalar() or 0
            
            if v_count > 0:
                # Проверяем, что данные покрывают весь запрошенный период
                v_date_range = db.query(
                    func.min(models.VKStats.date).label('min_date'),
                    func.max(models.VKStats.date).label('max_date')
                ).join(
                    models.Campaign, models.VKStats.campaign_id == models.Campaign.id
                ).filter(
                    models.VKStats.client_id.in_(client_ids),
                    models.VKStats.date >= d_start,
                    models.VKStats.date <= d_end
                )
                if campaign_ids:
                    v_date_range = v_date_range.filter(models.Campaign.id.in_(campaign_ids))
                date_range = v_date_range.first()
                
                if date_range and date_range.min_date and date_range.max_date:
                    if date_range.min_date > d_start:
                        logger.info(f"⚠️ VK Data gap detected: DB min_date={date_range.min_date}, requested start={d_start}")
                        return False
                    if date_range.max_date < d_end:
                        logger.info(f"⚠️ VK Data gap detected: DB max_date={date_range.max_date}, requested end={d_end}")
                        return False
                    return True
        
        # Если для выбранной платформы нет данных - возвращаем False
        return False
    except Exception as e:
        logger.error(f"Error checking data availability: {e}")
        return False

async def sync_integration_background_async(
    integration_id: uuid.UUID,
    date_from_str: str,
    date_to_str: str
):
    """
    Асинхронная функция для синхронизации интеграции в фоне.
    Создает новую сессию БД для фоновой задачи.
    """
    from core.database import SessionLocal
    
    db = SessionLocal()
    try:
        integration = db.query(models.Integration).filter(
            models.Integration.id == integration_id
        ).first()
        
        if not integration:
            logger.warning(f"Integration {integration_id} not found for background sync")
            return
        
        logger.info(f"🔄 Background sync started for integration {integration.id} ({integration.platform}) for period {date_from_str} to {date_to_str}")
        
        await sync_integration(db, integration, date_from_str, date_to_str)
        db.commit()
        
        logger.info(f"✅ Background sync completed for integration {integration.id}")
        
        # Очищаем кеш дашборда после синхронизации
        from backend_api.cache_service import CacheService
        CacheService.invalidate_client(str(integration.client_id))
        logger.info(f"🗑️ Cleared dashboard cache after sync for integration {integration.id}")
        
    except Exception as e:
        logger.error(f"❌ Error in background sync for integration {integration_id}: {e}")
        db.rollback()
    finally:
        db.close()

def sync_integration_background(
    integration_id: uuid.UUID,
    date_from_str: str,
    date_to_str: str
):
    """
    Синхронная обертка для запуска синхронизации в отдельном потоке.
    Запускает асинхронную синхронизацию в отдельном event loop, чтобы не блокировать основной event loop FastAPI.
    """
    try:
        d_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()
        d_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()
        days = max(1, (d_to - d_from).days + 1)
    except Exception:
        days = 7
    enqueue_sync_job(integration_id, days)

def ensure_data_synced_async(
    db: Session,
    client_ids: List[uuid.UUID],
    d_start: date,
    d_end: date,
    platform: str = "all",
    campaign_ids: Optional[List[uuid.UUID]] = None
):
    """
    Проверяет наличие данных в БД за указанный период и запускает синхронизацию в фоне, если данных нет.
    НЕ БЛОКИРУЕТ запрос - синхронизация выполняется асинхронно.
    """
    # Проверяем наличие данных
    has_data = check_data_availability(db, client_ids, d_start, d_end, platform, campaign_ids)
    
    if has_data:
        logger.info(f"✅ Data available in DB for period {d_start} to {d_end}")
        return
    
    logger.info(f"⚠️ Data not available in DB for period {d_start} to {d_end}. Starting background sync...")
    
    # Очищаем кеш при запуске синка — следующий запрос получит свежие данные после завершения
    from backend_api.cache_service import CacheService
    for cid in client_ids:
        CacheService.invalidate_client(str(cid))
    
    # Получаем все интеграции для этих клиентов
    integrations = (
        db.query(models.Integration)
        .join(models.Client, models.Client.id == models.Integration.client_id)
        .filter(
            models.Integration.client_id.in_(client_ids),
            models.Client.status == models.ClientStatus.ACTIVE,
        )
        .all()
    )
    
    if not integrations:
        logger.warning(f"No integrations found for client_ids: {client_ids}")
        return
    
    # Фильтруем интеграции по платформе
    if platform == "yandex":
        integrations = [i for i in integrations if i.platform == models.IntegrationPlatform.YANDEX_DIRECT]
    elif platform == "vk":
        integrations = [i for i in integrations if i.platform == models.IntegrationPlatform.VK_ADS]
    elif platform == "avito":
        integrations = [i for i in integrations if i.platform == models.IntegrationPlatform.AVITO_ADS]
    elif platform == "all":
        # Для "all" синхронизируем все платформы
        integrations = [i for i in integrations if i.platform in [
            models.IntegrationPlatform.YANDEX_DIRECT,
            models.IntegrationPlatform.VK_ADS,
            models.IntegrationPlatform.AVITO_ADS,
        ]]
    
    if not integrations:
        logger.warning(f"No integrations found for platform: {platform}")
        return
    
    # Если указаны campaign_ids, фильтруем интеграции по этим кампаниям
    if campaign_ids:
        campaign_integrations = db.query(models.Campaign.integration_id).filter(
            models.Campaign.id.in_(campaign_ids)
        ).distinct().all()
        integration_ids = [ci[0] for ci in campaign_integrations if ci[0]]
        integrations = [i for i in integrations if i.id in integration_ids]
    
    # Запускаем синхронизацию для каждой интеграции в фоне (не ждем завершения)
    # CRITICAL: Ограничиваем количество одновременных синхронизаций, чтобы не исчерпать пул соединений
    # Максимум 5 одновременных синхронизаций (остальные будут ждать освобождения соединений)
    MAX_CONCURRENT_SYNCS = 5
    date_from_str = d_start.strftime("%Y-%m-%d")
    date_to_str = d_end.strftime("%Y-%m-%d")
    
    # Запускаем синхронизацию только для первых MAX_CONCURRENT_SYNCS интеграций
    # Остальные будут синхронизированы при следующем запросе
    integrations_to_sync = integrations[:MAX_CONCURRENT_SYNCS]
    if len(integrations) > MAX_CONCURRENT_SYNCS:
        logger.warning(f"⚠️ Too many integrations ({len(integrations)}). Syncing only first {MAX_CONCURRENT_SYNCS}. Rest will sync on next request.")
    
    # Дедупликация: не запускать повторный sync для той же интеграции в течение _sync_cooldown_sec
    import time as _time
    _now = _time.time()
    for integration in integrations_to_sync:
        try:
            _last = _sync_last_started.get(str(integration.id), 0)
            if _now - _last < _sync_cooldown_sec:
                logger.debug(f"📤 Skip sync for {integration.id} (cooldown {_sync_cooldown_sec - int(_now - _last)}s)")
                continue
            _sync_last_started[str(integration.id)] = _now
            sync_integration_background(integration.id, date_from_str, date_to_str)
            logger.info(f"📤 Background sync task created for integration {integration.id}")
        except Exception as e:
            logger.error(f"❌ Error creating background sync task for integration {integration.id}: {e}")

@router.get("/summary", response_model=schemas.StatsSummary)
async def get_summary(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[str] = Query(None),
    campaign_ids: Optional[List[str]] = Query(None),
    goal_action_ids: Optional[List[str]] = Query(None),
    platform: Optional[str] = "all", # 'yandex', 'vk', 'all'
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get aggregated statistics (Expenses, Impressions, Clicks, Leads, CPC, CPA) for a specified period.
    """
    # Safe UUID conversion
    u_client_id = None
    if client_id and client_id.strip():
        try: u_client_id = uuid.UUID(client_id)
        except: pass
    
    u_campaign_ids = None
    if campaign_ids:
        u_campaign_ids = []
        for cid in campaign_ids:
            if cid and cid.strip():
                try: u_campaign_ids.append(uuid.UUID(cid))
                except: pass
        if not u_campaign_ids: u_campaign_ids = None

    u_goal_action_ids = None
    if goal_action_ids:
        u_goal_action_ids = [gid for gid in goal_action_ids if gid and gid.strip()]
        if not u_goal_action_ids:
            u_goal_action_ids = None

    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not effective_client_ids:
        return {"expenses": 0, "impressions": 0, "clicks": 0, "leads": 0, "cpc": 0, "cpa": 0, "balance": 0, "currency": "RUB", "trends": None}

    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else d_end - timedelta(days=13)
    
    return StatsService.aggregate_summary(db, effective_client_ids, d_start, d_end, platform, u_campaign_ids, u_goal_action_ids)

@router.get("/dynamics", response_model=schemas.DynamicsStat)
async def get_dynamics(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[str] = Query(None),
    campaign_ids: Optional[List[str]] = Query(None),
    goal_action_ids: Optional[List[str]] = Query(None),
    platform: Optional[str] = "all",
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get daily dynamics of costs and clicks for the dashboard chart.
    """
    # Safe UUID conversion
    u_client_id = None
    if client_id and client_id.strip():
        try: u_client_id = uuid.UUID(client_id)
        except: pass
    
    u_campaign_ids = None
    if campaign_ids:
        u_campaign_ids = []
        for cid in campaign_ids:
            if cid and cid.strip():
                try: u_campaign_ids.append(uuid.UUID(cid))
                except: pass
        if not u_campaign_ids: u_campaign_ids = None

    u_goal_action_ids = None
    if goal_action_ids:
        u_goal_action_ids = [gid for gid in goal_action_ids if gid and gid.strip()]
        if not u_goal_action_ids:
            u_goal_action_ids = None

    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not effective_client_ids:
        return {
            "labels": [], 
            "costs": [], 
            "clicks": [],
            "impressions": [],
            "leads": [],
            "cpc": [],
            "cpa": []
        }
    
    # Defaults
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else d_end - timedelta(days=13)
    
    y_stats = db.query(
        models.YandexStats.date,
        func.sum(models.YandexStats.cost).label("cost"),
        func.sum(models.YandexStats.clicks).label("clicks"),
        func.sum(models.YandexStats.impressions).label("impressions"),
        func.sum(models.YandexStats.conversions).label("leads")
    ).join(models.Campaign, models.YandexStats.campaign_id == models.Campaign.id).filter(
        models.YandexStats.client_id.in_(effective_client_ids),
        # CRITICAL: Removed is_active filter - statistics should be shown for all campaigns
        # is_active is a user selection flag, not a data filtering flag
        models.YandexStats.date >= d_start,
        models.YandexStats.date <= d_end
    )
    if u_campaign_ids:
        y_stats = y_stats.filter(models.Campaign.id.in_(u_campaign_ids))
        # CRITICAL: Also filter by integration_id when campaigns are selected
        campaign_integrations = db.query(models.Campaign.integration_id).filter(
            models.Campaign.id.in_(u_campaign_ids)
        ).distinct().all()
        integration_ids = [ci[0] for ci in campaign_integrations if ci[0]]
        if integration_ids:
            y_stats = y_stats.filter(models.Campaign.integration_id.in_(integration_ids))
    else:
        # При "все кампании" — все интеграции клиента (не фильтруем по active)
        if len(effective_client_ids) == 1:
            client_integrations = db.query(models.Integration.id).filter(
                models.Integration.client_id.in_(effective_client_ids)
            ).distinct().all()
            integration_ids = [ci[0] for ci in client_integrations if ci[0]]
            if integration_ids:
                y_stats = y_stats.filter(models.Campaign.integration_id.in_(integration_ids))
    y_stats = y_stats.group_by(models.YandexStats.date).all()

    v_stats = db.query(
        models.VKStats.date,
        func.sum(models.VKStats.cost).label("cost"),
        func.sum(models.VKStats.clicks).label("clicks"),
        func.sum(models.VKStats.impressions).label("impressions"),
        func.sum(models.VKStats.conversions).label("leads")
    ).join(models.Campaign, models.VKStats.campaign_id == models.Campaign.id).filter(
        models.VKStats.client_id.in_(effective_client_ids),
        # CRITICAL: Removed is_active filter - statistics should be shown for all campaigns
        # is_active is a user selection flag, not a data filtering flag
        models.VKStats.date >= d_start,
        models.VKStats.date <= d_end
    )
    if u_campaign_ids:
        v_stats = v_stats.filter(models.Campaign.id.in_(u_campaign_ids))
        # CRITICAL: Also filter by integration_id when campaigns are selected
        campaign_integrations = db.query(models.Campaign.integration_id).filter(
            models.Campaign.id.in_(u_campaign_ids)
        ).distinct().all()
        integration_ids = [ci[0] for ci in campaign_integrations if ci[0]]
        if integration_ids:
            v_stats = v_stats.filter(models.Campaign.integration_id.in_(integration_ids))
    elif u_goal_action_ids:
        v_stats = v_stats.filter(models.Campaign.vk_goal_action_id.in_(u_goal_action_ids))
    else:
        if len(effective_client_ids) == 1:
            client_integrations = db.query(models.Integration.id).filter(
                models.Integration.client_id.in_(effective_client_ids)
            ).distinct().all()
            integration_ids = [ci[0] for ci in client_integrations if ci[0]]
            if integration_ids:
                v_stats = v_stats.filter(models.Campaign.integration_id.in_(integration_ids))
    v_stats = v_stats.group_by(models.VKStats.date).all()

    a_stats = db.query(
        models.AvitoStats.date,
        func.sum(models.AvitoStats.cost).label("cost"),
        func.sum(models.AvitoStats.clicks).label("clicks"),
        func.sum(models.AvitoStats.impressions).label("impressions"),
        func.sum(models.AvitoStats.conversions).label("leads")
    ).join(models.Campaign, models.AvitoStats.campaign_id == models.Campaign.id).filter(
        models.AvitoStats.client_id.in_(effective_client_ids),
        models.AvitoStats.date >= d_start,
        models.AvitoStats.date <= d_end
    )
    if u_campaign_ids:
        a_stats = a_stats.filter(models.Campaign.id.in_(u_campaign_ids))
        campaign_integrations = db.query(models.Campaign.integration_id).filter(
            models.Campaign.id.in_(u_campaign_ids)
        ).distinct().all()
        integration_ids = [ci[0] for ci in campaign_integrations if ci[0]]
        if integration_ids:
            a_stats = a_stats.filter(models.Campaign.integration_id.in_(integration_ids))
    else:
        if len(effective_client_ids) == 1:
            client_integrations = db.query(models.Integration.id).filter(
                models.Integration.client_id.in_(effective_client_ids)
            ).distinct().all()
            integration_ids = [ci[0] for ci in client_integrations if ci[0]]
            if integration_ids:
                a_stats = a_stats.filter(models.Campaign.integration_id.in_(integration_ids))
    a_stats = a_stats.group_by(models.AvitoStats.date).all()

    # Metrica Goals dynamics — при "все кампании" НЕ фильтруем по integration
    m_integration_ids = None
    campaign_platforms = []
    if u_campaign_ids:
        campaign_integrations = db.query(models.Campaign.integration_id).filter(
            models.Campaign.id.in_(u_campaign_ids)
        ).distinct().all()
        m_integration_ids = [ci[0] for ci in campaign_integrations if ci[0]]
        campaign_platforms = [
            row[0]
            for row in db.query(models.Integration.platform)
            .filter(models.Integration.id.in_(m_integration_ids))
            .distinct()
            .all()
        ]

    metrika_goal_platform = platform
    if platform == "all" and campaign_platforms:
        if all(p == models.IntegrationPlatform.AVITO_ADS for p in campaign_platforms):
            metrika_goal_platform = "avito"
        elif all(p == models.IntegrationPlatform.YANDEX_DIRECT for p in campaign_platforms):
            metrika_goal_platform = "yandex"
    
    m_stats = []
    if platform in ["all", "yandex", "avito"]:
        # Важно: используем тот же фильтр selected_goals, что и в summary,
        # чтобы суточные лиды на графике совпадали с итогом за период.
        selected_goal_ids = set(
            StatsService.get_selected_metrika_goal_ids(db, effective_client_ids, metrika_goal_platform)
        )

        # Лиды по дням = сумма по всем целям (как в summary и на круговой диаграмме)
        m_query = db.query(
            models.MetrikaGoals.date,
            func.sum(models.MetrikaGoals.conversion_count).label("leads")
        ).filter(
            models.MetrikaGoals.client_id.in_(effective_client_ids),
            models.MetrikaGoals.goal_id != "all",
            models.MetrikaGoals.date >= d_start,
            models.MetrikaGoals.date <= d_end
        )

        if selected_goal_ids:
            m_query = m_query.filter(models.MetrikaGoals.goal_id.in_(selected_goal_ids))
        elif metrika_goal_platform == "avito":
            m_query = m_query.filter(models.MetrikaGoals.goal_id == "__no_avito_goal_selected__")
        
        # CRITICAL: Filter MetrikaGoals by integration_id to match campaign selection
        if m_integration_ids:
            m_query = m_query.filter(models.MetrikaGoals.integration_id.in_(m_integration_ids))
        elif metrika_goal_platform in ("avito", "yandex"):
            goal_scope_ids = StatsService.get_metrika_goal_integration_ids(
                db,
                effective_client_ids,
                metrika_goal_platform,
            )
            if goal_scope_ids:
                m_query = m_query.filter(models.MetrikaGoals.integration_id.in_(goal_scope_ids))
            else:
                m_query = m_query.filter(models.MetrikaGoals.integration_id.is_(None))
        
        m_stats = m_query.group_by(models.MetrikaGoals.date).all()

    y_scope_cost_by_date = {}
    if u_campaign_ids and platform in ["all", "yandex"]:
        # Для фильтра по направлению MetrikaGoals не имеют campaign_id.
        # Поэтому дневные лиды Метрики распределяем по доле расхода выбранных
        # кампаний от общего расхода тех же интеграций за этот день.
        y_scope_q = db.query(
            models.YandexStats.date,
            func.sum(models.YandexStats.cost).label("cost")
        ).join(models.Campaign, models.YandexStats.campaign_id == models.Campaign.id).filter(
            models.YandexStats.client_id.in_(effective_client_ids),
            models.YandexStats.date >= d_start,
            models.YandexStats.date <= d_end
        )
        if m_integration_ids:
            y_scope_q = y_scope_q.filter(models.Campaign.integration_id.in_(m_integration_ids))
        y_scope_cost_by_date = {
            row.date: float((row.cost or 0) or 0)
            for row in y_scope_q.group_by(models.YandexStats.date).all()
        }

    avito_scope_cost_by_date = {}
    if u_campaign_ids and platform in ["all", "avito"] and models.IntegrationPlatform.AVITO_ADS in campaign_platforms:
        avito_integration_ids = [
            row[0]
            for row in db.query(models.Campaign.integration_id)
            .filter(models.Campaign.id.in_(u_campaign_ids))
            .distinct()
            .all()
            if row[0]
        ]
        avito_scope_q = db.query(
            models.AvitoStats.date,
            func.sum(models.AvitoStats.cost).label("cost")
        ).join(models.Campaign, models.AvitoStats.campaign_id == models.Campaign.id).filter(
            models.AvitoStats.client_id.in_(effective_client_ids),
            models.AvitoStats.date >= d_start,
            models.AvitoStats.date <= d_end
        )
        if avito_integration_ids:
            avito_scope_q = avito_scope_q.filter(models.Campaign.integration_id.in_(avito_integration_ids))
        avito_scope_cost_by_date = {
            row.date: float((row.cost or 0) or 0)
            for row in avito_scope_q.group_by(models.AvitoStats.date).all()
        }

    selected_platforms = [
        row[0]
        for row in db.query(models.Integration.platform)
        .filter(models.Integration.client_id.in_(effective_client_ids))
        .distinct()
        .all()
    ]
    mixed_goal_types = (
        platform == "all"
        and not u_campaign_ids
        and models.IntegrationPlatform.VK_ADS in selected_platforms
        and any(p in [models.IntegrationPlatform.YANDEX_DIRECT, models.IntegrationPlatform.YANDEX_METRIKA] for p in selected_platforms)
    )

    labels, costs, clicks, impressions, leads, cpc, cpa = [], [], [], [], [], [], []
    for i in range((d_end - d_start).days + 1):
        d = d_start + timedelta(days=i)
        labels.append(d.strftime("%d %b"))
        
        y_s = next((s for s in y_stats if s.date == d), None) if platform in ["all", "yandex"] else None
        v_s = next((s for s in v_stats if s.date == d), None) if platform in ["all", "vk"] else None
        a_s = next((s for s in a_stats if s.date == d), None) if platform in ["all", "avito"] else None
        m_s = next((s for s in m_stats if s.date == d), None) if m_stats else None

        c = float((y_s.cost if y_s else 0) + (v_s.cost if v_s else 0) + (a_s.cost if a_s else 0))
        cl = int((y_s.clicks if y_s else 0) + (v_s.clicks if v_s else 0) + (a_s.clicks if a_s else 0))
        im = int((y_s.impressions if y_s else 0) + (v_s.impressions if v_s else 0) + (a_s.impressions if a_s else 0))
        
        # Лиды для Yandex — только Метрика. Direct conversions не используем
        # fallback-ом, чтобы график совпадал со страницей проектов и целями.
        metrika_le = int(m_s.leads if m_s else 0)
        vk_le = int(v_s.leads if v_s else 0)
        if platform == "vk":
            le = vk_le
        elif platform == "avito":
            if u_campaign_ids:
                selected_avito_cost = float((a_s.cost if a_s else 0) or 0)
                avito_scope_cost = avito_scope_cost_by_date.get(d, selected_avito_cost)
                le = (
                    int(round(metrika_le * (selected_avito_cost / avito_scope_cost)))
                    if metrika_le > 0 and selected_avito_cost > 0 and avito_scope_cost > 0
                    else 0
                )
            else:
                le = metrika_le
        elif u_campaign_ids:
            selected_yandex_cost = float((y_s.cost if y_s else 0) or 0)
            yandex_scope_cost = y_scope_cost_by_date.get(d, selected_yandex_cost)
            yandex_metrika_le = (
                int(round(metrika_le * (selected_yandex_cost / yandex_scope_cost)))
                if metrika_le > 0 and selected_yandex_cost > 0 and yandex_scope_cost > 0
                else 0
            )
            selected_avito_cost = float((a_s.cost if a_s else 0) or 0)
            avito_scope_cost = avito_scope_cost_by_date.get(d, selected_avito_cost)
            avito_metrika_le = (
                int(round(metrika_le * (selected_avito_cost / avito_scope_cost)))
                if metrika_le > 0 and selected_avito_cost > 0 and avito_scope_cost > 0
                else 0
            )
            selected_has_yandex = models.IntegrationPlatform.YANDEX_DIRECT in campaign_platforms
            selected_has_avito = models.IntegrationPlatform.AVITO_ADS in campaign_platforms
            le = (
                (yandex_metrika_le if selected_has_yandex or not campaign_platforms else 0)
                + vk_le
                + (avito_metrika_le if selected_has_avito else 0)
            )
        elif mixed_goal_types:
            le = 0
        else:
            le = metrika_le + vk_le
        
        costs.append(round(c, 2)); clicks.append(cl); impressions.append(im); leads.append(le)
        cpc.append(round(c/cl, 2) if cl > 0 else 0)
        cpa.append(round(c/le, 2) if le > 0 and not mixed_goal_types else 0)

    return {
        "labels": labels, 
        "costs": costs, 
        "clicks": clicks,
        "impressions": impressions,
        "leads": leads,
        "cpc": cpc,
        "cpa": cpa
    }


@router.get("/dynamics-series")
async def get_dynamics_series_endpoint(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[str] = Query(None),
    campaign_ids: Optional[List[str]] = Query(None),
    platform: Optional[str] = "all",
    granularity: str = Query("month"),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Экран «Динамика»: ряд периодов (месяцы/недели) с дельтами к предыдущему
    периоду. Только чтение из витрины; без обращения к площадкам.
    """
    u_client_id = None
    if client_id and client_id.strip():
        try:
            u_client_id = uuid.UUID(client_id)
        except Exception:
            pass

    u_campaign_ids = None
    if campaign_ids:
        u_campaign_ids = []
        for cid in campaign_ids:
            if cid and cid.strip():
                try:
                    u_campaign_ids.append(uuid.UUID(cid))
                except Exception:
                    pass
        if not u_campaign_ids:
            u_campaign_ids = None

    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not effective_client_ids:
        return {"granularity": granularity, "goals": [], "periods": []}

    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else (d_end - timedelta(days=90))
    gran = "week" if str(granularity).lower().startswith("w") else "month"

    from backend_api.services.dynamics_service import get_dynamics_series
    return get_dynamics_series(
        db, effective_client_ids, d_start, d_end, platform, u_campaign_ids, gran
    )


@router.post("/dynamics/backfill")
async def dynamics_backfill_start_endpoint(
    client_id: Optional[str] = Query(None),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Запустить фоновую загрузку истории (до 12 мес) в витрину для текущего
    клиента — чтобы на «Динамике» появились прошлые периоды. Идемпотентно:
    повторный вызов во время прогона/кулдауна вернёт текущий статус.
    """
    u_client_id = None
    if client_id and client_id.strip():
        try:
            u_client_id = uuid.UUID(client_id)
        except Exception:
            pass
    client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not client_ids:
        return {"started": False, "reason": "no_client"}
    from backend_api.services.dynamics_backfill import start_backfill
    return start_backfill(client_ids)


@router.get("/dynamics/backfill-status")
async def dynamics_backfill_status_endpoint(
    client_id: Optional[str] = Query(None),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Статус фоновой загрузки истории + самая ранняя дата данных в витрине."""
    u_client_id = None
    if client_id and client_id.strip():
        try:
            u_client_id = uuid.UUID(client_id)
        except Exception:
            pass
    client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not client_ids:
        return {"status": "idle", "running": False, "history_from": None}
    from backend_api.services.dynamics_backfill import get_status
    return get_status(client_ids)


@router.get("/dynamics/export")
async def dynamics_export_endpoint(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[str] = Query(None),
    campaign_ids: Optional[List[str]] = Query(None),
    platform: Optional[str] = "all",
    granularity: str = Query("month"),
    fmt: str = Query("csv"),         # csv | xlsx
    include_vat: bool = Query(True),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Экспорт ряда «Динамики» (CSV/XLSX). Ряд строится тем же движком, что и экран,
    поэтому числа гарантированно совпадают. НДС применяется как на дашборде
    (Яндекс/VK ×1.22, Avito уже с НДС; «без НДС» → Avito ÷1.22).
    """
    u_client_id = None
    if client_id and client_id.strip():
        try:
            u_client_id = uuid.UUID(client_id)
        except Exception:
            pass
    u_campaign_ids = None
    if campaign_ids:
        u_campaign_ids = []
        for cid in campaign_ids:
            if cid and cid.strip():
                try:
                    u_campaign_ids.append(uuid.UUID(cid))
                except Exception:
                    pass
        if not u_campaign_ids:
            u_campaign_ids = None

    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else (d_end - timedelta(days=90))
    gran = "week" if str(granularity).lower().startswith("w") else "month"

    if not effective_client_ids:
        data = {"goals": [], "periods": []}
    else:
        from backend_api.services.dynamics_service import get_dynamics_series
        data = get_dynamics_series(db, effective_client_ids, d_start, d_end, platform, u_campaign_ids, gran)

    goals = data.get("goals", [])
    periods = data.get("periods", [])
    VAT = 1.22

    def _vat_cost(cbp: dict) -> float:
        y = float((cbp or {}).get("yandex") or 0)
        v = float((cbp or {}).get("vk") or 0)
        a = float((cbp or {}).get("avito") or 0)
        return (y * VAT + v * VAT + a) if include_vat else (y + v + a / VAT)

    header = ["Период", "Начало", "Конец", "Неполный", "Расход", "Показы", "Клики",
              "CTR %", "CPC", "Конверсии Я", "CPL Я"]
    for g in goals:
        header += [g["name"], f'{g["name"]} CPA']

    rows = []
    for p in periods:
        cost = _vat_cost(p.get("cost_by_platform") or {})
        clicks = int(p.get("clicks") or 0)
        cpc = round(cost / clicks, 2) if clicks > 0 else 0
        ys = p.get("yandex_summary") or {}
        yconv = ys.get("conversions")
        ycpl = ys.get("cpl")
        ycpl_adj = round(float(ycpl) * (VAT if include_vat else 1.0), 2) if ycpl else ""
        row = [
            p.get("label", ""), p.get("start", ""), p.get("end", ""),
            "да" if p.get("incomplete") else "нет",
            round(cost, 2), int(p.get("impressions") or 0), clicks,
            round(float(p.get("ctr") or 0), 2), cpc,
            yconv if yconv is not None else "", ycpl_adj,
        ]
        for g in goals:
            gg = (p.get("goals") or {}).get(g["id"]) or {}
            cnt = int(gg.get("count") or 0)
            row += [cnt, round(cost / cnt, 2) if cnt > 0 else ""]
        rows.append(row)

    filename = f"dynamics_{d_start}_{d_end}"

    if str(fmt).lower() == "xlsx":
        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Динамика"
            ws.append(header)
            for r in rows:
                ws.append(r)
            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)
            return StreamingResponse(
                buf,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f'attachment; filename="{filename}.xlsx"'},
            )
        except Exception as e:
            logger.warning("XLSX export unavailable (%s), falling back to CSV", e)

    output = io.StringIO()
    output.write('﻿')  # BOM для Excel
    writer = csv.writer(output, delimiter=';')
    writer.writerow(header)
    for r in rows:
        writer.writerow(r)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
    )


@router.get("/campaigns", response_model=List[schemas.CampaignStat])
async def get_campaign_stats(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[str] = Query(None),
    campaign_ids: Optional[List[str]] = Query(None),
    goal_action_ids: Optional[List[str]] = Query(None),
    platform: Optional[str] = "all",
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics grouped by campaign for the specified period.
    """
    # Safe UUID conversion
    u_client_id = None
    if client_id and client_id.strip():
        try: u_client_id = uuid.UUID(client_id)
        except: pass
    
    u_campaign_ids = None
    if campaign_ids:
        u_campaign_ids = []
        for cid in campaign_ids:
            if cid and cid.strip():
                try: u_campaign_ids.append(uuid.UUID(cid))
                except: pass
        if not u_campaign_ids: u_campaign_ids = None

    u_goal_action_ids = None
    if goal_action_ids:
        u_goal_action_ids = [gid for gid in goal_action_ids if gid and gid.strip()]
        if not u_goal_action_ids:
            u_goal_action_ids = None

    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not effective_client_ids: return []

    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()

    yandex_conversion_overrides = None
    yandex_prev_conversion_overrides = None
    avito_conversion_overrides = None
    avito_prev_conversion_overrides = None
    if platform in ["all", "yandex"]:
        yandex_conversion_overrides = await _build_yandex_campaign_conversion_overrides(
            db,
            effective_client_ids,
            d_start,
            d_end,
            u_campaign_ids,
        )
        if d_start:
            delta = (d_end - d_start).days + 1
            prev_start = d_start - timedelta(days=delta)
            prev_end = d_start - timedelta(days=1)
            yandex_prev_conversion_overrides = await _build_yandex_campaign_conversion_overrides(
                db,
                effective_client_ids,
                prev_start,
                prev_end,
                u_campaign_ids,
            )

    if platform in ["all", "avito"]:
        avito_conversion_overrides = await _build_avito_campaign_conversion_overrides(
            db,
            effective_client_ids,
            d_start,
            d_end,
            u_campaign_ids,
        )
        if d_start:
            delta = (d_end - d_start).days + 1
            prev_start = d_start - timedelta(days=delta)
            prev_end = d_start - timedelta(days=1)
            avito_prev_conversion_overrides = await _build_avito_campaign_conversion_overrides(
                db,
                effective_client_ids,
                prev_start,
                prev_end,
                u_campaign_ids,
            )

    return StatsService.get_campaign_stats(
        db,
        effective_client_ids,
        d_start,
        d_end,
        platform,
        u_campaign_ids,
        u_goal_action_ids,
        yandex_conversion_overrides=yandex_conversion_overrides,
        yandex_prev_conversion_overrides=yandex_prev_conversion_overrides,
        avito_conversion_overrides=avito_conversion_overrides,
        avito_prev_conversion_overrides=avito_prev_conversion_overrides,
    )


@router.get("/campaigns/{campaign_id}/children", response_model=List[schemas.CampaignStat])
async def get_campaign_children(
    campaign_id: str,
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[str] = Query(None),
    level: str = Query("campaign"),
    node_id: Optional[str] = Query(None),
    sort_by: str = Query("leads"),
    sort_dir: str = Query("desc"),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lazy drill-down for campaign hierarchy:
    campaign -> ad groups -> ads.
    """
    try:
        u_campaign_id = uuid.UUID(campaign_id)
    except Exception:
        return []

    u_client_id = None
    if client_id and client_id.strip():
        try:
            u_client_id = uuid.UUID(client_id)
        except Exception:
            pass

    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not effective_client_ids:
        return []

    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()

    campaign = (
        db.query(models.Campaign)
        .join(models.Integration, models.Campaign.integration_id == models.Integration.id)
        .filter(
            models.Campaign.id == u_campaign_id,
            models.Integration.client_id.in_(effective_client_ids),
        )
        .first()
    )
    if not campaign or not campaign.integration:
        return []

    if campaign.integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
        await _ensure_yandex_hierarchy_rows_for_campaign(
            db,
            campaign,
            d_start,
            d_end,
            include_ads=(level == "group"),
        )
        conv_map, conv_available = await _metrika_drill_conv_map(
            campaign.integration,
            campaign,
            level,
            d_start,
            d_end,
        )
        if conv_available:
            if level == "campaign":
                campaign_overrides = await _build_yandex_campaign_conversion_overrides(
                    db,
                    effective_client_ids,
                    d_start,
                    d_end,
                    campaign_ids=[campaign.id],
                )
                if str(campaign.id) in campaign_overrides:
                    conv_map["__campaign_total__"] = int(campaign_overrides[str(campaign.id)] or 0)
            elif level == "group" and node_id:
                group_conv_map, group_available = await _metrika_drill_conv_map(
                    campaign.integration,
                    campaign,
                    "campaign",
                    d_start,
                    d_end,
                )
                if group_available:
                    conv_map["__parent_total__"] = int(round(float(group_conv_map.get(str(node_id), 0) or 0)))
    elif campaign.integration.platform == models.IntegrationPlatform.AVITO_ADS:
        campaign_conv_map, creative_conv_map, conv_available = await _avito_metrika_utm_conv_maps(
            db,
            campaign.integration,
            d_start,
            d_end,
        )
        campaign_exact_convs = float(campaign_conv_map.get(str(campaign.external_id), 0) or 0)
        # For Avito hierarchy, group/ad precision requires utm_content
        # (creative id). If only utm_campaign is present and there are leads,
        # fall back to estimated distribution instead of showing exact zeros.
        hierarchy_conv_available = bool(creative_conv_map) or campaign_exact_convs <= 0
        conv_available = bool(conv_available and hierarchy_conv_available)
        if conv_available and level == "campaign":
            creative_rows_q = db.query(
                models.AvitoCreatives.group_id,
                models.AvitoCreatives.creative_id,
            ).filter(
                models.AvitoCreatives.client_id.in_(effective_client_ids),
                models.AvitoCreatives.campaign_id == campaign.id,
                models.AvitoCreatives.group_id.isnot(None),
                models.AvitoCreatives.creative_id.isnot(None),
            )
            if d_start:
                creative_rows_q = creative_rows_q.filter(models.AvitoCreatives.date >= d_start)
            if d_end:
                creative_rows_q = creative_rows_q.filter(models.AvitoCreatives.date <= d_end)
            group_conv_map: dict = {}
            seen_pairs = set()
            for group_id, creative_id in creative_rows_q.distinct().all():
                pair = (str(group_id), str(creative_id))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                group_conv_map[pair[0]] = group_conv_map.get(pair[0], 0.0) + float(
                    creative_conv_map.get(pair[1], 0) or 0
                )
            conv_map = group_conv_map
        else:
            conv_map = creative_conv_map
    else:
        conv_map, conv_available = {}, False

    return StatsService.get_campaign_children(
        db,
        effective_client_ids,
        u_campaign_id,
        d_start,
        d_end,
        level=level,
        node_id=node_id,
        sort_by=sort_by,
        sort_dir=sort_dir,
        conv_map=conv_map,
        conv_available=conv_available,
    )


@router.get("/top-ads", response_model=List[dict])
async def get_top_ads(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[str] = Query(None),
    campaign_ids: Optional[List[str]] = Query(None),
    goal_action_ids: Optional[List[str]] = Query(None),
    platform: Optional[str] = "all",
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get top 4 ads (posts) by conversions. For Yandex: real ads with image_url from Ads.get + AdImages.get.
    For VK: fallback to campaign-level (no image_url).
    """
    u_client_id = None
    if client_id and client_id.strip():
        try:
            u_client_id = uuid.UUID(client_id)
        except Exception:
            pass

    u_campaign_ids = None
    if campaign_ids:
        u_campaign_ids = []
        for cid in campaign_ids:
            if cid and cid.strip():
                try:
                    u_campaign_ids.append(uuid.UUID(cid))
                except Exception:
                    pass
        if not u_campaign_ids:
            u_campaign_ids = None

    u_goal_action_ids = None
    if goal_action_ids:
        u_goal_action_ids = [gid for gid in goal_action_ids if gid and gid.strip()]
        if not u_goal_action_ids:
            u_goal_action_ids = None

    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not effective_client_ids:
        return []

    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()

    try:
        ads = await get_top_ads_with_images(
            db, effective_client_ids, d_start, d_end,
            platform, u_campaign_ids, u_goal_action_ids, limit=16
        )
        return ads
    except Exception as e:
        logger.warning(f"top-ads error, fallback to campaign-level: {e}")
        campaigns = StatsService.get_campaign_stats(
            db, effective_client_ids, d_start, d_end, platform, u_campaign_ids, u_goal_action_ids
        )
        sorted_campaigns = sorted(
            campaigns,
            key=lambda x: (x.get("conversions", 0) or 0, x.get("cost", 0) or 0),
            reverse=True
        )
        top = sorted_campaigns[:4]
        return [
            {
                "id": c["id"],
                "title": c["name"],
                "image_url": None,
                "impressions": c.get("impressions", 0),
                "clicks": c.get("clicks", 0),
                "cost": c.get("cost", 0),
                "conversions": c.get("conversions", 0),
                "ctr": round((c.get("clicks", 0) or 0) / (c.get("impressions", 1) or 1) * 100, 2),
                "platform": c.get("platform") or (
                    "yandex"
                    if c["name"].startswith("[ЯД]")
                    else "avito"
                    if c["name"].startswith("[Avito]")
                    else "vk"
                ),
            }
            for c in top
        ]


@router.get("/activity-by-weekday", response_model=dict)
async def get_activity_by_weekday(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[str] = Query(None),
    campaign_ids: Optional[List[str]] = Query(None),
    goal_action_ids: Optional[List[str]] = Query(None),
    platform: Optional[str] = "all",
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get clicks and leads aggregated by day of week.
    Returns: {"clicks": {"0": N, ...}, "leads": {"0": N, ...}} where 0=Sunday, 1=Monday, ..., 6=Saturday.
    """
    u_client_id = None
    if client_id and client_id.strip():
        try:
            u_client_id = uuid.UUID(client_id)
        except Exception:
            pass

    u_campaign_ids = None
    if campaign_ids:
        u_campaign_ids = []
        for cid in campaign_ids:
            if cid and cid.strip():
                try:
                    u_campaign_ids.append(uuid.UUID(cid))
                except Exception:
                    pass
        if not u_campaign_ids:
            u_campaign_ids = None

    u_goal_action_ids = None
    if goal_action_ids:
        u_goal_action_ids = [gid for gid in goal_action_ids if gid and gid.strip()]
        if not u_goal_action_ids:
            u_goal_action_ids = None

    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not effective_client_ids:
        empty = {str(i): 0 for i in range(7)}
        return {"clicks": dict(empty), "leads": dict(empty)}

    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()

    return StatsService.get_activity_by_weekday(
        db, effective_client_ids, d_start, d_end, platform, u_campaign_ids, u_goal_action_ids
    )


@router.get("/audience-age", response_model=List[dict])
async def get_audience_age(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[str] = Query(None),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get audience age distribution from Yandex Metrica.
    Returns list of {age_interval: str, visits: int}.
    """
    u_client_id = None
    if client_id and client_id.strip():
        try:
            u_client_id = uuid.UUID(client_id)
        except Exception:
            pass

    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not effective_client_ids or len(effective_client_ids) != 1:
        return []

    # Get integration with Metrika: YANDEX_METRIKA или YANDEX_DIRECT с selected_counters
    integration = db.query(models.Integration).filter(
        models.Integration.client_id.in_(effective_client_ids),
        models.Integration.platform == models.IntegrationPlatform.YANDEX_METRIKA
    ).first()
    if not integration or not integration.access_token or not integration.selected_counters:
        integration = db.query(models.Integration).filter(
            models.Integration.client_id.in_(effective_client_ids),
            models.Integration.platform == models.IntegrationPlatform.YANDEX_DIRECT,
            models.Integration.selected_counters.isnot(None),
            models.Integration.selected_counters != ""
        ).first()
    if not integration or not integration.access_token or not integration.selected_counters:
        return []

    import json
    try:
        counters = json.loads(integration.selected_counters) if isinstance(integration.selected_counters, str) else integration.selected_counters
    except Exception:
        counters = []
    if not counters:
        return []

    counter_id = str(counters[0]) if counters else None
    if not counter_id:
        return []

    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else d_end - timedelta(days=30)
    date_from = d_start.strftime("%Y-%m-%d")
    date_to = d_end.strftime("%Y-%m-%d")

    from automation.yandex_metrica import YandexMetricaAPI
    access_token = security.decrypt_token(integration.access_token)
    api = YandexMetricaAPI(access_token)
    try:
        data = await api.get_audience_age(counter_id, date_from, date_to)
    except Exception as e:
        logger.warning(f"Metrika audience-age error: {e}")
        return []

    result = []
    for row in data:
        dims = row.get("dimensions", [])
        metrics = row.get("metrics", [])
        age_name = dims[0].get("name", "unknown") if dims else "unknown"
        visits = int(metrics[0]) if metrics else 0
        result.append({"age_interval": age_name, "visits": visits})
    return result


@router.get("/keywords", response_model=List[schemas.KeywordStat])
async def get_keyword_stats(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[uuid.UUID] = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed statistics by keyword.
    """
    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, client_id)
    if not effective_client_ids: return []
        
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()

    query = db.query(
        models.YandexKeywords.keyword,
        models.YandexKeywords.campaign_name,
        func.sum(models.YandexKeywords.impressions).label("impressions"),
        func.sum(models.YandexKeywords.clicks).label("clicks"),
        func.sum(models.YandexKeywords.cost).label("cost"),
        func.sum(models.YandexKeywords.conversions).label("conversions")
    ).filter(models.YandexKeywords.client_id.in_(effective_client_ids))

    if d_start: query = query.filter(models.YandexKeywords.date >= d_start)
    if d_end: query = query.filter(models.YandexKeywords.date <= d_end)

    results = query.group_by(models.YandexKeywords.keyword, models.YandexKeywords.campaign_name).all()

    keywords = []
    for r in results:
        cost = float(r.cost or 0)
        clicks = int(r.clicks or 0)
        convs = int(r.conversions or 0)
        keywords.append({
            "keyword": r.keyword,
            "campaign_name": r.campaign_name,
            "impressions": int(r.impressions or 0),
            "clicks": clicks,
            "cost": round(cost, 2),
            "conversions": convs,
            "cpc": round(cost / clicks, 2) if clicks > 0 else 0,
            "cpa": round(cost / convs, 2) if convs > 0 else 0
        })
    return keywords

@router.get("/groups", response_model=List[schemas.GroupStat])
async def get_group_stats(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[uuid.UUID] = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed statistics by ad group.
    """
    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, client_id)
    if not effective_client_ids: return []

    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()

    query = db.query(
        models.YandexGroups.group_name,
        models.YandexGroups.campaign_name,
        func.sum(models.YandexGroups.impressions).label("impressions"),
        func.sum(models.YandexGroups.clicks).label("clicks"),
        func.sum(models.YandexGroups.cost).label("cost"),
        func.sum(models.YandexGroups.conversions).label("conversions")
    ).filter(models.YandexGroups.client_id.in_(effective_client_ids))

    if d_start: query = query.filter(models.YandexGroups.date >= d_start)
    if d_end: query = query.filter(models.YandexGroups.date <= d_end)

    results = query.group_by(models.YandexGroups.group_name, models.YandexGroups.campaign_name).all()

    groups = []
    for r in results:
        cost = float(r.cost or 0)
        clicks = int(r.clicks or 0)
        convs = int(r.conversions or 0)
        groups.append({
            "name": r.group_name,
            "campaign_name": r.campaign_name,
            "impressions": int(r.impressions or 0),
            "clicks": clicks,
            "cost": round(cost, 2),
            "conversions": convs,
            "cpc": round(cost / clicks, 2) if clicks > 0 else 0,
            "cpa": round(cost / convs, 2) if convs > 0 else 0
        })
    return groups

@router.get("/top-clients", response_model=List[schemas.TopClient])
async def get_top_clients(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get top projects by total expenses.
    """
    user_clients = db.query(models.Client.id, models.Client.name).filter_by(owner_id=current_user.id).all()
    if not user_clients: return []
        
    client_map = {c.id: c.name for c in user_clients}
    client_ids = list(client_map.keys())

    yandex_costs = db.query(models.YandexStats.client_id, func.sum(models.YandexStats.cost).label("total_cost")).filter(models.YandexStats.client_id.in_(client_ids)).group_by(models.YandexStats.client_id).all()
    vk_costs = db.query(models.VKStats.client_id, func.sum(models.VKStats.cost).label("total_cost")).filter(models.VKStats.client_id.in_(client_ids)).group_by(models.VKStats.client_id).all()
    avito_costs = db.query(models.AvitoStats.client_id, func.sum(models.AvitoStats.cost).label("total_cost")).filter(models.AvitoStats.client_id.in_(client_ids)).group_by(models.AvitoStats.client_id).all()

    expenses_map = {cid: 0 for cid in client_ids}
    for cid, cost in yandex_costs: expenses_map[cid] += float(cost or 0)
    for cid, cost in vk_costs: expenses_map[cid] += float(cost or 0)
    for cid, cost in avito_costs: expenses_map[cid] += float(cost or 0)

    results = []
    total_all = 0
    for cid, total in expenses_map.items():
        if total > 0:
            results.append({"name": client_map[cid], "expenses": total})
            total_all += total

    results.sort(key=lambda x: x["expenses"], reverse=True)
    results = results[:5]
    for r in results:
        r["percentage"] = round((r["expenses"] / total_all) * 100, 1) if total_all > 0 else 0
        r["expenses"] = round(r["expenses"], 2)
    return results

@router.get("/goals", response_model=List[schemas.GoalStat])
async def get_goals(
    client_id: Optional[uuid.UUID] = None,
    integration_id: Optional[uuid.UUID] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    platform: Optional[str] = Query("all", description="yandex | vk | avito | all"),
    campaign_ids: Optional[str] = Query(None, description="comma-separated campaign UUIDs (для VK)"),
    direction_name: Optional[str] = Query(None, description="Selected direction name for goal narrowing"),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get goals for the current client from database.
    - platform=yandex: Metrika goals (конверсии по целям Метрики)
    - platform=vk: VK goal actions (разбивка по типам ЦД: подписчики, трафик, лид-формы и т.д.)
    - platform=avito: лиды Avito из Яндекс.Метрики по выбранным целям
    - platform=all: Metrika goals; VK при all не показываем — разные метрики.
    
    Cost is calculated by distributing total ad spend proportionally to conversions.
    """
    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, client_id)
    if not effective_client_ids: return []

    # Default date range: last 14 days if not specified
    if not date_to:
        date_to_obj = datetime.utcnow().date()
    else:
        date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
    
    if not date_from:
        date_from_obj = date_to_obj - timedelta(days=13)
    else:
        date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()

    u_campaign_ids = None
    if campaign_ids:
        try:
            u_campaign_ids = [uuid.UUID(x.strip()) for x in campaign_ids.split(",") if x.strip()]
        except ValueError:
            u_campaign_ids = None

    platform_key = (platform or "all").lower()

    if u_campaign_ids and platform_key != "vk":
        campaign_integration_ids = [
            row[0]
            for row in db.query(models.Campaign.integration_id)
            .filter(models.Campaign.id.in_(u_campaign_ids))
            .distinct()
            .all()
            if row[0]
        ]
        goal_platform = platform_key
        if platform_key == "all" and campaign_integration_ids:
            selected_platforms = [
                row[0]
                for row in db.query(models.Integration.platform)
                .filter(models.Integration.id.in_(campaign_integration_ids))
                .distinct()
                .all()
            ]
            if selected_platforms and all(p == models.IntegrationPlatform.YANDEX_DIRECT for p in selected_platforms):
                goal_platform = "yandex"
            elif selected_platforms and all(p == models.IntegrationPlatform.AVITO_ADS for p in selected_platforms):
                goal_platform = "avito"

        selected_goal_ids_for_direction = StatsService.get_selected_metrika_goal_ids(
            db,
            effective_client_ids,
            goal_platform,
        )
        direction_key = (direction_name or "").strip().lower()
        if direction_key and selected_goal_ids_for_direction:
            name_q = db.query(
                models.MetrikaGoals.goal_id,
                models.MetrikaGoals.goal_name,
            ).filter(
                models.MetrikaGoals.client_id.in_(effective_client_ids),
                models.MetrikaGoals.goal_id.in_(selected_goal_ids_for_direction),
                models.MetrikaGoals.goal_id != "all",
            )
            if campaign_integration_ids:
                name_q = name_q.filter(models.MetrikaGoals.integration_id.in_(campaign_integration_ids))
            latest_goal_names = {}
            for goal_id, goal_name in name_q.order_by(models.MetrikaGoals.date.desc()).all():
                gid = str(goal_id)
                if gid not in latest_goal_names and goal_name:
                    latest_goal_names[gid] = goal_name

            matching_goal_ids = [
                gid
                for gid, goal_name in latest_goal_names.items()
                if direction_key in str(goal_name or "").lower()
            ]
            if matching_goal_ids:
                period_days = (date_to_obj - date_from_obj).days + 1
                prev_date_from = date_from_obj - timedelta(days=period_days)
                prev_date_to = date_from_obj - timedelta(days=1)

                def goal_counts(start_date, end_date):
                    q = db.query(
                        models.MetrikaGoals.goal_id,
                        func.sum(models.MetrikaGoals.conversion_count).label("count"),
                    ).filter(
                        models.MetrikaGoals.client_id.in_(effective_client_ids),
                        models.MetrikaGoals.goal_id.in_(matching_goal_ids),
                        models.MetrikaGoals.date >= start_date,
                        models.MetrikaGoals.date <= end_date,
                    )
                    if campaign_integration_ids:
                        q = q.filter(models.MetrikaGoals.integration_id.in_(campaign_integration_ids))
                    return {
                        str(row.goal_id): int(row.count or 0)
                        for row in q.group_by(models.MetrikaGoals.goal_id).all()
                    }

                current_counts = goal_counts(date_from_obj, date_to_obj)
                previous_counts = goal_counts(prev_date_from, prev_date_to)
                return [
                    {
                        "id": gid,
                        "name": latest_goal_names.get(gid) or f"Goal {gid}",
                        "count": int(current_counts.get(gid, 0) or 0),
                        "trend": (
                            round(((int(current_counts.get(gid, 0) or 0) - int(previous_counts.get(gid, 0) or 0)) / int(previous_counts.get(gid, 0) or 1)) * 100, 1)
                            if int(previous_counts.get(gid, 0) or 0) > 0
                            else 0.0
                        ),
                        "cost": None,
                    }
                    for gid in matching_goal_ids
                ]

        current_summary = StatsService.aggregate_summary(
            db,
            effective_client_ids,
            date_from_obj,
            date_to_obj,
            platform_key,
            u_campaign_ids,
        )
        period_days = (date_to_obj - date_from_obj).days + 1
        prev_date_from = date_from_obj - timedelta(days=period_days)
        prev_date_to = date_from_obj - timedelta(days=1)
        prev_summary = StatsService.aggregate_summary(
            db,
            effective_client_ids,
            prev_date_from,
            prev_date_to,
            platform_key,
            u_campaign_ids,
        )

        current_count = int(current_summary.get("leads") or 0)
        current_cost = float(current_summary.get("expenses") or 0)
        prev_count = int(prev_summary.get("leads") or 0)
        prev_cost = float(prev_summary.get("expenses") or 0)
        trend = 0.0
        current_cpl = current_cost / current_count if current_count > 0 else 0
        prev_cpl = prev_cost / prev_count if prev_count > 0 else 0
        if current_cpl > 0 and prev_cpl > 0:
            trend = round(((current_cpl - prev_cpl) / prev_cpl) * 100, 1)

        return [{
            "id": "selected_campaigns",
            "name": "Конверсии выбранных кампаний",
            "count": current_count,
            "trend": trend,
            "cost": current_cost,
        }]

    # ——— VK: разбивка по типам целевых действий (подписчики, трафик, лид-формы и т.д.) ———
    if platform_key == "vk":
        vk_q = db.query(
            models.Campaign.vk_goal_action_id,
            models.Campaign.vk_goal_action_name,
            func.sum(models.VKStats.conversions).label("count"),
            func.sum(models.VKStats.cost).label("cost"),
        ).join(models.VKStats, models.VKStats.campaign_id == models.Campaign.id).filter(
            models.VKStats.client_id.in_(effective_client_ids),
            models.VKStats.date >= date_from_obj,
            models.VKStats.date <= date_to_obj,
            models.Campaign.vk_goal_action_id.isnot(None),
            models.Campaign.vk_goal_action_id != "",
        )
        if u_campaign_ids:
            vk_q = vk_q.filter(models.Campaign.id.in_(u_campaign_ids))
        vk_rows = vk_q.group_by(
            models.Campaign.vk_goal_action_id,
            models.Campaign.vk_goal_action_name,
        ).all()

        result = []
        period_days = (date_to_obj - date_from_obj).days + 1
        prev_date_from = date_from_obj - timedelta(days=period_days)
        prev_date_to = date_from_obj - timedelta(days=1)

        for row in vk_rows:
            prev_q = db.query(
                func.sum(models.VKStats.conversions),
                func.sum(models.VKStats.cost),
            ).join(models.Campaign, models.VKStats.campaign_id == models.Campaign.id).filter(
                models.VKStats.client_id.in_(effective_client_ids),
                models.Campaign.vk_goal_action_id == row.vk_goal_action_id,
                models.VKStats.date >= prev_date_from,
                models.VKStats.date <= prev_date_to,
            )
            if u_campaign_ids:
                prev_q = prev_q.filter(models.Campaign.id.in_(u_campaign_ids))
            prev_count, prev_cost = prev_q.first() or (0, 0)

            current_count = int(row.count or 0)
            current_cost = float(row.cost or 0)
            prev_count = int(prev_count or 0)
            prev_cost = float(prev_cost or 0)
            trend = 0.0
            current_cpl = current_cost / current_count if current_count > 0 else 0
            prev_cpl = prev_cost / prev_count if prev_count > 0 else 0
            if prev_cpl > 0 and current_cpl > 0:
                trend = round(((current_cpl - prev_cpl) / prev_cpl) * 100, 1)

            name = (row.vk_goal_action_name or "").strip() or get_vk_goal_action_name_ru(row.vk_goal_action_id or "")
            if not name:
                name = str(row.vk_goal_action_id or "ЦД")

            result.append({
                "id": str(row.vk_goal_action_id or ""),
                "name": name,
                "count": current_count,
                "trend": trend,
                "cost": current_cost,
            })

        return result

    # ——— Yandex / Avito / all: Metrika goals ———
    metrika_goal_integration_id = integration_id
    if platform_key == "avito":
        goal_platforms = [models.IntegrationPlatform.AVITO_ADS]
    elif platform_key == "yandex":
        goal_platforms = [models.IntegrationPlatform.YANDEX_DIRECT]
    else:
        goal_platforms = [
            models.IntegrationPlatform.YANDEX_DIRECT,
            models.IntegrationPlatform.YANDEX_METRIKA,
            models.IntegrationPlatform.AVITO_ADS,
        ]

    yandex_integrations_query = db.query(models.Integration).filter(
        models.Integration.client_id.in_(effective_client_ids),
        models.Integration.platform.in_(goal_platforms),
    )
    if metrika_goal_integration_id:
        yandex_integrations_query = yandex_integrations_query.filter(models.Integration.id == metrika_goal_integration_id)
    yandex_integrations = yandex_integrations_query.all()

    selected_goal_ids = StatsService.get_selected_metrika_goal_ids(
        db,
        effective_client_ids,
        platform_key,
    )
    if platform_key == "avito" and not selected_goal_ids:
        return []
    goal_scope_ids = []
    if not metrika_goal_integration_id and platform_key in ("avito", "yandex"):
        goal_scope_ids = StatsService.get_metrika_goal_integration_ids(
            db,
            effective_client_ids,
            platform_key,
        )

    query = db.query(
        models.MetrikaGoals.goal_id,
        func.sum(models.MetrikaGoals.conversion_count).label("count")
    ).filter(
        models.MetrikaGoals.client_id.in_(effective_client_ids),
        models.MetrikaGoals.date >= date_from_obj,
        models.MetrikaGoals.date <= date_to_obj,
        models.MetrikaGoals.goal_id != "all",
    )
    if metrika_goal_integration_id:
        query = query.filter(models.MetrikaGoals.integration_id == metrika_goal_integration_id)
    elif goal_scope_ids:
        query = query.filter(models.MetrikaGoals.integration_id.in_(goal_scope_ids))
    elif platform_key in ("avito", "yandex"):
        query = query.filter(models.MetrikaGoals.integration_id.is_(None))
    if selected_goal_ids:
        query = query.filter(models.MetrikaGoals.goal_id.in_(selected_goal_ids))
    current_counts = {
        str(row.goal_id): int(row.count or 0)
        for row in query.group_by(models.MetrikaGoals.goal_id).all()
    }

    latest_name_rows = db.query(
        models.MetrikaGoals.goal_id,
        models.MetrikaGoals.goal_name,
    ).filter(
        models.MetrikaGoals.client_id.in_(effective_client_ids),
        models.MetrikaGoals.goal_id != "all",
    )
    if metrika_goal_integration_id:
        latest_name_rows = latest_name_rows.filter(models.MetrikaGoals.integration_id == metrika_goal_integration_id)
    elif goal_scope_ids:
        latest_name_rows = latest_name_rows.filter(models.MetrikaGoals.integration_id.in_(goal_scope_ids))
    elif platform_key in ("avito", "yandex"):
        latest_name_rows = latest_name_rows.filter(models.MetrikaGoals.integration_id.is_(None))
    if selected_goal_ids:
        latest_name_rows = latest_name_rows.filter(models.MetrikaGoals.goal_id.in_(selected_goal_ids))
    latest_names = {}
    for row in latest_name_rows.order_by(models.MetrikaGoals.date.desc()).all():
        goal_id = str(row.goal_id)
        if goal_id not in latest_names and row.goal_name:
            latest_names[goal_id] = row.goal_name

    goal_ids_to_show = selected_goal_ids or list(current_counts.keys())

    has_any_period_goal_rows = db.query(func.count(models.MetrikaGoals.id)).filter(
        models.MetrikaGoals.client_id.in_(effective_client_ids),
        models.MetrikaGoals.date >= date_from_obj,
        models.MetrikaGoals.date <= date_to_obj,
        models.MetrikaGoals.goal_id != "all",
    )
    if selected_goal_ids:
        has_any_period_goal_rows = has_any_period_goal_rows.filter(
            models.MetrikaGoals.goal_id.in_(selected_goal_ids)
        )
    if goal_scope_ids:
        has_any_period_goal_rows = has_any_period_goal_rows.filter(
            models.MetrikaGoals.integration_id.in_(goal_scope_ids)
        )
    elif not metrika_goal_integration_id and platform_key in ("avito", "yandex"):
        has_any_period_goal_rows = has_any_period_goal_rows.filter(
            models.MetrikaGoals.integration_id.is_(None)
        )
    has_any_period_goal_rows = has_any_period_goal_rows.scalar() or 0
    if metrika_goal_integration_id:
        has_any_period_goal_rows = db.query(func.count(models.MetrikaGoals.id)).filter(
            models.MetrikaGoals.integration_id == metrika_goal_integration_id,
            models.MetrikaGoals.date >= date_from_obj,
            models.MetrikaGoals.date <= date_to_obj,
            models.MetrikaGoals.goal_id != "all",
        )
        if selected_goal_ids:
            has_any_period_goal_rows = has_any_period_goal_rows.filter(
                models.MetrikaGoals.goal_id.in_(selected_goal_ids)
            )
        has_any_period_goal_rows = has_any_period_goal_rows.scalar() or 0

    goals_syncing = bool(selected_goal_ids and not has_any_period_goal_rows)
    if goals_syncing:
        logger.info(
            "📊 get_goals: selected goals exist but no period rows for client=%s period=%s..%s",
            effective_client_ids,
            date_from_obj,
            date_to_obj,
        )
        for integration in yandex_integrations:
            if (integration.selected_goals or integration.primary_goal_id) and integration.selected_counters:
                sync_metrika_goals_background(integration.id, str(date_from_obj), str(date_to_obj))
                logger.info(f"📊 get_goals: triggered goals-only sync for integration {integration.id}")
                break

    period_days = (date_to_obj - date_from_obj).days + 1
    prev_date_from = date_from_obj - timedelta(days=period_days)
    prev_date_to = date_from_obj - timedelta(days=1)

    # Yandex/Metrika stores goal reaches separately from Direct spend. Without
    # campaign-goal attribution, assigning spend per individual goal would make
    # every goal's CPL identical. Return no per-goal cost instead of fake CPL.
    result = []
    for goal_id in goal_ids_to_show:
        prev_count = db.query(
            func.sum(models.MetrikaGoals.conversion_count)
        ).filter(
            models.MetrikaGoals.client_id.in_(effective_client_ids),
            models.MetrikaGoals.goal_id == goal_id,
            models.MetrikaGoals.date >= prev_date_from,
            models.MetrikaGoals.date <= prev_date_to
        )
        if metrika_goal_integration_id:
            prev_count = prev_count.filter(models.MetrikaGoals.integration_id == metrika_goal_integration_id)
        elif goal_scope_ids:
            prev_count = prev_count.filter(models.MetrikaGoals.integration_id.in_(goal_scope_ids))
        elif platform_key in ("avito", "yandex"):
            prev_count = prev_count.filter(models.MetrikaGoals.integration_id.is_(None))
        prev_count = prev_count.scalar() or 0

        current_count = int(current_counts.get(str(goal_id), 0) or 0)
        count_trend = 0.0
        if prev_count > 0:
            count_trend = round(((current_count - int(prev_count)) / int(prev_count)) * 100, 1)

        result.append({
            "id": str(goal_id),
            "name": latest_names.get(str(goal_id)) or f"Goal {goal_id}",
            "count": current_count,
            "trend": count_trend,
            "cost": None,
            "syncing": goals_syncing,
            "missing_in_metrika": bool(selected_goal_ids and str(goal_id) not in latest_names and not goals_syncing),
        })
    
    return result

@router.get("/integrations", response_model=List[schemas.DashboardIntegrationStatus])
def get_integrations_status(
    client_id: Optional[str] = Query(None),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    u_client_id = None
    if client_id:
        try:
            u_client_id = uuid.UUID(client_id)
        except ValueError:
            pass
    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not effective_client_ids: return []

    # Get integrations with balance and last_sync_at for connected platforms
    integrations = db.query(
        models.Integration.platform,
        models.Integration.balance,
        models.Integration.currency,
        models.Integration.last_sync_at,
        models.Integration.last_sync_trigger
    ).filter(models.Integration.client_id.in_(effective_client_ids)).all()

    platform_data = {}
    for row in integrations:
        raw = row.platform.value if hasattr(row.platform, 'value') else str(row.platform)
        p = raw.lower().replace("-", "_")  # YANDEX_DIRECT -> yandex_direct
        if p not in platform_data or (row.balance is not None and platform_data[p].get("balance") is None):
            platform_data[p] = {
                "platform": p,
                "is_connected": True,
                "balance": float(row.balance) if row.balance is not None else None,
                "currency": row.currency,
                "last_sync_at": row.last_sync_at,
                "last_sync_trigger": row.last_sync_trigger,
            }
        else:
            # Keep the most recent last_sync_at across multiple integrations for same platform
            existing = platform_data[p].get("last_sync_at")
            if row.last_sync_at and (not existing or row.last_sync_at > existing):
                platform_data[p]["last_sync_at"] = row.last_sync_at
                platform_data[p]["last_sync_trigger"] = row.last_sync_trigger
            if row.balance is not None and platform_data[p].get("balance") is not None:
                platform_data[p]["balance"] = (platform_data[p]["balance"] or 0) + float(row.balance)

    all_platforms = ["yandex_direct", "vk_ads", "avito_ads", "google_ads", "facebook_ads", "instagram", "telegram"]
    return [
        platform_data.get(p, {"platform": p, "is_connected": False, "balance": None, "currency": None})
        for p in all_platforms
    ]
@router.get("/export/csv")
async def export_stats_csv(
    start_date: str = None,
    end_date: str = None,
    client_id: Optional[str] = Query(None),
    campaign_ids: Optional[List[str]] = Query(None),
    goal_action_ids: Optional[List[str]] = Query(None),
    platform: Optional[str] = "all",
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export statistics to CSV file.
    """
    # Safe UUID conversion
    u_client_id = None
    if client_id and client_id.strip():
        try: u_client_id = uuid.UUID(client_id)
        except: pass
    
    u_campaign_ids = None
    if campaign_ids:
        u_campaign_ids = []
        for cid in campaign_ids:
            if cid and cid.strip():
                try: u_campaign_ids.append(uuid.UUID(cid))
                except: pass
        if not u_campaign_ids: u_campaign_ids = None

    u_goal_action_ids = None
    if goal_action_ids:
        u_goal_action_ids = [gid for gid in goal_action_ids if gid and gid.strip()]
        if not u_goal_action_ids:
            u_goal_action_ids = None

    effective_client_ids = StatsService.get_effective_client_ids(db, current_user.id, u_client_id)
    if not effective_client_ids:
        return StreamingResponse(io.StringIO("No data"), media_type="text/csv")
        
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()
    
    stats = StatsService.get_campaign_stats(db, effective_client_ids, d_start, d_end, platform, u_campaign_ids, u_goal_action_ids)
    
    output = io.StringIO()
    # Add BOM for Excel compatibility with UTF-8
    output.write('\ufeff')
    
    if stats:
        keys = ["name", "impressions", "clicks", "cost", "conversions", "cpc", "cpa"]
        writer = csv.DictWriter(output, fieldnames=keys, delimiter=';', extrasaction='ignore')
        
        # Header translation
        header = {
            "name": "Название кампании",
            "impressions": "Показы",
            "clicks": "Клики",
            "cost": "Расход (₽)",
            "conversions": "Лиды",
            "cpc": "CPC (₽)",
            "cpa": "CPA (₽)"
        }
        writer.writerow(header)
        writer.writerows(stats)
    else:
        output.write("Нет данных за выбранный период")
        
    output.seek(0)
    
    filename = f"report_{d_start or 'all'}_{d_end}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
