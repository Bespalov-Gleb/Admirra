"""Detached advertising snapshot: no SQL connection is held during HTTP.

Only a complete snapshot may replace statistics. The caller supplies the durable
execution fence and commits statistics, business status and watermark together.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta
import json
import logging
import uuid

from sqlalchemy import delete, select

from core import models, security
from automation import metrika_goal_work as goals
from automation.ads_sync_contract import bounded, identifier, number, IncompleteAdsSnapshot
from automation.sync_request import settings_digest

logger = logging.getLogger(__name__)
PLATFORMS = {models.IntegrationPlatform.YANDEX_DIRECT, models.IntegrationPlatform.VK_ADS,
             models.IntegrationPlatform.AVITO_ADS}


@dataclass(frozen=True)
class Plan:
    integration_id: uuid.UUID
    client_id: uuid.UUID
    owner_id: uuid.UUID
    platform: models.IntegrationPlatform
    settings: str = field(repr=False)
    start: str
    end: str
    credentials: dict = field(repr=False)
    known: dict = field(repr=False)
    goal_plan: goals.GoalPlan | None = field(repr=False)


def prepare(db, integration_id, start, end):
    from automation.sync import _selected_yandex_direct_profile, _yandex_app_credentials, _json_list
    integration = db.get(models.Integration, integration_id)
    client = db.get(models.Client, integration.client_id)
    if integration.platform not in PLATFORMS or date.fromisoformat(start) > date.fromisoformat(end):
        raise ValueError("Unsupported advertising snapshot")
    plain = lambda value: security.decrypt_token(value) if value else None
    credentials = dict(token=plain(integration.access_token), refresh=plain(integration.refresh_token),
        account=integration.account_id, profile=_selected_yandex_direct_profile(integration),
        agency=integration.is_agency, agency_login=integration.agency_client_login,
        client_id=plain(integration.platform_client_id), secret=plain(integration.platform_client_secret))
    if integration.platform == models.IntegrationPlatform.AVITO_ADS:
        if not credentials["client_id"] or not credentials["secret"]:
            raise ValueError("Avito credentials unavailable")
    elif not credentials["token"]:
        raise ValueError("Advertising credentials unavailable")
    if integration.platform == models.IntegrationPlatform.YANDEX_DIRECT:
        owner = db.get(models.User, client.owner_id)
        credentials["finance"] = owner.yandex_finance_token if owner else None
        credentials["oauth"] = _yandex_app_credentials(integration)
    goal_plan = None
    if integration.platform != models.IntegrationPlatform.VK_ADS:
        if _json_list(integration.selected_goals) or integration.primary_goal_id:
            goal_plan = goals.prepare(db, integration.id, start, end)
            if goal_plan is None:
                raise ValueError("Selected goals have no available Metrika counter")
    known = {str(c.external_id): dict(name=c.name, goal_action_id=c.vk_goal_action_id,
                                    goal_action_name=c.vk_goal_action_name)
             for c in db.scalars(select(models.Campaign).where(models.Campaign.integration_id == integration.id))
             if c.external_id}
    return Plan(integration.id, client.id, client.owner_id, integration.platform,
                settings_digest(integration, client), start, end, credentials, known, goal_plan)


def windows(start, end):
    current, last = date.fromisoformat(start), date.fromisoformat(end)
    while current <= last:
        finish = min(last, current + timedelta(days=89))
        yield current.isoformat(), finish.isoformat()
        current = finish + timedelta(days=1)


def make_api(plan):
    c = plan.credentials
    if plan.platform == models.IntegrationPlatform.YANDEX_DIRECT:
        from automation.yandex_direct import YandexDirectAPI
        api = YandexDirectAPI(c["token"], client_login=c["profile"], finance_token=c["finance"])
    elif plan.platform == models.IntegrationPlatform.VK_ADS:
        from automation.vk_ads import VKAdsAPI
        api = VKAdsAPI(c["token"], c["account"], send_client_id=False)
    else:
        from automation.avito_ads import AvitoAdsAPI
        api = AvitoAdsAPI(credential_type="client_credentials", client_id=c["client_id"],
                         client_secret=c["secret"], account_id=c["account"])
    api.strict_sync = True
    return api


async def refresh(plan, error):
    """One authorization recovery; never exchange credentials after HTTP 5xx."""
    from backend_api.services import IntegrationService
    c = plan.credentials
    unauthorized = "401" in str(error) or "expired_token" in str(error) or "Unauthorized" in str(error)
    if plan.platform == models.IntegrationPlatform.YANDEX_DIRECT:
        if unauthorized and c["refresh"]:
            return await IntegrationService.refresh_yandex_token(c["refresh"], *c["oauth"])
    elif plan.platform == models.IntegrationPlatform.VK_ADS:
        from backend_api.integrations import VK_CLIENT_ID, VK_CLIENT_SECRET
        from automation.vk_ads import (vk_campaigns_error_needs_agency_client_retry,
                                      exchange_vk_agency_client_credentials_for_integration)
        if unauthorized:
            if c["refresh"]:
                data = await IntegrationService.refresh_vk_token(c["refresh"], VK_CLIENT_ID, VK_CLIENT_SECRET)
                if data and data.get("access_token"):
                    return data
            if c["client_id"] and c["secret"]:
                return await IntegrationService.exchange_vk_token(c["client_id"], c["secret"])
        if c["agency"] and vk_campaigns_error_needs_agency_client_retry(error):
            return await exchange_vk_agency_client_credentials_for_integration(
                client_id=VK_CLIENT_ID, client_secret=VK_CLIENT_SECRET, agency_access_token=c["token"],
                agency_client_login=c["agency_login"], account_id=c["account"])
    return None


def save_credentials(integration, data):
    from datetime import datetime, timezone
    if not isinstance(data, dict) or not isinstance(data.get("access_token"), str) or not data["access_token"]:
        raise ValueError("Provider returned no refreshed credentials")
    integration.access_token = security.encrypt_token(data["access_token"])
    if data.get("refresh_token"):
        integration.refresh_token = security.encrypt_token(data["refresh_token"])
    if data.get("expires_in") is not None:
        seconds = int(data["expires_in"])
        if not 0 < seconds <= 366 * 86400:
            raise ValueError("Invalid OAuth expiry")
        integration.expires_at = datetime.now(timezone.utc) + timedelta(seconds=seconds)


async def collect(plan):
    api = make_api(plan)
    direct = plan.platform == models.IntegrationPlatform.YANDEX_DIRECT
    avito = plan.platform == models.IntegrationPlatform.AVITO_ADS
    catalog = await api.get_campaigns(plan.credentials["account"]) if avito else await api.get_campaigns()
    if catalog is None and not direct:
        raise IncompleteAdsSnapshot("Advertising catalog unavailable")
    catalog = catalog or []
    by_id = {}
    for entry in catalog:
        key = identifier(entry.get("id"))
        if key in by_id:
            raise IncompleteAdsSnapshot("Duplicate campaign in catalog")
        by_id[key] = dict(entry)
    data = {"campaigns": [], "groups": [], "keywords": [], "creatives": []}
    for start, end in windows(plan.start, plan.end):
        if direct:
            for level, key in (("campaign", "campaigns"), ("group", "groups"), ("keyword", "keywords")):
                data[key].extend(await api.get_report(start, end, level=level))
                bounded(data[key])
        elif avito:
            # Include archived and previously known campaigns: a historical
            # window may contain their spend even if today's catalog does not.
            for campaign in sorted(set(by_id) | set(plan.known)):
                bundle = await api.get_campaign_statistics_bundle(campaign, start, end, plan.credentials["account"])
                for key in ("campaigns", "groups", "creatives"):
                    if not isinstance(bundle.get(key), list):
                        raise IncompleteAdsSnapshot("Avito statistics level unavailable")
                    data[key].extend(bundle[key])
                    bounded(data[key])
        else:
            # Explicitly include known campaigns omitted from today's catalog.
            requested = [*catalog, *[dict(id=key, name=meta["name"]) for key, meta in plan.known.items() if key not in by_id]]
            data["campaigns"].extend(await api.get_statistics(start, end, campaigns=requested))
            bounded(data["campaigns"])
    for rows in data.values():
        for row in rows:
            key = identifier(row.get("campaign_id"))
            if not direct and key not in by_id and key not in plan.known:
                raise IncompleteAdsSnapshot("Statistics escaped the requested campaign scope")
            by_id.setdefault(key, dict(id=key, name=row.get("campaign_name") or plan.known.get(key, {}).get("name")))
    if direct:
        # Strategy/balance are optional metadata, unlike the required reports.
        try:
            strategies = await api.get_campaign_strategies()
            for key, value in strategies.items():
                if str(key) in by_id:
                    by_id[str(key)]["bid_strategy"] = value
        except Exception as error:
            logger.warning("Optional Direct strategies unavailable (%s)", type(error).__name__)
    elif not avito:
        action_map = await api.get_goal_actions_from_statistics(list(by_id), plan.start, plan.end, campaigns=list(by_id.values()))
        for key, entry in by_id.items():
            action = action_map.get(key) or (entry.get("goal_action_id"), entry.get("goal_action_name"))
            if not action[0]:
                previous = plan.known.get(key, {})
                action = (previous.get("goal_action_id"), previous.get("goal_action_name"))
            entry.update(goal_action_id=action[0], goal_action_name=action[1])
        for row in data["campaigns"]:
            if row["conversions"] and not by_id[str(row["campaign_id"])].get("goal_action_id"):
                raise IncompleteAdsSnapshot("VK conversions have no confirmed objective")
    goal_rows, missing = await goals.collect(plan.goal_plan) if plan.goal_plan else ([], [])
    balance = None
    try:
        balance = await api.get_balance(plan.credentials["account"]) if avito else await api.get_balance()
        if balance and balance.get("balance") is not None:
            # Credit balances may be negative; don't coerce unavailable values to zero.
            from decimal import Decimal
            amount = Decimal(str(balance["balance"]))
            if not amount.is_finite() or abs(amount) >= Decimal("1e18"):
                raise ValueError("Invalid balance")
            balance = dict(balance=amount, currency=balance.get("currency") or "RUB")
        else:
            balance = None
    except Exception as error:
        logger.warning("Optional advertising balance unavailable (%s)", type(error).__name__)
        balance = None
    result = dict(catalog=list(by_id.values()), data=data, balance=balance, goals=goal_rows, missing=missing)
    bounded(result)
    validate(plan, result)
    return result


def validate(plan, snapshot):
    """Reject duplicate/truncated/out-of-window rows before any database writes."""
    for level, rows in snapshot["data"].items():
        seen = set()
        for row in rows:
            campaign = identifier(row.get("campaign_id"))
            day = date.fromisoformat(row["date"]).isoformat()
            if not plan.start <= day <= plan.end:
                raise IncompleteAdsSnapshot("Advertising response is outside requested dates")
            for metric in ("impressions", "clicks", "conversions"):
                number(row.get(metric), integer=True)
            number(row.get("cost"))
            child = (identifier(row.get("group_id")) if level == "groups" else
                     identifier(row.get("creative_id")) if level == "creatives" else
                     row.get("name") if level == "keywords" else None)
            if level == "keywords" and not isinstance(child, str):
                raise IncompleteAdsSnapshot("Keyword text missing")
            key = campaign, day, child
            if key in seen:
                raise IncompleteAdsSnapshot("Duplicate advertising statistic key")
            seen.add(key)


def apply(db, plan, snapshot, *, historical=False):
    from automation.sync import _upsert_campaign_catalog
    client = db.scalar(select(models.Client).where(models.Client.id == plan.client_id).with_for_update())
    integration = db.scalar(select(models.Integration).where(models.Integration.id == plan.integration_id).with_for_update())
    if not client or not integration or settings_digest(integration, client) != plan.settings:
        raise goals.GoalSettingsChanged("Advertising settings changed during collection")
    validate(plan, snapshot)
    catalog = _upsert_campaign_catalog(db, integration, snapshot["catalog"])
    if plan.platform == models.IntegrationPlatform.AVITO_ADS:
        # Preserve Avito discovery semantics without changing the user's
        # existing tracking selections, including historical archived entries.
        metadata = {str(row["id"]): row for row in snapshot["catalog"]}
        for row in snapshot["data"]["campaigns"]:
            key = str(row["campaign_id"])
            if key not in plan.known and metadata[key].get("state") != "ARCHIVED":
                catalog[key].is_active = True
    all_campaigns = list(db.scalars(select(models.Campaign).where(models.Campaign.integration_id == integration.id)))
    campaign_ids = [c.id for c in all_campaigns]
    levels = {
        models.IntegrationPlatform.YANDEX_DIRECT: (("campaigns", models.YandexStats), ("groups", models.YandexGroups), ("keywords", models.YandexKeywords)),
        models.IntegrationPlatform.VK_ADS: (("campaigns", models.VKStats),),
        models.IntegrationPlatform.AVITO_ADS: (("campaigns", models.AvitoStats), ("groups", models.AvitoGroups), ("creatives", models.AvitoCreatives)),
    }[plan.platform]
    start, end = date.fromisoformat(plan.start), date.fromisoformat(plan.end)
    for level, model in levels:
        if level == "keywords":
            # Old keyword rows had no campaign FK. They can only be replaced if
            # their name identifies a single campaign in this project.
            names = {c.name for c in all_campaigns} | {meta["name"] for meta in plan.known.values()}
            owners = {}
            for campaign_id, name in db.execute(select(models.Campaign.id, models.Campaign.name).join(models.Integration).where(
                    models.Integration.client_id == client.id)):
                owners.setdefault(name, set()).add(campaign_id)
            current_by_external = {str(c.external_id): c.id for c in all_campaigns}
            for external, meta in plan.known.items():
                if external in current_by_external:
                    owners.setdefault(meta["name"], set()).add(current_by_external[external])
            legacy_names = set(db.scalars(select(model.campaign_name).where(model.client_id == client.id,
                model.campaign_id.is_(None), model.campaign_name.in_(names), model.date >= start, model.date <= end)))
            if any(not owners.get(name) or not owners[name].issubset(set(campaign_ids)) for name in legacy_names):
                raise IncompleteAdsSnapshot("Legacy keyword rows have ambiguous campaign names")
            db.execute(delete(model).where(model.client_id == client.id, model.campaign_id.is_(None),
                model.campaign_name.in_(legacy_names), model.date >= start, model.date <= end))
        # Only this integration's IDs and exactly the successfully fetched window.
        db.execute(delete(model).where(model.client_id == plan.client_id, model.campaign_id.in_(campaign_ids),
                                       model.date >= start, model.date <= end))
        values = []
        for row in snapshot["data"][level]:
            campaign = catalog[str(row["campaign_id"])]
            value = {key: row[key] for key in ("impressions", "clicks", "conversions", "cost")}
            value.update(client_id=plan.client_id, campaign_id=campaign.id,
                         campaign_name=campaign.name, date=date.fromisoformat(row["date"]))
            if level == "keywords":
                value["keyword"] = row["name"]
            elif level == "groups":
                value.update(group_id=str(row["group_id"]), group_name=row.get("group_name") or row.get("name"))
            elif level == "creatives":
                value.update(creative_id=str(row["creative_id"]), creative_name=row.get("creative_name"), group_id=row.get("group_id"))
            if hasattr(model, "cpc"):
                value["cpc"] = row["cost"] / row["clicks"] if row["clicks"] else None
            if hasattr(model, "cpa"):
                value["cpa"] = row["cost"] / row["conversions"] if row["conversions"] else None
            if hasattr(model, "ctr"):
                value["ctr"] = row["clicks"] * 100 / row["impressions"] if row["impressions"] else None
            values.append(value)
        if values:
            db.execute(model.__table__.insert(), values)
    if plan.goal_plan:
        goals.apply(db, plan.goal_plan, snapshot["goals"], snapshot["missing"])
    if plan.platform == models.IntegrationPlatform.VK_ADS:
        for meta in snapshot["catalog"]:
            campaign = catalog[str(meta["id"])]
            if meta.get("goal_action_id"):
                campaign.vk_goal_action_id, campaign.vk_goal_action_name = meta["goal_action_id"], meta.get("goal_action_name")
        observed = {str(c.vk_goal_action_id) for c in all_campaigns if c.vk_goal_action_id}
        if integration.lead_action_types is None:
            from automation.vk_goal_action_mapping import is_vk_lead_form
            defaults = sorted(value for value in observed if is_vk_lead_form(value))
            if defaults:
                integration.lead_action_types = json.dumps(defaults)
                integration.vk_known_lead_action_types = json.dumps(sorted(observed))
        if integration.lead_action_types is not None:
            from automation.sync import _json_list
            known = set(_json_list(integration.vk_known_lead_action_types))
            if observed - known:
                integration.vk_known_lead_action_types = json.dumps(sorted(observed | known))
                integration.vk_new_lead_actions_pending = True
                try:
                    with db.begin_nested():
                        from backend_api.services.notifications import create_notification
                        create_notification(db, client.owner_id, "vk_lead_action_new",
                            f"В VK Ads появились новые типы действий · {client.name}",
                            "Проверьте состав заявок и CPL.", meta={"route": "/integrations", "integration_id": str(integration.id)})
                except Exception as error:
                    logger.warning("Optional VK notification unavailable (%s)", type(error).__name__)
    if not historical:
        balance = snapshot["balance"] or {}
        integration.balance, integration.currency = balance.get("balance"), balance.get("currency")


async def execute_history(factory, payload):
    from automation.integration_work_scope import require_scope, IntegrationScopeChanged
    def prepare_history(db):
        integration, _ = require_scope(db, payload, kind="history.backfill", integration_id=payload["integration_id"])
        return prepare(db, integration.id, payload["date_from"], payload["date_to"])
    with factory.begin() as db:
        plan = prepare_history(db)
    try:
        snapshot = await collect(plan)
    except Exception as error:
        credentials = await refresh(plan, error)
        if not credentials or not credentials.get("access_token"):
            raise
        with factory.begin() as db:
            client = db.scalar(select(models.Client).where(models.Client.id == plan.client_id).with_for_update())
            integration = db.scalar(select(models.Integration).where(models.Integration.id == plan.integration_id).with_for_update())
            require_scope(db, payload, kind="history.backfill", integration_id=plan.integration_id)
            if settings_digest(integration, client) != plan.settings:
                raise IntegrationScopeChanged("Integration changed during OAuth renewal")
            save_credentials(integration, credentials)
            from automation.metrika_sync_work import rebase_followups
            rebase_followups(db, integration, client, plan.settings)
            db.flush()
            plan = prepare_history(db)
        snapshot = await collect(plan)
    with factory.begin() as db:
        require_scope(db, payload, kind="history.backfill", integration_id=plan.integration_id)
        apply(db, plan, snapshot, historical=True)
        from automation.metrika_sync_work import rebase_followups
        integration = db.get(models.Integration, plan.integration_id)
        client = db.get(models.Client, plan.client_id)
        rebase_followups(db, integration, client, plan.settings)
        from backend_api.services.project_settings import update_actual_start_date
        update_actual_start_date(db, plan.client_id)
    try:
        from backend_api.cache_service import CacheService
        CacheService.invalidate_client(str(plan.client_id))
    except Exception as error:
        logger.warning("History cache invalidation unavailable (%s)", type(error).__name__)
    return "updated"
