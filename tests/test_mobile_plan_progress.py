"""Mobile progress exposes numeric facts; it must not parse localized references."""
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend_api.services import detector_iteration3 as iteration3
from core import models


@pytest.mark.parametrize('warmup', [False, True])
@pytest.mark.parametrize('spend,leads', [(12000, 10), (0, 0), (150000, 100)])
def test_progress_is_same_active_plan_even_during_warmup(monkeypatch, warmup, spend, leads):
    channel = models.IntegrationPlatform.YANDEX_DIRECT
    budget = SimpleNamespace(amount=30000, manual_leads=30,
                             period_start=date(2026, 9, 1), period_end=date(2026, 9, 30))
    monkeypatch.setattr(iteration3, 'plan_warmup_state', lambda *_: {'is_warming_up': warmup})
    monkeypatch.setattr(iteration3, '_ad_integrations', lambda *_: [SimpleNamespace(platform=channel)])
    monkeypatch.setattr(iteration3, '_selected_goal_ids', lambda *_: [])
    monkeypatch.setattr(iteration3, '_latest_budgets', lambda *_: {channel: budget})
    monkeypatch.setattr(iteration3, '_latest_targets', lambda *_: [])
    monkeypatch.setattr(iteration3, '_sum_channel_stats', lambda *_: (spend, 100, leads))
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(actual_start_date=date(2026, 9, 3))

    result = iteration3.metric_plan_context(db, 'test-project', date(2026, 9, 10))
    assert result['expenses']['actual'] == spend
    assert result['expenses']['target'] == 30000
    assert result['expenses']['elapsed_fraction'] == pytest.approx(10 / 30)
    assert result['leads']['actual'] == leads
    assert result['leads']['target'] == 30
    assert result['leads']['elapsed_fraction'] == result['expenses']['elapsed_fraction']
    assert result['cpa']['actual'] == (spend / leads if leads else None)
    assert result['cpa']['target'] == 1000
    for metric in result.values():
        assert metric['period_start'] == '2026-09-01'
        assert metric['period_end'] == '2026-09-30'
        assert metric['reference']
        if warmup:
            assert 'gap' not in metric
            assert 'verdict' not in metric
