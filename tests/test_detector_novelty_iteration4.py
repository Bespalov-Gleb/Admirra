from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from backend_api import detector
from backend_api.services import detector_iteration3 as iteration3
from core import models


def _alert(**overrides):
    values = {
        "severity": "warning",
        "deviation_pct": 30,
        "actual_value": 130,
        "baseline_value": 100,
        "opened_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _view(**overrides):
    values = {
        "seen_at": datetime(2026, 8, 2, tzinfo=timezone.utc),
        "seen_severity": "warning",
        "seen_deviation_pct": 30,
        "seen_actual_value": 130,
        "seen_baseline_value": 100,
        "acknowledged": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_ratio_measures_distance_for_declining_metrics():
    assert detector._alert_ratio("warning", -40, 60, 100) == pytest.approx(1.4)
    assert detector._alert_ratio("warning", None, 60, 100) == pytest.approx(1.4)


def test_personal_novelty_new_known_and_red_acknowledgement():
    assert detector._compute_novelty(_alert(), None)["novelty"] == "new"
    assert detector._compute_novelty(_alert(), _view())["novelty"] == "known"
    assert detector._compute_novelty(_alert(severity="problem"), None)["novelty"] == "action_required"
    assert detector._compute_novelty(
        _alert(severity="problem"),
        _view(seen_severity="problem", acknowledged=False),
    )["novelty"] == "action_required"
    assert detector._compute_novelty(
        _alert(severity="problem"),
        _view(seen_severity="problem", acknowledged=True),
    )["novelty"] == "known"


def test_novelty_returns_on_severity_or_25_percent_ratio_change():
    worsened = detector._compute_novelty(
        _alert(severity="problem", deviation_pct=30),
        _view(seen_severity="warning", seen_deviation_pct=30),
    )
    assert worsened["novelty"] == "worsened"

    at_threshold = detector._compute_novelty(
        _alert(deviation_pct=62.5),  # 1.625 / 1.30 == 1.25
        _view(seen_deviation_pct=30),
    )
    assert at_threshold["novelty"] == "worsened"

    below_threshold = detector._compute_novelty(
        _alert(deviation_pct=62.4),
        _view(seen_deviation_pct=30),
    )
    assert below_threshold["novelty"] == "known"

    improved = detector._compute_novelty(
        _alert(deviation_pct=30),
        _view(seen_deviation_pct=80),
    )
    assert improved["novelty"] == "improved"


def test_reopened_episode_is_new_even_with_an_old_view():
    result = detector._compute_novelty(
        _alert(opened_at=datetime(2026, 8, 3, tzinfo=timezone.utc)),
        _view(seen_at=datetime(2026, 8, 2, tzinfo=timezone.utc)),
    )
    assert result["novelty"] == "new"


def test_duration_is_deliberately_coarsened():
    assert detector._duration_label(7) is None
    assert detector._duration_label(8) == "держится больше недели"
    assert detector._duration_label(31) == "держится больше месяца"


class _Query:
    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return SimpleNamespace(actual_start_date=date(2026, 7, 1))


class _Db:
    def query(self, *_args, **_kwargs):
        return _Query()


def test_cpl_only_alert_explains_multiplication_of_two_tolerances(monkeypatch):
    budget = SimpleNamespace(
        amount=100_000,
        manual_leads=100,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 30),
    )
    goal = SimpleNamespace(is_summary=True, control_enabled=True, target_cpa=1_000)
    monkeypatch.setattr(iteration3, "_latest_budgets", lambda *_: {models.IntegrationPlatform.YANDEX_DIRECT: budget})
    monkeypatch.setattr(iteration3, "_latest_targets", lambda *_: [goal])
    monkeypatch.setattr(iteration3, "_sum_channel_stats", lambda *_: (57_000, 0, 44))

    alert = iteration3.AlertCandidate(
        metric="cpa",
        detection_level="project",
        entity_id=None,
        channel=models.IntegrationPlatform.YANDEX_DIRECT,
        mode="plan",
        severity="warning",
        deviation_pct=30,
        baseline_value=1_000,
        actual_value=1_300,
        direction="up",
        meta={"checks": ["P-2"]},
    )
    cfg = SimpleNamespace(
        plan_spend_warning_deviation=0.20,
        plan_leads_warning_deviation=0.20,
    )

    note = iteration3._tolerance_multiplication_note(
        _Db(), "project", alert, date(2026, 7, 15), cfg, None, None,
    )
    assert note is not None
    assert "Перерасход 14%" in note["full"]
    assert "недобор 12%" in note["full"]
    assert "1,3×" in note["full"]


def test_tolerance_note_is_absent_when_component_has_own_alert(monkeypatch):
    alert = iteration3.AlertCandidate(
        metric="cpa",
        detection_level="project",
        entity_id=None,
        channel=models.IntegrationPlatform.YANDEX_DIRECT,
        mode="plan",
        severity="warning",
        deviation_pct=30,
        baseline_value=1_000,
        actual_value=1_300,
        direction="up",
        meta={"checks": ["P-1", "P-2"]},
    )
    assert iteration3._tolerance_multiplication_note(
        None, "project", alert, date(2026, 7, 15), SimpleNamespace(), None, None,
    ) is None
