import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import httpx


class AvitoAdsAPI:
    def __init__(
        self,
        *,
        credential_type: str,
        api_key: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        base_url: str = "https://api.avito.ru",
        timeout: float = 30.0,
    ) -> None:
        self.credential_type = credential_type
        self.api_key = (api_key or "").strip() or None
        self.client_id = (client_id or "").strip() or None
        self.client_secret = (client_secret or "").strip() or None
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._cached_bearer_token: Optional[str] = None

    async def _get_bearer_token(self) -> str:
        if self.credential_type == "single_api_key":
            if not self.api_key:
                raise ValueError("Avito API key is not configured")
            return self.api_key

        if self.credential_type != "client_credentials":
            raise ValueError("Unsupported Avito credential type")

        if self._cached_bearer_token:
            return self._cached_bearer_token

        if not self.client_id or not self.client_secret:
            raise ValueError("Avito client_id/client_secret are required")

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
        headers = {"Authorization": f"Bearer {token}"}
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

    async def validate_credentials(self) -> dict:
        """
        Best-effort credential check: tries user info endpoint first.
        """
        return await self._request("GET", "/core/v1/accounts/self")

    async def get_profiles_or_accounts(self) -> List[dict]:
        data = await self._request("GET", "/core/v1/accounts")
        items = data.get("accounts") if isinstance(data, dict) else None
        if isinstance(items, list):
            return items
        return []

    async def get_campaigns(self, account_id: Optional[str] = None) -> List[dict]:
        params = {}
        if account_id:
            params["account_id"] = account_id
        data = await self._request("GET", "/ads/v1/campaigns", params=params or None)
        items = data.get("campaigns") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []
        campaigns: List[dict] = []
        for item in items:
            cid = item.get("id") or item.get("campaign_id")
            if cid is None:
                continue
            campaigns.append(
                {
                    "id": str(cid),
                    "name": item.get("name") or f"Campaign {cid}",
                    "state": item.get("status") or "ON",
                }
            )
        return campaigns

    async def get_statistics(
        self,
        campaign_external_ids: List[str],
        date_from: str,
        date_to: str,
        account_id: Optional[str] = None,
    ) -> List[dict]:
        if not campaign_external_ids:
            return []
        payload = {
            "dateFrom": date_from,
            "dateTo": date_to,
            "campaignIds": [int(c) for c in campaign_external_ids if str(c).isdigit()],
            "groupBy": "day",
        }
        if account_id:
            payload["accountId"] = account_id
        data = await self._request("POST", "/ads/v1/statistics", json_data=payload)
        rows = data.get("rows") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            return []
        normalized: List[dict] = []
        for row in rows:
            campaign_id = row.get("campaignId")
            day = row.get("date")
            if campaign_id is None or not day:
                continue
            clicks = int(row.get("clicks") or 0)
            conversions = int(row.get("conversions") or 0)
            cost = float(row.get("cost") or 0)
            normalized.append(
                {
                    "campaign_id": str(campaign_id),
                    "campaign_name": row.get("campaignName") or f"Campaign {campaign_id}",
                    "date": day,
                    "impressions": int(row.get("impressions") or 0),
                    "clicks": clicks,
                    "cost": cost,
                    "conversions": conversions,
                    "cpc": (cost / clicks) if clicks > 0 else None,
                    "cpa": (cost / conversions) if conversions > 0 else None,
                }
            )
        return normalized

    async def get_balance(self, account_id: Optional[str] = None) -> Optional[dict]:
        params = {}
        if account_id:
            params["account_id"] = account_id
        data = await self._request("GET", "/ads/v1/balance", params=params or None)
        if not isinstance(data, dict):
            return None
        value = data.get("balance")
        if value is None:
            return None
        return {"balance": float(value), "currency": data.get("currency") or "RUB"}
