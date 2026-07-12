"""
Детектор аномалий рекламных метрик.

Правила, не AI. Два режима:
  Mode 1 (baseline) — сравнение с историей (6 недель, по дням недели).
  Mode 2 (plan-fact) — 2A темп расхода vs бюджет, 2B факт CPA vs целевой.

Запускается после каждой синхронизации для проекта.
"""
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from core import models
from core.config import get_config, DetectorCfg
from backend_api.services.detector_holidays import is_near_holiday

logger = logging.getLogger("detector")

# ── Default thresholds (from TZ) ─────────────────────────────────

DEFAULT_THRESHOLDS: dict[str, dict[str, float]] = {
    "expenses":    {"warning": 0.25, "problem": 0.40},
    "clicks":      {"warning": 0.30, "problem": 0.50},
    "impressions": {"warning": 0.30, "problem": 0.50},
    "cpc":         {"warning": 0.25, "problem": 0.40},
    "conversions": {"warning": 0.35, "problem": 0.55},
    "cpa":         {"warning": 0.40, "problem": 0.60},
}

METRICS = ["expenses", "impressions", "clicks", "cpc", "conversions", "cpa"]

# Расход из API рекламных кабинетов приходит без НДС. На дашборде и в целевых
# CPA пользователь оперирует суммами с НДС (×1.22), поэтому в формуле план-факт
# CPA (Режим 2Б) расход тоже приводим к сумме с НДС — иначе факт CPA занижен
# относительно целевого, который агентство задаёт «как на дашборде».
VAT_RATE = 1.22

# Campaign level is intentionally narrow in iteration 2: only money-without-result
# signals paint campaign rows. Yandex conversions come from selected Metrika goals.
CAMPAIGN_METRICS_YD = ["cpa"]
CAMPAIGN_METRICS_VK = ["cpa"]

BAD_DIRECTIONS = {
    "expenses": {"up", "down"},
    "impressions": {"down"},
    "clicks": {"down"},
    "cpc": {"up"},
    "conversions": {"down"},
    "cpa": {"up"},
}

# ── Correlation patterns (from TZ 1.9) ───────────────────────────

PATTERNS = [
    {
        "key": "budget_exhausted",
        "text": "Закончился бюджет или остановилась кампания",
        "match": lambda d: d.get("expenses") == "down" and d.get("clicks") == "down",
    },
    {
        "key": "auction_up",
        "text": "Подорожал аукцион / выросла конкуренция",
        "match": lambda d: d.get("cpc") == "up" and d.get("clicks") == "down",
    },
    {
        "key": "reach_down",
        "text": "Сужение охвата / упал объём трафика",
        "match": lambda d: d.get("impressions") == "down",
    },
    {
        "key": "conversion_drop",
        "text": "Просела конверсия сайта / посадочной",
        "match": lambda d: d.get("cpa") == "up" and d.get("conversions") == "down" and d.get("clicks") != "down",
    },
    {
        "key": "tracking_issue",
        "text": "Проблема с целями Метрики / трекингом",
        "match": lambda d: d.get("conversions") == "down" and d.get("clicks") != "down" and d.get("expenses") != "down",
    },
    {
        "key": "empty_spend",
        "text": "Открут в пустоту — проверить таргетинг/площадки",
        "match": lambda d: d.get("expenses") == "up" and d.get("conversions") in ("down", None),
    },
]


@dataclass
class AlertCandidate:
    metric: str
    detection_level: str
    entity_id: Optional[str]
    channel: Optional[models.IntegrationPlatform]
    mode: str
    severity: str
    deviation_pct: float
    baseline_value: float
    actual_value: float
    direction: str  # "up" or "down"
    consecutive_days: int = 1
    pattern_key: Optional[str] = None
    hypothesis_text: Optional[str] = None
    # Structured context is consumed by the UI/AI, while the deterministic
    # text above remains safe to show when AI is unavailable.
    meta: Optional[dict] = None


_METRIC_NAMES_RU: dict[str, str] = {
    "expenses": "расходы",
    "clicks": "клики",
    "impressions": "показы",
    "cpc": "CPC",
    "conversions": "заявки",
    "cpa": "CPL",
}


def _fmt_plain(v: float) -> str:
    return f"{round(float(v or 0)):,.0f}".replace(",", " ")


def _money_multiplier(channel: Optional[models.IntegrationPlatform]) -> float:
    # Avito API already returns VAT-inclusive amounts. Other ad APIs are
    # normalized in our UI as VAT-inclusive (×1.22), and alert copy follows UI.
    return 1.0 if channel == models.IntegrationPlatform.AVITO_ADS else VAT_RATE


def _fmt_money(v: float, channel: Optional[models.IntegrationPlatform] = None) -> str:
    return f"{_fmt_plain(float(v or 0) * _money_multiplier(channel))} ₽"


def _fmt_change_ru(deviation_pct: float, direction: str) -> str:
    abs_pct = abs(float(deviation_pct or 0))
    word_more = "больше" if direction == "up" else "меньше"
    if abs_pct > 100:
        ratio = 1 + abs_pct / 100
        return f"в {ratio:.1f} раза {word_more}".replace(".", ",")
    return f"на {round(abs_pct)}% {word_more}"


def _period_ru(days: int) -> str:
    d = max(int(days or 1), 1)
    if d == 1:
        return "за последний день"
    if d in (2, 3, 4):
        return f"за последние {d} дня"
    return f"за последние {d} дней"


def _make_hypothesis_text(c: "AlertCandidate", pattern_text: Optional[str] = None) -> str:
    period = _period_ru(c.consecutive_days)
    change = _fmt_change_ru(c.deviation_pct, c.direction)
    base_label = "по плану" if c.mode.startswith("plan") else "обычно для этого проекта"
    suffix = " Суммы с НДС."

    if c.mode == "plan_spend":
        expected = _fmt_money(c.baseline_value, c.channel)
        actual = _fmt_money(c.actual_value, c.channel)
        if c.direction == "up":
            return (
                f"Тратим быстрее плана. К текущей дате ожидалось ~{expected}, "
                f"по факту — {actual} ({change}). При таком темпе бюджет закончится раньше периода."
                f"{suffix}"
            )
        return (
            f"Отстаём от плана расхода. К текущей дате должно быть потрачено ~{expected}, "
            f"по факту — {actual} ({change}). При таком темпе бюджет открутится не полностью."
            f"{suffix}"
        )

    if c.mode == "plan_cpa":
        return (
            f"Стоимость заявки выше цели. Целевой CPL — {_fmt_money(c.baseline_value, c.channel)}, "
            f"по факту {period} — {_fmt_money(c.actual_value, c.channel)} ({change}).{suffix}"
        )

    if c.pattern_key == "empty_spend":
        return (
            f"Бюджет тратится без заявок. {period.capitalize()} расход по кампании — "
            f"{_fmt_money(c.actual_value, c.channel)}, заявок — 0. Проверьте таргетинг, площадки и посадочную страницу."
            f"{suffix}"
        )

    if c.metric == "cpa":
        return (
            f"Заявки подорожали. {period.capitalize()} заявка стоит ~{_fmt_money(c.actual_value, c.channel)}, "
            f"{base_label} — ~{_fmt_money(c.baseline_value, c.channel)} ({change}).{suffix}"
        )
    if c.metric == "conversions":
        return (
            f"Заявок меньше обычного. {period.capitalize()} — {_fmt_plain(c.actual_value)} заявок, "
            f"{base_label} — около {_fmt_plain(c.baseline_value)} ({change})."
        )
    if c.metric == "expenses" and c.direction == "down":
        return (
            f"Реклама почти не крутится. Расход {period} — {_fmt_money(c.actual_value, c.channel)}, "
            f"{base_label} — ~{_fmt_money(c.baseline_value, c.channel)}. "
            f"Похоже, закончился бюджет или остановились кампании — проверьте баланс или РК.{suffix}"
        )
    if c.metric == "expenses" and c.direction == "up":
        return (
            f"Бюджет тратится быстрее обычного. Расход {period} — {_fmt_money(c.actual_value, c.channel)}, "
            f"{base_label} — ~{_fmt_money(c.baseline_value, c.channel)} ({change}).{suffix}"
        )
    if c.metric == "cpc":
        return (
            f"Клики подорожали. CPC {period} — {_fmt_money(c.actual_value, c.channel)} "
            f"при обычных ~{_fmt_money(c.baseline_value, c.channel)}: тот же расход даёт меньше трафика. "
            f"Похоже, подорожал аукцион или выросла конкуренция.{suffix}"
        )
    if c.metric == "impressions":
        return (
            f"Охват сузился. Показов {period} {change}. "
            f"Проверьте ставки, статусы кампаний и ограничения показов."
        )
    if c.metric == "clicks":
        return (
            f"Кликов стало меньше. {period.capitalize()} — {_fmt_plain(c.actual_value)}, "
            f"{base_label} — около {_fmt_plain(c.baseline_value)} ({change})."
        )

    metric_ru = _METRIC_NAMES_RU.get(c.metric, c.metric)
    return (
        f"Изменился показатель «{metric_ru}». Факт {period} — {_fmt_plain(c.actual_value)}, "
        f"{base_label} — около {_fmt_plain(c.baseline_value)} ({change})."
    )


# ── Thresholds ────────────────────────────────────────────────────

def get_thresholds(cfg: DetectorCfg) -> dict:
    thresholds = {metric: values.copy() for metric, values in DEFAULT_THRESHOLDS.items()}
    if cfg.thresholds_json:
        try:
            overrides = json.loads(cfg.thresholds_json)
            for metric, vals in overrides.items():
                if metric in thresholds:
                    thresholds[metric].update(vals)
        except Exception:
            pass
    return thresholds


# ── Metric queries ────────────────────────────────────────────────

def _query_daily_metrics(
    db: Session,
    client_id: uuid.UUID,
    channel: models.IntegrationPlatform,
    d_start: date,
    d_end: date,
) -> list[dict]:
    """Query per-day aggregated metrics for a channel within date range."""
    rows = []

    if channel == models.IntegrationPlatform.YANDEX_DIRECT:
        q = (
            db.query(
                models.YandexStats.date.label("dt"),
                func.sum(models.YandexStats.cost).label("expenses"),
                func.sum(models.YandexStats.impressions).label("impressions"),
                func.sum(models.YandexStats.clicks).label("clicks"),
            )
            .filter(
                models.YandexStats.client_id == client_id,
                models.YandexStats.date >= d_start,
                models.YandexStats.date <= d_end,
            )
            .group_by(models.YandexStats.date)
            .all()
        )
        yandex_daily = {r.dt: r for r in q}

        selected_goal_ids = set()
        for intg in db.query(models.Integration).filter(
            models.Integration.client_id == client_id,
            models.Integration.platform == models.IntegrationPlatform.YANDEX_DIRECT,
        ).all():
            if intg.selected_goals:
                try:
                    sg = json.loads(intg.selected_goals) if isinstance(intg.selected_goals, str) else intg.selected_goals
                    selected_goal_ids.update(str(g) for g in (sg or []))
                except Exception:
                    pass
            if intg.primary_goal_id:
                selected_goal_ids.add(str(intg.primary_goal_id))

        mq = (
            db.query(
                models.MetrikaGoals.date.label("dt"),
                func.sum(models.MetrikaGoals.conversion_count).label("conversions"),
            )
            .filter(
                models.MetrikaGoals.client_id == client_id,
                models.MetrikaGoals.date >= d_start,
                models.MetrikaGoals.date <= d_end,
                models.MetrikaGoals.goal_id != "all",
            )
        )
        if selected_goal_ids:
            mq = mq.filter(models.MetrikaGoals.goal_id.in_(selected_goal_ids))
        mq = mq.group_by(models.MetrikaGoals.date).all()
        metrika_daily = {r.dt: int(r.conversions or 0) for r in mq}

        all_dates = set(yandex_daily.keys()) | set(metrika_daily.keys())
        for dt in sorted(all_dates):
            yr = yandex_daily.get(dt)
            exp = float(yr.expenses or 0) if yr else 0.0
            imp = int(yr.impressions or 0) if yr else 0
            clk = int(yr.clicks or 0) if yr else 0
            conv = metrika_daily.get(dt, 0)
            cpc = exp / clk if clk > 0 else 0.0
            cpa = exp / conv if conv > 0 else 0.0
            rows.append({
                "date": dt, "expenses": exp, "impressions": imp, "clicks": clk,
                "conversions": conv, "cpc": cpc, "cpa": cpa,
            })

    elif channel == models.IntegrationPlatform.VK_ADS:
        q = (
            db.query(
                models.VKStats.date.label("dt"),
                func.sum(models.VKStats.cost).label("expenses"),
                func.sum(models.VKStats.impressions).label("impressions"),
                func.sum(models.VKStats.clicks).label("clicks"),
                func.sum(models.VKStats.conversions).label("conversions"),
            )
            .filter(
                models.VKStats.client_id == client_id,
                models.VKStats.date >= d_start,
                models.VKStats.date <= d_end,
            )
            .group_by(models.VKStats.date)
            .all()
        )
        for r in q:
            exp = float(r.expenses or 0)
            clk = int(r.clicks or 0)
            conv = int(r.conversions or 0)
            rows.append({
                "date": r.dt,
                "expenses": exp,
                "impressions": int(r.impressions or 0),
                "clicks": clk,
                "conversions": conv,
                "cpc": exp / clk if clk > 0 else 0.0,
                "cpa": exp / conv if conv > 0 else 0.0,
            })

    return rows


# ── Baseline ──────────────────────────────────────────────────────

def compute_baseline(
    db: Session,
    client_id: uuid.UUID,
    channel: models.IntegrationPlatform,
    reference_date: date,
    cfg: DetectorCfg,
) -> dict[str, dict[int, float]]:
    """Compute DOW-averaged baseline per metric for the baseline window."""
    skip = cfg.fresh_window_skip_days
    fresh = cfg.fresh_window_days
    baseline_days = cfg.baseline_days

    window_end = reference_date - timedelta(days=skip + fresh + 1)
    window_start = window_end - timedelta(days=baseline_days - 1)

    daily = _query_daily_metrics(db, client_id, channel, window_start, window_end)

    dow_sums: dict[str, dict[int, list[float]]] = {m: {d: [] for d in range(7)} for m in METRICS}
    for row in daily:
        dow = row["date"].weekday()  # 0=Monday ... 6=Sunday
        for m in METRICS:
            dow_sums[m][dow].append(float(row.get(m, 0)))

    result: dict[str, dict[int, float]] = {}
    for m in METRICS:
        result[m] = {}
        for dow in range(7):
            vals = dow_sums[m][dow]
            result[m][dow] = sum(vals) / len(vals) if vals else 0.0
    return result


def compute_fresh_window(
    db: Session,
    client_id: uuid.UUID,
    channel: models.IntegrationPlatform,
    reference_date: date,
    cfg: DetectorCfg,
) -> list[dict]:
    """Return daily metrics for the fresh window (recent N days, skipping incomplete)."""
    skip = cfg.fresh_window_skip_days
    fresh = cfg.fresh_window_days

    window_end = reference_date - timedelta(days=skip + 1)
    window_start = window_end - timedelta(days=fresh - 1)

    return _query_daily_metrics(db, client_id, channel, window_start, window_end)


def _best_consecutive_run(points: list[dict], min_days: int) -> list[dict]:
    """Return the longest same-direction consecutive deviation run."""
    best: list[dict] = []
    current: list[dict] = []
    prev_date: date | None = None
    prev_direction: str | None = None

    for point in sorted(points, key=lambda item: item["date"]):
        is_next_day = prev_date is not None and point["date"] == prev_date + timedelta(days=1)
        same_direction = prev_direction is not None and point["direction"] == prev_direction
        if current and is_next_day and same_direction:
            current.append(point)
        else:
            current = [point]

        if len(current) > len(best):
            best = list(current)

        prev_date = point["date"]
        prev_direction = point["direction"]

    return best if len(best) >= min_days else []


# ── Campaign helpers (Layer 5) ────────────────────────────────────

def _get_active_campaigns(
    db: Session,
    client_id: uuid.UUID,
    channel: models.IntegrationPlatform,
) -> dict[uuid.UUID, "models.Campaign"]:
    """Return active campaigns for client+channel keyed by Campaign.id."""
    campaigns = (
        db.query(models.Campaign)
        .join(models.Integration, models.Campaign.integration_id == models.Integration.id)
        .filter(
            models.Integration.client_id == client_id,
            models.Integration.platform == channel,
            models.Campaign.is_active.is_(True),
        )
        .all()
    )
    return {c.id: c for c in campaigns}


def _query_all_campaign_metrics(
    db: Session,
    client_id: uuid.UUID,
    channel: models.IntegrationPlatform,
    d_start: date,
    d_end: date,
) -> dict[uuid.UUID, list[dict]]:
    """Per-campaign daily metrics for a date range. Returns {campaign_id: [daily_row]}."""
    result: dict[uuid.UUID, list[dict]] = {}

    if channel == models.IntegrationPlatform.YANDEX_DIRECT:
        rows = (
            db.query(
                models.YandexStats.campaign_id.label("camp_id"),
                models.YandexStats.date.label("dt"),
                func.sum(models.YandexStats.cost).label("expenses"),
                func.sum(models.YandexStats.impressions).label("impressions"),
                func.sum(models.YandexStats.clicks).label("clicks"),
            )
            .filter(
                models.YandexStats.client_id == client_id,
                models.YandexStats.campaign_id.isnot(None),
                models.YandexStats.date >= d_start,
                models.YandexStats.date <= d_end,
            )
            .group_by(models.YandexStats.campaign_id, models.YandexStats.date)
            .all()
        )
        daily_campaign_rows: dict[date, list] = {}
        for r in rows:
            daily_campaign_rows.setdefault(r.dt, []).append(r)

        daily_conversions: dict[tuple[uuid.UUID, date], int] = {}
        try:
            from backend_api.stats_service import StatsService

            selected_goal_ids = set(StatsService.get_selected_metrika_goal_ids(db, [client_id], "yandex"))
            goal_scope_ids = StatsService.get_metrika_goal_integration_ids(db, [client_id], "yandex")
            for dt, day_rows in daily_campaign_rows.items():
                m_q = db.query(func.sum(models.MetrikaGoals.conversion_count)).filter(
                    models.MetrikaGoals.client_id == client_id,
                    models.MetrikaGoals.goal_id != "all",
                    models.MetrikaGoals.date == dt,
                )
                if selected_goal_ids:
                    m_q = m_q.filter(models.MetrikaGoals.goal_id.in_(selected_goal_ids))
                if goal_scope_ids:
                    m_q = m_q.filter(models.MetrikaGoals.integration_id.in_(goal_scope_ids))
                total_convs = int((m_q.scalar() or 0) or 0)
                if total_convs <= 0:
                    continue
                weights = [(r, max(float(r.expenses or 0), 0.0)) for r in day_rows]
                total_weight = sum(w for _, w in weights)
                if total_weight <= 0:
                    continue
                raw = [(r, total_convs * w / total_weight) for r, w in weights]
                base = [(r, int(v), v) for r, v in raw]
                remainder = total_convs - sum(v for _, v, _ in base)
                if remainder > 0:
                    order = sorted(range(len(base)), key=lambda i: (base[i][2] - base[i][1], weights[i][1]), reverse=True)
                    bump = set(order[:remainder])
                else:
                    bump = set()
                for idx, (r, value, _) in enumerate(base):
                    daily_conversions[(r.camp_id, dt)] = value + (1 if idx in bump else 0)
        except Exception:
            logger.exception("Failed to allocate Yandex Metrika conversions for detector")

        for r in rows:
            exp = float(r.expenses or 0)
            clk = int(r.clicks or 0)
            conv = int(daily_conversions.get((r.camp_id, r.dt), 0) or 0)
            result.setdefault(r.camp_id, []).append({
                "date": r.dt,
                "expenses": exp,
                "impressions": int(r.impressions or 0),
                "clicks": clk,
                "cpc": exp / clk if clk > 0 else 0.0,
                "conversions": conv,
                "cpa": exp / conv if conv > 0 else 0.0,
            })

    elif channel == models.IntegrationPlatform.VK_ADS:
        rows = (
            db.query(
                models.VKStats.campaign_id.label("camp_id"),
                models.VKStats.date.label("dt"),
                func.sum(models.VKStats.cost).label("expenses"),
                func.sum(models.VKStats.impressions).label("impressions"),
                func.sum(models.VKStats.clicks).label("clicks"),
                func.sum(models.VKStats.conversions).label("conversions"),
            )
            .filter(
                models.VKStats.client_id == client_id,
                models.VKStats.campaign_id.isnot(None),
                models.VKStats.date >= d_start,
                models.VKStats.date <= d_end,
            )
            .group_by(models.VKStats.campaign_id, models.VKStats.date)
            .all()
        )
        for r in rows:
            exp = float(r.expenses or 0)
            clk = int(r.clicks or 0)
            conv = int(r.conversions or 0)
            result.setdefault(r.camp_id, []).append({
                "date": r.dt,
                "expenses": exp,
                "impressions": int(r.impressions or 0),
                "clicks": clk,
                "cpc": exp / clk if clk > 0 else 0.0,
                "conversions": conv,
                "cpa": exp / conv if conv > 0 else 0.0,
            })

    return result


def check_mode1_campaigns(
    db: Session,
    client_id: uuid.UUID,
    channel: models.IntegrationPlatform,
    reference_date: date,
    cfg: DetectorCfg,
) -> list[AlertCandidate]:
    """Mode 1 campaign-level detection (TZ Layer 5). Stricter volume filters."""
    active = _get_active_campaigns(db, client_id, channel)
    if not active:
        return []

    skip = cfg.fresh_window_skip_days
    fresh_n = cfg.fresh_window_days
    baseline_n = cfg.baseline_days

    fresh_end = reference_date - timedelta(days=skip + 1)
    fresh_start = fresh_end - timedelta(days=fresh_n - 1)
    baseline_end = reference_date - timedelta(days=skip + fresh_n + 1)
    baseline_start = baseline_end - timedelta(days=baseline_n - 1)

    baseline_data = _query_all_campaign_metrics(db, client_id, channel, baseline_start, baseline_end)
    fresh_data = _query_all_campaign_metrics(db, client_id, channel, fresh_start, fresh_end)

    thresholds = get_thresholds(cfg)
    metrics = (
        CAMPAIGN_METRICS_YD
        if channel == models.IntegrationPlatform.YANDEX_DIRECT
        else CAMPAIGN_METRICS_VK
    )
    min_spend = cfg.campaign_min_baseline_spend

    candidates: list[AlertCandidate] = []

    for camp_id, campaign in active.items():
        base_daily = baseline_data.get(camp_id, [])
        fresh_daily = fresh_data.get(camp_id, [])
        if not base_daily or not fresh_daily:
            continue

        avg_daily_spend = sum(r["expenses"] for r in base_daily) / len(base_daily)
        if avg_daily_spend < min_spend:
            continue

        camp_baseline: dict[str, dict[int, float]] = {}
        for metric in metrics:
            dow_vals: dict[int, list[float]] = {d: [] for d in range(7)}
            for row in base_daily:
                dow_vals[row["date"].weekday()].append(float(row.get(metric, 0)))
            camp_baseline[metric] = {
                d: sum(v) / len(v) if v else 0.0
                for d, v in dow_vals.items()
            }

        total_conv = sum(r.get("conversions", 0) for r in fresh_daily)
        baseline_conv = sum(r.get("conversions", 0) for r in base_daily)

        zero_lead_points = []
        for row in fresh_daily:
            if is_near_holiday(row["date"]):
                continue
            exp = float(row.get("expenses", 0) or 0)
            conv = int(row.get("conversions", 0) or 0)
            if exp >= cfg.campaign_empty_spend_threshold and conv == 0 and baseline_conv > 0:
                zero_lead_points.append({
                    "date": row["date"],
                    "dev": 1.0,
                    "direction": "up",
                    "baseline": 0.0,
                    "actual": exp,
                })

        empty_problem = _best_consecutive_run(zero_lead_points, max(cfg.duration_problem, 3))
        empty_warning = _best_consecutive_run(zero_lead_points, max(cfg.duration_warning, 2))
        if empty_problem or empty_warning:
            run = empty_problem or empty_warning
            candidates.append(AlertCandidate(
                metric="cpa",
                detection_level="campaign",
                entity_id=str(camp_id),
                channel=channel,
                mode="baseline",
                severity="problem" if empty_problem else "warning",
                deviation_pct=100.0,
                baseline_value=0,
                actual_value=round(sum(p["actual"] for p in run) / len(run), 2),
                direction="up",
                consecutive_days=len(run),
                pattern_key="empty_spend",
            ))
            continue

        for metric in metrics:
            if metric in ("conversions", "cpa") and total_conv < cfg.min_conversions_silence:
                continue

            warning_pts: list[dict] = []
            problem_pts: list[dict] = []

            for row in fresh_daily:
                if is_near_holiday(row["date"]):
                    continue
                dow = row["date"].weekday()
                bv = camp_baseline[metric].get(dow, 0)
                av = float(row.get(metric, 0))
                if bv == 0:
                    continue
                dev = (av - bv) / bv
                direction = "up" if dev > 0 else "down"
                if direction not in BAD_DIRECTIONS.get(metric, {"up", "down"}):
                    continue
                pt = {"date": row["date"], "dev": dev, "direction": direction,
                      "baseline": float(bv), "actual": av}
                th = thresholds.get(metric, {"warning": 0.30, "problem": 0.50})
                abs_dev = abs(dev)
                if abs_dev >= th["warning"]:
                    warning_pts.append(pt)
                if abs_dev >= th["problem"]:
                    problem_pts.append(pt)

            prob_run = _best_consecutive_run(problem_pts, cfg.duration_problem)
            warn_run = _best_consecutive_run(warning_pts, cfg.duration_warning)

            if prob_run:
                severity, run = "problem", prob_run
            elif warn_run:
                severity, run = "warning", warn_run
            else:
                continue

            if metric in ("conversions", "cpa") and total_conv < cfg.min_conversions_warning_only:
                severity = "warning"

            avg_dev = sum(p["dev"] for p in run) / len(run)
            bv_avg = sum(p["baseline"] for p in run) / len(run)
            av_avg = sum(p["actual"] for p in run) / len(run)

            candidates.append(AlertCandidate(
                metric=metric,
                detection_level="campaign",
                entity_id=str(camp_id),
                channel=channel,
                mode="baseline",
                severity=severity,
                deviation_pct=round(avg_dev * 100, 2),
                baseline_value=round(bv_avg, 2),
                actual_value=round(av_avg, 2),
                direction=run[-1]["direction"],
                consecutive_days=len(run),
                pattern_key="cpa_up" if metric == "cpa" else None,
            ))

    majority_threshold = min(max(float(getattr(cfg, "campaign_majority_threshold", 0.5) or 0.5), 0.1), 1.0)
    active_count = max(len(active), 1)
    by_pattern: dict[str, list[AlertCandidate]] = {}
    for c in candidates:
        by_pattern.setdefault(c.pattern_key or c.metric, []).append(c)
    escalated: list[AlertCandidate] = []
    suppressed: set[int] = set()
    for pattern, rows in by_pattern.items():
        if len(rows) / active_count < majority_threshold:
            continue
        severity = "problem" if any(c.severity == "problem" for c in rows) else "warning"
        avg_actual = sum(c.actual_value for c in rows) / len(rows)
        avg_base = sum(c.baseline_value for c in rows) / len(rows)
        avg_dev = sum(c.deviation_pct for c in rows) / len(rows)
        escalated.append(AlertCandidate(
            metric=rows[0].metric,
            detection_level="project",
            entity_id=None,
            channel=channel,
            mode="baseline",
            severity=severity,
            deviation_pct=round(avg_dev, 2),
            baseline_value=round(avg_base, 2),
            actual_value=round(avg_actual, 2),
            direction=rows[0].direction,
            consecutive_days=max(c.consecutive_days for c in rows),
            pattern_key=pattern,
        ))
        suppressed.update(id(c) for c in rows)

    if suppressed:
        candidates = [c for c in candidates if id(c) not in suppressed] + escalated

    return candidates


# ── Mode 1: Baseline comparison ──────────────────────────────────

def check_mode1(
    baseline: dict[str, dict[int, float]],
    fresh_window: list[dict],
    thresholds: dict,
    cfg: DetectorCfg,
) -> list[AlertCandidate]:
    """Check each metric in fresh window against DOW-baseline."""
    candidates = []
    total_conversions = sum(row.get("conversions", 0) for row in fresh_window)

    for metric in METRICS:
        if metric in ("conversions", "cpa") and total_conversions < cfg.min_conversions_silence:
            continue

        warning_points: list[dict] = []
        problem_points: list[dict] = []
        for row in fresh_window:
            if is_near_holiday(row["date"]):
                continue
            dow = row["date"].weekday()
            bv = baseline[metric].get(dow, 0)
            av = float(row.get(metric, 0))
            if bv == 0:
                continue
            dev = (av - bv) / bv
            direction = "up" if dev > 0 else "down"
            if direction not in BAD_DIRECTIONS.get(metric, {"up", "down"}):
                continue

            point = {
                "date": row["date"],
                "dev": dev,
                "direction": direction,
                "baseline": float(bv),
                "actual": av,
            }

            th = thresholds.get(metric, {"warning": 0.30, "problem": 0.50})
            abs_dev = abs(dev)
            if abs_dev >= th["warning"]:
                warning_points.append(point)
            if abs_dev >= th["problem"]:
                problem_points.append(point)

        problem_run = _best_consecutive_run(problem_points, cfg.duration_problem)
        warning_run = _best_consecutive_run(warning_points, cfg.duration_warning)

        if problem_run:
            severity = "problem"
            run = problem_run
        elif warning_run:
            severity = "warning"
            run = warning_run
        else:
            continue

        if metric in ("conversions", "cpa") and total_conversions < cfg.min_conversions_warning_only:
            severity = "warning"

        avg_dev = sum(point["dev"] for point in run) / len(run)
        bv_avg = sum(point["baseline"] for point in run) / len(run)
        av_avg = sum(point["actual"] for point in run) / len(run)

        candidates.append(AlertCandidate(
            metric=metric,
            detection_level="project",
            entity_id=None,
            channel=None,
            mode="baseline",
            severity=severity,
            deviation_pct=round(avg_dev * 100, 2),
            baseline_value=round(bv_avg, 2),
            actual_value=round(av_avg, 2),
            direction=run[-1]["direction"],
            consecutive_days=len(run),
        ))

    return candidates


# ── Mode 2A: Spend pace ──────────────────────────────────────────

def check_mode2a_spend(
    db: Session,
    client_id: uuid.UUID,
    channel: models.IntegrationPlatform,
    reference_date: date,
    cfg: DetectorCfg,
) -> Optional[AlertCandidate]:
    """Compare actual spend vs expected pace within budget period."""
    budget = (
        db.query(models.ProjectBudget)
        .filter(
            models.ProjectBudget.client_id == client_id,
            models.ProjectBudget.channel == channel,
            models.ProjectBudget.period_start <= reference_date,
            models.ProjectBudget.period_end >= reference_date,
        )
        .order_by(models.ProjectBudget.created_at.desc())
        .first()
    )
    if not budget or float(budget.amount or 0) <= 0:
        return None

    total_days = (budget.period_end - budget.period_start).days + 1
    elapsed_days = (reference_date - budget.period_start).days + 1
    if total_days <= 0 or elapsed_days <= 0:
        return None

    expected_spend = float(budget.amount) * elapsed_days / total_days

    if channel == models.IntegrationPlatform.YANDEX_DIRECT:
        actual = db.query(func.sum(models.YandexStats.cost)).filter(
            models.YandexStats.client_id == client_id,
            models.YandexStats.date >= budget.period_start,
            models.YandexStats.date <= reference_date,
        ).scalar()
    elif channel == models.IntegrationPlatform.VK_ADS:
        actual = db.query(func.sum(models.VKStats.cost)).filter(
            models.VKStats.client_id == client_id,
            models.VKStats.date >= budget.period_start,
            models.VKStats.date <= reference_date,
        ).scalar()
    else:
        return None

    actual_spend = float(actual or 0)
    if expected_spend == 0:
        return None

    dev = (actual_spend - expected_spend) / expected_spend
    abs_dev = abs(dev)
    direction = "up" if dev > 0 else "down"

    th = get_thresholds(cfg).get("expenses", DEFAULT_THRESHOLDS["expenses"])
    if abs_dev < th["warning"]:
        return None
    severity = "problem" if abs_dev >= th["problem"] else "warning"

    return AlertCandidate(
        metric="expenses",
        detection_level="project",
        entity_id=None,
        channel=channel,
        mode="plan_spend",
        severity=severity,
        deviation_pct=round(dev * 100, 2),
        baseline_value=round(expected_spend, 2),
        actual_value=round(actual_spend, 2),
        direction=direction,
    )


# ── Mode 2B: CPA vs target ───────────────────────────────────────

def check_mode2b_cpa(
    db: Session,
    client_id: uuid.UUID,
    channel: models.IntegrationPlatform,
    reference_date: date,
    cfg: DetectorCfg,
) -> list[AlertCandidate]:
    """Compare actual CPA per goal vs target CPA."""
    targets = (
        db.query(models.ProjectTargetCPA)
        .filter(
            models.ProjectTargetCPA.client_id == client_id,
            models.ProjectTargetCPA.channel == channel,
            models.ProjectTargetCPA.control_enabled.is_(True),
            models.ProjectTargetCPA.target_cpa.isnot(None),
            models.ProjectTargetCPA.period_start <= reference_date,
            models.ProjectTargetCPA.period_end >= reference_date,
        )
        .all()
    )
    if not targets:
        return []

    th = get_thresholds(cfg).get("cpa", DEFAULT_THRESHOLDS["cpa"])
    candidates = []
    for target in targets:
        target_val = float(target.target_cpa or 0)
        if target_val <= 0:
            continue

        if channel == models.IntegrationPlatform.YANDEX_DIRECT:
            cost_q = db.query(func.sum(models.YandexStats.cost)).filter(
                models.YandexStats.client_id == client_id,
                models.YandexStats.date >= target.period_start,
                models.YandexStats.date <= reference_date,
            ).scalar()
            if target.is_summary:
                conv_q = db.query(func.sum(models.MetrikaGoals.conversion_count)).filter(
                    models.MetrikaGoals.client_id == client_id,
                    models.MetrikaGoals.date >= target.period_start,
                    models.MetrikaGoals.date <= reference_date,
                    models.MetrikaGoals.goal_id != "all",
                ).scalar()
            else:
                conv_q = db.query(func.sum(models.MetrikaGoals.conversion_count)).filter(
                    models.MetrikaGoals.client_id == client_id,
                    models.MetrikaGoals.goal_id == target.goal_id,
                    models.MetrikaGoals.date >= target.period_start,
                    models.MetrikaGoals.date <= reference_date,
                ).scalar()
        elif channel == models.IntegrationPlatform.VK_ADS:
            cost_q = db.query(func.sum(models.VKStats.cost)).filter(
                models.VKStats.client_id == client_id,
                models.VKStats.date >= target.period_start,
                models.VKStats.date <= reference_date,
            ).scalar()
            conv_q = db.query(func.sum(models.VKStats.conversions)).filter(
                models.VKStats.client_id == client_id,
                models.VKStats.date >= target.period_start,
                models.VKStats.date <= reference_date,
            ).scalar()
        else:
            continue

        total_cost = float(cost_q or 0)
        total_conv = int(conv_q or 0)

        if total_conv < cfg.min_conversions_silence:
            continue

        # Расход с НДС — для соответствия целевому CPA, заданному «как на дашборде»
        actual_cpa = (total_cost * VAT_RATE) / total_conv if total_conv > 0 else 0
        dev = (actual_cpa - target_val) / target_val if target_val > 0 else 0
        if dev <= 0:
            continue
        abs_dev = abs(dev)

        if abs_dev < th["warning"]:
            continue

        severity = "problem" if abs_dev >= th["problem"] else "warning"
        if total_conv < cfg.min_conversions_warning_only:
            severity = "warning"

        candidates.append(AlertCandidate(
            metric="cpa",
            detection_level="goal" if not target.is_summary else "project",
            entity_id=target.goal_id,
            channel=channel,
            mode="plan_cpa",
            severity=severity,
            deviation_pct=round(dev * 100, 2),
            baseline_value=round(target_val, 2),
            actual_value=round(actual_cpa, 2),
            direction="up" if dev > 0 else "down",
            consecutive_days=1,
        ))

    return candidates


# ── Correlation grouping ──────────────────────────────────────────

def _is_project_baseline(c: AlertCandidate) -> bool:
    return c.mode == "baseline" and c.detection_level == "project"


def apply_correlations(candidates: list[AlertCandidate]) -> list[AlertCandidate]:
    """Detect correlated drops/spikes and assign pattern + hypothesis.

    Correlation merge applies only to project-level baseline candidates (TZ 1.7
    «связанность метрик» works on project metrics); campaign/goal-level and
    plan-fact candidates pass through untouched.
    """
    if not candidates:
        return candidates

    directions = {}
    for c in candidates:
        if _is_project_baseline(c):
            directions[c.metric] = c.direction

    matched_pattern = None
    for pat in PATTERNS:
        if pat["match"](directions):
            matched_pattern = pat
            break

    if matched_pattern:
        best = max(
            (c for c in candidates if _is_project_baseline(c)),
            key=lambda c: abs(c.deviation_pct),
            default=None,
        )
        if best:
            best.pattern_key = matched_pattern["key"]
            best.hypothesis_text = _make_hypothesis_text(best, matched_pattern["text"])
            merged = [best]
            merged.extend(c for c in candidates if not _is_project_baseline(c))
            candidates = merged

    for c in candidates:
        if c.hypothesis_text is None:
            c.hypothesis_text = _make_hypothesis_text(c)

    return candidates


# ── Alert lifecycle ───────────────────────────────────────────────

def _alert_key(c: AlertCandidate) -> tuple:
    ch_val = c.channel.value if c.channel else None
    # A composite P alert remains the same episode when its leading check
    # changes from CPL to spend (or vice versa).
    metric = "plan" if c.mode == "plan" else c.metric
    return (metric, c.detection_level, c.entity_id, ch_val, c.mode)


def _stored_alert_key(alert: models.DetectorAlert) -> tuple:
    ch_val = alert.channel.value if alert.channel else None
    metric = "plan" if alert.mode == "plan" else alert.metric
    return (metric, alert.detection_level, alert.entity_id, ch_val, alert.mode)


def upsert_alerts(
    db: Session,
    client_id: uuid.UUID,
    owner_id: uuid.UUID,
    candidates: list[AlertCandidate],
    cfg: DetectorCfg,
    notify: bool = True,
):
    """Create/update/close alerts based on current detection results.

    notify=False — alerts are still calculated/stored (TZ 1.12: disabled detector
    keeps computing in background) but no user notifications are created.
    """
    now = datetime.now(timezone.utc)

    open_alerts = (
        db.query(models.DetectorAlert)
        .filter(
            models.DetectorAlert.client_id == client_id,
            models.DetectorAlert.status.in_(["open", "dismissed", "closed"]),
        )
        .order_by(models.DetectorAlert.opened_at.desc())
        .all()
    )
    active_map = {}
    latest_map = {}
    for a in open_alerts:
        key = _stored_alert_key(a)
        latest_map.setdefault(key, a)
        if a.status in ("open", "dismissed"):
            active_map.setdefault(key, a)

    fired_keys = set()
    for c in candidates:
        key = _alert_key(c)
        fired_keys.add(key)

        existing = active_map.get(key)
        if existing:
            existing.severity = c.severity
            existing.metric = c.metric
            existing.deviation_pct = Decimal(str(c.deviation_pct))
            existing.baseline_value = Decimal(str(c.baseline_value))
            existing.actual_value = Decimal(str(c.actual_value))
            existing.consecutive_days = max(existing.consecutive_days or 1, c.consecutive_days)
            existing.pattern_key = c.pattern_key
            existing.hypothesis_text = c.hypothesis_text
            existing.last_checked_at = now
            existing.meta = {**(existing.meta or {}), **(c.meta or {}), "recovery_count": 0}
        else:
            alert = latest_map.get(key)
            if alert:
                alert.owner_id = owner_id
                alert.severity = c.severity
                alert.metric = c.metric
                alert.deviation_pct = Decimal(str(c.deviation_pct))
                alert.baseline_value = Decimal(str(c.baseline_value))
                alert.actual_value = Decimal(str(c.actual_value))
                alert.consecutive_days = c.consecutive_days
                alert.pattern_key = c.pattern_key
                alert.hypothesis_text = c.hypothesis_text
                alert.status = "open"
                alert.opened_at = now
                alert.dismissed_at = None
                alert.snoozed_until = None
                alert.snooze_source = None
                alert.not_problem_at = None
                alert.closed_at = None
                alert.last_checked_at = now
                alert.meta = {**(c.meta or {}), "recovery_count": 0}
            else:
                alert = models.DetectorAlert(
                    client_id=client_id,
                    owner_id=owner_id,
                    metric=c.metric,
                    detection_level=c.detection_level,
                    entity_id=c.entity_id,
                    channel=c.channel,
                    mode=c.mode,
                    severity=c.severity,
                    deviation_pct=Decimal(str(c.deviation_pct)),
                    baseline_value=Decimal(str(c.baseline_value)),
                    actual_value=Decimal(str(c.actual_value)),
                    consecutive_days=c.consecutive_days,
                    pattern_key=c.pattern_key,
                    hypothesis_text=c.hypothesis_text,
                    status="open",
                    opened_at=now,
                    last_checked_at=now,
                    meta={**(c.meta or {}), "recovery_count": 0},
                )
                db.add(alert)
            if notify:
                try:
                    from backend_api.services.notifications import create_notification
                    sev_text = "Проблема" if c.severity == "problem" else "Внимание"
                    create_notification(
                        db,
                        user_id=owner_id,
                        type=f"anomaly_{c.severity}",
                        title=f"{sev_text}: {c.metric}",
                        # Alert text itself is stored without a product limit;
                        # the notifications table intentionally has a 1000-char
                        # transport limit.
                        body=(c.hypothesis_text or f"Отклонение {c.metric}: {c.deviation_pct:+.1f}%")[:1000],
                        meta={"client_id": str(client_id), "metric": c.metric, "mode": c.mode},
                    )
                except Exception:
                    logger.exception("Failed to create notification for alert")

    for key, alert in active_map.items():
        if key not in fired_keys:
            if not alert.meta:
                alert.meta = {}
            recovery_count = (alert.meta or {}).get("recovery_count", 0) + 1
            alert.meta = {**(alert.meta or {}), "recovery_count": recovery_count}
            alert.last_checked_at = now
            if recovery_count >= cfg.recovery_days:
                alert.status = "closed"
                alert.closed_at = now

    db.flush()


# ── Orchestrator ──────────────────────────────────────────────────

def run_detector_for_client(
    db: Session,
    client_id: uuid.UUID,
    reference_date: date | None = None,
    immediate_plan_recalculation: bool = False,
):
    """Run the iteration-3 detector for a single project.

    The original baseline helpers are deliberately kept in this module: the
    product still calculates the baseline in the background for diagnostics and
    AI, but it must no longer create user-facing alerts from it.
    """
    from backend_api.services.detector_iteration3 import run_detector_iteration3
    return run_detector_iteration3(db, client_id, reference_date, immediate_plan_recalculation=immediate_plan_recalculation)


def _run_detector_for_client_legacy(
    db: Session,
    client_id: uuid.UUID,
    reference_date: date | None = None,
):
    """Previous v1/v2 implementation retained only as a migration reference."""
    cfg = get_config().detector
    if not cfg.enabled:
        return

    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        return

    status_val = client.status.value if hasattr(client.status, "value") else str(client.status or "")
    if status_val.upper() == "PAUSED":
        return

    ref = reference_date or date.today()
    actual_start = client.actual_start_date

    mode1_ready = False
    if actual_start:
        data_days = (ref - actual_start).days + 1
        mode1_ready = data_days >= cfg.warmup_days

    integrations = (
        db.query(models.Integration)
        .filter(models.Integration.client_id == client_id)
        .all()
    )
    channels = list({
        intg.platform for intg in integrations
        if intg.platform in (models.IntegrationPlatform.YANDEX_DIRECT, models.IntegrationPlatform.VK_ADS)
    })

    all_candidates: list[AlertCandidate] = []

    for channel in channels:
        if mode1_ready:
            baseline = compute_baseline(db, client_id, channel, ref, cfg)
            fresh = compute_fresh_window(db, client_id, channel, ref, cfg)
            if fresh:
                m1 = check_mode1(baseline, fresh, get_thresholds(cfg), cfg)
                for c in m1:
                    c.channel = channel
                all_candidates.extend(m1)

            # Layer 5: campaign-level detection (TZ 1.7)
            camp = check_mode1_campaigns(db, client_id, channel, ref, cfg)
            all_candidates.extend(camp)

        m2a = check_mode2a_spend(db, client_id, channel, ref, cfg)
        if m2a:
            all_candidates.append(m2a)

        m2b = check_mode2b_cpa(db, client_id, channel, ref, cfg)
        all_candidates.extend(m2b)

    # TZ 1.8: «при наличии плана детектор по абсолютному расходу — мягкий или отключён».
    # When an active budget plan exists for a channel, Mode 2A (pace) is the authoritative
    # expense signal — suppress Mode 1 project-level expense alerts for that channel,
    # regardless of whether 2A fired (plan change is not an anomaly).
    planned_channels = {
        row.channel
        for row in db.query(models.ProjectBudget.channel)
        .filter(
            models.ProjectBudget.client_id == client_id,
            models.ProjectBudget.period_start <= ref,
            models.ProjectBudget.period_end >= ref,
        )
        .all()
    }
    if planned_channels:
        all_candidates = [
            c for c in all_candidates
            if not (
                c.mode == "baseline"
                and c.metric == "expenses"
                and c.detection_level == "project"
                and c.channel in planned_channels
            )
        ]

    all_candidates = apply_correlations(all_candidates)

    # TZ 1.12: if detector is toggled off (project or account level), keep computing
    # in background but do not emit notifications
    owner = db.query(models.User).filter(models.User.id == client.owner_id).first()
    global_on = getattr(owner, "global_detector_enabled", True) if owner else True
    notify = bool(getattr(client, "detector_enabled", False)) and global_on

    upsert_alerts(db, client_id, client.owner_id, all_candidates, cfg, notify=notify)


def run_detector_all(db: Session):
    """Run detector for all active projects.

    TZ 1.12: runs even for projects with detector toggled off — keeps computing
    in background so data is ready on re-enable; visibility is gated at API level.
    """
    clients = (
        db.query(models.Client)
        .filter(
            models.Client.status == models.ClientStatus.ACTIVE,
        )
        .all()
    )
    for client in clients:
        try:
            run_detector_for_client(db, client.id)
        except Exception:
            logger.exception("Detector failed for client %s", client.id)
