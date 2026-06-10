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

# Документированные статусы кампании (CampaignStatus)
AVITO_ADS_ACTIVE_STATUSES = frozenset({"active", "unpausing"})


def _map_campaign_state(status: Optional[str]) -> str:
    if status in AVITO_ADS_ACTIVE_STATUSES:
        return "ON"
    return "OFF"


def _parse_stats_date(timestamp: Optional[str]) -> Optional[str]:
    if not timestamp:
        return None
    try:
        if "T" in timestamp:
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).date().isoformat()
        return datetime.strptime(timestamp[:10], "%Y-%m-%d").date().isoformat()
    except (ValueError, TypeError):
        return None


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

    async def get_campaign_statistics(
        self,
        campaign_external_id: str,
        date_from: str,
        date_to: str,
        account_id: Optional[str] = None,
    ) -> List[dict]:
        """POST /ads/v1/account/{accountID}/campaigns/{campaignID}/stats."""
        acc = self._require_account_id(account_id)
        if not str(campaign_external_id).isdigit():
            return []

        payload = await self._request(
            "POST",
            f"/ads/v1/account/{acc}/campaigns/{int(campaign_external_id)}/stats",
            json_data={"dateFrom": date_from, "dateTo": date_to},
        )
        campaign_block = payload.get("campaign") if isinstance(payload, dict) else None
        if not isinstance(campaign_block, dict):
            return []

        campaign_id = str(campaign_block.get("id") or campaign_external_id)
        campaign_name = campaign_block.get("name") or f"Campaign {campaign_id}"
        rows: List[dict] = []

        data_rows = campaign_block.get("data")
        if isinstance(data_rows, list):
            for row in data_rows:
                if not isinstance(row, dict):
                    continue
                day = _parse_stats_date(row.get("timestamp"))
                if not day:
                    continue
                clicks = int(row.get("clicks") or 0)
                spend = float(row.get("spend") or 0)
                rows.append(
                    {
                        "campaign_id": campaign_id,
                        "campaign_name": campaign_name,
                        "date": day,
                        "impressions": int(row.get("views") or 0),
                        "clicks": clicks,
                        "cost": spend,
                        "cpc": float(row.get("cpc")) if row.get("cpc") is not None else (
                            (spend / clicks) if clicks > 0 else None
                        ),
                    }
                )

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
