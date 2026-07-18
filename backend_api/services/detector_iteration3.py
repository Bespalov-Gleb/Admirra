"""Iteration 3 detector: plan/fact first, critical failures always.

Historical baselines intentionally remain calculated by ``detector.py`` for
diagnostics and AI.  This module is the only producer of user-facing detector
alerts, so secondary metrics and baseline deviations cannot leak back into the
product as alerts.
"""
from __future__ import annotations

import json
import logging
import math
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Iterable, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend_api.services.detector import AlertCandidate, VAT_RATE, compute_baseline, upsert_alerts
from core import models
from core.config import DetectorCfg, get_config


logger = logging.getLogger("detector.iteration3")
AD_CHANNELS = (models.IntegrationPlatform.YANDEX_DIRECT, models.IntegrationPlatform.VK_ADS)


def _enum(value) -> str:
    return value.value if hasattr(value, "value") else str(value or "")


def _money_factor(channel: models.IntegrationPlatform | None) -> float:
    return 1.0 if channel == models.IntegrationPlatform.AVITO_ADS else VAT_RATE


def _money(value: float) -> str:
    return f"{round(float(value or 0)):,}".replace(",", " ") + " ₽"


def _date_ru(value: date) -> str:
    return value.strftime("%d.%m")


def _table_for(channel: models.IntegrationPlatform):
    if channel == models.IntegrationPlatform.YANDEX_DIRECT:
        return models.YandexStats
    if channel == models.IntegrationPlatform.VK_ADS:
        return models.VKStats
    return None


def _ad_integrations(db: Session, client_id: uuid.UUID) -> list[models.Integration]:
    return (
        db.query(models.Integration)
        .filter(
            models.Integration.client_id == client_id,
            models.Integration.platform.in_(AD_CHANNELS),
        )
        .all()
    )


def _vk_lead_codes(db: Session, client_id: uuid.UUID) -> set[str]:
    """Выбранные лид-типы VK для быстрых проверок детектора.

    Пустой set означает «лиды не настроены». Считать все native-конверсии
    лидовыми нельзя; точные запросы ниже дополнительно применяют scope отдельно
    для каждой интеграции, чтобы не смешивать настройки нескольких кабинетов.
    """
    from backend_api.stats_service import StatsService

    scope = StatsService.get_vk_lead_action_scope(db, [client_id])
    return {code for codes in scope.values() for code in codes}


def _vk_leads_query(db: Session, client_id: uuid.UUID, start: date, end: date, vk_codes: set[str] | None, goal_id: str | None = None):
    """Sum of VK leads honouring the project's selected lead action types."""
    query = db.query(func.sum(models.VKStats.conversions)).filter(
        models.VKStats.client_id == client_id,
        models.VKStats.date >= start,
        models.VKStats.date <= end,
    )
    if goal_id is not None:
        query = query.join(models.Campaign, models.VKStats.campaign_id == models.Campaign.id).filter(
            models.Campaign.vk_goal_action_id == str(goal_id)
        )
    else:
        # Для сводной цели применяем выбор отдельно для каждого VK-кабинета.
        from backend_api.stats_service import StatsService
        query = query.join(models.Campaign, models.VKStats.campaign_id == models.Campaign.id)
        query = StatsService.apply_vk_lead_action_scope(query, db, [client_id])
    return query


def _vk_lead_spend(db: Session, client_id: uuid.UUID, start: date, end: date, vk_codes: set[str] | None) -> float | None:
    """«Лидовый расход» VK — расход только кампаний выбранных действий."""
    from backend_api.stats_service import StatsService

    query = (
        db.query(func.sum(models.VKStats.cost))
        .join(models.Campaign, models.VKStats.campaign_id == models.Campaign.id)
        .filter(
            models.VKStats.client_id == client_id,
            models.VKStats.date >= start,
            models.VKStats.date <= end,
        )
    )
    row = StatsService.apply_vk_lead_action_scope(query, db, [client_id]).one()
    return float(row[0] or 0)


def _selected_goal_ids(integrations: Iterable[models.Integration]) -> set[str]:
    result: set[str] = set()
    for integration in integrations:
        if integration.platform != models.IntegrationPlatform.YANDEX_DIRECT:
            continue
        raw = integration.selected_goals
        if raw:
            try:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                for item in parsed or []:
                    result.add(str(item.get("id") if isinstance(item, dict) else item))
            except (TypeError, ValueError, json.JSONDecodeError):
                logger.warning("Invalid selected_goals for integration %s", integration.id)
        if integration.primary_goal_id:
            result.add(str(integration.primary_goal_id))
    return result


def _sum_channel_stats(
    db: Session,
    client_id: uuid.UUID,
    channel: models.IntegrationPlatform,
    start: date,
    end: date,
    selected: set[str] | None = None,
    vk_codes: set[str] | None = None,
) -> tuple[float, int, int]:
    """Spend (including project display VAT), clicks and all configured leads.

    ``selected``/``vk_codes`` let one detector run reuse the goal configuration
    instead of re-reading integrations on every window.
    """
    table = _table_for(channel)
    if not table or end < start:
        return 0.0, 0, 0
    row = (
        db.query(func.sum(table.cost), func.sum(table.clicks), func.sum(table.conversions))
        .filter(table.client_id == client_id, table.date >= start, table.date <= end)
        .one()
    )
    raw_spend = float(row[0] or 0)
    clicks = int(row[1] or 0)
    if channel == models.IntegrationPlatform.VK_ADS:
        if vk_codes is None:
            vk_codes = _vk_lead_codes(db, client_id)
        leads = int(_vk_leads_query(db, client_id, start, end, vk_codes).scalar() or 0)
        # CPL считаем от лидового расхода — расход кампаний с лидовым objective,
        # а не всего кабинета VK (ТЗ единого дашборда п.10).
        raw_spend = _vk_lead_spend(db, client_id, start, end, vk_codes) or 0.0
    else:
        query = db.query(func.sum(models.MetrikaGoals.conversion_count)).filter(
            models.MetrikaGoals.client_id == client_id,
            models.MetrikaGoals.date >= start,
            models.MetrikaGoals.date <= end,
            models.MetrikaGoals.goal_id != "all",
        )
        if selected is None:
            selected = _selected_goal_ids(_ad_integrations(db, client_id))
        if selected:
            query = query.filter(models.MetrikaGoals.goal_id.in_(selected))
        leads = int(query.scalar() or 0)
    return raw_spend * _money_factor(channel), clicks, leads


def _window_funnel(
    db: Session,
    client_id: uuid.UUID,
    channel: models.IntegrationPlatform,
    start: date,
    end: date,
    selected: set[str] | None = None,
    vk_codes: set[str] | None = None,
) -> dict:
    """Full funnel for the diagnostic layer: spend, impressions, clicks, leads."""
    table = _table_for(channel)
    if not table or end < start:
        return {"spend": 0.0, "impressions": 0, "clicks": 0, "leads": 0}
    row = (
        db.query(func.sum(table.cost), func.sum(table.impressions), func.sum(table.clicks), func.sum(table.conversions))
        .filter(table.client_id == client_id, table.date >= start, table.date <= end)
        .one()
    )
    spend = float(row[0] or 0) * _money_factor(channel)
    impressions = int(row[1] or 0)
    clicks = int(row[2] or 0)
    if channel == models.IntegrationPlatform.VK_ADS:
        if vk_codes is None:
            vk_codes = _vk_lead_codes(db, client_id)
        leads = int(_vk_leads_query(db, client_id, start, end, vk_codes).scalar() or 0)
    else:
        query = db.query(func.sum(models.MetrikaGoals.conversion_count)).filter(
            models.MetrikaGoals.client_id == client_id,
            models.MetrikaGoals.date >= start,
            models.MetrikaGoals.date <= end,
            models.MetrikaGoals.goal_id != "all",
        )
        if selected:
            query = query.filter(models.MetrikaGoals.goal_id.in_(selected))
        leads = int(query.scalar() or 0)
    return {"spend": spend, "impressions": impressions, "clicks": clicks, "leads": leads}


def _sum_goal_leads(
    db: Session,
    client_id: uuid.UUID,
    channel: models.IntegrationPlatform,
    goal_id: str | None,
    is_summary: bool,
    start: date,
    end: date,
    selected: set[str] | None = None,
    vk_codes: set[str] | None = None,
) -> int:
    if end < start:
        return 0
    if channel == models.IntegrationPlatform.VK_ADS:
        if vk_codes is None and is_summary:
            vk_codes = _vk_lead_codes(db, client_id)
        # Отдельная цель VK — это конкретный тип целевого действия кампаний;
        # summary — сумма по выбранным лид-типам проекта.
        query = _vk_leads_query(
            db, client_id, start, end, vk_codes,
            goal_id=None if is_summary else goal_id,
        )
        return int(query.scalar() or 0)
    query = db.query(func.sum(models.MetrikaGoals.conversion_count)).filter(
        models.MetrikaGoals.client_id == client_id,
        models.MetrikaGoals.date >= start,
        models.MetrikaGoals.date <= end,
        models.MetrikaGoals.goal_id != "all",
    )
    if not is_summary:
        query = query.filter(models.MetrikaGoals.goal_id == str(goal_id))
    else:
        if selected is None:
            selected = _selected_goal_ids(_ad_integrations(db, client_id))
        if selected:
            query = query.filter(models.MetrikaGoals.goal_id.in_(selected))
    return int(query.scalar() or 0)


def _daily_channel_values(
    db: Session,
    client_id: uuid.UUID,
    channel: models.IntegrationPlatform,
    start: date,
    end: date,
    selected: set[str] | None = None,
    vk_codes: set[str] | None = None,
) -> list[tuple[date, float, int, int]]:
    """Dense daily values. Missing data is a genuine zero only after sync is fresh.

    A single grouped query per source instead of one round-trip per day: the
    detector runs on every synchronization for every project.
    """
    table = _table_for(channel)
    if not table or end < start:
        return []
    factor = _money_factor(channel)
    stat_rows = {
        row[0]: (float(row[1] or 0) * factor, int(row[2] or 0), int(row[3] or 0))
        for row in (
            db.query(table.date, func.sum(table.cost), func.sum(table.clicks), func.sum(table.conversions))
            .filter(table.client_id == client_id, table.date >= start, table.date <= end)
            .group_by(table.date)
            .all()
        )
    }
    goal_rows: dict[date, int] = {}
    if channel == models.IntegrationPlatform.VK_ADS:
        from backend_api.stats_service import StatsService

        query = (
            db.query(models.VKStats.date, func.sum(models.VKStats.conversions))
            .join(models.Campaign, models.VKStats.campaign_id == models.Campaign.id)
            .filter(
                models.VKStats.client_id == client_id,
                models.VKStats.date >= start,
                models.VKStats.date <= end,
            )
        )
        query = StatsService.apply_vk_lead_action_scope(query, db, [client_id])
        goal_rows = {row[0]: int(row[1] or 0) for row in query.group_by(models.VKStats.date).all()}
    if channel != models.IntegrationPlatform.VK_ADS:
        query = db.query(models.MetrikaGoals.date, func.sum(models.MetrikaGoals.conversion_count)).filter(
            models.MetrikaGoals.client_id == client_id,
            models.MetrikaGoals.date >= start,
            models.MetrikaGoals.date <= end,
            models.MetrikaGoals.goal_id != "all",
        )
        if selected is None:
            selected = _selected_goal_ids(_ad_integrations(db, client_id))
        if selected:
            query = query.filter(models.MetrikaGoals.goal_id.in_(selected))
        goal_rows = {row[0]: int(row[1] or 0) for row in query.group_by(models.MetrikaGoals.date).all()}

    values: list[tuple[date, float, int, int]] = []
    cursor = start
    while cursor <= end:
        spend, clicks, conversions = stat_rows.get(cursor, (0.0, 0, 0))
        if channel == models.IntegrationPlatform.VK_ADS:
            leads = goal_rows.get(cursor, 0)
        else:
            leads = goal_rows.get(cursor, 0)
        values.append((cursor, spend, clicks, leads))
        cursor += timedelta(days=1)
    return values


def _daily_goal_leads(
    db: Session,
    client_id: uuid.UUID,
    channel: models.IntegrationPlatform,
    goal_id: str | None,
    is_summary: bool,
    start: date,
    end: date,
    selected: set[str] | None = None,
    vk_codes: set[str] | None = None,
) -> dict[date, int]:
    """Per-day lead counts for one goal (or the whole channel) in one query."""
    if end < start:
        return {}
    if channel == models.IntegrationPlatform.VK_ADS:
        query = db.query(models.VKStats.date, func.sum(models.VKStats.conversions)).filter(
            models.VKStats.client_id == client_id, models.VKStats.date >= start, models.VKStats.date <= end
        )
        if not is_summary and goal_id:
            query = query.join(models.Campaign, models.VKStats.campaign_id == models.Campaign.id).filter(
                models.Campaign.vk_goal_action_id == str(goal_id)
            )
        elif is_summary:
            from backend_api.stats_service import StatsService
            query = query.join(models.Campaign, models.VKStats.campaign_id == models.Campaign.id)
            query = StatsService.apply_vk_lead_action_scope(query, db, [client_id])
        return {row[0]: int(row[1] or 0) for row in query.group_by(models.VKStats.date).all()}
    query = db.query(models.MetrikaGoals.date, func.sum(models.MetrikaGoals.conversion_count)).filter(
        models.MetrikaGoals.client_id == client_id,
        models.MetrikaGoals.date >= start,
        models.MetrikaGoals.date <= end,
        models.MetrikaGoals.goal_id != "all",
    )
    if not is_summary:
        query = query.filter(models.MetrikaGoals.goal_id == str(goal_id))
    else:
        if selected is None:
            selected = _selected_goal_ids(_ad_integrations(db, client_id))
        if selected:
            query = query.filter(models.MetrikaGoals.goal_id.in_(selected))
    return {row[0]: int(row[1] or 0) for row in query.group_by(models.MetrikaGoals.date).all()}


def _latest_budgets(
    db: Session, client_id: uuid.UUID, reference_date: date
) -> dict[models.IntegrationPlatform | None, models.ProjectBudget]:
    rows = (
        db.query(models.ProjectBudget)
        .filter(
            models.ProjectBudget.client_id == client_id,
            models.ProjectBudget.period_start <= reference_date,
            models.ProjectBudget.period_end >= reference_date,
        )
        .order_by(models.ProjectBudget.created_at.desc(), models.ProjectBudget.id.desc())
        .all()
    )
    latest: dict[models.IntegrationPlatform | None, models.ProjectBudget] = {}
    for row in rows:
        latest.setdefault(row.channel, row)
    return latest


def _latest_targets(
    db: Session, client_id: uuid.UUID, reference_date: date
) -> list[models.ProjectTargetCPA]:
    rows = (
        db.query(models.ProjectTargetCPA)
        .filter(
            models.ProjectTargetCPA.client_id == client_id,
            models.ProjectTargetCPA.period_start <= reference_date,
            models.ProjectTargetCPA.period_end >= reference_date,
        )
        .order_by(models.ProjectTargetCPA.created_at.desc(), models.ProjectTargetCPA.id.desc())
        .all()
    )
    latest: dict[tuple, models.ProjectTargetCPA] = {}
    for row in rows:
        latest.setdefault((row.channel, row.goal_id, bool(row.is_summary)), row)
    return list(latest.values())


def _budget_for_channel(
    budgets: dict[models.IntegrationPlatform | None, models.ProjectBudget],
    channel: models.IntegrationPlatform,
) -> models.ProjectBudget | None:
    # The product may hold a project-wide budget, but never fires duplicates:
    # explicit channel plans win; otherwise only the total plan is used by the
    # caller once (channel=None is represented by the primary channel).
    return budgets.get(channel)


def _is_sync_stale(integration: models.Integration, reference_date: date, cfg: DetectorCfg) -> tuple[bool, int | None]:
    """Freeze data-dependent checks only when the imported data is stale.

    ``sync_status=FAILED`` records the latest attempt, while ``last_sync_at``
    remains the timestamp of the last successful import. A transient failed
    attempt must not hide a critical plan/fact issue when yesterday's data is
    already available.
    """
    last = integration.last_sync_at
    if not last:
        return True, None
    last_date = last.date() if isinstance(last, datetime) else last
    age = max((reference_date - last_date).days, 0)
    return age >= cfg.sync_stale_days, age


def sync_issues_for_client(db: Session, client_id: uuid.UUID, reference_date: date | None = None) -> list[dict]:
    ref = reference_date or date.today()
    cfg = get_config().detector
    issues: list[dict] = []
    for integration in _ad_integrations(db, client_id):
        stale, age = _is_sync_stale(integration, ref, cfg)
        if stale:
            channel = _enum(integration.platform)
            text = (
                f"Данные по каналу {channel} не обновлялись {age} дн."
                if age is not None
                else f"Данные по каналу {channel} недоступны — проверьте подключение."
            )
            issues.append({"channel": channel, "days": age, "text": text, "status": "no_data"})
    return issues


def _make_plan_spend(
    db: Session, client_id: uuid.UUID, channel: models.IntegrationPlatform | None,
    budget: models.ProjectBudget, reference_date: date, client: models.Client, cfg: DetectorCfg,
    selected: set[str] | None = None, channels: list[models.IntegrationPlatform] | None = None,
) -> AlertCandidate | None:
    total_days = (budget.period_end - budget.period_start).days + 1
    start = max(budget.period_start, client.actual_start_date or budget.period_start)
    elapsed = (reference_date - start).days + 1
    if total_days <= 0 or elapsed <= 0 or (reference_date - budget.period_start).days < cfg.plan_start_pause_days:
        return None
    expected = float(budget.amount) * elapsed / total_days
    if expected < cfg.plan_min_expected_spend:
        return None
    # ``channels`` carries the project-wide plan case (channel=None): the pace
    # is judged against the total spend of every fresh ad channel.
    report_channels = channels or [channel]
    actual = sum(
        _sum_channel_stats(db, client_id, report_channel, start, reference_date, selected)[0]
        for report_channel in report_channels
    )
    remaining = (budget.period_end - reference_date).days
    if actual >= float(budget.amount) and remaining >= cfg.plan_exhausted_min_days_remaining:
        text = (
            f"Бюджет периода израсходован полностью, до конца периода {remaining} дн. "
            "Согласуйте с клиентом увеличение или остановите открутку. Суммы с НДС."
        )
        return AlertCandidate("expenses", "project", None, channel, "plan_spend", "problem", 100.0,
                              float(budget.amount), actual, "up", hypothesis_text=text,
                              meta={"check": "P-1", "period_start": budget.period_start.isoformat(), "period_end": budget.period_end.isoformat(), "budget": float(budget.amount)})
    deviation = (actual - expected) / expected
    absolute = abs(deviation)
    if absolute < cfg.plan_spend_warning_deviation:
        return None
    severity = "problem" if absolute >= cfg.plan_spend_problem_deviation else "warning"
    daily_rate = actual / elapsed if elapsed else 0
    forecast = daily_rate * total_days
    if deviation < 0:
        copy = f"При таком темпе бюджет открутится не полностью (~{_money(forecast)} из {_money(float(budget.amount))})."
    else:
        depletion = start + timedelta(days=(float(budget.amount) / daily_rate if daily_rate else 0))
        shortfall = max(forecast - float(budget.amount), 0)
        copy = f"При таком темпе бюджет закончится ~к {_date_ru(depletion)}, до конца периода не хватит ~{_money(shortfall)}."
    text = (
        f"{'Перерасход' if deviation > 0 else 'Отстаём'} по темпу расхода: ожидалось ~{_money(expected)}, "
        f"по факту {_money(actual)} ({abs(round(deviation * 100))}% {'больше' if deviation > 0 else 'меньше'}). {copy} Суммы с НДС."
    )
    return AlertCandidate("expenses", "project", None, channel, "plan_spend", severity, round(deviation * 100, 2),
                          expected, actual, "up" if deviation > 0 else "down", hypothesis_text=text,
                          meta={"check": "P-1", "period_start": budget.period_start.isoformat(), "period_end": budget.period_end.isoformat(), "forecast": forecast})


def _target_window_start(
    db: Session, target: models.ProjectTargetCPA, reference_date: date, cfg: DetectorCfg
) -> date:
    # Цель — это текущая договорённость с клиентом. После её изменения
    # детектор должен сразу сравнить актуальное скользящее окно с новой целью,
    # а не молчать ещё семь дней. Иначе новый, более строгий CPL фактически
    # не защищает проект (как было у SIB ATV).
    return max(target.period_start, reference_date - timedelta(days=cfg.plan_cpl_window_days - 1))


def _target_exists(db: Session, client_id: uuid.UUID, target: models.ProjectTargetCPA) -> bool:
    if target.is_summary or target.channel != models.IntegrationPlatform.YANDEX_DIRECT:
        return True
    integrations = _ad_integrations(db, client_id)
    known = _selected_goal_ids(integrations)
    has_goal_configuration = any(bool(row.selected_goals or row.primary_goal_id) for row in integrations if row.platform == models.IntegrationPlatform.YANDEX_DIRECT)
    if has_goal_configuration:
        return str(target.goal_id) in known
    return bool(
        db.query(models.MetrikaGoals.id)
        .filter(models.MetrikaGoals.client_id == client_id, models.MetrikaGoals.goal_id == str(target.goal_id))
        .first()
    )


def _plan_base_label(period_start: date, period_end: date) -> str:
    """Мини-ТЗ P-2 §3: база расчёта всегда названа, голая цифра запрещена."""
    month_last_day = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    if period_start.day == 1 and period_end == month_last_day:
        return "с начала месяца"
    return f"с начала периода {period_start.strftime('%d.%m')}–{period_end.strftime('%d.%m')}"


def _times_ru(ratio: float) -> str:
    """«в 2 раза дороже» вместо «+117%» — правило текстов итерации 2."""
    value = f"{ratio:.1f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"в {value} раза дороже"


def _make_plan_cpl(
    db: Session, client_id: uuid.UUID, target: models.ProjectTargetCPA,
    budget: models.ProjectBudget | None, reference_date: date, cfg: DetectorCfg,
    selected: set[str] | None = None, vk_codes: set[str] | None = None,
) -> AlertCandidate | None:
    if not target.control_enabled or not target.target_cpa or not _target_exists(db, client_id, target):
        return None
    channel = target.channel
    if channel not in AD_CHANNELS:
        return None
    # Мини-ТЗ P-2: основной CPL — накопительный с начала периода плана (даты
    # версии цели). План — договорённость на период, проверяется само обещание;
    # число в алерте совпадает с карточкой при фильтре по периоду. Правило
    # «окно минимум 7 дней» отменено: ранний шум отсекают денежные фильтры.
    period_first = target.period_start
    if reference_date < period_first:
        return None
    spend, _, _ = _sum_channel_stats(db, client_id, channel, period_first, reference_date, selected)
    leads = _sum_goal_leads(db, client_id, channel, target.goal_id, bool(target.is_summary), period_first, reference_date, selected, vk_codes)
    target_cpl = float(target.target_cpa)
    budget_amount = float(budget.amount) if budget else float("inf")
    red_min = min(cfg.plan_cpl_problem_target_multiplier * target_cpl, cfg.plan_cpl_problem_budget_share * budget_amount)
    yellow_min = min(cfg.plan_cpl_warning_target_multiplier * target_cpl, cfg.plan_cpl_warning_budget_share * budget_amount)

    cpl_period = spend / leads if leads else (math.inf if spend > 0 else 0.0)
    ratio_period = cpl_period / target_cpl if target_cpl else math.inf

    # Триггер деградации: скользящие 7 дней (не раньше версии плана), только
    # красный порог и красный денежный фильтр, применённый к 7-дневному окну.
    window_start = _target_window_start(db, target, reference_date, cfg)
    spend_7d, _, _ = _sum_channel_stats(db, client_id, channel, window_start, reference_date, selected)
    leads_7d = _sum_goal_leads(db, client_id, channel, target.goal_id, bool(target.is_summary), window_start, reference_date, selected, vk_codes)
    cpl_7d = spend_7d / leads_7d if leads_7d else (math.inf if spend_7d > 0 else 0.0)
    ratio_7d = cpl_7d / target_cpl if target_cpl else math.inf

    period_severity = None
    if spend >= red_min and ratio_period >= cfg.plan_cpl_problem_ratio:
        period_severity = "problem"
    elif spend >= yellow_min and ratio_period >= cfg.plan_cpl_warning_ratio:
        period_severity = "warning"
    degradation = spend_7d >= red_min and ratio_7d >= cfg.plan_cpl_problem_ratio

    if not period_severity and not degradation:
        return None
    # Один алерт: превышены оба — ведёт накопительный, деградация внутри текстом.
    lead = "period" if period_severity else "degradation"
    severity = period_severity or "problem"

    label = target.goal_name or ("Все конверсии" if target.is_summary else f"цели {target.goal_id}")
    base_label = _plan_base_label(target.period_start, target.period_end)

    # Вторая цифра — только при заметном расхождении баз (§3), с направлением.
    divergence = None
    if math.isfinite(cpl_period) and math.isfinite(cpl_7d) and cpl_period > 0 and leads and leads_7d:
        if abs(cpl_7d - cpl_period) / cpl_period > cfg.plan_cpl_divergence_threshold:
            divergence = "улучшается" if cpl_7d < cpl_period else "ухудшается"

    if lead == "period":
        if not leads:
            text = (
                f"Расход идёт, заявок нет по «{label}»: {base_label} потрачено {_money(spend)} "
                f"при целевом CPL {_money(target_cpl)}. Проверьте трафик и трекинг. Суммы с НДС."
            )
        else:
            text = (
                f"Стоимость заявки выше цели по «{label}»: {base_label} — {_money(cpl_period)} "
                f"при целевом CPL {_money(target_cpl)} ({_times_ru(ratio_period)})."
            )
            if divergence:
                text += f" За последние 7 дней — {_money(cpl_7d)}, ситуация {divergence}."
            text += " Суммы с НДС."
        ratio_lead, cpl_lead = ratio_period, cpl_period
    else:
        base_cap = base_label[0].upper() + base_label[1:]
        period_part = (
            f"{base_cap} пока {_money(cpl_period)}" if math.isfinite(cpl_period) and leads
            else f"{base_cap} статистики пока мало"
        )
        text = (
            f"Заявки резко подорожали по «{label}»: за последние 7 дней — {_money(cpl_7d)} "
            f"при целевом CPL {_money(target_cpl)} ({_times_ru(ratio_7d)}). "
            f"{period_part} — успейте скорректировать, пока неделя не испортила месяц. Суммы с НДС."
        )
        ratio_lead, cpl_lead = ratio_7d, cpl_7d

    return AlertCandidate("cpa", "goal" if not target.is_summary else "project", target.goal_id, channel,
                          "plan_cpl", severity, round((ratio_lead - 1) * 100, 2) if math.isfinite(ratio_lead) else 9999,
                          target_cpl, cpl_lead if math.isfinite(cpl_lead) else spend, "up", hypothesis_text=text,
                          meta={"check": "P-2", "lead": lead, "goal_name": label,
                                "spend": spend, "leads": leads,
                                "cpl_period": cpl_period if math.isfinite(cpl_period) else None,
                                "spend_7d": spend_7d, "leads_7d": leads_7d,
                                "cpl_7d": cpl_7d if math.isfinite(cpl_7d) else None,
                                "window_start": window_start.isoformat(),
                                "period_start": target.period_start.isoformat(), "period_end": target.period_end.isoformat()})


def _make_plan_leads(
    db: Session, client_id: uuid.UUID, channel: models.IntegrationPlatform,
    budget: models.ProjectBudget, summary_target: models.ProjectTargetCPA | None,
    reference_date: date, client: models.Client, cfg: DetectorCfg,
    selected: set[str] | None = None, vk_codes: set[str] | None = None,
) -> AlertCandidate | None:
    if not summary_target or not summary_target.control_enabled or not summary_target.target_cpa:
        return None
    planned = int(budget.manual_leads) if budget.manual_leads is not None else math.floor(float(budget.amount) / float(summary_target.target_cpa))
    if planned <= 0:
        return None
    start = max(budget.period_start, client.actual_start_date or budget.period_start)
    elapsed = (reference_date - start).days + 1
    total_days = (budget.period_end - budget.period_start).days + 1
    if elapsed <= 0 or total_days <= 0:
        return None
    expected = planned * elapsed / total_days
    if expected < cfg.plan_min_expected_leads:
        return None
    _, _, actual = _sum_channel_stats(db, client_id, channel, start, reference_date, selected, vk_codes)
    deviation = (actual - expected) / expected
    if deviation > -cfg.plan_leads_warning_deviation:
        return None
    severity = "problem" if deviation <= -cfg.plan_leads_problem_deviation else "warning"
    forecast = actual / elapsed * total_days
    text = f"Отстаём по темпу заявок: ожидалось ~{expected:.0f}, по факту {actual}. При таком темпе к концу периода будет ~{forecast:.0f} заявок из {planned} по плану."
    return AlertCandidate("conversions", "project", None, channel, "plan_leads", severity, round(deviation * 100, 2),
                          expected, actual, "down", hypothesis_text=text,
                          meta={"check": "P-3", "planned_leads": planned, "forecast": forecast,
                                "period_start": budget.period_start.isoformat(), "period_end": budget.period_end.isoformat()})


def _collapse_plan_checks(candidates: list[AlertCandidate]) -> list[AlertCandidate]:
    """One episode, one alert per channel; P-2 > P-1 > P-3."""
    by_channel: dict[models.IntegrationPlatform, list[AlertCandidate]] = {}
    for candidate in candidates:
        by_channel.setdefault(candidate.channel, []).append(candidate)
    result: list[AlertCandidate] = []
    priority = {"plan_cpl": 0, "plan_spend": 1, "plan_leads": 2}
    for channel, rows in by_channel.items():
        primary = sorted(rows, key=lambda item: (priority[item.mode], 0 if item.severity == "problem" else 1, -abs(item.deviation_pct)))[0]
        context = [item.hypothesis_text for item in rows if item is not primary and item.hypothesis_text]
        # Составной алерт читается списком: каждая проверка — отдельный пункт
        # с новой строки, а не слитная простыня (фронт рендерит pre-line).
        parts = [primary.hypothesis_text or "Отклонение от плана."]
        for index, item_text in enumerate(context):
            parts.append(("Дополнительно: " if index == 0 else "") + item_text)
        text = "\n• ".join(parts)
        if len(parts) > 1:
            text = "• " + text
        result.append(AlertCandidate(primary.metric, "project", None, channel, "plan", primary.severity,
                                     primary.deviation_pct, primary.baseline_value, primary.actual_value,
                                     primary.direction, hypothesis_text=text,
                                     meta={**(primary.meta or {}), "checks": [item.meta.get("check") for item in rows if item.meta],
                                           # Поповер KPI-карточки показывает только свою проверку
                                           # (P-1 → расходы, P-2 → CPL, P-3 → лиды), полный
                                           # составной текст остаётся баннеру на дашборде.
                                           "check_texts": {item.meta.get("check"): item.hypothesis_text
                                                           for item in rows if item.meta and item.hypothesis_text},
                                           "composite": len(rows) > 1}))
    return result


def _relative_change(prior: float, fresh: float) -> float | None:
    """Window-over-window change; None when there is no base to compare with."""
    if prior <= 0:
        return None
    return (fresh - prior) / prior


def _diagnose_pattern(check: str, direction: str, fresh: dict, prior: dict, threshold: float) -> str | None:
    """§4: deterministic funnel diagnosis for an open P alert.

    Secondary metrics never trigger anything on their own — they only explain
    an alert that money/leads already raised.  Patterns follow the base spec
    table; the wording is a ready hypothesis, safe without any AI.
    """
    impressions = _relative_change(float(prior.get("impressions") or 0), float(fresh.get("impressions") or 0))
    clicks = _relative_change(float(prior.get("clicks") or 0), float(fresh.get("clicks") or 0))
    spend = _relative_change(float(prior.get("spend") or 0), float(fresh.get("spend") or 0))
    leads = _relative_change(float(prior.get("leads") or 0), float(fresh.get("leads") or 0))

    def ratio_change(numerator: str, denominator: str) -> float | None:
        prior_den = float(prior.get(denominator) or 0)
        fresh_den = float(fresh.get(denominator) or 0)
        prior_num = float(prior.get(numerator) or 0)
        if prior_den <= 0 or fresh_den <= 0 or prior_num <= 0:
            return None
        return _relative_change(prior_num / prior_den, float(fresh.get(numerator) or 0) / fresh_den)

    cpc = ratio_change("spend", "clicks")
    conversion = ratio_change("leads", "clicks")

    if check == "P-2":
        if cpc is not None and cpc >= threshold and clicks is not None and clicks <= -threshold and (conversion is None or abs(conversion) < threshold):
            return "Диагностика: CPC вырос, кликов меньше, конверсия в норме — похоже, подорожал аукцион или выросла конкуренция."
        if conversion is not None and conversion <= -threshold and (cpc is None or abs(cpc) < threshold):
            return "Диагностика: клики и CPC в норме, а заявок с клика меньше — похоже, просела конверсия посадочной."
    if check == "P-1" and direction == "down" and impressions is not None and impressions <= -threshold:
        return "Диагностика: показы снизились, остальное за ними — похоже, сузился охват или упал объём трафика."
    if check == "P-1" and direction == "up" and spend is not None and spend >= threshold and (leads is None or leads < threshold):
        return "Диагностика: расход растёт, а заявки нет — похоже, открут в пустоту; проверьте таргетинг и площадки."
    return None


def _campaign_contributors(db: Session, client_id: uuid.UUID, channel: models.IntegrationPlatform, reference_date: date, cfg: DetectorCfg) -> str | None:
    """§4.1 ↔ P-2 link: the highlighted rows are the alert's own breakdown."""
    end = reference_date - timedelta(days=1)
    start = end - timedelta(days=cfg.plan_cpl_window_days - 1)
    rows = campaign_highlights(db, client_id, start, end)
    scored = sorted(
        (
            (item.get("actual_cpl") or math.inf if item.get("leads") else math.inf, key, item)
            for key, item in rows.items()
            if item.get("channel") == _enum(channel)
        ),
        key=lambda entry: (0 if entry[2]["severity"] == "problem" else 1, -entry[0] if math.isfinite(entry[0]) else float("-inf")),
    )
    names = [entry[2].get("name") for entry in scored[:2] if entry[2].get("name")]
    if not names:
        return None
    quoted = " и ".join(f"«{name}»" for name in names)
    return f"Основной вклад — {'кампании' if len(names) > 1 else 'кампания'} {quoted}."


def _apply_diagnostics(
    db: Session, client_id: uuid.UUID, alerts: list[AlertCandidate],
    reference_date: date, cfg: DetectorCfg, selected: set[str] | None,
    vk_codes: set[str] | None = None,
) -> None:
    """Attach the §4 diagnostic layer to composite P alerts in place."""
    fresh_end = reference_date - timedelta(days=1)
    fresh_start = fresh_end - timedelta(days=cfg.plan_cpl_window_days - 1)
    prior_end = fresh_start - timedelta(days=1)
    prior_start = prior_end - timedelta(days=cfg.plan_cpl_window_days - 1)
    for alert in alerts:
        if alert.mode != "plan" or not alert.channel:
            continue
        try:
            fresh = _window_funnel(db, client_id, alert.channel, fresh_start, fresh_end, selected, vk_codes)
            prior = _window_funnel(db, client_id, alert.channel, prior_start, prior_end, selected, vk_codes)
            check = (alert.meta or {}).get("check") or ""
            parts: list[str] = []
            diagnosis = _diagnose_pattern(check, alert.direction, fresh, prior, cfg.diagnostic_change_threshold)
            if diagnosis:
                parts.append(diagnosis)
            if "P-2" in ((alert.meta or {}).get("checks") or [check]):
                contributors = _campaign_contributors(db, client_id, alert.channel, reference_date, cfg)
                if contributors:
                    parts.append(contributors)
            if parts:
                # Диагностика и «основной вклад» — отдельные пункты списка
                alert.hypothesis_text = alert.hypothesis_text + "".join(f"\n• {part}" for part in parts)
                alert.meta = {**(alert.meta or {}), "diagnosis": " ".join(parts)}
        except Exception:
            # The diagnosis explains an alert; failing to build it must never
            # cancel the alert itself.
            logger.exception("Diagnostic layer failed for %s / %s", client_id, alert.channel)


def _make_balance_alert(
    db: Session, client_id: uuid.UUID, integration: models.Integration,
    reference_date: date, cfg: DetectorCfg,
    selected: set[str] | None = None,
) -> AlertCandidate | None:
    if integration.balance is None:
        return None
    channel = integration.platform
    end = reference_date - timedelta(days=1)
    start = end - timedelta(days=cfg.balance_spend_window_days - 1)
    if end < start:
        return None
    daily = _daily_channel_values(db, client_id, channel, start, end, selected)
    avg = sum(row[1] for row in daily) / len(daily) if daily else 0
    if avg <= 0:
        return None
    balance = float(integration.balance) * _money_factor(channel)
    # A persistently zero API balance while money is still spent signals a
    # credit line/autotop-up, not an impending stop.
    if balance == 0 and len(daily) >= cfg.balance_zero_history_days and all(row[1] > 0 for row in daily[-cfg.balance_zero_history_days:]):
        return None
    days_left = balance / avg
    if days_left > cfg.balance_warning_days:
        return None
    severity = "problem" if days_left <= cfg.balance_problem_days else "warning"
    text = f"Баланса в кабинете {_enum(channel)} хватит примерно на {max(0, round(days_left))} дн. (осталось {_money(balance)} при расходе ~{_money(avg)}/день). Пополните, чтобы реклама не остановилась."
    return AlertCandidate("balance", "project", None, channel, "critical_balance", severity,
                          round(days_left, 2), cfg.balance_warning_days, days_left, "down", hypothesis_text=text,
                          meta={"check": "C-0", "balance": balance, "daily_spend": avg})


def _make_stopped_alert(
    db: Session, client_id: uuid.UUID, integration: models.Integration,
    reference_date: date, cfg: DetectorCfg,
    selected: set[str] | None = None,
) -> AlertCandidate | None:
    channel = integration.platform
    end = reference_date - timedelta(days=1)
    zero_start = end - timedelta(days=cfg.stopped_spend_zero_days - 1)
    if end < zero_start:
        return None
    current = _daily_channel_values(db, client_id, channel, zero_start, end, selected)
    if any(row[1] > 0 for row in current):
        return None
    active = (
        db.query(models.Campaign.id)
        .join(models.Integration, models.Campaign.integration_id == models.Integration.id)
        .filter(models.Integration.client_id == client_id, models.Integration.platform == channel, models.Campaign.is_active.is_(True))
        .first()
    )
    if not active:
        return None
    prior_end = zero_start - timedelta(days=1)
    prior_start = prior_end - timedelta(days=cfg.stopped_prior_spend_days - 1)
    prior = _daily_channel_values(db, client_id, channel, prior_start, prior_end, selected)
    average = sum(row[1] for row in prior) / len(prior) if prior else 0
    if average < cfg.stopped_min_daily_spend:
        return None
    text = f"Реклама встала: за последние {cfg.stopped_spend_zero_days} полных дня расход равен нулю при активных кампаниях. Проверьте баланс, статусы РК и кабинет."
    return AlertCandidate("expenses", "project", None, channel, "critical_stopped", "problem", -100.0,
                          average, 0, "down", consecutive_days=cfg.stopped_spend_zero_days, hypothesis_text=text,
                          meta={"check": "C-1", "prior_daily_spend": average})


def _make_tracking_alerts(
    db: Session, client_id: uuid.UUID, integration: models.Integration,
    reference_date: date, cfg: DetectorCfg,
    selected: set[str] | None = None, vk_codes: set[str] | None = None,
) -> list[AlertCandidate]:
    channel = integration.platform
    end = reference_date - timedelta(days=1)
    start = end - timedelta(days=cfg.tracking_zero_leads_days - 1)
    _, clicks, _ = _sum_channel_stats(db, client_id, channel, start, end, selected)
    if clicks < cfg.tracking_min_clicks:
        return []
    goal_ids = _selected_goal_ids([integration]) if channel == models.IntegrationPlatform.YANDEX_DIRECT else {"__all__"}
    if not goal_ids:
        return []
    history_end = start - timedelta(days=1)
    history_start = history_end - timedelta(days=cfg.tracking_history_days - 1)
    result: list[AlertCandidate] = []
    for goal_id in goal_ids:
        now_leads = _sum_goal_leads(db, client_id, channel, goal_id, goal_id == "__all__", start, end, selected, vk_codes)
        if now_leads:
            continue
        history = _daily_goal_leads(db, client_id, channel, goal_id, goal_id == "__all__", history_start, history_end, selected, vk_codes)
        active_days = sum(1 for leads in history.values() if leads >= 1)
        if active_days < cfg.tracking_history_active_days:
            continue
        label = "заявок" if goal_id == "__all__" else f"цели {goal_id}"
        text = f"Похоже, сломался трекинг: за последние {cfg.tracking_zero_leads_days} полных дня {label} нет при {clicks} кликах. Проверьте цели Метрики / трекинг."
        result.append(AlertCandidate("conversions", "goal", None if goal_id == "__all__" else goal_id, channel,
                                     "critical_tracking", "problem", -100.0, float(active_days), 0, "down",
                                     consecutive_days=cfg.tracking_zero_leads_days, hypothesis_text=text,
                                     meta={"check": "C-2", "clicks": clicks, "goal_id": goal_id}))
    return result


def _close_superseded_alerts(db: Session, client_id: uuid.UUID, reference_date: date) -> None:
    now = datetime.now(timezone.utc)
    # v1/v2 historical signals are explicitly closed by migration, not marked
    # as recovered.  Old plan rows are also replaced by the composite P alert.
    rows = (
        db.query(models.DetectorAlert)
        .filter(
            models.DetectorAlert.client_id == client_id,
            models.DetectorAlert.status.in_(("open", "dismissed")),
            models.DetectorAlert.mode.in_(("baseline", "plan_spend", "plan_cpa", "plan_leads")),
        )
        .all()
    )
    for alert in rows:
        alert.status = "closed"
        alert.closed_at = now
        alert.meta = {**(alert.meta or {}), "close_reason": "closed_by_iteration3_migration"}
    plan_rows = (
        db.query(models.DetectorAlert)
        .filter(models.DetectorAlert.client_id == client_id, models.DetectorAlert.mode == "plan", models.DetectorAlert.status.in_(("open", "dismissed")))
        .all()
    )
    for alert in plan_rows:
        end = (alert.meta or {}).get("period_end")
        try:
            ended = date.fromisoformat(end) < reference_date if end else False
        except (TypeError, ValueError):
            ended = False
        if ended:
            alert.status = "closed"
            alert.closed_at = now
            alert.meta = {**(alert.meta or {}), "close_reason": "plan_period_completed"}


def campaign_highlights(
    db: Session, client_id: uuid.UUID, start: date, end: date,
    yandex_overrides: dict | None = None,
) -> dict[str, dict]:
    """Return read-only campaign tint data for the selected table period.

    Campaigns never create detector-alert rows, notifications or counters.  A
    highlighted row has exactly one meaning: its CPL is above the current
    summary CPL plan (or spend is meaningful and it has no leads).

    Заявки кампании — из её собственной статистики (Yandex/VK stats по
    campaign_id), ровно как в таблице дашборда. Пропорциональная размазка
    конверсий Метрики по расходу здесь запрещена: она делает CPL всех
    кампаний одинаковым и подсвечивает не те строки.
    """
    cfg = get_config().detector
    budgets = _latest_budgets(db, client_id, end)
    targets = _latest_targets(db, client_id, end)
    summaries = {
        target.channel: target for target in targets
        if target.is_summary and target.control_enabled and target.target_cpa and target.channel in AD_CHANNELS
    }
    campaign_names = {
        str(row[0]): row[1]
        for row in (
            db.query(models.Campaign.id, models.Campaign.name)
            .join(models.Integration, models.Campaign.integration_id == models.Integration.id)
            .filter(models.Integration.client_id == client_id)
            .all()
        )
    }
    vk_codes = _vk_lead_codes(db, client_id)
    # Если проект настроил выбранные цели Метрики, native-конверсии Директа
    # содержат другие действия и непригодны для CPL кампании. В таком случае
    # подсвечиваем только кампании с точной атрибуцией по DirectClickOrder;
    # при временной недоступности Метрики честнее не подсветить строку, чем
    # показать ложные 6 092 ₽ из чужих конверсий.
    has_selected_yandex_goals = bool(_selected_goal_ids(_ad_integrations(db, client_id)))
    result: dict[str, dict] = {}
    for channel, target in summaries.items():
        budget = _budget_for_channel(budgets, channel)
        # Consistent with P-2: the budget only caps the money filter.  A plan
        # holding a target CPL without a budget still highlights rows.
        budget_amount = float(budget.amount) if budget and float(budget.amount or 0) > 0 else float("inf")
        minimum = min(
            cfg.campaign_cpl_problem_target_multiplier * float(target.target_cpa),
            cfg.campaign_cpl_budget_share * budget_amount,
        )
        table = _table_for(channel)
        if table is None:
            continue
        query = (
            db.query(table.campaign_id, func.sum(table.cost), func.sum(table.conversions))
            .filter(
                table.client_id == client_id,
                table.campaign_id.isnot(None),
                table.date >= start,
                table.date <= end,
            )
        )
        if channel == models.IntegrationPlatform.VK_ADS:
            # Кампании с нелидовым целевым действием не судим по цене заявки:
            # их «конверсии» — не заявки по определению проекта.
            from backend_api.stats_service import StatsService
            query = query.join(models.Campaign, table.campaign_id == models.Campaign.id)
            query = StatsService.apply_vk_lead_action_scope(query, db, [client_id])
        factor = _money_factor(channel)
        for campaign_id, cost, conversions in query.group_by(table.campaign_id).all():
            spend = float(cost or 0) * factor
            leads = int(conversions or 0)
            # Таблица дашборда для Яндекса переопределяет конверсии кампаний
            # живыми данными Метрики (по имени кампании). Подсветка обязана
            # видеть те же числа, иначе строка «CPL 1 016 ₽» подсвечивается
            # текстом про 6 092 ₽ по данным Директа.
            if channel == models.IntegrationPlatform.YANDEX_DIRECT and has_selected_yandex_goals:
                if str(campaign_id) not in (yandex_overrides or {}):
                    continue
                leads = int((yandex_overrides or {})[str(campaign_id)] or 0)
            if spend < minimum:
                continue
            cpl = spend / leads if leads else math.inf
            ratio = cpl / float(target.target_cpa) if math.isfinite(cpl) else math.inf
            if leads and ratio < cfg.plan_cpl_warning_ratio:
                continue
            severity = "problem" if not leads or ratio >= cfg.plan_cpl_problem_ratio else "warning"
            if not leads:
                text = f"Расход без заявок: {_money(spend)} при целевом CPL {_money(float(target.target_cpa))}."
            else:
                text = f"Заявка по кампании ~{_money(cpl)} при целевой {_money(float(target.target_cpa))} ({ratio:.1f}×), {leads} заявок за период."
            result[str(campaign_id)] = {
                "severity": severity,
                "hypothesis_text": text,
                "target_cpl": float(target.target_cpa),
                "actual_cpl": cpl if math.isfinite(cpl) else None,
                "spend": spend,
                "leads": leads,
                "name": campaign_names.get(str(campaign_id)),
                "channel": _enum(channel),
            }
    return result


def plan_completion(db: Session, client_id: uuid.UUID, today: date | None = None) -> dict | None:
    """Completion of the most recent finished plan period (§6, «выполнен на N%»).

    Sums the latest budget versions that share the most recent past period_end
    against the actual spend of their channels for that period.
    """
    ref = today or date.today()
    rows = (
        db.query(models.ProjectBudget)
        .filter(models.ProjectBudget.client_id == client_id, models.ProjectBudget.period_end < ref)
        .order_by(models.ProjectBudget.period_end.desc(), models.ProjectBudget.created_at.desc(), models.ProjectBudget.id.desc())
        .all()
    )
    if not rows:
        return None
    last_end = rows[0].period_end
    latest: dict[models.IntegrationPlatform | None, models.ProjectBudget] = {}
    for row in rows:
        if row.period_end == last_end:
            latest.setdefault(row.channel, row)
    total_budget = sum(float(row.amount or 0) for row in latest.values())
    if total_budget <= 0:
        return None
    integrations = _ad_integrations(db, client_id)
    selected = _selected_goal_ids(integrations)
    channels = {row.platform for row in integrations}
    spent = 0.0
    for channel, row in latest.items():
        report_channels = [channel] if channel is not None else list(channels)
        for report_channel in report_channels:
            spend, _, _ = _sum_channel_stats(db, client_id, report_channel, row.period_start, row.period_end, selected)
            spent += spend
    return {
        "pct": round(spent / total_budget * 100),
        "period_end": last_end.isoformat(),
        "budget": total_budget,
        "spent": round(spent, 2),
    }


def run_detector_iteration3(
    db: Session,
    client_id: uuid.UUID,
    reference_date: date | None = None,
    *,
    immediate_plan_recalculation: bool = False,
) -> None:
    cfg = get_config().detector
    if not cfg.enabled:
        return
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client or _enum(client.status).upper() == "PAUSED":
        return
    ref = reference_date or date.today()
    integrations = _ad_integrations(db, client_id)
    # Preserve baseline calculation in the background; iteration 3 only turns
    # off its alert generation.
    for channel in {row.platform for row in integrations}:
        try:
            compute_baseline(db, client_id, channel, ref, cfg)
        except Exception:
            logger.exception("Baseline diagnostic calculation failed for %s", client_id)

    _close_superseded_alerts(db, client_id, ref)
    budgets = _latest_budgets(db, client_id, ref)
    targets = _latest_targets(db, client_id, ref)
    # One goal-configuration read per run: every window below reuses it.
    selected = _selected_goal_ids(integrations)
    vk_codes = _vk_lead_codes(db, client_id)
    targets_by_channel: dict[models.IntegrationPlatform, list[models.ProjectTargetCPA]] = {}
    for target in targets:
        if target.channel in AD_CHANNELS:
            targets_by_channel.setdefault(target.channel, []).append(target)

    plan_checks: list[AlertCandidate] = []
    critical: list[AlertCandidate] = []
    fresh_channels: list[models.IntegrationPlatform] = []
    has_channel_budget = False
    for integration in integrations:
        channel = integration.platform
        stale, _ = _is_sync_stale(integration, ref, cfg)
        if stale:
            # C-3 is deliberately exposed as neutral status through the API;
            # every data-dependent detector check is frozen.
            continue
        fresh_channels.append(channel)
        budget = _budget_for_channel(budgets, channel)
        if budget:
            has_channel_budget = True
            candidate = _make_plan_spend(db, client_id, channel, budget, ref, client, cfg, selected)
            if candidate:
                plan_checks.append(candidate)
        for target in targets_by_channel.get(channel, []):
            candidate = _make_plan_cpl(db, client_id, target, budget, ref, cfg, selected, vk_codes)
            if candidate:
                plan_checks.append(candidate)
        summary = next((target for target in targets_by_channel.get(channel, []) if target.is_summary), None)
        if budget:
            candidate = _make_plan_leads(db, client_id, channel, budget, summary, ref, client, cfg, selected, vk_codes)
            if candidate:
                plan_checks.append(candidate)
        for candidate in (
            _make_balance_alert(db, client_id, integration, ref, cfg, selected),
            _make_stopped_alert(db, client_id, integration, ref, cfg, selected),
        ):
            if candidate:
                critical.append(candidate)
        critical.extend(_make_tracking_alerts(db, client_id, integration, ref, cfg, selected, vk_codes))

    # §2 P-1: a project-wide budget (channel=None) is judged against the total
    # spend, and only when no per-channel budgets exist — never both at once.
    total_budget = budgets.get(None)
    if total_budget and not has_channel_budget and fresh_channels:
        candidate = _make_plan_spend(
            db, client_id, None, total_budget, ref, client, cfg, selected, channels=fresh_channels,
        )
        if candidate:
            plan_checks.append(candidate)

    owner = db.query(models.User).filter(models.User.id == client.owner_id).first()
    global_on = getattr(owner, "global_detector_enabled", True) if owner else True
    plan_alerts = _collapse_plan_checks(plan_checks)
    _apply_diagnostics(db, client_id, plan_alerts, ref, cfg, selected, vk_codes)
    upsert_alerts(db, client_id, client.owner_id, plan_alerts + critical, cfg,
                  notify=bool(client.detector_enabled) and global_on)
    if immediate_plan_recalculation:
        # A changed agreement is not a recovery.  Close P alerts that no
        # longer match immediately, as the settings save promised the user.
        now = datetime.now(timezone.utc)
        fired_channels = {candidate.channel for candidate in plan_alerts}
        for alert in (
            db.query(models.DetectorAlert)
            .filter(models.DetectorAlert.client_id == client_id, models.DetectorAlert.mode == "plan", models.DetectorAlert.status.in_(("open", "dismissed")))
            .all()
        ):
            if alert.channel not in fired_channels:
                alert.status = "closed"
                alert.closed_at = now
                alert.meta = {**(alert.meta or {}), "close_reason": "plan_recalculated"}
        db.flush()
