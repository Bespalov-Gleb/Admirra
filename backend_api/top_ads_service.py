"""
Сервис для получения топ объявлений (постов) с изображениями для блока "Лучшие посты".
Использует Yandex Direct API (Ads.get, AdImages.get, Reports) и fallback на кампании для VK.
"""
import logging
import uuid
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from core import models
from core import security
from backend_api.stats_service import StatsService
from automation.yandex_direct import YandexDirectAPI

logger = logging.getLogger(__name__)


async def get_top_ads_with_images(
    db: Session,
    client_ids: List[uuid.UUID],
    d_start: Optional[date],
    d_end: date,
    platform: str = "all",
    campaign_ids: Optional[List[uuid.UUID]] = None,
    vk_goal_action_ids: Optional[List[str]] = None,
    limit: int = 4,
) -> List[Dict[str, Any]]:
    """
    Возвращает топ N объявлений (постов) с image_url, title, impressions, clicks, ctr, cost.
    Для Yandex: реальные объявления из Ads.get + AdImages.get + AD_PERFORMANCE_REPORT.
    Для VK: fallback на кампании (без image_url) — VK Ads API не предоставляет ad-level креативы с превью в доступной документации.
    """
    if not client_ids:
        return []

    date_from = (d_start or d_end - timedelta(days=13)).strftime("%Y-%m-%d")
    date_to = d_end.strftime("%Y-%m-%d")

    result: List[Dict[str, Any]] = []
    seen_ids: set = set()

    # --- Yandex Direct ---
    if platform in ["all", "yandex"]:
        yandex_ads = await _get_yandex_top_ads(
            db, client_ids, date_from, date_to, campaign_ids, limit
        )
        for ad in yandex_ads:
            key = f"yandex_{ad.get('id', '')}"
            if key not in seen_ids:
                seen_ids.add(key)
                result.append(ad)
                if len(result) >= limit:
                    break
        # Fallback: если ad-level API вернул 400/пусто — показываем кампании как «посты»
        if len(result) < limit and platform in ["all", "yandex"]:
            yandex_campaigns = _get_yandex_top_ads_fallback(
                db, client_ids, d_start, d_end, campaign_ids, limit - len(result)
            )
            for ad in yandex_campaigns:
                key = f"yd_camp_{ad.get('id', '')}"
                if key not in seen_ids:
                    seen_ids.add(key)
                    result.append(ad)
                    if len(result) >= limit:
                        break
        if len(result) >= limit:
            return result[:limit]

    # --- VK Ads (fallback: кампании без image_url) ---
    if platform in ["all", "vk"]:
        vk_ads = _get_vk_top_ads_fallback(
            db, client_ids, d_start, d_end, campaign_ids, vk_goal_action_ids, limit - len(result)
        )
        for ad in vk_ads:
            key = f"vk_{ad.get('id', '')}"
            if key not in seen_ids:
                seen_ids.add(key)
                result.append(ad)
                if len(result) >= limit:
                    break

    return result[:limit]


async def _get_yandex_top_ads(
    db: Session,
    client_ids: List[uuid.UUID],
    date_from: str,
    date_to: str,
    campaign_ids: Optional[List[uuid.UUID]],
    limit: int,
) -> List[Dict[str, Any]]:
    """Получает топ объявления Yandex с изображениями через API."""
    integrations = db.query(models.Integration).filter(
        models.Integration.client_id.in_(client_ids),
        models.Integration.platform == models.IntegrationPlatform.YANDEX_DIRECT,
    ).all()

    if not integrations:
        return []

    integration_ids_filter = None
    if campaign_ids:
        camp_int = db.query(models.Campaign.integration_id).filter(
            models.Campaign.id.in_(campaign_ids)
        ).distinct().all()
        integration_ids_filter = [c[0] for c in camp_int if c[0]]
        if integration_ids_filter:
            integrations = [i for i in integrations if i.id in integration_ids_filter]
    elif len(client_ids) == 1:
        active_int = db.query(models.Campaign.integration_id).join(
            models.Integration
        ).filter(
            models.Integration.client_id.in_(client_ids),
            models.Campaign.is_active.is_(True),
        ).distinct().all()
        aid_list = [r[0] for r in active_int if r[0]]
        if aid_list:
            integration_ids_filter = aid_list
            integrations = [i for i in integrations if i.id in integration_ids_filter]

    all_ads: List[Dict[str, Any]] = []

    for integration in integrations:
        api = None
        yandex_campaign_ids = []
        try:
            access_token = security.decrypt_token(integration.access_token)
            if not access_token:
                continue

            # Используем тот же профиль, что и при синхронизации
            client_login = None
            if integration.agency_client_login and str(integration.agency_client_login).lower() not in ["unknown", "none", ""]:
                client_login = integration.agency_client_login
            elif integration.account_id:
                client_login = integration.account_id
            api = YandexDirectAPI(access_token, client_login=client_login)

            # Получаем external_id кампаний для этой интеграции
            camp_query = db.query(models.Campaign.external_id).filter(
                models.Campaign.integration_id == integration.id,
            )
            if campaign_ids:
                camp_query = camp_query.filter(models.Campaign.id.in_(campaign_ids))
            yandex_campaign_ids = [
                int(c[0]) for c in camp_query.all()
                if c[0] and str(c[0]).isdigit()
            ]

            if not yandex_campaign_ids:
                continue

            # Ограничиваем период 31 днём — большие отчёты часто таймаутят (201/202)
            try:
                dt_from = datetime.strptime(date_from, "%Y-%m-%d").date()
                dt_to = datetime.strptime(date_to, "%Y-%m-%d").date()
                if (dt_to - dt_from).days > 31:
                    date_from = (dt_to - timedelta(days=31)).strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                pass

            # 1. AD_PERFORMANCE_REPORT — статистика по объявлениям
            report_ads = await api.get_report(
                date_from, date_to, level="ad",
                campaign_ids=yandex_campaign_ids,
                max_retries=3,
            )

            if not report_ads:
                logger.info(f"top-ads: No ad-level rows for integration {integration.id}, will use campaign fallback")
                continue

            # Агрегируем по ad_id
            ad_stats: Dict[str, Dict] = {}
            for row in report_ads:
                ad_id = str(row.get("ad_id", ""))
                if not ad_id:
                    continue
                if ad_id not in ad_stats:
                    ad_stats[ad_id] = {
                        "ad_id": ad_id,
                        "campaign_id": row.get("campaign_id"),
                        "campaign_name": row.get("campaign_name", ""),
                        "impressions": 0,
                        "clicks": 0,
                        "cost": 0.0,
                        "conversions": 0,
                    }
                try:
                    ad_stats[ad_id]["impressions"] += int(row.get("impressions", 0) or 0)
                    ad_stats[ad_id]["clicks"] += int(row.get("clicks", 0) or 0)
                    ad_stats[ad_id]["cost"] += float(row.get("cost", 0) or 0)
                    ad_stats[ad_id]["conversions"] += int(row.get("conversions", 0) or 0)
                except (TypeError, ValueError):
                    pass

            # Сортируем по conversions, затем cost
            sorted_ads = sorted(
                ad_stats.values(),
                key=lambda x: (x["conversions"], x["cost"]),
                reverse=True,
            )[:limit * 2]

            if not sorted_ads:
                logger.info(f"top-ads: No sorted ads after aggregation for integration {integration.id}")
                continue

            ad_ids_to_fetch = [int(a["ad_id"]) for a in sorted_ads if a["ad_id"].isdigit()][:limit * 2]
            if not ad_ids_to_fetch:
                # AdId не отображается для Smart-кампаний и кампаний из Мастера (документация Яндекс.Директ API).
                # Используем Ads.get по campaign_ids — получаем объявления с изображениями, статистика на уровне кампании.
                logger.info(f"top-ads: AdId='--' (Smart/Мастер кампаний), using Ads.get by campaign_ids for integration {integration.id}")
                d_start = datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else None
                d_end = datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else datetime.utcnow().date()
                ads_via_campaigns = await _get_yandex_ads_via_campaigns_get(
                    api, db, integration, client_ids, yandex_campaign_ids, d_start, d_end, campaign_ids, limit
                )
                all_ads.extend(ads_via_campaigns)
                continue

            # 2. Ads.get — title и AdImageHash
            ads_info = await api.get_ads_with_titles_and_images(ad_ids=ad_ids_to_fetch)
            ad_info_map = {str(a["Id"]): a for a in ads_info}

            # 3. AdImages.get — PreviewUrl по хешам
            hashes = list({
                a["AdImageHash"] for a in ads_info
                if a.get("AdImageHash")
            })
            hash_to_url = await api.get_ad_images_preview_urls(hashes) if hashes else {}

            for stat in sorted_ads:
                ad_id = stat["ad_id"]
                info = ad_info_map.get(ad_id, {})
                title = info.get("Title") or stat.get("campaign_name", "") or f"Объявление {ad_id}"
                ad_image_hash = info.get("AdImageHash")
                image_url = (hash_to_url.get(ad_image_hash) or "") if ad_image_hash else None

                imps = stat.get("impressions", 0) or 0
                clicks = stat.get("clicks", 0) or 0
                cost = stat.get("cost", 0) or 0
                ctr = round(clicks / imps * 100, 2) if imps else 0

                all_ads.append({
                    "id": f"yd_{ad_id}",
                    "title": title[:120] if title else f"Объявление {ad_id}",
                    "text": (info.get("Text") or "")[:200],
                    "ad_type": info.get("Type", ""),
                    "image_url": image_url,
                    "thumbnail_url": info.get("ThumbnailUrl"),
                    "impressions": imps,
                    "clicks": clicks,
                    "cost": round(cost, 2),
                    "ctr": ctr,
                    "conversions": stat.get("conversions", 0),
                    "platform": "yandex",
                    "subtitle": "Яндекс.Директ",
                })
                if len(all_ads) >= limit:
                    break

        except Exception as e:
            logger.warning(f"Yandex top-ads for integration {integration.id}: {e}")
            # При таймауте/ошибке отчёта пробуем Ads.get (объявления с изображениями, статистика из БД)
            err_str = str(e).lower()
            if api and yandex_campaign_ids and ("retries" in err_str or "timeout" in err_str):
                try:
                    d_start = datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else None
                    d_end = datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else datetime.utcnow().date()
                    ads_via = await _get_yandex_ads_via_campaigns_get(
                        api, db, integration, client_ids, yandex_campaign_ids, d_start, d_end, campaign_ids, limit
                    )
                    all_ads.extend(ads_via)
                except Exception as fallback_err:
                    logger.debug(f"Ads.get fallback failed: {fallback_err}")

    out = sorted(all_ads, key=lambda x: (x.get("conversions", 0), x.get("cost", 0)), reverse=True)[:limit]
    if not out:
        logger.info(f"top-ads: Yandex path returned 0 ads for client_ids={client_ids}, fallback will add campaigns")
    return out


async def _get_yandex_ads_via_campaigns_get(
    api: YandexDirectAPI,
    db: Session,
    integration: models.Integration,
    client_ids: List[uuid.UUID],
    yandex_campaign_ids: List[int],
    d_start: Optional[date],
    d_end: date,
    campaign_ids: Optional[List[uuid.UUID]],
    limit: int,
) -> List[Dict[str, Any]]:
    """
    Для Smart-кампаний и кампаний из Мастера: AdId в отчёте = '--' (документация Яндекс.Директ API).
    Получаем объявления через Ads.get по campaign_ids, статистика — на уровне кампании из БД.
    """
    if not yandex_campaign_ids:
        return []

    # Наши campaign_id (UUID) для этих Yandex external_id
    ext_strs = [str(x) for x in yandex_campaign_ids]
    camp_rows = db.query(models.Campaign.id, models.Campaign.external_id).filter(
        models.Campaign.integration_id == integration.id,
        models.Campaign.external_id.in_(ext_strs),
    ).all()
    our_campaign_ids = [r[0] for r in camp_rows]
    ext_to_id = {str(r.external_id): str(r.id) for r in camp_rows}

    if not our_campaign_ids:
        return []

    # Статистика кампаний (может быть пустой для новых/несинканных кампаний — это нормально)
    campaigns = StatsService.get_campaign_stats(
        db, client_ids, d_start, d_end, "yandex", our_campaign_ids, None
    )
    id_to_stats = {str(c["id"]): c for c in campaigns}
    campaign_by_ext: Dict[str, Dict] = {}
    for ext, our_id in ext_to_id.items():
        if our_id in id_to_stats:
            campaign_by_ext[ext] = id_to_stats[our_id]

    # Топ кампаний по conversions, cost; если статистики нет — берём все campaign_ids
    if campaign_by_ext:
        sorted_campaigns = sorted(
            campaign_by_ext.values(),
            key=lambda x: (x.get("conversions", 0) or 0, x.get("cost", 0) or 0),
            reverse=True,
        )[:limit]
        top_ext_ids = [
            int(ext) for ext, stats in campaign_by_ext.items()
            if stats in sorted_campaigns
        ]
    else:
        sorted_campaigns = []
        top_ext_ids = yandex_campaign_ids[:limit * 2]

    if not top_ext_ids:
        return []

    # Ads.get по campaign_ids
    ads_info = await api.get_ads_with_titles_and_images(campaign_ids=top_ext_ids)
    if not ads_info:
        logger.info(f"top-ads: Ads.get returned 0 ads for campaign_ids={top_ext_ids} (Smart/Мастер)")
        return []

    # Первое объявление по каждой кампании
    ad_by_campaign: Dict[str, Dict] = {}
    for ad in ads_info:
        cid = str(ad.get("CampaignId", ""))
        if cid not in ad_by_campaign:
            ad_by_campaign[cid] = ad

    hashes = list({a["AdImageHash"] for a in ad_by_campaign.values() if a.get("AdImageHash")})
    hash_to_url = await api.get_ad_images_preview_urls(hashes) if hashes else {}

    result = []
    # Строим результат: если есть статистика — сортируем по ней, иначе просто по порядку
    items_to_process = (
        [(next((e for e in campaign_by_ext if campaign_by_ext[e] is stats), None), stats) for stats in sorted_campaigns]
        if sorted_campaigns
        else [(str(cid), {}) for cid in top_ext_ids]
    )
    for ext, stats in items_to_process:
        if not ext or str(ext) not in ad_by_campaign:
            continue
        ad = ad_by_campaign[str(ext)]
        imps = stats.get("impressions", 0) or 0
        clicks = stats.get("clicks", 0) or 0
        cost = stats.get("cost", 0) or 0
        convs = stats.get("conversions", 0) or 0
        title = (ad.get("Title") or stats.get("name", "") or "Объявление").replace("[ЯД] ", "")
        image_url = ad.get("PreviewUrl") or ((hash_to_url.get(ad.get("AdImageHash")) or "") if ad.get("AdImageHash") else None)
        result.append({
            "id": f"yd_{ad['Id']}",
            "title": title[:120] if title else "Объявление",
            "text": (ad.get("Text") or "")[:200],
            "ad_type": ad.get("Type", "SMART_AD"),
            "image_url": image_url,
            "thumbnail_url": ad.get("ThumbnailUrl"),
            "impressions": imps,
            "clicks": clicks,
            "cost": round(float(cost), 2),
            "ctr": round(clicks / imps * 100, 2) if imps else 0,
            "conversions": convs,
            "platform": "yandex",
            "subtitle": "Яндекс.Директ",
        })
        if len(result) >= limit:
            break
    logger.info(f"top-ads: Ads.get path returned {len(result)} posts for Smart/Мастер campaigns")
    return result


def _get_yandex_top_ads_fallback(
    db: Session,
    client_ids: List[uuid.UUID],
    d_start: Optional[date],
    d_end: date,
    campaign_ids: Optional[List[uuid.UUID]],
    limit: int,
) -> List[Dict[str, Any]]:
    """
    Fallback: топ кампаний Yandex как «посты» (без image_url), когда AD_PERFORMANCE_REPORT недоступен.
    """
    campaigns = StatsService.get_campaign_stats(
        db, client_ids, d_start, d_end, "yandex", campaign_ids, None
    )
    sorted_campaigns = sorted(
        campaigns,
        key=lambda x: (x.get("conversions", 0) or 0, x.get("cost", 0) or 0),
        reverse=True,
    )[:limit]

    result = []
    for c in sorted_campaigns:
        imps = c.get("impressions", 0) or 0
        clicks = c.get("clicks", 0) or 0
        name = (c.get("name", "") or "Кампания").replace("[ЯД] ", "")
        result.append({
            "id": f"yd_camp_{c.get('id', '')}",
            "title": name,
            "text": "",
            "ad_type": "CAMPAIGN_FALLBACK",
            "image_url": None,
            "thumbnail_url": None,
            "impressions": imps,
            "clicks": clicks,
            "cost": c.get("cost", 0),
            "ctr": round(clicks / imps * 100, 2) if imps else 0,
            "conversions": c.get("conversions", 0),
            "platform": "yandex",
            "subtitle": "Яндекс.Директ",
        })
    return result


def _get_vk_top_ads_fallback(
    db: Session,
    client_ids: List[uuid.UUID],
    d_start: Optional[date],
    d_end: date,
    campaign_ids: Optional[List[uuid.UUID]],
    vk_goal_action_ids: Optional[List[str]],
    limit: int,
) -> List[Dict[str, Any]]:
    """
    Fallback: топ кампаний VK без image_url.
    VK Ads API v2 не предоставляет ad-level креативы с превью в доступной документации.
    """
    campaigns = StatsService.get_campaign_stats(
        db, client_ids, d_start, d_end, "vk", campaign_ids, vk_goal_action_ids
    )
    sorted_campaigns = sorted(
        campaigns,
        key=lambda x: (x.get("conversions", 0) or 0, x.get("cost", 0) or 0),
        reverse=True,
    )[:limit]

    result = []
    for c in sorted_campaigns:
        imps = c.get("impressions", 0) or 0
        clicks = c.get("clicks", 0) or 0
        result.append({
            "id": c.get("id", ""),
            "title": (c.get("name", "") or "Кампания").replace("[VK] ", ""),
            "image_url": None,
            "impressions": imps,
            "clicks": clicks,
            "cost": c.get("cost", 0),
            "ctr": round(clicks / imps * 100, 2) if imps else 0,
            "conversions": c.get("conversions", 0),
            "platform": "vk",
            "subtitle": "VK Ads",
        })
    return result
