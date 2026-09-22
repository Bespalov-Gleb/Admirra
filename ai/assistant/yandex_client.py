"""Тонкий async-клиент Yandex Direct + Metrika для ассистента.

Токен берётся из YandexAccess проекта; на 401 — один рефреш и повтор. Только
чтение. Direct: JSON API v5 + Reports API (async с ретраями). Metrika:
Reporting API (/stat/v1/data*) и Management API (/management/v1/*)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from automation.provider_transport import provider_client

from .token_provider import YandexAccess

logger = logging.getLogger("ai_assistant.yandex_client")

DIRECT_API_URL = "https://api.direct.yandex.com/json/v5"
METRIKA_API_URL = "https://api-metrika.yandex.net"
DEFAULT_TIMEOUT = 40.0
REPORT_TIMEOUT = 120.0


class YandexApiError(RuntimeError):
    """Ошибка Яндекс API — пробрасывается в инструмент как текст для модели."""


def _is_unauthorized(status: int, body: str) -> bool:
    return status == 401 or "Unauthorized" in body or '"error_code":"53"' in body


class AiYandexClient:
    def __init__(self, access: YandexAccess):
        self.access = access

    # ── Yandex Direct JSON API v5 ────────────────────────────────────────────
    def _direct_headers(self, token: str) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept-Language": "ru",
            "Content-Type": "application/json",
        }
        if self.access.client_login:
            headers["Client-Login"] = self.access.client_login
        return headers

    async def direct_call(self, service: str, method: str, params: dict) -> dict:
        """POST json/v5/{service} с {method, params}. Возвращает result."""
        url = f"{DIRECT_API_URL}/{service}"
        payload = {"method": method, "params": params}
        for attempt in range(2):
            token = self.access.access_token()
            async with provider_client("direct", timeout=DEFAULT_TIMEOUT) as client:
                resp = await client.post(url, json=payload, headers=self._direct_headers(token))
            body = resp.text
            if _is_unauthorized(resp.status_code, body) and attempt == 0:
                await self.access.refresh()
                continue
            if resp.status_code >= 400:
                raise YandexApiError(f"Direct {service}.{method} HTTP {resp.status_code}: {body[:400]}")
            data = resp.json()
            if isinstance(data, dict) and data.get("error"):
                err = data["error"]
                raise YandexApiError(f"Direct {service}.{method}: {err.get('error_string')} — {err.get('error_detail')}")
            return (data or {}).get("result", {})
        raise YandexApiError(f"Direct {service}.{method}: авторизация не удалась")

    async def direct_report(self, report_def: dict) -> list[dict]:
        """Reports API: POST /reports (async), парсит TSV в список словарей."""
        url = f"{DIRECT_API_URL}/reports"
        for attempt in range(2):
            token = self.access.access_token()
            headers = {
                **self._direct_headers(token),
                "processingMode": "auto",
                "returnMoneyInMicros": "false",
                "skipReportHeader": "true",
                "skipColumnHeader": "false",
                "skipReportSummary": "true",
            }
            async with provider_client("direct", timeout=REPORT_TIMEOUT) as client:
                resp = None
                for _ in range(10):
                    resp = await client.post(url, json={"params": report_def}, headers=headers)
                    if resp.status_code == 200:
                        break
                    if resp.status_code in (201, 202):
                        await asyncio.sleep(min(int(resp.headers.get("retryIn", 5)), 15))
                        continue
                    break
            if resp is not None and _is_unauthorized(resp.status_code, resp.text) and attempt == 0:
                await self.access.refresh()
                continue
            if resp is None or resp.status_code in (201, 202):
                raise YandexApiError("Отчёт Директа ещё готовится — повторите запрос позже")
            if resp.status_code >= 400:
                raise YandexApiError(f"Direct Reports HTTP {resp.status_code}: {resp.text[:400]}")
            return _parse_tsv(resp.text)
        raise YandexApiError("Direct Reports: авторизация не удалась")

    # ── Yandex Metrika ───────────────────────────────────────────────────────
    async def metrika_get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        url = f"{METRIKA_API_URL}{endpoint}"
        for attempt in range(2):
            token = self.access.access_token()
            headers = {"Authorization": f"OAuth {token}", "Content-Type": "application/json"}
            async with provider_client("metrica", timeout=DEFAULT_TIMEOUT) as client:
                resp = await client.get(url, params=params, headers=headers)
            if _is_unauthorized(resp.status_code, resp.text) and attempt == 0:
                await self.access.refresh()
                continue
            if resp.status_code >= 400:
                raise YandexApiError(f"Metrika {endpoint} HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
        raise YandexApiError(f"Metrika {endpoint}: авторизация не удалась")


class ReportRows(list):
    """List-compatible bounded report that retains the untruncated row count."""
    source_row_count = 0


def _parse_tsv(text: str, max_rows: int = 200) -> list[dict]:
    lines = [ln.rstrip("\r") for ln in text.split("\n") if ln.strip()]
    if len(lines) < 1:
        return ReportRows()
    header = lines[0].split("\t")
    rows = ReportRows()
    for line in lines[1:]:
        cells = line.split("\t")
        if len(cells) != len(header):
            raise ValueError("Некорректная строка отчёта Директа")
        rows.source_row_count += 1
        if len(rows) < max_rows:
            rows.append(dict(zip(header, cells)))
    return rows
