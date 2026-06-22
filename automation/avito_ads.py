"""
Клиент Avito Ads API.

Спецификация: https://developers.avito.ru/api-catalog/ads/documentation
OpenAPI: GET https://developers.avito.ru/web/1/openapi/info/ads

Авторизация: POST https://api.avito.ru/token (grant_type=client_credentials).
Все методы Ads API привязаны к accountID в пути /ads/v1/account/{accountID}/...
Метрики статистики (StatsData): views, clicks, spend, spendBonus, ctr, cpc, cpm — без лидов/конверсий.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

# Документированные и встречающиеся статусы кампании (CampaignStatus).
# Точные значения Avito API нужно пополнять по логам, но неизвестные статусы
# нельзя превращать в OFF: такая кампания может быть активной.
AVITO_ADS_ACTIVE_STATUSES = frozenset({"active", "unpausing"})
AVITO_ADS_PAUSED_STATUSES = frozenset({
    "paused",
    "stopped",
    "inactive",
    "moderation",
    "rejected",
    "blocked",
    "draft",
    "finished",
})
AVITO_ADS_ARCHIVED_STATUSES = frozenset({"archived", "deleted", "removed", "completed"})


def _map_campaign_state(status: Optional[str]) -> str:
    normalized = str(status or "").strip().lower()
    if normalized in AVITO_ADS_ACTIVE_STATUSES:
        return "ON"
    if normalized in AVITO_ADS_ARCHIVED_STATUSES:
        return "ARCHIVED"
    if normalized in AVITO_ADS_PAUSED_STATUSES:
        return "OFF"
    return "UNKNOWN"


def _parse_stats_date(timestamp: Optional[str]) -> Optional[str]:
    if not timestamp:
        return None
    try:
        if "T" in timestamp:
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).date().isoformat()
        return datetime.strptime(timestamp[:10], "%Y-%m-%d").date().isoformat()
    except (ValueError, TypeError):
        return None


def _chunked(items: List[str], size: int = 100):
    for index in range(0, len(items), size):
        yield items[index:index + size]


class AvitoAdsAPI:
    def __init__(
        self,
        *,
        credential_type: str,
        api_key: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        account_id: Optional[str] = None,
        base_url: str = "https://api.avito.ru",
        timeout: float = 30.0,
    ) -> None:
        self.credential_type = credential_type
        self.api_key = (api_key or "").strip() or None
        self.client_id = (client_id or "").strip() or None
        self.client_secret = (client_secret or "").strip() or None
        self.account_id = (str(account_id).strip() if account_id is not None else "") or None
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._cached_bearer_token: Optional[str] = None

    def _require_account_id(self, account_id: Optional[str] = None) -> str:
        resolved = (account_id or self.account_id or "").strip()
        if not resolved or not resolved.isdigit():
            raise ValueError(
                "account_id (ID рекламного аккаунта Avito Рекламы) обязателен для Ads API"
            )
        return resolved

    async def _get_bearer_token(self) -> str:
        if self.credential_type == "single_api_key":
            if not self.api_key:
                raise ValueError("Bearer-токен Avito не задан")
            return self.api_key

        if self.credential_type != "client_credentials":
            raise ValueError("Поддерживается только client_credentials или single_api_key (готовый Bearer)")

        if self._cached_bearer_token:
            return self._cached_bearer_token

        if not self.client_id or not self.client_secret:
            raise ValueError("client_id и client_secret обязательны для client_credentials")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"Avito token exchange failed: {response.status_code} {response.text[:300]}"
                )
            payload = response.json()
            token = payload.get("access_token")
            if not token:
                raise RuntimeError("Avito token exchange returned empty access_token")
            self._cached_bearer_token = token
            return token

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
    ) -> dict:
        token = await self._get_bearer_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
            response = await client.request(
                method,
                f"{self.base_url}{path}",
                params=params,
                json=json_data,
            )
            if response.status_code >= 400:
                raise RuntimeError(
                    f"Avito request failed: {response.status_code} {path} {response.text[:500]}"
                )
            if not response.text:
                return {}
            return response.json()

    async def validate_credentials(self, account_id: Optional[str] = None) -> dict:
        """GET /ads/v1/account/{accountID}/balance — проверка ключа и accountID."""
        acc = self._require_account_id(account_id)
        return await self._request("GET", f"/ads/v1/account/{acc}/balance")

    async def get_account_info(self, account_id: Optional[str] = None) -> dict:
        """GET /ads/v1/account/{accountID}."""
        acc = self._require_account_id(account_id)
        return await self._request("GET", f"/ads/v1/account/{acc}")

    async def get_profiles_or_accounts(self, account_id: Optional[str] = None) -> List[dict]:
        """
        Родительский аккаунт + дочерние (GET /children).
        Используется для выбора кабинета в визарде.
        """
        acc = self._require_account_id(account_id)
        profiles: List[dict] = []

        try:
            account_payload = await self.get_account_info(acc)
            account = account_payload.get("account") if isinstance(account_payload, dict) else None
            if isinstance(account, dict):
                profiles.append(
                    {
                        "id": acc,
                        "name": account.get("shortName") or account.get("longName") or f"Аккаунт {acc}",
                        "type": "parent",
                    }
                )
            else:
                profiles.append({"id": acc, "name": f"Аккаунт {acc}", "type": "parent"})
        except Exception:
            profiles.append({"id": acc, "name": f"Аккаунт {acc}", "type": "parent"})

        try:
            children_payload = await self._request("GET", f"/ads/v1/account/{acc}/children")
            children = children_payload.get("children") if isinstance(children_payload, dict) else None
            if isinstance(children, list):
                for item in children:
                    child_account = item.get("account") if isinstance(item, dict) else None
                    if not isinstance(child_account, dict):
                        continue
                    child_id = child_account.get("id")
                    if child_id is None:
                        continue
                    profiles.append(
                        {
                            "id": str(child_id),
                            "name": child_account.get("shortName") or f"Дочерний аккаунт {child_id}",
                            "type": "child",
                        }
                    )
        except Exception:
            pass

        return profiles

    async def get_campaigns(self, account_id: Optional[str] = None) -> List[dict]:
        """POST /ads/v1/account/{accountID}/campaigns (V1GetCampaignsList)."""
        acc = self._require_account_id(account_id)
        campaigns: List[dict] = []
        page = 1
        limit = 100

        while True:
            payload = await self._request(
                "POST",
                f"/ads/v1/account/{acc}/campaigns",
                json_data={"filter": {}, "limit": limit, "page": page},
            )
            items = payload.get("campaigns") if isinstance(payload, dict) else None
            if not isinstance(items, list) or not items:
                break

            for item in items:
                cid = item.get("id")
                if cid is None:
                    continue
                status = item.get("status")
                campaigns.append(
                    {
                        "id": str(cid),
                        "name": item.get("name") or f"Campaign {cid}",
                        "state": _map_campaign_state(status),
                        "status": status,
                    }
                )

            total = int(payload.get("total") or 0)
            if page * limit >= total or len(items) < limit:
                break
            page += 1

        return campaigns

    def _stats_rows_from_entity(
        self,
        entity: dict,
        *,
        entity_id_key: str,
        entity_name_key: str,
        row_id_field: str,
        row_name_field: str,
        campaign_id: str,
        campaign_name: str,
        default_name_prefix: str,
    ) -> List[dict]:
        entity_id = entity.get(entity_id_key)
        if entity_id is None:
            return []
        entity_id = str(entity_id)
        entity_name = entity.get(entity_name_key) or f"{default_name_prefix} {entity_id}"
        rows: List[dict] = []
        data_rows = entity.get("data")
        if not isinstance(data_rows, list):
            return rows

        for row in data_rows:
            if not isinstance(row, dict):
                continue
            day = _parse_stats_date(row.get("timestamp"))
            if not day:
                continue
            clicks = int(row.get("clicks") or 0)
            spend = float(row.get("spend") or 0)
            normalized = {
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "date": day,
                row_id_field: entity_id,
                row_name_field: entity_name,
                "impressions": int(row.get("views") or 0),
                "clicks": clicks,
                "cost": spend,
                "cpc": round(spend / clicks, 2) if clicks > 0 else None,
            }
            if "groupId" in entity:
                normalized["group_id"] = str(entity.get("groupId") or "")
            elif "groupID" in entity:
                normalized["group_id"] = str(entity.get("groupID") or "")
            rows.append(normalized)
        return rows

    def _zero_stats_row_from_entity(
        self,
        entity: dict,
        *,
        date_to: str,
        entity_id_key: str,
        entity_name_key: str,
        row_id_field: str,
        row_name_field: str,
        campaign_id: str,
        campaign_name: str,
        default_name_prefix: str,
    ) -> Optional[dict]:
        entity_id = entity.get(entity_id_key)
        if entity_id is None:
            return None
        entity_id = str(entity_id)
        row = {
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "date": date_to,
            row_id_field: entity_id,
            row_name_field: entity.get(entity_name_key) or f"{default_name_prefix} {entity_id}",
            "impressions": 0,
            "clicks": 0,
            "cost": 0,
            "cpc": None,
        }
        if "groupId" in entity:
            row["group_id"] = str(entity.get("groupId") or "")
        elif "groupID" in entity:
            row["group_id"] = str(entity.get("groupID") or "")
        return row

    def _parse_campaign_stats_payload(
        self,
        payload: dict,
        campaign_external_id: str,
        date_to: str,
    ) -> dict:
        campaign_block = payload.get("campaign") if isinstance(payload, dict) else None
        if not isinstance(campaign_block, dict):
            return {"campaigns": [], "groups": [], "creatives": [], "group_ids": [], "creative_ids": []}

        campaign_id = str(campaign_block.get("id") or campaign_external_id)
        campaign_name = campaign_block.get("name") or f"Campaign {campaign_id}"
        campaign_rows = self._stats_rows_from_entity(
            campaign_block,
            entity_id_key="id",
            entity_name_key="name",
            row_id_field="campaign_id",
            row_name_field="campaign_name",
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            default_name_prefix="Campaign",
        )

        group_items = payload.get("groups") if isinstance(payload, dict) else None
        if not isinstance(group_items, list):
            group_items = []
        creative_items = payload.get("creatives") if isinstance(payload, dict) else None
        if not isinstance(creative_items, list):
            creative_items = []

        group_rows: List[dict] = []
        group_ids: List[str] = []
        for group in group_items:
            if not isinstance(group, dict):
                continue
            group_id = group.get("id")
            if group_id is not None:
                group_ids.append(str(group_id))
            rows = self._stats_rows_from_entity(
                group,
                entity_id_key="id",
                entity_name_key="name",
                row_id_field="group_id",
                row_name_field="group_name",
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                default_name_prefix="Группа",
            )
            if not rows and group_id is not None:
                zero_row = self._zero_stats_row_from_entity(
                    group,
                    date_to=date_to,
                    entity_id_key="id",
                    entity_name_key="name",
                    row_id_field="group_id",
                    row_name_field="group_name",
                    campaign_id=campaign_id,
                    campaign_name=campaign_name,
                    default_name_prefix="Группа",
                )
                if zero_row:
                    rows.append(zero_row)
            group_rows.extend(rows)

        creative_rows: List[dict] = []
        creative_ids: List[str] = []
        for creative in creative_items:
            if not isinstance(creative, dict):
                continue
            creative_id = creative.get("id")
            if creative_id is not None:
                creative_ids.append(str(creative_id))
            rows = self._stats_rows_from_entity(
                creative,
                entity_id_key="id",
                entity_name_key="name",
                row_id_field="creative_id",
                row_name_field="creative_name",
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                default_name_prefix="Креатив",
            )
            if not rows and creative_id is not None:
                zero_row = self._zero_stats_row_from_entity(
                    creative,
                    date_to=date_to,
                    entity_id_key="id",
                    entity_name_key="name",
                    row_id_field="creative_id",
                    row_name_field="creative_name",
                    campaign_id=campaign_id,
                    campaign_name=campaign_name,
                    default_name_prefix="Креатив",
                )
                if zero_row:
                    rows.append(zero_row)
            creative_rows.extend(rows)

        return {
            "campaigns": campaign_rows,
            "groups": group_rows,
            "creatives": creative_rows,
            "group_ids": group_ids,
            "creative_ids": creative_ids,
        }

    async def get_campaign_statistics_bundle(
        self,
        campaign_external_id: str,
        date_from: str,
        date_to: str,
        account_id: Optional[str] = None,
    ) -> dict:
        """POST /ads/v1/account/{accountID}/campaigns/{campaignID}/stats."""
        acc = self._require_account_id(account_id)
        if not str(campaign_external_id).isdigit():
            return {"campaigns": [], "groups": [], "creatives": []}

        payload = await self._request(
            "POST",
            f"/ads/v1/account/{acc}/campaigns/{int(campaign_external_id)}/stats",
            json_data={"dateFrom": date_from, "dateTo": date_to},
        )
        parsed = self._parse_campaign_stats_payload(payload, campaign_external_id, date_to)

        # In regular responses /campaigns/{id}/stats already contains child
        # daily rows. If Avito returns only aggregates, fall back to dedicated
        # child stats endpoints using IDs from the same response.
        if parsed["group_ids"] and not parsed["groups"]:
            parsed["groups"] = await self.get_group_statistics(
                campaign_external_id,
                parsed["group_ids"],
                date_from,
                date_to,
                account_id=acc,
            )
        if parsed["creative_ids"] and not parsed["creatives"]:
            parsed["creatives"] = await self.get_creative_statistics(
                campaign_external_id,
                parsed["creative_ids"],
                date_from,
                date_to,
                account_id=acc,
            )

        return parsed

    async def get_campaign_statistics(
        self,
        campaign_external_id: str,
        date_from: str,
        date_to: str,
        account_id: Optional[str] = None,
    ) -> List[dict]:
        bundle = await self.get_campaign_statistics_bundle(
            campaign_external_id,
            date_from,
            date_to,
            account_id=account_id,
        )
        return bundle.get("campaigns", [])

    async def get_group_statistics(
        self,
        campaign_external_id: str,
        group_external_ids: List[str],
        date_from: str,
        date_to: str,
        account_id: Optional[str] = None,
    ) -> List[dict]:
        acc = self._require_account_id(account_id)
        if not str(campaign_external_id).isdigit():
            return []
        rows: List[dict] = []
        for group_ids in _chunked([str(g) for g in group_external_ids if str(g).isdigit()]):
            if not group_ids:
                continue
            payload = await self._request(
                "POST",
                f"/ads/v1/account/{acc}/campaigns/{int(campaign_external_id)}/groups/stats",
                json_data={
                    "dateFrom": date_from,
                    "dateTo": date_to,
                    "groupIDs": [int(group_id) for group_id in group_ids],
                },
            )
            campaign_name = f"Campaign {campaign_external_id}"
            for group in payload.get("groups", []) if isinstance(payload, dict) else []:
                if not isinstance(group, dict):
                    continue
                rows.extend(self._stats_rows_from_entity(
                    group,
                    entity_id_key="id",
                    entity_name_key="name",
                    row_id_field="group_id",
                    row_name_field="group_name",
                    campaign_id=str(campaign_external_id),
                    campaign_name=campaign_name,
                    default_name_prefix="Группа",
                ))
        return rows

    async def get_creative_statistics(
        self,
        campaign_external_id: str,
        creative_external_ids: List[str],
        date_from: str,
        date_to: str,
        account_id: Optional[str] = None,
    ) -> List[dict]:
        acc = self._require_account_id(account_id)
        if not str(campaign_external_id).isdigit():
            return []
        rows: List[dict] = []
        for creative_ids in _chunked([str(c) for c in creative_external_ids if str(c).isdigit()]):
            if not creative_ids:
                continue
            payload = await self._request(
                "POST",
                f"/ads/v1/account/{acc}/campaigns/{int(campaign_external_id)}/creatives/stats",
                json_data={
                    "dateFrom": date_from,
                    "dateTo": date_to,
                    "creativeIDs": [int(creative_id) for creative_id in creative_ids],
                },
            )
            campaign_name = f"Campaign {campaign_external_id}"
            for creative in payload.get("creatives", []) if isinstance(payload, dict) else []:
                if not isinstance(creative, dict):
                    continue
                rows.extend(self._stats_rows_from_entity(
                    creative,
                    entity_id_key="id",
                    entity_name_key="name",
                    row_id_field="creative_id",
                    row_name_field="creative_name",
                    campaign_id=str(campaign_external_id),
                    campaign_name=campaign_name,
                    default_name_prefix="Креатив",
                ))
        return rows

    async def get_statistics(
        self,
        campaign_external_ids: List[str],
        date_from: str,
        date_to: str,
        account_id: Optional[str] = None,
    ) -> List[dict]:
        """Агрегирует дневную статистику по списку кампаний (до 100 дней на запрос — лимит API)."""
        if not campaign_external_ids:
            return []

        normalized: List[dict] = []
        for external_id in campaign_external_ids:
            try:
                rows = await self.get_campaign_statistics(
                    external_id, date_from, date_to, account_id=account_id
                )
                normalized.extend(rows)
            except Exception:
                continue
        return normalized

    async def get_statistics_bundle(
        self,
        campaign_external_ids: List[str],
        date_from: str,
        date_to: str,
        account_id: Optional[str] = None,
    ) -> dict:
        bundle = {"campaigns": [], "groups": [], "creatives": []}
        for external_id in campaign_external_ids:
            try:
                campaign_bundle = await self.get_campaign_statistics_bundle(
                    external_id, date_from, date_to, account_id=account_id
                )
            except Exception:
                continue
            for key in bundle:
                bundle[key].extend(campaign_bundle.get(key, []))
        return bundle

    async def get_balance(self, account_id: Optional[str] = None) -> Optional[dict]:
        """GET /ads/v1/account/{accountID}/balance — balance и bonusBalance в рублях."""
        acc = self._require_account_id(account_id)
        data = await self._request("GET", f"/ads/v1/account/{acc}/balance")
        if not isinstance(data, dict):
            return None
        balance = data.get("balance")
        if balance is None:
            return None
        return {
            "balance": float(balance),
            "bonus_balance": float(data.get("bonusBalance") or 0),
            "currency": "RUB",
        }
