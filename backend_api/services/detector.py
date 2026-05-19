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
    pattern_key: Optional[str] = None
    hypothesis_text: Optional[str] = None


# ── Thresholds ────────────────────────────────────────────────────

def get_thresholds(cfg: DetectorCfg) -> dict:
    thresholds = dict(DEFAULT_THRESHOLDS)
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

        deviations = []
        for row in fresh_window:
            if is_near_holiday(row["date"]):
                continue
            dow = row["date"].weekday()
            bv = baseline[metric].get(dow, 0)
            av = float(row.get(metric, 0))
            if bv == 0:
                continue
            dev = (av - bv) / bv
            deviations.append(dev)

        if not deviations:
            continue

        avg_dev = sum(deviations) / len(deviations)
        abs_dev = abs(avg_dev)
        direction = "up" if avg_dev > 0 else "down"

        th = thresholds.get(metric, {"warning": 0.30, "problem": 0.50})

        severity = None
        if abs_dev >= th["problem"]:
            if len(deviations) >= cfg.duration_problem:
                severity = "problem"
            elif len(deviations) >= cfg.duration_warning:
                severity = "warning"
        elif abs_dev >= th["warning"]:
            if len(deviations) >= cfg.duration_warning:
                severity = "warning"

        if severity is None:
            continue

        if metric in ("conversions", "cpa") and total_conversions < cfg.min_conversions_warning_only:
            severity = "warning"

        bv_avg = sum(baseline[metric].values()) / max(len(baseline[metric]), 1)
        av_avg = sum(row.get(metric, 0) for row in fresh_window) / max(len(fresh_window), 1)

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
            direction=direction,
        ))

    return candidates


# ── Mode 2A: Spend pace ──────────────────────────────────────────

def check_mode2a_spend(
    db: Session,
    client_id: uuid.UUID,
    channel: models.IntegrationPlatform,
    reference_date: date,
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

    if abs_dev < 0.25:
        return None
    severity = "problem" if abs_dev >= 0.40 else "warning"

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

        actual_cpa = total_cost / total_conv if total_conv > 0 else 0
        dev = (actual_cpa - target_val) / target_val if target_val > 0 else 0
        abs_dev = abs(dev)

        if abs_dev < 0.25:
            continue

        severity = "problem" if abs_dev >= 0.40 else "warning"
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
        ))

    return candidates


# ── Correlation grouping ──────────────────────────────────────────

def apply_correlations(candidates: list[AlertCandidate]) -> list[AlertCandidate]:
    """Detect correlated drops/spikes and assign pattern + hypothesis."""
    if not candidates:
        return candidates

    directions = {}
    for c in candidates:
        if c.mode == "baseline":
            directions[c.metric] = c.direction

    matched_pattern = None
    for pat in PATTERNS:
        if pat["match"](directions):
            matched_pattern = pat
            break

    if matched_pattern:
        best = max(
            (c for c in candidates if c.mode == "baseline"),
            key=lambda c: abs(c.deviation_pct),
            default=None,
        )
        if best:
            best.pattern_key = matched_pattern["key"]
            best.hypothesis_text = matched_pattern["text"]
            merged = [best]
            merged.extend(c for c in candidates if c.mode != "baseline")
            return merged

    return candidates


# ── Alert lifecycle ───────────────────────────────────────────────

def _alert_key(c: AlertCandidate) -> tuple:
    ch_val = c.channel.value if c.channel else None
    return (c.metric, c.detection_level, c.entity_id, ch_val, c.mode)


def upsert_alerts(
    db: Session,
    client_id: uuid.UUID,
    owner_id: uuid.UUID,
    candidates: list[AlertCandidate],
    cfg: DetectorCfg,
):
    """Create/update/close alerts based on current detection results."""
    now = datetime.now(timezone.utc)

    open_alerts = (
        db.query(models.DetectorAlert)
        .filter(
            models.DetectorAlert.client_id == client_id,
            models.DetectorAlert.status == "open",
        )
        .all()
    )
    open_map = {}
    for a in open_alerts:
        ch_val = a.channel.value if a.channel else None
        key = (a.metric, a.detection_level, a.entity_id, ch_val, a.mode)
        open_map[key] = a

    fired_keys = set()
    for c in candidates:
        key = _alert_key(c)
        fired_keys.add(key)

        existing = open_map.get(key)
        if existing:
            existing.severity = c.severity
            existing.deviation_pct = Decimal(str(c.deviation_pct))
            existing.baseline_value = Decimal(str(c.baseline_value))
            existing.actual_value = Decimal(str(c.actual_value))
            existing.consecutive_days = (existing.consecutive_days or 0) + 1
            existing.pattern_key = c.pattern_key
            existing.hypothesis_text = c.hypothesis_text
            existing.last_checked_at = now
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
                consecutive_days=1,
                pattern_key=c.pattern_key,
                hypothesis_text=c.hypothesis_text,
                status="open",
                opened_at=now,
                last_checked_at=now,
            )
            db.add(alert)
            try:
                from backend_api.services.notifications import create_notification
                sev_text = "Проблема" if c.severity == "problem" else "Внимание"
                create_notification(
                    db,
                    user_id=owner_id,
                    type=f"anomaly_{c.severity}",
                    title=f"{sev_text}: {c.metric}",
                    body=c.hypothesis_text or f"Отклонение {c.metric}: {c.deviation_pct:+.1f}%",
                    meta={"client_id": str(client_id), "metric": c.metric, "mode": c.mode},
                )
            except Exception:
                logger.exception("Failed to create notification for alert")

    for key, alert in open_map.items():
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
):
    """Run all detector checks for a single project."""
    cfg = get_config().detector
    if not cfg.enabled:
        return

    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        return

    status_val = client.status.value if hasattr(client.status, "value") else str(client.status or "")
    if status_val.upper() == "PAUSED":
        return
    if not client.detector_enabled:
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

        m2a = check_mode2a_spend(db, client_id, channel, ref)
        if m2a:
            all_candidates.append(m2a)

        m2b = check_mode2b_cpa(db, client_id, channel, ref, cfg)
        all_candidates.extend(m2b)

    all_candidates = apply_correlations(all_candidates)

    upsert_alerts(db, client_id, client.owner_id, all_candidates, cfg)


def run_detector_all(db: Session):
    """Run detector for all active projects with detector enabled."""
    clients = (
        db.query(models.Client)
        .filter(
            models.Client.detector_enabled.is_(True),
            models.Client.status == models.ClientStatus.ACTIVE,
        )
        .all()
    )
    for client in clients:
        try:
            run_detector_for_client(db, client.id)
        except Exception:
            logger.exception("Detector failed for client %s", client.id)
