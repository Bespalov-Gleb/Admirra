"""Инструменты ассистента (read-only).

Аккаунт-широкий агент: инструменты работают в контексте ToolContext, который
держит доступ пользователя и «текущий проект». Проект выбирается либо из шапки
(предустановлен), либо агентом по названию через use_project. Наборы:
  • Проекты: list_projects, use_project — резолв проекта по имени (в пределах
    доступных пользователю — изоляция).
  • Yandex Direct/Metrika (live, read): работают по текущему проекту.
  • Wordstat (Yandex Cloud Search API v2, общий ключ): без привязки к проекту.

Metrika-инструменты валидируют counter_id по счётчикам текущего проекта.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

from sqlalchemy.orm import Session

from core import models

from . import projects, wordstat_client
from .token_provider import YandexAccess, YandexAccessError, resolve_yandex
from .yandex_client import AiYandexClient, YandexApiError

# ── Значения по умолчанию ────────────────────────────────────────────────────
DEFAULT_DIRECT_FIELDS = ["CampaignId", "CampaignName", "Impressions", "Clicks", "Cost", "Ctr", "AvgCpc"]
DIRECT_REPORT_TYPES = [
    "CAMPAIGN_PERFORMANCE_REPORT", "ACCOUNT_PERFORMANCE_REPORT", "AD_PERFORMANCE_REPORT",
    "ADGROUP_PERFORMANCE_REPORT", "CRITERIA_PERFORMANCE_REPORT", "SEARCH_QUERY_PERFORMANCE_REPORT",
]
MAX_ROWS = 200
_NO_PROJECT = {"error": "Проект не выбран. Сначала вызовите use_project с названием проекта."}


@dataclass
class ToolContext:
    """Контекст исполнения инструментов: доступ пользователя и текущий проект.
    conversation — чтобы запомнить выбранный проект на весь диалог."""
    db: Session
    user: models.User
    conversation: Optional[models.AiConversation] = None
    access: Optional[YandexAccess] = None
    _client: Optional[AiYandexClient] = None

    @property
    def client(self) -> Optional[AiYandexClient]:
        if self.access is not None and self._client is None:
            self._client = AiYandexClient(self.access)
        return self._client

    def set_project(self, client_id) -> None:
        """Переключает текущий проект (может бросить YandexAccessError)."""
        self.access = resolve_yandex(self.db, client_id)
        self._client = None


def _dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def _clip(rows: list, limit: int = MAX_ROWS) -> list:
    return rows[:limit]


# ── Проекты ──────────────────────────────────────────────────────────────────
async def _exec_list_projects(ctx: ToolContext, args: dict) -> str:
    return _dump({"projects": projects.list_accessible(ctx.db, ctx.user)})


async def _exec_use_project(ctx: ToolContext, args: dict) -> str:
    query = args.get("query") or args.get("name") or args.get("project") or ""
    res = projects.resolve(ctx.db, ctx.user, query)
    if "project" not in res:
        return _dump(res)
    p = res["project"]
    if not p.get("yandex"):
        return _dump({"error": f"У проекта «{p['name']}» не подключён Яндекс.Директ — данных нет"})
    try:
        ctx.set_project(p["id"])
    except YandexAccessError as exc:
        return _dump({"error": str(exc)})
    # Запоминаем выбор на весь диалог, чтобы следующие сообщения не переспрашивали.
    if ctx.conversation is not None:
        ctx.conversation.client_id = ctx.access.integration.client_id
        try:
            ctx.db.commit()
        except Exception:
            ctx.db.rollback()
    return _dump({"selected_project": {"id": p["id"], "name": p["name"]},
                  "cabinet": ctx.access.account_name, "counter_ids": ctx.access.counter_ids})


# ── Yandex Direct ────────────────────────────────────────────────────────────
async def _exec_direct_get_campaigns(ctx: ToolContext, args: dict) -> str:
    if not ctx.access:
        return _dump(_NO_PROJECT)
    params: dict = {"SelectionCriteria": {}, "FieldNames": ["Id", "Name", "State", "Status", "Type", "StartDate"]}
    if args.get("states"):
        params["SelectionCriteria"]["States"] = args["states"]
    result = await ctx.client.direct_call("campaigns", "get", params)
    return _dump({"campaigns": _clip(result.get("Campaigns", []))})


async def _exec_direct_get_statistics(ctx: ToolContext, args: dict) -> str:
    if not ctx.access:
        return _dump(_NO_PROJECT)
    date_from, date_to = args["date_from"], args["date_to"]
    report_type = args.get("report_type", "CAMPAIGN_PERFORMANCE_REPORT")
    if report_type not in DIRECT_REPORT_TYPES:
        report_type = "CAMPAIGN_PERFORMANCE_REPORT"
    fields = args.get("field_names") or list(DEFAULT_DIRECT_FIELDS)
    if args.get("group_by_date") and "Date" not in fields:
        fields = ["Date", *fields]
    report_def: dict = {
        "SelectionCriteria": {"DateFrom": date_from, "DateTo": date_to},
        "FieldNames": fields,
        "ReportName": f"ai_{report_type}_{date_from}_{date_to}_{abs(hash(tuple(fields))) % 10_000_000}",
        "ReportType": report_type,
        "DateRangeType": "CUSTOM_DATE",
        "Format": "TSV",
        "IncludeVAT": "YES" if args.get("include_vat", True) else "NO",
        "IncludeDiscount": "NO",
    }
    if args.get("campaign_ids"):
        report_def["SelectionCriteria"]["Filter"] = [
            {"Field": "CampaignId", "Operator": "IN", "Values": [str(c) for c in args["campaign_ids"]]}
        ]
    rows = await ctx.client.direct_report(report_def)
    return _dump({"report_type": report_type, "period": [date_from, date_to], "rows": rows, "row_count": len(rows)})


async def _exec_direct_get_adgroups(ctx: ToolContext, args: dict) -> str:
    if not ctx.access:
        return _dump(_NO_PROJECT)
    sel: dict = {}
    if args.get("campaign_ids"):
        sel["CampaignIds"] = [str(c) for c in args["campaign_ids"]]
    params = {"SelectionCriteria": sel, "FieldNames": ["Id", "Name", "CampaignId", "Status", "Type"]}
    result = await ctx.client.direct_call("adgroups", "get", params)
    return _dump({"adgroups": _clip(result.get("AdGroups", []))})


async def _exec_direct_get_ads(ctx: ToolContext, args: dict) -> str:
    if not ctx.access:
        return _dump(_NO_PROJECT)
    sel: dict = {}
    if args.get("campaign_ids"):
        sel["CampaignIds"] = [str(c) for c in args["campaign_ids"]]
    if args.get("adgroup_ids"):
        sel["AdGroupIds"] = [str(c) for c in args["adgroup_ids"]]
    if not sel:
        return _dump({"error": "Укажите campaign_ids или adgroup_ids"})
    params = {"SelectionCriteria": sel,
              "FieldNames": ["Id", "AdGroupId", "CampaignId", "State", "Status", "Type"],
              "TextAdFieldNames": ["Title", "Title2", "Text", "Href"]}
    result = await ctx.client.direct_call("ads", "get", params)
    return _dump({"ads": _clip(result.get("Ads", []))})


async def _exec_direct_get_keywords(ctx: ToolContext, args: dict) -> str:
    if not ctx.access:
        return _dump(_NO_PROJECT)
    sel: dict = {}
    if args.get("campaign_ids"):
        sel["CampaignIds"] = [str(c) for c in args["campaign_ids"]]
    if args.get("adgroup_ids"):
        sel["AdGroupIds"] = [str(c) for c in args["adgroup_ids"]]
    if not sel:
        return _dump({"error": "Укажите campaign_ids или adgroup_ids"})
    params = {"SelectionCriteria": sel, "FieldNames": ["Id", "Keyword", "AdGroupId", "CampaignId", "State", "Status"]}
    result = await ctx.client.direct_call("keywords", "get", params)
    return _dump({"keywords": _clip(result.get("Keywords", []))})


# ── Yandex Metrika ───────────────────────────────────────────────────────────
def _check_counter(access: YandexAccess, counter_id: Any) -> Optional[str]:
    if not access.counter_ids:
        return None
    if str(counter_id) not in {str(c) for c in access.counter_ids}:
        return (f"Счётчик {counter_id} не относится к проекту. "
                f"Доступные: {', '.join(map(str, access.counter_ids))}")
    return None


async def _exec_metrika_get_counters(ctx: ToolContext, args: dict) -> str:
    if not ctx.access:
        return _dump(_NO_PROJECT)
    data = await ctx.client.metrika_get("/management/v1/counters", {"per_page": 200})
    allowed = {str(c) for c in ctx.access.counter_ids}
    slim = [{"id": c.get("id"), "name": c.get("name"), "site": c.get("site")}
            for c in data.get("counters", []) if not allowed or str(c.get("id")) in allowed]
    return _dump({"counters": slim, "project_counter_ids": ctx.access.counter_ids})


async def _exec_metrika_get_goals(ctx: ToolContext, args: dict) -> str:
    if not ctx.access:
        return _dump(_NO_PROJECT)
    counter_id = args["counter_id"]
    err = _check_counter(ctx.access, counter_id)
    if err:
        return _dump({"error": err})
    data = await ctx.client.metrika_get(f"/management/v1/counter/{counter_id}/goals")
    goals = [{"id": g.get("id"), "name": g.get("name"), "type": g.get("type")} for g in data.get("goals", [])]
    return _dump({"goals": goals})


async def _exec_metrika_get_report(ctx: ToolContext, args: dict) -> str:
    if not ctx.access:
        return _dump(_NO_PROJECT)
    counter_id = args["counter_id"]
    err = _check_counter(ctx.access, counter_id)
    if err:
        return _dump({"error": err})
    qp: dict = {"id": counter_id, "metrics": ",".join(args["metrics"]), "limit": min(int(args.get("limit", 100)), MAX_ROWS)}
    if args.get("dimensions"):
        qp["dimensions"] = ",".join(args["dimensions"])
    for k in ("date1", "date2", "filters", "sort"):
        if args.get(k):
            qp[k] = args[k]
    data = await ctx.client.metrika_get("/stat/v1/data", qp)
    return _dump(_slim_metrika(data))


async def _exec_metrika_get_report_by_time(ctx: ToolContext, args: dict) -> str:
    if not ctx.access:
        return _dump(_NO_PROJECT)
    counter_id = args["counter_id"]
    err = _check_counter(ctx.access, counter_id)
    if err:
        return _dump({"error": err})
    qp: dict = {"id": counter_id, "metrics": ",".join(args["metrics"]), "group": args.get("group", "day")}
    if args.get("dimensions"):
        qp["dimensions"] = ",".join(args["dimensions"])
    for k in ("date1", "date2"):
        if args.get(k):
            qp[k] = args[k]
    data = await ctx.client.metrika_get("/stat/v1/data/bytime", qp)
    return _dump(_slim_metrika(data, by_time=True))


def _slim_metrika(data: dict, by_time: bool = False) -> dict:
    out: dict = {
        "query": {k: data.get("query", {}).get(k) for k in ("metrics", "dimensions", "date1", "date2")},
        "totals": data.get("totals"),
        "total_rows": data.get("total_rows"),
    }
    rows = []
    for item in (data.get("data", []) or [])[:MAX_ROWS]:
        rows.append({"dimensions": [d.get("name") for d in item.get("dimensions", [])], "metrics": item.get("metrics")})
    out["rows"] = rows
    if by_time:
        out["time_intervals"] = data.get("time_intervals")
    return out


# ── Wordstat (общий ключ, без привязки к проекту) ────────────────────────────
async def _exec_wordstat_top_requests(ctx: ToolContext, args: dict) -> str:
    return _dump(await wordstat_client.top_requests(args["phrase"], args.get("devices")))


async def _exec_wordstat_dynamics(ctx: ToolContext, args: dict) -> str:
    return _dump(await wordstat_client.dynamics(
        args["phrase"], args.get("period", "monthly"), args.get("from_date"), args.get("to_date"), args.get("devices")))


async def _exec_wordstat_regions(ctx: ToolContext, args: dict) -> str:
    return _dump(await wordstat_client.regions(args["phrase"], args.get("region_type", "all"), args.get("devices")))


# ── Реестр ───────────────────────────────────────────────────────────────────
_Executor = Callable[[ToolContext, dict], Awaitable[str]]
_DEVICES = {"type": "array", "items": {"type": "string", "enum": ["all", "desktop", "phone", "tablet"]},
            "description": "Устройства (опционально)."}

_REGISTRY: dict[str, tuple[dict, _Executor]] = {
    "list_projects": (
        {"name": "list_projects",
         "description": "Список проектов, доступных пользователю (id, название, подключён ли Яндекс). Используй, чтобы найти нужный проект по названию.",
         "parameters": {"type": "object", "properties": {}}},
        _exec_list_projects,
    ),
    "use_project": (
        {"name": "use_project",
         "description": "Выбрать текущий проект по названию или id (в пределах доступных). После выбора инструменты Директа/Метрики работают по нему. Если проект уже выбран в шапке — вызывать не обязательно.",
         "parameters": {"type": "object", "properties": {
             "query": {"type": "string", "description": "Название проекта (можно часть) или его id."}},
             "required": ["query"]}},
        _exec_use_project,
    ),
    "direct_get_campaigns": (
        {"name": "direct_get_campaigns",
         "description": "Кампании Яндекс.Директа текущего проекта (id, имя, статус). Отсюда берут CampaignId.",
         "parameters": {"type": "object", "properties": {
             "states": {"type": "array", "items": {"type": "string", "enum": ["ON", "OFF", "SUSPENDED", "ENDED", "CONVERTED", "ARCHIVED"]}}}}},
        _exec_direct_get_campaigns,
    ),
    "direct_get_statistics": (
        {"name": "direct_get_statistics",
         "description": "Статистика Директа за период (показы, клики, расход, CTR, CPC) через Reports API. Можно по дням и по кампаниям.",
         "parameters": {"type": "object", "properties": {
             "date_from": {"type": "string", "description": "YYYY-MM-DD"},
             "date_to": {"type": "string", "description": "YYYY-MM-DD"},
             "report_type": {"type": "string", "enum": DIRECT_REPORT_TYPES},
             "field_names": {"type": "array", "items": {"type": "string"}},
             "campaign_ids": {"type": "array", "items": {"type": "string"}},
             "group_by_date": {"type": "boolean"},
             "include_vat": {"type": "boolean"}},
             "required": ["date_from", "date_to"]}},
        _exec_direct_get_statistics,
    ),
    "direct_get_adgroups": (
        {"name": "direct_get_adgroups", "description": "Группы объявлений Директа (фильтр по campaign_ids).",
         "parameters": {"type": "object", "properties": {"campaign_ids": {"type": "array", "items": {"type": "string"}}}}},
        _exec_direct_get_adgroups,
    ),
    "direct_get_ads": (
        {"name": "direct_get_ads", "description": "Объявления Директа с текстами. Нужен campaign_ids или adgroup_ids.",
         "parameters": {"type": "object", "properties": {
             "campaign_ids": {"type": "array", "items": {"type": "string"}},
             "adgroup_ids": {"type": "array", "items": {"type": "string"}}}}},
        _exec_direct_get_ads,
    ),
    "direct_get_keywords": (
        {"name": "direct_get_keywords", "description": "Ключевые слова Директа. Нужен campaign_ids или adgroup_ids.",
         "parameters": {"type": "object", "properties": {
             "campaign_ids": {"type": "array", "items": {"type": "string"}},
             "adgroup_ids": {"type": "array", "items": {"type": "string"}}}}},
        _exec_direct_get_keywords,
    ),
    "metrika_get_counters": (
        {"name": "metrika_get_counters", "description": "Счётчики Метрики текущего проекта (id, имя, сайт).",
         "parameters": {"type": "object", "properties": {}}},
        _exec_metrika_get_counters,
    ),
    "metrika_get_goals": (
        {"name": "metrika_get_goals", "description": "Цели счётчика Метрики. Конверсия по цели — метрика ym:s:goal<ID>reaches.",
         "parameters": {"type": "object", "properties": {"counter_id": {"type": "string"}}, "required": ["counter_id"]}},
        _exec_metrika_get_goals,
    ),
    "metrika_get_report": (
        {"name": "metrika_get_report",
         "description": "Отчёт Метрики (/stat/v1/data) с произвольными метриками/измерениями. Метрики: ym:s:visits, ym:s:users, ym:s:bounceRate, ym:s:goal<ID>reaches. Измерения: ym:s:date, ym:s:trafficSource, ym:s:lastDirectClickOrder, ym:s:UTMSource.",
         "parameters": {"type": "object", "properties": {
             "counter_id": {"type": "string"}, "metrics": {"type": "array", "items": {"type": "string"}},
             "dimensions": {"type": "array", "items": {"type": "string"}},
             "date1": {"type": "string"}, "date2": {"type": "string"},
             "filters": {"type": "string"}, "sort": {"type": "string"}, "limit": {"type": "integer"}},
             "required": ["counter_id", "metrics"]}},
        _exec_metrika_get_report,
    ),
    "metrika_get_report_by_time": (
        {"name": "metrika_get_report_by_time",
         "description": "Динамика метрик Метрики по времени (/bytime) — тренды по дням/неделям/месяцам.",
         "parameters": {"type": "object", "properties": {
             "counter_id": {"type": "string"}, "metrics": {"type": "array", "items": {"type": "string"}},
             "group": {"type": "string", "enum": ["day", "week", "month", "quarter", "year"]},
             "dimensions": {"type": "array", "items": {"type": "string"}},
             "date1": {"type": "string"}, "date2": {"type": "string"}},
             "required": ["counter_id", "metrics"]}},
        _exec_metrika_get_report_by_time,
    ),
    "wordstat_top_requests": (
        {"name": "wordstat_top_requests",
         "description": "Wordstat: популярные поисковые запросы и ассоциации по фразе (спрос в Яндексе). Не требует проекта.",
         "parameters": {"type": "object", "properties": {
             "phrase": {"type": "string", "description": "Ключевая фраза."}, "devices": _DEVICES},
             "required": ["phrase"]}},
        _exec_wordstat_top_requests,
    ),
    "wordstat_dynamics": (
        {"name": "wordstat_dynamics",
         "description": "Wordstat: динамика частотности фразы по времени (тренд спроса).",
         "parameters": {"type": "object", "properties": {
             "phrase": {"type": "string"},
             "period": {"type": "string", "enum": ["monthly", "weekly", "daily"]},
             "from_date": {"type": "string", "description": "YYYY-MM-DD"},
             "to_date": {"type": "string", "description": "YYYY-MM-DD"},
             "devices": _DEVICES},
             "required": ["phrase"]}},
        _exec_wordstat_dynamics,
    ),
    "wordstat_regions": (
        {"name": "wordstat_regions",
         "description": "Wordstat: региональное распределение спроса по фразе.",
         "parameters": {"type": "object", "properties": {
             "phrase": {"type": "string"},
             "region_type": {"type": "string", "enum": ["all", "cities", "regions"]},
             "devices": _DEVICES},
             "required": ["phrase"]}},
        _exec_wordstat_regions,
    ),
}

_WORDSTAT_TOOLS = {"wordstat_top_requests", "wordstat_dynamics", "wordstat_regions"}


def tool_schemas() -> list[dict]:
    """Инструменты для OpenRouter. Wordstat включается только при наличии ключа."""
    wordstat_ok = wordstat_client.is_configured()
    out = []
    for name, (schema, _) in _REGISTRY.items():
        if name in _WORDSTAT_TOOLS and not wordstat_ok:
            continue
        out.append({"type": "function", "function": schema})
    return out


async def execute_tool(name: str, args: dict, ctx: ToolContext) -> str:
    entry = _REGISTRY.get(name)
    if not entry:
        return _dump({"error": f"Неизвестный инструмент: {name}"})
    _, executor = entry
    try:
        return await executor(ctx, args or {})
    except (YandexApiError, wordstat_client.WordstatError) as exc:
        return _dump({"error": str(exc)})
    except KeyError as exc:
        return _dump({"error": f"Не хватает обязательного параметра: {exc}"})
    except Exception as exc:  # noqa: BLE001
        return _dump({"error": f"Ошибка инструмента {name}: {exc}"})
