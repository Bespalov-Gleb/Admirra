import re
import uuid
from collections import Counter
from datetime import date
from typing import Iterable

from sqlalchemy.orm import Session

from core import models
from core.campaign_status import status_label
from backend_api.stats_service import StatsService


LABELS = {
    "directions": "Направления",
    "categories": "Категории",
    "products": "Товары",
    "services": "Услуги",
    "brands": "Бренды",
    "branches": "Филиалы",
    "regions": "Регионы",
}

PLATFORM_TO_ENUM = {
    "yandex": models.IntegrationPlatform.YANDEX_DIRECT,
    "vk": models.IntegrationPlatform.VK_ADS,
}

STOP_TOKENS = {
    "яд", "yandex", "direct", "директ", "vk", "вк", "ads", "реклама",
    "поиск", "рся", "мастер", "кампания", "campaign", "new", "новая",
    "лиды", "лид", "заявки", "заявка", "трафик", "бренд", "общая",
    "общий", "тест", "test", "ретаргет", "ретаргетинг", "мск", "спб",
}


def normalize_mask(mask: str) -> str:
    return re.sub(r"\s+", " ", str(mask or "").strip().lower())


def normalize_label(label: str | None) -> str:
    value = str(label or "directions").strip().lower()
    return value if value in LABELS else "directions"


def platform_key(platform: models.IntegrationPlatform | str | None) -> str:
    raw = platform.value if hasattr(platform, "value") else str(platform or "")
    raw = raw.lower()
    if raw == "yandex_direct":
        return "yandex"
    if raw == "vk_ads":
        return "vk"
    return raw


def campaign_query(db: Session, client_id: uuid.UUID, platform: str = "all", only_active: bool = True):
    query = (
        db.query(models.Campaign)
        .join(models.Integration)
        .filter(models.Integration.client_id == client_id)
    )
    target_platform = PLATFORM_TO_ENUM.get(str(platform or "all").lower())
    if target_platform:
        query = query.filter(models.Integration.platform == target_platform)
    if only_active:
        query = query.filter(models.Campaign.is_active.is_(True))
    return query.order_by(models.Campaign.name.asc())


def campaign_status(campaign: models.Campaign) -> tuple[str, str]:
    display_status = str(getattr(campaign, "display_status", "") or "").strip().lower()
    if display_status:
        return display_status, status_label(display_status)
    if getattr(campaign, "is_active", False):
        return "active", "Активна"
    return "archived", "Архив"


def get_active_directions(db: Session, client_id: uuid.UUID):
    return (
        db.query(models.ProjectDirection)
        .filter(
            models.ProjectDirection.client_id == client_id,
            models.ProjectDirection.is_active.is_(True),
        )
        .order_by(models.ProjectDirection.position.asc(), models.ProjectDirection.created_at.asc())
        .all()
    )


def clean_masks(masks: Iterable[str]) -> list[str]:
    seen = set()
    result = []
    for mask in masks or []:
        normalized = normalize_mask(mask)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def match_campaign_to_masks(campaign_name: str, masks: Iterable[str]) -> tuple[bool, str | None]:
    haystack = normalize_mask(campaign_name)
    for mask in masks or []:
        normalized = normalize_mask(mask)
        if normalized and normalized in haystack:
            return True, normalized
    return False, None


def build_direction_matches(
    db: Session,
    client_id: uuid.UUID,
    platform: str = "all",
    include_inactive: bool = False,
):
    campaigns = campaign_query(db, client_id, platform=platform, only_active=not include_inactive).all()
    directions = get_active_directions(db, client_id)
    direction_masks = {
        str(direction.id): [m.mask for m in sorted(direction.masks, key=lambda item: item.position)]
        for direction in directions
    }

    campaign_to_direction: dict[str, str] = {}
    direction_to_campaigns: dict[str, list[str]] = {str(direction.id): [] for direction in directions}
    matched_masks: dict[str, str] = {}

    for campaign in campaigns:
        cid = str(campaign.id)
        for direction in directions:
            ok, mask = match_campaign_to_masks(campaign.name, direction_masks.get(str(direction.id), []))
            if ok:
                did = str(direction.id)
                campaign_to_direction[cid] = did
                direction_to_campaigns[did].append(cid)
                if mask:
                    matched_masks[cid] = mask
                break

    unassigned = [str(campaign.id) for campaign in campaigns if str(campaign.id) not in campaign_to_direction]
    return {
        "campaigns": campaigns,
        "directions": directions,
        "campaign_to_direction": campaign_to_direction,
        "direction_to_campaigns": direction_to_campaigns,
        "matched_masks": matched_masks,
        "unassigned": unassigned,
    }


def serialize_direction(direction: models.ProjectDirection, campaign_ids: list[str] | None = None) -> dict:
    masks = sorted(direction.masks, key=lambda item: item.position)
    ids = campaign_ids or []
    return {
        "id": direction.id,
        "client_id": direction.client_id,
        "name": direction.name,
        "position": direction.position,
        "is_active": direction.is_active,
        "masks": masks,
        "campaign_ids": ids,
        "campaign_count": len(ids),
        "created_at": direction.created_at,
        "updated_at": direction.updated_at,
    }


def preview_masks(
    db: Session,
    client_id: uuid.UUID,
    masks: Iterable[str],
    platform: str = "all",
    exclude_direction_id: uuid.UUID | None = None,
) -> dict:
    cleaned = clean_masks(masks)
    existing = build_direction_matches(db, client_id, platform=platform, include_inactive=True)
    excluded = str(exclude_direction_id) if exclude_direction_id else None
    directions_by_id = {str(d.id): d for d in existing["directions"]}
    campaigns = []
    conflict_count = 0

    for campaign in existing["campaigns"]:
        matched, mask = match_campaign_to_masks(campaign.name, cleaned)
        existing_did = existing["campaign_to_direction"].get(str(campaign.id))
        if excluded and existing_did == excluded:
            existing_did = None
        conflict = directions_by_id.get(existing_did) if existing_did else None
        if matched and conflict:
            conflict_count += 1
        status, status_label = campaign_status(campaign)
        campaigns.append({
            "id": str(campaign.id),
            "name": campaign.name,
            "platform": platform_key(campaign.integration.platform if campaign.integration else None),
            "status": status,
            "status_label": status_label,
            "selected": matched,
            "is_active": bool(getattr(campaign, "is_active", False)),
            "matched_mask": mask,
            "conflict_direction_id": str(conflict.id) if conflict else None,
            "conflict_direction_name": conflict.name if conflict else None,
        })
    campaigns.sort(key=lambda item: (not item["selected"], item["status"] != "active", item["name"].lower()))

    return {
        "total_campaigns": len(existing["campaigns"]),
        "matched_count": sum(1 for campaign in campaigns if campaign["selected"]),
        "conflict_count": conflict_count,
        "campaigns": campaigns,
    }


def suggest_directions(
    db: Session,
    client_id: uuid.UUID,
    platform: str = "all",
    limit: int = 8,
    only_unassigned: bool = False,
) -> list[dict]:
    if only_unassigned:
        matches = build_direction_matches(db, client_id, platform=platform)
        unassigned_ids = set(matches["unassigned"])
        campaigns = [campaign for campaign in matches["campaigns"] if str(campaign.id) in unassigned_ids]
    else:
        campaigns = campaign_query(db, client_id, platform=platform, only_active=True).all()

    if len(campaigns) < 2:
        return []

    token_to_campaigns: dict[str, set[str]] = {}
    for campaign in campaigns:
        raw = normalize_mask(campaign.name)
        for token in re.split(r"[\s/\|+\-_:\[\](),.;]+", raw):
            token = normalize_mask(token)
            if len(token) < 3 or token.isdigit() or token in STOP_TOKENS:
                continue
            token_to_campaigns.setdefault(token, set()).add(str(campaign.id))

    total = len(campaigns)
    candidates = []
    for token, ids in token_to_campaigns.items():
        count = len(ids)
        if count <= 1 or count >= total:
            continue
        candidates.append((token, ids))

    candidates.sort(key=lambda item: (len(item[1]), len(item[0])), reverse=True)
    used: set[str] = set()
    suggestions = []
    for token, ids in candidates:
        if ids.issubset(used):
            continue
        used.update(ids)
        suggestions.append({
            "name": token[:1].upper() + token[1:],
            "masks": [token],
            "matched_count": len(ids),
            "campaign_ids": sorted(ids),
        })
        if len(suggestions) >= limit:
            break
    return suggestions


def direction_stats(
    db: Session,
    client: models.Client,
    d_start: date | None,
    d_end: date,
    platform: str = "all",
    yandex_conversion_overrides: dict | None = None,
    yandex_prev_conversion_overrides: dict | None = None,
    avito_conversion_overrides: dict | None = None,
    avito_prev_conversion_overrides: dict | None = None,
) -> dict:
    matches = build_direction_matches(db, client.id, platform=platform, include_inactive=True)
    label_key = normalize_label(client.direction_label)
    label = LABELS.get(label_key, "Направления")
    if not matches["directions"]:
        return {
            "label": label,
            "label_key": label_key,
            "mode": "cards",
            "total_expenses": 0,
            "items": [],
        }

    all_campaign_ids = [str(campaign.id) for campaign in matches["campaigns"]]
    if not all_campaign_ids:
        return {
            "label": label,
            "label_key": label_key,
            "mode": "cards",
            "total_expenses": 0,
            "items": [],
        }

    # По ТЗ «Направления» §4.5: конверсии приходят в разрезе кампании, а
    # направление = сумма лидов своих кампаний. Поэтому считаем кампании той же
    # точной Metrika-атрибуцией (оверрайды), что и таблица кампаний — иначе
    # разбивка расходится с таблицей (раньше тут был грубый fallback по бюджету).
    stats = StatsService.get_campaign_stats(
        db,
        [client.id],
        d_start,
        d_end,
        platform=platform,
        campaign_ids=[uuid.UUID(cid) for cid in all_campaign_ids],
        yandex_conversion_overrides=yandex_conversion_overrides,
        yandex_prev_conversion_overrides=yandex_prev_conversion_overrides,
        avito_conversion_overrides=avito_conversion_overrides,
        avito_prev_conversion_overrides=avito_prev_conversion_overrides,
    )
    stat_by_id = {str(item.get("id")): item for item in stats}
    total_expenses = sum(float(item.get("cost") or 0) for item in stats)

    def aggregate(ids: list[str]) -> dict:
        rows = [stat_by_id[cid] for cid in ids if cid in stat_by_id]
        impressions = sum(int(row.get("impressions") or 0) for row in rows)
        expenses = sum(float(row.get("cost") or 0) for row in rows)
        leads = sum(int(row.get("conversions") or 0) for row in rows)
        cpl = round(expenses / leads, 2) if leads > 0 else 0
        weighted_trend = 0.0
        if rows:
            weights = sum(abs(float(row.get("cost") or 0)) for row in rows) or len(rows)
            weighted_trend = sum(float(row.get("trend_cpa") or 0) * (abs(float(row.get("cost") or 0)) or 1) for row in rows) / weights
        return {
            "impressions": impressions,
            "expenses": round(expenses, 2),
            "budget_share": round((expenses / total_expenses) * 100, 1) if total_expenses > 0 else 0,
            "leads": leads,
            "cpl": cpl,
            "trend": round(weighted_trend, 1),
        }

    items = []
    for direction in matches["directions"]:
        ids = matches["direction_to_campaigns"].get(str(direction.id), [])
        if not ids:
            continue
        items.append({
            "id": str(direction.id),
            "name": direction.name,
            "is_unassigned": False,
            "campaign_ids": ids,
            "campaign_count": len(ids),
            **aggregate(ids),
        })

    if matches["unassigned"]:
        ids = matches["unassigned"]
        unassigned_stats = aggregate(ids)
        if unassigned_stats["impressions"] > 0 or unassigned_stats["expenses"] > 0:
            items.append({
                "id": "unassigned",
                "name": "Без направления",
                "is_unassigned": True,
                "campaign_ids": ids,
                "campaign_count": len(ids),
                **unassigned_stats,
            })

    return {
        "label": label,
        "label_key": label_key,
        "mode": "table" if len(items) >= 10 else "cards",
        "total_expenses": round(total_expenses, 2),
        "items": items,
    }
