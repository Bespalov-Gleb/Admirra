"""DATA-02: Avito denominator correctness across existing consumers, no API IO."""
import asyncio
from datetime import date
from types import SimpleNamespace
import uuid

import pytest
import sqlalchemy as sa

from backend_api.stats_service import StatsService
from core import models
from tests.test_summary_queries import summary_db, DAY, PREV
from tests.test_durable_work import pg


def test_avito_500_divided_by_3_not_6(summary_db):
    db, _, a, _, _, _ = summary_db
    result = StatsService.aggregate_summary(db, [a], DAY, DAY, "avito")
    assert (result["expenses"], result["leads"]) == (500, 3)
    assert result["cpa"] == 166.67
    assert result["calculation_version"] == StatsService.CALCULATION_VERSION
    assert result["lead_cost_by_platform"] == {"yandex": 0, "vk": 0, "avito": 500}


@pytest.mark.parametrize("campaign_filter", [False, True])
def test_avito_exact_direction_and_previous_period(summary_db, campaign_filter):
    db, _, a, _, ids, campaigns = summary_db
    db.execute(sa.update(models.AvitoStats).where(models.AvitoStats.date == PREV).values(cost=900))
    db.execute(sa.update(models.MetrikaGoals).where(models.MetrikaGoals.integration_id == ids["a"],
        models.MetrikaGoals.date == PREV).values(conversion_count=3))
    db.commit()
    kwargs = dict(campaign_ids=[campaigns["a"]], campaign_lead_overrides={"avito": 2},
                  previous_campaign_lead_overrides={"avito": 3}) if campaign_filter else {}
    current = StatsService.aggregate_summary(db, [a], DAY, DAY, "avito", **kwargs)
    previous = StatsService.aggregate_summary(db, [a], PREV, PREV, "avito", include_trends=False)
    cpl = 250 if campaign_filter else 166.67
    assert current["cpa"] == cpl and previous["cpa"] == 300
    assert current["prev"]["leads"] == 3
    assert current["trends"]["cpa"] == (-16.7 if campaign_filter else -44.4)
    # Source absolutes used by project-card ruble delta agree with the endpoint.
    prev_cpl = current["prev"]["lead_cost_by_platform"]["avito"] / current["prev"]["leads"]
    assert round(current["cpa"] - prev_cpl, 2) == (-50 if campaign_filter else -133.33)


def test_avito_no_leads_does_not_divide_by_native_conversions(summary_db):
    db, _, a, _, ids, _ = summary_db
    db.execute(sa.update(models.MetrikaGoals).where(models.MetrikaGoals.integration_id == ids["a"])
        .values(conversion_count=0))
    db.commit()
    result = StatsService.aggregate_summary(db, [a], DAY, DAY, "avito")
    # Existing API's legacy 0/null contract is deliberately not changed here.
    assert result["leads"] == 0 and result["cpa"] == 0


def test_avito_summary_endpoint_and_frozen_report_builder_agree(summary_db, monkeypatch):
    from backend_api import stats
    from backend_api.reports import pdf_service
    from backend_api.reports.scheduler import _format_text_report
    db, _, a, _, _, _ = summary_db
    monkeypatch.setattr(StatsService, "get_effective_client_ids", lambda *args: [a])
    monkeypatch.setattr(StatsService, "get_campaign_stats", lambda *args, **kwargs: [])
    result = asyncio.run(stats.get_summary(start_date=str(DAY), end_date=str(DAY), client_id=None,
        folder_id=None, campaign_ids=None, goal_action_ids=None, platform="avito", period_preset=None,
        current_user=SimpleNamespace(id=uuid.uuid4()), db=db))
    _, frozen = pdf_service.generate_report_pdf(db, uuid.uuid4(), None, str(DAY), str(DAY),
        platform="avito", sections=["kpi"], return_data=True, render_pdf=False)
    assert result["cpa"] == frozen["summary"]["cpa"] == 166.67
    message = _format_text_report(frozen["summary"], [], "Synthetic", str(DAY), str(DAY))
    assert "CPL: 166.67 ₽" in message  # Avito costs already include VAT


def test_avito_dynamic_series_matches_summary(summary_db):
    from backend_api.services.dynamics_service import get_dynamics_series
    db, engine, a, _, _, _ = summary_db
    # Only this additional table is read by the real dynamics service.
    sa.Table("clients", sa.MetaData(), sa.Column("id", sa.UUID, primary_key=True),
             sa.Column("actual_start_date", sa.Date)).create(engine)
    series = get_dynamics_series(db, [a], DAY, DAY, platform="avito", granularity="week")
    period = series["periods"][0]
    # Dynamics aligns its bucket to Monday, not to the requested single day.
    current = StatsService.aggregate_summary(db, [a], date.fromisoformat(period["start"]),
                                            date.fromisoformat(period["end"]), "avito")
    assert period["leads"] == current["leads"] == 9
    assert period["cpl"] == current["cpa"] == 166.67


def test_avito_ai_comment_context_matches_screen_without_paid_call(summary_db, monkeypatch):
    from ai import report_generator
    db, _, a, b, _, _ = summary_db
    monkeypatch.setattr(report_generator, "_comment_campaigns", lambda *args: [])
    # A second scope member has no Avito data; aggregate context needs no client
    # detector/plan tables. The actual summary/goal/VAT path remains unmocked.
    context = report_generator._build_comment_context(db, [a, b], DAY, DAY, str(DAY), str(DAY), "avito")
    assert context["kpi"]["cpl"]["value"] == 166.67
    assert context["kpi"]["leads"]["value"] == 3


def test_old_avito_visit_is_not_compared_as_if_its_cpl_had_grown():
    current = {"platform": "avito", "calculation_version": StatsService.CALCULATION_VERSION}
    assert StatsService.dashboard_snapshots_comparable(current, current, "avito")
    assert not StatsService.dashboard_snapshots_comparable({"platform": "avito"}, current, "avito")
    assert not StatsService.dashboard_snapshots_comparable({**current, "platform": "all"}, current, "avito")
    assert StatsService.dashboard_snapshots_comparable({}, {}, "yandex")


def test_calculation_version_survives_response_schema(summary_db):
    from core.schemas import StatsSummary
    db, _, a, _, _, _ = summary_db
    response = StatsSummary.model_validate(StatsService.aggregate_summary(db, [a], DAY, DAY, "avito"))
    assert response.model_dump()["calculation_version"] == StatsService.CALCULATION_VERSION
