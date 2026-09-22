from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
import json

import pytest
import sqlalchemy as sa
from core import models, consumer_freshness as gate
from core.data_requirements import DataNotReady
from tests.test_durable_work import pg
from tests.test_metrika_goal_work import goals, DAY
from tests.test_sync_coverage import write


@pytest.fixture
def consumer(goals, monkeypatch):
    for flag in (*gate.FLAGS.values(), "REPORT_FRESHNESS_GUARDS", "REPORT_DELIVERY_GUARDS", "DURABLE_TASKS"):
        monkeypatch.setenv(flag, "true")
    with goals.factory.begin() as db:
        client = db.get(models.Client, goals.client)
        goals.owner = client.owner_id
        client.spreadsheet_id = "synthetic-sheet"
    return goals


def cover(g, first=DAY - timedelta(days=1), last=DAY):
    for stage in ("campaigns", "metrika_goals"):
        write(g, first, last, stage=stage, observed=datetime.now(timezone.utc))


def test_revision_changes_after_refresh_and_does_not_commit(consumer):
    g = consumer
    cover(g)
    with g.factory() as db:
        before = gate.verify(db, [g.client], DAY, DAY)
        db.get(models.Client, g.client).name = "pending"
    cover(g)
    with g.factory() as db:
        after = gate.verify(db, [g.client], DAY, DAY)
        assert before["revision"] != after["revision"]
        assert db.get(models.Client, g.client).name != "pending"


@pytest.mark.asyncio
async def test_ai_missing_data_never_calls_model(consumer, monkeypatch):
    from ai import report_generator as ai
    g = consumer
    model = AsyncMock(side_effect=AssertionError("No paid IO"))
    monkeypatch.setattr(ai, "_generate_report", model)
    with g.factory() as db, pytest.raises(DataNotReady):
        await ai.generate_report(db, g.owner, g.client, str(DAY), str(DAY))
    model.assert_not_called()
    assert g.engine.pool.checkedout() == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("change", [False, True])
async def test_ai_detached_prompt_and_changed_source_rejected(consumer, monkeypatch, change):
    from ai import report_generator as ai
    g = consumer
    cover(g)
    monkeypatch.setattr(ai.StatsService, "aggregate_summary", lambda *_: {"leads": 34})
    monkeypatch.setattr(ai.StatsService, "get_campaign_stats", lambda *_: [])
    async def model(**kwargs):
        assert kwargs["_prepared"][0]["leads"] == 34
        assert g.engine.pool.checkedout() == 0
        with g.factory.begin() as other:
            other.execute(sa.select(models.Integration).where(models.Integration.id == g.id).with_for_update(nowait=True))
        if change:
            cover(g)
        return "34 заявки"
    monkeypatch.setattr(ai, "_generate_report", model)
    with g.factory() as db:
        if change:
            with pytest.raises(DataNotReady):
                await ai.generate_report(db, g.owner, g.client, str(DAY), str(DAY))
        else:
            text = await ai.generate_report(db, g.owner, g.client, str(DAY), str(DAY))
            assert text == "34 заявки" and len(text.data_revision) == 64


@pytest.mark.asyncio
async def test_dashboard_prompt_excludes_unverified_memory(consumer, monkeypatch):
    from ai import report_generator as ai
    g = consumer
    cover(g)
    monkeypatch.setattr(ai, "_build_comment_context", lambda *_: {"kpi": {"leads": 34},
        "since_last_visit": {"leads": 999}, "previous_case": {"leads": 999}, "detector": {"flags": ["old"]}})
    async def model(**kwargs):
        data = kwargs["_prepared"]
        assert "since_last_visit" not in data and "previous_case" not in data
        assert data["detector"]["status"] == "not_verified"
        return "готово"
    monkeypatch.setattr(ai, "_generate_report", model)
    with g.factory() as db:
        assert await ai.generate_report(db, g.owner, g.client, str(DAY), str(DAY), "dashboard_comment") == "готово"


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["report", "chat"])
async def test_real_ai_path_releases_capture_connection_before_provider(consumer, monkeypatch, kind):
    from ai import report_generator as ai
    g = consumer
    cover(g)
    monkeypatch.setattr(ai.settings, "OPENAI_API_KEY", "synthetic")
    monkeypatch.setattr(ai.StatsService, "aggregate_summary", lambda *_: {"leads": 34})
    monkeypatch.setattr(ai.StatsService, "get_campaign_stats", lambda *_: [])
    monkeypatch.setattr(ai, "build_assistant_context", lambda *_: {"summary": {"leads": 34}, "alerts": []})
    async def create(**kwargs):
        assert g.engine.pool.checkedout() == 0
        return SimpleNamespace(content=[SimpleNamespace(text="34 заявки")])
    monkeypatch.setattr(ai, "_create_anthropic_client", lambda: SimpleNamespace(messages=SimpleNamespace(create=create)))
    with g.factory() as db:
        if kind == "report":
            result = await ai.generate_report(db, g.owner, g.client, str(DAY), str(DAY))
        else:
            result = await ai.chat(db, g.owner, g.client, str(DAY), str(DAY), "Сколько заявок?", [])
        assert result == "34 заявки"


def test_legacy_cache_never_becomes_verified():
    from ai.freshness import cache_matches, VerifiedText
    assert not cache_matches({"text": "old"}, "new")
    assert not cache_matches({"data_revision": "old"}, "new")
    assert cache_matches({"data_revision": "new"}, "new")
    assert cache_matches({"text": "old"}, None)
    assert VerifiedText("ok", {"revision": "r"}).data_revision == "r"


def test_sheets_refuses_before_sdk_and_preserves_reports(consumer):
    from automation.calendar_work import export_project
    from automation.sheets_freshness import SheetDataNotReady
    g = consumer
    constructor = Mock(side_effect=AssertionError("No external IO"))
    with pytest.raises(SheetDataNotReady):
        export_project(g.factory, {"client_id": str(g.client), "owner_id": str(g.owner),
            "scheduled_at": "2026-09-10T00:00:00+00:00"}, service_factory=constructor)
    constructor.assert_not_called()
    with g.factory() as db:
        assert db.query(models.WeeklyReport).count() == 0


def test_sheets_rebuilds_reports_and_rechecks_revision(consumer, monkeypatch):
    from automation.sheets_freshness import prepare, recheck, SheetDataNotReady
    g = consumer
    cover(g, date(2026, 7, 1), date.today())
    monkeypatch.setattr("automation.reports._period_summary", lambda *_: dict(
        total_cost=3400, total_clicks=100, total_conversions=34, avg_cpc=34, avg_cpa=100))
    with g.factory.begin() as db:
        db.add(models.MonthlyReport(client_id=g.client, year=2026, month=8, total_cost=999))
    sheet, snapshot, proof = prepare(g.factory, g.client, g.owner, DAY)
    assert sheet == "synthetic-sheet"
    assert snapshot["Monthly Report"][1][2] == 3400
    assert len(snapshot["Weekly Reports"]) > 2  # history is derived, not only today's key
    assert snapshot["Goals"][1][3] == 34
    assert g.engine.pool.checkedout() == 0
    recheck(g.factory, g.client, g.owner, sheet, proof)
    cover(g, date(2026, 7, 1), date.today())
    with pytest.raises(SheetDataNotReady):
        recheck(g.factory, g.client, g.owner, sheet, proof)
    with g.factory() as db:
        assert db.query(models.MonthlyReport).one().total_cost == 999  # no aggregate writes


@pytest.mark.parametrize("kind", ["orphan", "goal"])
def test_sheets_does_not_claim_uncovered_history(consumer, kind):
    from automation.sheets_freshness import prepare, SheetDataNotReady
    g = consumer
    cover(g, date(2026, 9, 1), date.today())
    with g.factory.begin() as db:
        if kind == "orphan":
            db.add(models.YandexStats(client_id=g.client, date=DAY, cost=100))
        else:
            db.add(models.MetrikaGoals(client_id=g.client, integration_id=g.id, date=DAY, goal_id="unselected", conversion_count=100))
    with pytest.raises(SheetDataNotReady):
        prepare(g.factory, g.client, g.owner, DAY)


def test_detector_missing_data_freezes_all_writes(consumer, monkeypatch):
    from backend_api.services import detector_iteration3 as detector
    g = consumer
    with g.factory.begin() as db:
        db.add(models.DetectorAlert(client_id=g.client, owner_id=g.owner, metric="cpa", mode="plan",
            status="open", consecutive_days=4, hypothesis_text="existing", meta={"keep": True}))
    monkeypatch.setattr(detector, "_close_superseded_alerts", Mock(side_effect=AssertionError("Do not close")))
    monkeypatch.setattr(detector, "upsert_alerts", Mock(side_effect=AssertionError("Do not recover or notify")))
    with g.factory.begin() as db:
        assert detector.run_detector_iteration3(db, g.client, DAY, immediate_plan_recalculation=True) is False
        assert detector.metric_plan_context(db, g.client, DAY) is None
        assert detector.campaign_highlights(db, g.client, DAY, DAY) == {}
        assert detector.sync_issues_for_client(db, g.client, DAY)[0]["status"] == "no_data"
        alert = db.query(models.DetectorAlert).one()
        assert alert.status == "open" and alert.consecutive_days == 4 and alert.meta == {"keep": True}


def test_detector_requires_full_baseline_not_only_current_day(consumer):
    from backend_api.services.detector_freshness import status
    g = consumer
    cover(g)
    with g.factory() as db:
        assert status(db, g.client, DAY)["status"] == "waiting_data"
    cover(g, DAY - timedelta(days=60), DAY)
    with g.factory() as db:
        assert status(db, g.client, DAY)["status"] == "ready"


def test_direct_tsv_keeps_truncation_and_rejects_malformed():
    from ai.assistant.yandex_client import _parse_tsv
    rows = _parse_tsv("CampaignId\tCost\n" + "\n".join(f"{i}\t10" for i in range(205)))
    assert len(rows) == 200 and rows.source_row_count == 205
    with pytest.raises(ValueError):
        _parse_tsv("A\tB\n1")


def test_metrika_partial_sampled_and_unavailable():
    from ai.assistant.tools import _slim_metrika
    assert _slim_metrika({})["data_status"] == "unavailable"
    assert _slim_metrika({"data": []})["data_status"] == "no_rows"
    rows = [{"dimensions": [], "metrics": [1]}] * 220
    result = _slim_metrika({"data": rows, "total_rows": 500, "sampled": True, "sample_share": .5})
    assert result["data_status"] == "sampled" and result["truncated"] and len(result["rows"]) == 200


@pytest.mark.asyncio
async def test_avito_does_not_hide_campaign_or_row_limit():
    from ai.assistant.tools import _exec_avito_get_statistics
    api = SimpleNamespace(get_statistics=AsyncMock(return_value=[{"cost": 1}] * 220))
    ctx = SimpleNamespace(avito=lambda: SimpleNamespace(api=lambda: api))
    result = json.loads(await _exec_avito_get_statistics(ctx, {"campaign_ids": list(range(250)),
        "date_from": "2026-09-01", "date_to": "2026-09-10"}))
    assert result["data_status"] == "partial" and result["queried_campaign_count"] == 200
    assert result["requested_campaign_count"] == 250 and len(result["rows"]) == 200


@pytest.mark.parametrize("flag", list(gate.FLAGS.values()))
def test_guard_configuration_requires_durable_report_gate(flag):
    from core.runtime import get_runtime
    with pytest.raises(ValueError):
        get_runtime({"APP_PROCESS_ROLE": "api", flag: "true"})
    assert get_runtime({"APP_PROCESS_ROLE": "api", flag: "true", "REPORT_FRESHNESS_GUARDS": "true",
        "DURABLE_TASKS": "true"}).role == "api"


def test_cache_publication_rechecks_under_source_locks(consumer):
    from ai.router import _save_comment_cache
    from ai.freshness import VerifiedText
    from backend_api.reports.direct_freshness import capture
    g = consumer
    cover(g)
    with g.factory() as db:
        _, proof = capture(db, g.owner, g.client, None, str(DAY), str(DAY), lambda *_: None, return_evidence=True)
    text = VerifiedText("ready", proof)
    with g.factory.begin() as db:
        _save_comment_cache(db, g.client, DAY, DAY, text)
        with g.factory() as other, pytest.raises(sa.exc.DBAPIError):
            other.execute(sa.select(models.Integration).where(models.Integration.id == g.id).with_for_update(nowait=True))
    cover(g)
    with g.factory.begin() as db, pytest.raises(DataNotReady):
        _save_comment_cache(db, g.client, DAY, DAY, text)


@pytest.mark.asyncio
async def test_ai_routes_return_waiting_not_unverified_cache(consumer):
    from ai import router
    from fastapi import HTTPException
    g = consumer
    with g.factory() as db:
        owner = db.get(models.User, g.owner)
        result = await router.get_ai_comment(str(g.client), str(DAY), str(DAY), owner, db)
        assert result["text"] is None and result["data_readiness"] == "waiting_data"
        with pytest.raises(HTTPException) as exc:
            await router.generate_report(router.GenerateReportRequest(client_id=str(g.client),
                start_date=str(DAY), end_date=str(DAY), report_type="dashboard_comment"), owner, db)
        assert exc.value.status_code == 409


def test_hypotheses_refuse_unverified_or_changed_alerts(consumer):
    from automation import detector_hypothesis_work as work
    from backend_api.services.detector_freshness import evidence
    g = consumer
    now = datetime.now(timezone.utc)
    with g.factory.begin() as db:
        db.get(models.Client, g.client).detector_enabled = True
        db.get(models.User, g.owner).global_detector_enabled = True
        db.add(models.DetectorAlert(client_id=g.client, owner_id=g.owner, metric="cpa", mode="baseline"))
    with g.factory() as db:
        assert work.prepare(db, g.client, now) == []
    cover(g, now.date() - timedelta(days=90), now.date())
    with g.factory.begin() as db:
        assert work.prepare(db, g.client, now) == []  # old alert without revision
        proof = evidence(db, g.client, now.date())
        db.query(models.DetectorAlert).one().meta = {"data_revision": proof["revision"]}
    with g.factory() as db:
        plans = work.prepare(db, g.client, now)
        assert len(plans) == 1
    cover(g, now.date() - timedelta(days=90), now.date())
    with g.factory.begin() as db:
        assert not work.apply(db, plans[0], "must not publish", now)
