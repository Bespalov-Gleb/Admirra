from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest

from backend_api.services import detector_iteration3 as iteration3
from backend_api.services import project_settings
from core import models


def cfg(**overrides):
    values = {
        "plan_start_pause_days": 3,
        "plan_spend_warning_deviation": 0.10,
        "plan_spend_problem_deviation": 0.40,
        "plan_min_expected_spend": 1000.0,
        "plan_exhausted_min_days_remaining": 2,
        "plan_cpl_window_days": 7,
        "plan_cpl_warning_ratio": 1.1,
        "plan_cpl_problem_ratio": 1.8,
        "plan_cpl_problem_target_multiplier": 5.0,
        "plan_cpl_warning_target_multiplier": 10.0,
        "plan_cpl_problem_budget_share": 0.15,
        "plan_cpl_warning_budget_share": 0.30,
        "plan_cpl_divergence_threshold": 0.15,
        "plan_leads_warning_deviation": 0.10,
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


def test_p1_uses_ten_percent_yellow_threshold(monkeypatch):
    # Жёлтый порог для плановых проверок — 10%; красный — 40%.
    # На 15-й день из 30 при бюджете 100 000 ₽ ожидание равно 50 000 ₽.
    monkeypatch.setattr(iteration3, "_sum_channel_stats", lambda *_: (54_999, 0, 0))
    assert iteration3._make_plan_spend(
        None, "p", models.IntegrationPlatform.YANDEX_DIRECT, budget(100_000), date(2026, 7, 15), client(), cfg(),
    ) is None

    monkeypatch.setattr(iteration3, "_sum_channel_stats", lambda *_: (55_000, 0, 0))
    warning = iteration3._make_plan_spend(
        None, "p", models.IntegrationPlatform.YANDEX_DIRECT, budget(100_000), date(2026, 7, 15), client(), cfg(),
    )
    assert warning and warning.severity == "warning"

    monkeypatch.setattr(iteration3, "_sum_channel_stats", lambda *_: (70_000, 0, 0))
    problem = iteration3._make_plan_spend(
        None, "p", models.IntegrationPlatform.YANDEX_DIRECT, budget(100_000), date(2026, 7, 15), client(), cfg(),
    )
    assert problem and problem.severity == "problem"


def test_p2_and_p3_use_ten_percent_yellow_threshold(monkeypatch):
    monkeypatch.setattr(iteration3, "_target_window_start", lambda *_: date(2026, 7, 1))
    monkeypatch.setattr(iteration3, "_target_exists", lambda *_: True)
    monkeypatch.setattr(iteration3, "_sum_channel_stats", lambda *_: (12_000, 0, 45))
    monkeypatch.setattr(iteration3, "_sum_goal_leads", lambda *_: 11)
    assert iteration3._make_plan_cpl(
        None, "p", target(1_000), budget(100_000), date(2026, 7, 7), cfg(),
    ) is None

    monkeypatch.setattr(iteration3, "_sum_goal_leads", lambda *_: 10)
    cpl = iteration3._make_plan_cpl(
        None, "p", target(1_000), budget(100_000), date(2026, 7, 7), cfg(),
    )
    assert cpl and cpl.severity == "warning"

    monkeypatch.setattr(iteration3, "_sum_channel_stats", lambda *_: (12_000, 0, 46))
    assert iteration3._make_plan_leads(
        None, "p", models.IntegrationPlatform.YANDEX_DIRECT, budget(100_000), target(1_000), date(2026, 7, 15), client(), cfg(),
    ) is None

    monkeypatch.setattr(iteration3, "_sum_channel_stats", lambda *_: (12_000, 0, 45))
    leads = iteration3._make_plan_leads(
        None, "p", models.IntegrationPlatform.YANDEX_DIRECT, budget(100_000), target(1_000), date(2026, 7, 15), client(), cfg(),
    )
    assert leads and leads.severity == "warning"


def test_p2_uses_current_target_against_the_full_recent_window():
    changed_target = target(2_000)
    changed_target.created_at = datetime(2026, 7, 12)
    assert iteration3._target_window_start(None, changed_target, date(2026, 7, 14), cfg()) == date(2026, 7, 8)


def test_p2_uses_money_volume_not_lead_count_and_budget_cap(monkeypatch):
    monkeypatch.setattr(iteration3, "_target_window_start", lambda *_: date(2026, 7, 1))
    monkeypatch.setattr(iteration3, "_target_exists", lambda *_: True)
    monkeypatch.setattr(iteration3, "_sum_channel_stats", lambda *_: (48_000, 0, 0))
    monkeypatch.setattr(iteration3, "_sum_goal_leads", lambda *_: 0)
    result = iteration3._make_plan_cpl(None, "p", target(20_000), budget(300_000), date(2026, 7, 7), cfg())
    assert result is not None
    assert result.severity == "problem"
    assert "заявок нет" in result.hypothesis_text


def _p2_mocks(monkeypatch, spend_period, leads_period, spend_7d, leads_7d):
    """Раздаём накопительному и 7-дневному окнам разные значения по дате старта."""
    monkeypatch.setattr(iteration3, "_target_exists", lambda *_: True)

    def stats(db, client_id, channel, start, end, *args):
        return (spend_period if start == date(2026, 7, 1) else spend_7d, 0, 0)

    def goal_leads(db, client_id, channel, goal_id, is_summary, start, end, *args):
        return leads_period if start == date(2026, 7, 1) else leads_7d

    monkeypatch.setattr(iteration3, "_sum_channel_stats", stats)
    monkeypatch.setattr(iteration3, "_sum_goal_leads", goal_leads)


def test_p2_leads_with_cumulative_cpl_and_names_both_bases(monkeypatch):
    # §5, кейс SIB ATV: накопительный 4 067 ₽, 7-дневный 3 372 ₽, цель 2 000 ₽.
    _p2_mocks(monkeypatch, spend_period=113_876, leads_period=28, spend_7d=33_720, leads_7d=10)
    alert = iteration3._make_plan_cpl(None, "p", target(2_000), budget(200_000), date(2026, 7, 15), cfg())
    assert alert is not None
    assert alert.severity == "problem"
    assert alert.meta["lead"] == "period"
    assert round(alert.actual_value) == 4067  # число совпадает с карточкой периода
    assert "с начала периода 01.07–30.07" in alert.hypothesis_text
    assert "За последние 7 дней" in alert.hypothesis_text
    assert "улучшается" in alert.hypothesis_text
    assert alert.meta["cpl_7d"] == pytest.approx(3_372.0)


def test_p2_hides_second_number_when_divergence_is_small(monkeypatch):
    # Расхождение баз ≤ 15% — в тексте только накопительный CPL.
    _p2_mocks(monkeypatch, spend_period=52_000, leads_period=20, spend_7d=13_500, leads_7d=5)
    alert = iteration3._make_plan_cpl(None, "p", target(2_000), budget(200_000), date(2026, 7, 15), cfg(plan_cpl_warning_ratio=1.3))
    assert alert is not None
    assert alert.meta["lead"] == "period"
    assert "За последние 7 дней" not in alert.hypothesis_text


def test_p2_degradation_trigger_fires_red_when_cumulative_is_fine(monkeypatch):
    # §5: 20 дней в цели, последние 7 дней — 6 100 ₽; накопительный 2 250 ₽ (1.1×).
    _p2_mocks(monkeypatch, spend_period=56_250, leads_period=25, spend_7d=12_200, leads_7d=2)
    alert = iteration3._make_plan_cpl(None, "p", target(2_000), budget(200_000), date(2026, 7, 21), cfg(plan_cpl_warning_ratio=1.3))
    assert alert is not None
    assert alert.severity == "problem"
    assert alert.meta["lead"] == "degradation"
    assert "Заявки резко подорожали" in alert.hypothesis_text
    assert "6 100" in alert.hypothesis_text.replace(" ", " ")
    assert "2 250" in alert.hypothesis_text.replace(" ", " ")


def test_p2_stays_silent_when_neither_cumulative_nor_degradation_breaches(monkeypatch):
    # §5: накопительный 1.2× (ниже жёлтого 1.3), 7-дневный 1.55× (ниже красного 1.8) — тишина.
    _p2_mocks(monkeypatch, spend_period=48_000, leads_period=20, spend_7d=15_500, leads_7d=5)
    assert iteration3._make_plan_cpl(
        None, "p", target(2_000), budget(200_000), date(2026, 7, 15), cfg(plan_cpl_warning_ratio=1.3),
    ) is None


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
    assert merged[0].hypothesis_text == "• cpl\n• Дополнительно: spend"


def test_detector_alert_keeps_full_composite_diagnosis_text():
    # The UI must be able to show every related plan check and campaign clue,
    # not silently fail once a composite explanation exceeds 500 characters.
    assert isinstance(models.DetectorAlert.__table__.c.hypothesis_text.type, models.Text)


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

    # A failed retry does not erase fresh data from the preceding successful
    # import; plan/fact checks must still protect the project.
    failed_but_fresh = SimpleNamespace(sync_status=models.IntegrationSyncStatus.FAILED, last_sync_at=datetime(2026, 7, 7))
    assert iteration3._is_sync_stale(failed_but_fresh, date(2026, 7, 8), cfg())[0] is False
