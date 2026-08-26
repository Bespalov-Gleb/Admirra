"""Клиент Yandex Wordstat через Yandex Cloud Search API v2.

Старый api.wordstat.yandex.net (OAuth) отключён. Здесь — v2:
POST https://searchapi.api.cloud.yandex.net/v2/wordstat/<endpoint>
Заголовок Authorization: Api-Key <ключ сервисного аккаунта Yandex Cloud>.
Ключ — общий (наш), не зависит от проекта/OAuth пользователя. Ответы v2
приводим к простому виду (int64 приходит строками — коэрсим в int)."""
from __future__ import annotations

import logging
import json
import time
from typing import Any, Optional

import httpx

from core.config import get_config

logger = logging.getLogger("ai_assistant.wordstat")
cfg = get_config()

_DEVICE_MAP = {"all": "DEVICE_ALL", "desktop": "DEVICE_DESKTOP", "phone": "DEVICE_PHONE", "tablet": "DEVICE_TABLET"}
_PERIOD_MAP = {"monthly": "PERIOD_MONTHLY", "weekly": "PERIOD_WEEKLY", "daily": "PERIOD_DAILY"}
_REGION_MAP = {"all": "REGION_ALL", "cities": "REGION_CITIES", "regions": "REGION_REGIONS"}
TIMEOUT = 30.0
MAX_PHRASE_LENGTH = 400
MAX_TOP_PHRASES = 2000
MAX_REGIONS = 100
_region_labels: Optional[dict[str, str]] = None
_response_cache: dict[str, tuple[float, dict]] = {}
_CACHE_TTL_SECONDS = {
    "/topRequests": 15 * 60,
    "/dynamics": 15 * 60,
    "/regions": 60 * 60,
    "/getRegionsTree": 24 * 60 * 60,
}


class WordstatError(RuntimeError):
    pass


def is_configured() -> bool:
    # Для API-ключа сервисного аккаунта Search API определяет каталог по самому
    # ключу. folderId остаётся опциональным явным override для другого каталога.
    return bool((cfg.wordstat.api_key or "").strip())


def _map_devices(devices: Optional[list[str]]) -> Optional[list[str]]:
    if not devices:
        return None
    return [_DEVICE_MAP.get(str(d).strip().lower(), str(d).strip()) for d in devices]


def _to_int(v: Any) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _validate_phrase(phrase: str) -> str:
    """Предел Search API v2: одна фраза до 400 символов.

    Валидация на уровне клиента защищает и API-квоту, и tool-calling от
    случайно переданного моделью пустого/слишком длинного запроса.
    """
    value = (phrase or "").strip()
    if not value:
        raise WordstatError("Укажите поисковую фразу для Wordstat")
    if len(value) > MAX_PHRASE_LENGTH:
        raise WordstatError("Фраза для Wordstat длиннее 400 символов")
    return value


def _validate_regions(regions: Optional[list[str]]) -> Optional[list[str]]:
    if not regions:
        return None
    values = [str(value).strip() for value in regions if str(value).strip()]
    if len(values) > MAX_REGIONS:
        raise WordstatError("Для Wordstat можно указать не более 100 регионов")
    return values or None


async def _get_region_labels() -> dict[str, str]:
    """Один раз за жизнь процесса подгружаем дерево регионов.

    Search API отдаёт распределение по кодам регионов; для ответа человеку
    ассистент должен видеть «Москва», а не технический код 213.
    """
    global _region_labels
    if _region_labels is not None:
        return _region_labels
    payload = await _request("/getRegionsTree")
    labels: dict[str, str] = {}

    def walk(nodes: Any) -> None:
        for node in nodes or []:
            region_id = node.get("id")
            label = node.get("label")
            if region_id is not None and label:
                labels[str(region_id)] = str(label)
            walk(node.get("children"))

    walk(payload.get("regions"))
    _region_labels = labels
    return labels


async def _request(endpoint: str, body: Optional[dict] = None) -> dict:
    key = (cfg.wordstat.api_key or "").strip()
    if not key:
        raise WordstatError("Wordstat не подключён (нет ключа Yandex Cloud Search API)")
    payload: dict = dict(body or {})
    if cfg.wordstat.folder_id and "folderId" not in payload:
        payload["folderId"] = cfg.wordstat.folder_id
    cache_key = f"{endpoint}:{json.dumps(payload, ensure_ascii=False, sort_keys=True)}"
    now = time.monotonic()
    cached = _response_cache.get(cache_key)
    if cached and cached[0] > now:
        return cached[1]
    url = f"{cfg.wordstat.base_url}{endpoint}"
    headers = {"Authorization": f"Api-Key {key}", "Content-Type": "application/json;charset=utf-8"}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(url, json=payload, headers=headers)
    if resp.status_code >= 400:
        raise WordstatError(f"Wordstat HTTP {resp.status_code}: {resp.text[:300]}")
    result = resp.json()
    ttl = _CACHE_TTL_SECONDS.get(endpoint)
    if ttl:
        _response_cache[cache_key] = (now + ttl, result)
    return result


async def top_requests(
    phrase: str,
    devices: Optional[list[str]] = None,
    regions: Optional[list[str]] = None,
    num_phrases: Optional[int] = None,
) -> dict:
    phrase = _validate_phrase(phrase)
    body: dict = {"phrase": phrase}
    if num_phrases is not None:
        try:
            count = int(num_phrases)
        except (TypeError, ValueError) as exc:
            raise WordstatError("Количество фраз Wordstat должно быть числом") from exc
        if not 1 <= count <= MAX_TOP_PHRASES:
            raise WordstatError("Wordstat возвращает от 1 до 2000 фраз")
        # int64 в JSON-схеме Yandex передаётся строкой.
        body["numPhrases"] = str(count)
    region_ids = _validate_regions(regions)
    if region_ids:
        body["regions"] = region_ids
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
                   to_date: Optional[str] = None, devices: Optional[list[str]] = None,
                   regions: Optional[list[str]] = None) -> dict:
    phrase = _validate_phrase(phrase)
    body: dict = {"phrase": phrase, "period": _PERIOD_MAP.get((period or "monthly").lower(), "PERIOD_MONTHLY")}
    if from_date:
        body["fromDate"] = f"{from_date}T00:00:00Z"
    if to_date:
        body["toDate"] = f"{to_date}T00:00:00Z"
    region_ids = _validate_regions(regions)
    if region_ids:
        body["regions"] = region_ids
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
    phrase = _validate_phrase(phrase)
    body: dict = {"phrase": phrase, "region": _REGION_MAP.get((region_type or "all").lower(), "REGION_ALL")}
    dev = _map_devices(devices)
    if dev:
        body["devices"] = dev
    r = await _request("/regions", body)
    rows = r.get("results") or r.get("regions") or []
    labels = await _get_region_labels()
    return {
        "phrase": phrase,
        "regions": [
            {"id": str(i.get("region") or i.get("id") or ""),
             "name": labels.get(str(i.get("region") or i.get("id") or ""), "Регион без названия"),
             "count": _to_int(i.get("count", 0)), "share": float(i.get("share", 0.0) or 0.0),
             "affinity_index": float(i.get("affinityIndex", 0.0) or 0.0)}
            for i in rows
        ][:200],
    }
