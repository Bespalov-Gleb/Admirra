"""Клиент Yandex Wordstat через Yandex Cloud Search API v2.

Старый api.wordstat.yandex.net (OAuth) отключён. Здесь — v2:
POST https://searchapi.api.cloud.yandex.net/v2/wordstat/<endpoint>
Заголовок Authorization: Api-Key <ключ сервисного аккаунта Yandex Cloud>.
Ключ — общий (наш), не зависит от проекта/OAuth пользователя. Ответы v2
приводим к простому виду (int64 приходит строками — коэрсим в int)."""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from core.config import get_config

logger = logging.getLogger("ai_assistant.wordstat")
cfg = get_config()

_DEVICE_MAP = {"all": "DEVICE_ALL", "desktop": "DEVICE_DESKTOP", "phone": "DEVICE_PHONE", "tablet": "DEVICE_TABLET"}
_PERIOD_MAP = {"monthly": "PERIOD_MONTHLY", "weekly": "PERIOD_WEEKLY", "daily": "PERIOD_DAILY"}
_REGION_MAP = {"all": "REGION_ALL", "cities": "REGION_CITIES", "regions": "REGION_REGIONS"}
TIMEOUT = 30.0


class WordstatError(RuntimeError):
    pass


def is_configured() -> bool:
    # folderId обязателен в каждом запросе Search API v2 — без него вызовы падают,
    # поэтому Wordstat считаем подключённым только при наличии и ключа, и folderId.
    return bool((cfg.wordstat.api_key or "").strip()) and bool((cfg.wordstat.folder_id or "").strip())


def _map_devices(devices: Optional[list[str]]) -> Optional[list[str]]:
    if not devices:
        return None
    return [_DEVICE_MAP.get(str(d).strip().lower(), str(d).strip()) for d in devices]


def _to_int(v: Any) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


async def _request(endpoint: str, body: Optional[dict] = None) -> dict:
    key = (cfg.wordstat.api_key or "").strip()
    if not key:
        raise WordstatError("Wordstat не подключён (нет ключа Yandex Cloud Search API)")
    payload: dict = dict(body or {})
    if cfg.wordstat.folder_id and "folderId" not in payload:
        payload["folderId"] = cfg.wordstat.folder_id
    url = f"{cfg.wordstat.base_url}{endpoint}"
    headers = {"Authorization": f"Api-Key {key}", "Content-Type": "application/json;charset=utf-8"}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(url, json=payload, headers=headers)
    if resp.status_code >= 400:
        raise WordstatError(f"Wordstat HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json()


async def top_requests(phrase: str, devices: Optional[list[str]] = None) -> dict:
    body: dict = {"phrase": phrase}
    dev = _map_devices(devices)
    if dev:
        body["devices"] = dev
    r = await _request("/topRequests", body)
    items = lambda arr: [{"phrase": i.get("phrase", ""), "count": _to_int(i.get("count", 0))} for i in (arr or [])]
    return {
        "phrase": phrase,
        "total_count": _to_int(r.get("totalCount", 0)),
        "top": items(r.get("results")),
        "associations": items(r.get("associations")),
    }


async def dynamics(phrase: str, period: str = "monthly", from_date: Optional[str] = None,
                   to_date: Optional[str] = None, devices: Optional[list[str]] = None) -> dict:
    body: dict = {"phrase": phrase, "period": _PERIOD_MAP.get((period or "monthly").lower(), "PERIOD_MONTHLY")}
    if from_date:
        body["fromDate"] = f"{from_date}T00:00:00Z"
    if to_date:
        body["toDate"] = f"{to_date}T00:00:00Z"
    dev = _map_devices(devices)
    if dev:
        body["devices"] = dev
    r = await _request("/dynamics", body)
    return {
        "phrase": phrase,
        "dynamics": [
            {"date": str(i.get("date", ""))[:10], "count": _to_int(i.get("count", 0)),
             "share": float(i.get("share", 0.0) or 0.0)}
            for i in (r.get("results") or [])
        ],
    }


async def regions(phrase: str, region_type: str = "all", devices: Optional[list[str]] = None) -> dict:
    body: dict = {"phrase": phrase, "region": _REGION_MAP.get((region_type or "all").lower(), "REGION_ALL")}
    dev = _map_devices(devices)
    if dev:
        body["devices"] = dev
    r = await _request("/regions", body)
    rows = r.get("results") or r.get("regions") or []
    return {
        "phrase": phrase,
        "regions": [
            {"name": i.get("name") or i.get("regionName"), "count": _to_int(i.get("count", 0)),
             "share": float(i.get("share", 0.0) or 0.0)}
            for i in rows
        ][:200],
    }
