from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest

from backend_api.services import detector_iteration3 as iteration3
from backend_api.services import project_settings
from core import models


def cfg(**overrides):
    values = {
        "plan_start_pause_days": 3,
        "plan_spend_warning_deviation": 0.20,
        "plan_spend_problem_deviation": 0.40,
        "plan_min_expected_spend": 1000.0,
        "plan_exhausted_min_days_remaining": 2,
        "plan_cpl_window_days": 7,
        "plan_cpl_warning_ratio": 1.3,
        "plan_cpl_problem_ratio": 1.8,
        "plan_cpl_problem_target_multiplier": 5.0,
        "plan_cpl_warning_target_multiplier": 10.0,
        "plan_cpl_problem_budget_share": 0.15,
        "plan_cpl_warning_budget_share": 0.30,
        "plan_leads_warning_deviation": 0.20,
        "plan_leads_problem_deviation": 0.40,
        "plan_min_expected_leads": 10,
        "stopped_spend_zero_days": 2,
        "stopped_prior_spend_days": 7,
        "stopped_min_daily_spend": 200.0,
        "tracking_zero_leads_days": 3,
        "tracking_min_clicks": 100,
        "tracking_history_days": 14,
        "tracking_history_active_days": 10,
        "balance_spend_window_days": 7,
        "balance_zero_history_days": 7,
        "balance_warning_days": 3.0,
        "balance_problem_days": 1.0,
        "sync_stale_days": 2,
        "campaign_cpl_problem_target_multiplier": 3.0,
        "campaign_cpl_budget_share": 0.10,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def budget(amount=100_000, manual_leads=None):
    return SimpleNamespace(
        amount=amount,
        manual_leads=manual_leads,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 30),
    )


def target(cpl=1_000, summary=True):
    return SimpleNamespace(
        client_id="project",
        channel=models.IntegrationPlatform.YANDEX_DIRECT,
        goal_id="__summary__" if summary else "42",
        goal_name="Все конверсии" if summary else "Квиз",
        is_summary=summary,
        control_enabled=True,
        target_cpa=cpl,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 30),
        created_at=None,
    )


def client():
    return SimpleNamespace(actual_start_date=date(2026, 7, 1))


def test_p1_is_silent_for_first_three_days_and_small_expected_volume(monkeypatch):
    monkeypatch.setattr(iteration3, "_sum_channel_stats", lambda *_: (0, 0, 0))
    b = budget()
    assert iteration3._make_plan_spend(None, "p", models.IntegrationPlatform.YANDEX_DIRECT, b, date(2026, 7, 3), client(), cfg()) is None
    low = budget(5_000)
    assert iteration3._make_plan_spend(None, "p", models.IntegrationPlatform.YANDEX_DIRECT, low, date(2026, 7, 4), client(), cfg()) is None


def test_p1_red_overpace_has_forecast_and_exhaustion_has_special_copy(monkeypatch):
    monkeypatch.setattr(iteration3, "_sum_channel_stats", lambda *_: (145_000, 0, 0))
    normal = iteration3._make_plan_spend(None, "p", models.IntegrationPlatform.YANDEX_DIRECT, budget(200_000), date(2026, 7, 15), client(), cfg())
    assert normal.severity == "problem"
    assert normal.meta["check"] == "P-1"
    assert "закончится" in normal.hypothesis_text

    exhausted = iteration3._make_plan_spend(None, "p", models.IntegrationPlatform.YANDEX_DIRECT, budget(100_000), date(2026, 7, 15), client(), cfg())
    assert exhausted.severity == "problem"
    assert "израсходован полностью" in exhausted.hypothesis_text


def test_p2_uses_money_volume_not_lead_count_and_budget_cap(monkeypatch):
    monkeypatch.setattr(iteration3, "_target_window_start", lambda *_: date(2026, 7, 1))
    monkeypatch.setattr(iteration3, "_target_exists", lambda *_: True)
    monkeypatch.setattr(iteration3, "_sum_channel_stats", lambda *_: (48_000, 0, 0))
    monkeypatch.setattr(iteration3, "_sum_goal_leads", lambda *_: 0)
    result = iteration3._make_plan_cpl(None, "p", target(20_000), budget(300_000), date(2026, 7, 7), cfg())
    assert result is not None
    assert result.severity == "problem"
    assert "заявок нет" in result.hypothesis_text


def test_p3_derives_or_respects_manual_lead_plan(monkeypatch):
    monkeypatch.setattr(iteration3, "_sum_channel_stats", lambda *_: (30_000, 0, 20))
    auto = iteration3._make_plan_leads(None, "p", models.IntegrationPlatform.YANDEX_DIRECT, budget(100_000), target(1_000), date(2026, 7, 15), client(), cfg())
    assert auto is not None
    assert auto.meta["planned_leads"] == 100
    manual = iteration3._make_plan_leads(None, "p", models.IntegrationPlatform.YANDEX_DIRECT, budget(100_000, manual_leads=80), target(1_000), date(2026, 7, 15), client(), cfg())
    assert manual.meta["planned_leads"] == 80


def test_plan_checks_are_one_alert_and_cpl_has_priority():
    spend = iteration3.AlertCandidate("expenses", "project", None, models.IntegrationPlatform.YANDEX_DIRECT, "plan_spend", "problem", 50, 10, 15, "up", hypothesis_text="spend", meta={"check": "P-1"})
    cpl = iteration3.AlertCandidate("cpa", "goal", "42", models.IntegrationPlatform.YANDEX_DIRECT, "plan_cpl", "warning", 40, 10, 14, "up", hypothesis_text="cpl", meta={"check": "P-2"})
    merged = iteration3._collapse_plan_checks([spend, cpl])
    assert len(merged) == 1
    assert merged[0].metric == "cpa"
    assert merged[0].mode == "plan"
    assert merged[0].meta["checks"] == ["P-1", "P-2"]
    assert "spend" in merged[0].hypothesis_text


def test_warmup_is_only_for_a_new_active_project(monkeypatch):
    monkeypatch.setattr(
        project_settings,
        "get_config",
        lambda: SimpleNamespace(detector=SimpleNamespace(warmup_days=21)),
    )
    established = SimpleNamespace(
        detector_enabled=True,
        status=models.ClientStatus.ACTIVE,
        actual_start_date=date.today() - timedelta(days=30),
    )
    assert project_settings.get_detector_state(established)["status"] == "ready"

    paused = SimpleNamespace(
        detector_enabled=True,
        status=models.ClientStatus.PAUSED,
        actual_start_date=date.today() - timedelta(days=30),
    )
    assert project_settings.get_detector_state(paused)["status"] == "paused"


def test_diagnostic_layer_names_the_auction_and_funnel_patterns():
    thr = 0.2
    prior = {"spend": 10_000, "impressions": 10_000, "clicks": 1_000, "leads": 50}
    # CPC вырос, кликов меньше, CR в норме → аукцион
    auction = iteration3._diagnose_pattern(
        "P-2", "up", {"spend": 10_000, "impressions": 9_500, "clicks": 700, "leads": 35}, prior, thr,
    )
    assert auction and "аукцион" in auction
    # Клики/CPC в норме, конверсия просела → посадочная
    landing = iteration3._diagnose_pattern(
        "P-2", "up", {"spend": 10_000, "impressions": 10_000, "clicks": 1_000, "leads": 30}, prior, thr,
    )
    assert landing and "посадочной" in landing
    # Недокрут: показы упали → охват
    reach = iteration3._diagnose_pattern(
        "P-1", "down", {"spend": 6_000, "impressions": 6_000, "clicks": 600, "leads": 30}, prior, thr,
    )
    assert reach and "охват" in reach
    # Перерасход: расход растёт, заявки нет → открут в пустоту
    waste = iteration3._diagnose_pattern(
        "P-1", "up", {"spend": 15_000, "impressions": 11_000, "clicks": 1_050, "leads": 51}, prior, thr,
    )
    assert waste and "пустоту" in waste
    # Движение второстепенных метрик без паттерна — диагноза нет
    assert iteration3._diagnose_pattern(
        "P-2", "up", {"spend": 10_500, "impressions": 10_200, "clicks": 1_020, "leads": 49}, prior, thr,
    ) is None


def test_total_project_budget_is_judged_across_channels(monkeypatch):
    spends = {models.IntegrationPlatform.YANDEX_DIRECT: 90_000, models.IntegrationPlatform.VK_ADS: 55_000}
    monkeypatch.setattr(
        iteration3, "_sum_channel_stats",
        lambda db, cid, channel, *rest: (spends.get(channel, 0), 0, 0),
    )
    candidate = iteration3._make_plan_spend(
        None, "p", None, budget(200_000), date(2026, 7, 15), client(), cfg(),
        None, channels=list(spends),
    )
    assert candidate is not None
    assert candidate.channel is None
    assert candidate.severity == "problem"  # 145 000 при ожидаемых ~100 000


def test_c0_balance_warning_and_c3_stale_sync_are_distinct(monkeypatch):
    integration = SimpleNamespace(balance=3_400, platform=models.IntegrationPlatform.YANDEX_DIRECT)
    monkeypatch.setattr(
        iteration3,
        "_daily_channel_values",
        lambda *_: [(date(2026, 7, day), 1_700, 0, 0) for day in range(1, 8)],
    )
    balance = iteration3._make_balance_alert(None, "p", integration, date(2026, 7, 8), cfg())
    assert balance.severity == "warning"
    assert balance.meta["check"] == "C-0"

    stale = SimpleNamespace(sync_status=models.IntegrationSyncStatus.SUCCESS, last_sync_at=datetime(2026, 7, 5))
    assert iteration3._is_sync_stale(stale, date(2026, 7, 8), cfg())[0] is True
