"""SQL regression and query budgets on synthetic, isolated PostgreSQL only."""
from contextlib import contextmanager
from datetime import date
import json
import os
from pathlib import Path
import runpy
from types import SimpleNamespace
import uuid

import pytest
import sqlalchemy as sa

from backend_api.folders import _summary_with_combined_leads_cpl
from backend_api import folders
from backend_api.stats_service import StatsService
from backend_api.summary_scope import SummaryScope
from backend_api.summary_facts import SummaryFacts
from core import models
from tests.test_durable_work import pg  # explicitly isolated, per-test schema

DAY = date(2026, 9, 10)
PREV = date(2026, 9, 9)
P = models.IntegrationPlatform


@contextmanager
def statements(engine):
    queries = []
    def collect(conn, cursor, sql, params, context, many):
        if sql.lstrip().upper().startswith("SELECT"):
            queries.append(sql)
    sa.event.listen(engine, "before_cursor_execute", collect)
    try:
        yield queries
    finally:
        sa.event.remove(engine, "before_cursor_execute", collect)


@pytest.fixture
def summary_db(pg):
    factory, engine = pg
    # Real production column types/indexes, but no cross-domain foreign keys:
    # the test needs no billing/users/production data to exercise statistics.
    meta = sa.MetaData()
    for model in (models.Integration, models.Campaign, models.YandexStats,
                  models.VKStats, models.AvitoStats, models.MetrikaGoals):
        source = model.__table__
        table = sa.Table(source.name, meta, *[
            sa.Column(c.name, c.type.copy(), primary_key=c.primary_key, nullable=c.nullable)
            for c in source.columns
        ])
        for index in source.indexes:
            sa.Index(index.name, *[table.c[c.name] for c in index.columns])
    meta.create_all(engine)
    a, b = uuid.uuid4(), uuid.uuid4()
    ids = {name: uuid.uuid4() for name in ("y", "v", "a", "other")}
    campaign = {name: uuid.uuid4() for name in ("y", "v", "traffic", "a", "other")}
    with factory() as db:
        for name, owner, platform, goals, balance in (
            ("y", a, P.YANDEX_DIRECT, '["1"]', 10000),
            ("v", a, P.VK_ADS, None, 20000),
            ("a", a, P.AVITO_ADS, '["2"]', 500),
            ("other", b, P.YANDEX_DIRECT, '["2"]', 900000),
        ):
            db.execute(models.Integration.__table__.insert().values(
                id=ids[name], client_id=owner, platform=platform, selected_goals=goals,
                lead_action_types='["lead"]' if name == "v" else None,
                balance=balance, currency="RUB",
            ))
        for name in campaign:
            integration_name = "v" if name == "traffic" else name
            db.execute(models.Campaign.__table__.insert().values(
                id=campaign[name], integration_id=ids[integration_name], external_id=name, name=name,
                is_active=True, vk_goal_action_id="lead" if name == "v" else "traffic",
            ))
        for day, multiplier in ((DAY, 1), (PREV, 2)):
            for model, name, owner, cost, conversions in (
                (models.YandexStats, "y", a, 1000, 65),
                (models.VKStats, "v", a, 3000, 6),
                (models.VKStats, "traffic", a, 1000, 999),
                (models.AvitoStats, "a", a, 500, 777),
                (models.YandexStats, "other", b, 999999, 999),
            ):
                db.execute(model.__table__.insert().values(
                    client_id=owner, campaign_id=campaign[name], date=day, cost=cost * multiplier,
                    impressions=1000 * multiplier, clicks=100 * multiplier,
                    conversions=conversions * multiplier, cpc=cost / 100,
                ))
            for name, owner, goal, count in (("y", a, "1", 34), ("y", a, "all", 34),
                                            ("a", a, "2", 3), ("other", b, "1", 9999),
                                            ("other", b, "2", 7)):
                db.execute(models.MetrikaGoals.__table__.insert().values(
                    client_id=owner, integration_id=ids[name], goal_id=goal, date=day,
                    conversion_count=count * multiplier,
                ))
        db.commit()
        yield db, engine, a, b, ids, campaign


@pytest.mark.parametrize("platform,leads,cost", [("yandex", 34, 1000), ("vk", 6, 4000), ("avito", 3, 500)])
def test_platform_totals_and_previous_period(summary_db, platform, leads, cost):
    db, engine, a, _, _, _ = summary_db
    with statements(engine) as queries:
        result = StatsService.aggregate_summary(db, [a], DAY, DAY, platform)
    assert result["leads"] == leads
    assert result["expenses"] == cost
    assert result["prev"]["leads"] == leads * 2
    assert result["trends"]["leads"] == -50
    # DATA-02: Avito's selected Metrika conversions are counted exactly once.
    assert result["cpa"] == round((3000 if platform == "vk" else cost) / leads, 2)
    assert result["goals_syncing"] is False
    assert len(queries) <= 6
    assert sum("FROM integrations" in q and "FROM campaigns" in q for q in queries) == 1
    assert not any("count(metrika_goals" in q.lower() for q in queries)
    assert not any("access_token" in q for q in queries)


def test_combined_channels_share_one_metadata_read(summary_db):
    db, engine, a, _, _, _ = summary_db
    with statements(engine) as queries:
        result = _summary_with_combined_leads_cpl(db, [a], DAY, DAY, include_trends=False)
    assert result["leads"] == 43
    assert result["expenses"] == 5500
    assert result["cpa"] == round(4500 / 43, 2)
    assert result["balance"] == 30500
    assert result["lead_cost_by_platform"] == {"yandex": 1000, "vk": 3000, "avito": 500}
    assert len(queries) == 6  # metadata + five grouped facts, reused by channels


def test_folder_scope_narrows_goals_and_balances(summary_db):
    db, engine, a, b, _, _ = summary_db
    scope = SummaryScope.load(db, [a, b])
    with statements(engine) as queries:
        first = _summary_with_combined_leads_cpl(db, [a], DAY, DAY, include_trends=False, integration_scope=scope)
        second = _summary_with_combined_leads_cpl(db, [b], DAY, DAY, include_trends=False, integration_scope=scope)
    assert first["leads"] == 43
    assert second["leads"] == 7
    assert first["balance"] == 30500
    assert second["balance"] == 900000
    assert not any("FROM integrations" in q for q in queries)
    with pytest.raises(ValueError, match="cannot be expanded"):
        scope.rows_for([uuid.uuid4()])


def test_exact_direction_override_is_preserved(summary_db):
    db, _, a, _, _, campaign = summary_db
    result = StatsService.aggregate_summary(
        db, [a], DAY, DAY, "yandex", [campaign["y"]],
        campaign_lead_overrides={"yandex": 34}, previous_campaign_lead_overrides={"yandex": 12},
    )
    assert result["leads"] == 34
    assert result["prev"]["leads"] == 12
    assert result["cpa"] == round(1000 / 34, 2)


def test_new_request_reads_changed_selection_balance_and_activity(summary_db):
    db, _, a, _, ids, _ = summary_db
    assert StatsService.aggregate_summary(db, [a], DAY, DAY, "vk")["leads"] == 6
    db.execute(sa.update(models.Integration).where(models.Integration.id == ids["v"]).values(
        lead_action_types='["traffic"]', balance=123,
    ))
    db.commit()
    changed = StatsService.aggregate_summary(db, [a], DAY, DAY, "vk")
    assert changed["leads"] == 999 and changed["balance"] == 123
    db.execute(sa.update(models.Campaign).where(models.Campaign.integration_id == ids["v"]).values(is_active=False))
    db.commit()
    archived = StatsService.aggregate_summary(db, [a], DAY, DAY, "vk")
    assert archived["leads"] == 999 and archived["balance"] is None


def test_missing_data_is_not_zero_counted_as_present(summary_db):
    db, _, a, _, _, _ = summary_db
    db.execute(sa.delete(models.MetrikaGoals).where(models.MetrikaGoals.client_id == a))
    db.commit()
    result = StatsService.aggregate_summary(db, [a], DAY, DAY, "yandex")
    assert result["leads"] == 0 and result["goals_syncing"] is True


def test_yandex_companion_goal_fallback_and_empty_vk_selection(summary_db):
    db, _, a, _, ids, _ = summary_db
    db.execute(sa.update(models.Integration).where(models.Integration.id == ids["y"]).values(selected_goals=None))
    db.execute(models.Integration.__table__.insert().values(
        id=uuid.uuid4(), client_id=a, platform=P.YANDEX_METRIKA, primary_goal_id="1",
    ))
    db.execute(sa.update(models.Integration).where(models.Integration.id == ids["v"]).values(lead_action_types="[]"))
    db.commit()
    assert StatsService.aggregate_summary(db, [a], DAY, DAY, "yandex")["leads"] == 34
    vk = StatsService.aggregate_summary(db, [a], DAY, DAY, "vk")
    assert vk["leads"] == 0 and vk["leads_configured"] is False


def test_top_projects_loads_metadata_once_after_access_resolution(summary_db, monkeypatch):
    db, engine, a, b, _, _ = summary_db
    access_checked = []
    def accessible(session, user):
        assert session is db
        access_checked.append(user)
        return [SimpleNamespace(id=cid, name=name, status="active", avatar_url=None)
                for cid, name in ((a, "A"), (b, "B"))]
    monkeypatch.setattr(folders, "_accessible_clients", accessible)
    def checked(conn, cursor, sql, params, context, many):
        assert access_checked, "metadata queried before resolving access"
    sa.event.listen(engine, "before_cursor_execute", checked)
    try:
        with statements(engine) as queries:
            result = folders.top_projects(start_date=str(DAY), end_date=str(DAY), limit=5,
                                          include_vat=True, current_user="test-owner", db=db)
    finally:
        sa.event.remove(engine, "before_cursor_execute", checked)
    assert result["total_projects"] == 2
    assert [row["name"] for row in result["items"]] == ["A", "B"]
    assert sum("FROM integrations" in q for q in queries) == 1
    assert len(queries) == 6  # Constant within a bounded page, not 14 per project.


@pytest.mark.parametrize("platform", ["all", "yandex", "vk", "avito"])
@pytest.mark.parametrize("trends", [True, False])
@pytest.mark.parametrize("preset", [None, "this_week", "this_month", "last_month"])
def test_batched_facts_equal_canonical_all_fields(summary_db, platform, trends, preset):
    db, _, a, b, _, _ = summary_db
    scope = SummaryScope.load(db, [a, b])
    facts = SummaryFacts(scope)
    for ids in ([a], [b], [a, b], []):
        expected = StatsService.aggregate_summary(db, ids, DAY, DAY, platform,
            include_trends=trends, period_preset=preset, integration_scope=scope)
        actual = StatsService.aggregate_summary(db, ids, DAY, DAY, platform,
            include_trends=trends, period_preset=preset, integration_scope=scope, summary_facts=facts)
        assert actual == expected


def test_batched_facts_keep_filters_and_exact_direction_path(summary_db):
    db, _, a, b, _, campaigns = summary_db
    scope = SummaryScope.load(db, [a, b])
    facts = SummaryFacts(scope)
    for kwargs in ({"campaign_ids": [campaigns["y"]], "campaign_lead_overrides": {"yandex": 12}},
                   {"vk_goal_action_ids": ["traffic"]}):
        expected = StatsService.aggregate_summary(db, [a], DAY, DAY, integration_scope=scope, **kwargs)
        assert StatsService.aggregate_summary(db, [a], DAY, DAY, integration_scope=scope,
            summary_facts=facts, **kwargs) == expected
    assert len(facts.cache) == 0
    with pytest.raises(ValueError, match="cannot be expanded"):
        facts.read(db, [uuid.uuid4()], DAY, DAY)


def test_batched_new_request_observes_settings_and_stat_commit(summary_db):
    db, _, a, b, ids, _ = summary_db
    def read():
        scope = SummaryScope.load(db, [a, b])
        return StatsService.aggregate_summary(db, [a], DAY, DAY, "vk", integration_scope=scope,
            summary_facts=SummaryFacts(scope))
    assert read()["leads"] == 6
    db.execute(sa.update(models.Integration).where(models.Integration.id == ids["v"]).values(lead_action_types='["traffic"]'))
    db.commit()
    assert read()["leads"] == 999
    db.execute(sa.update(models.VKStats).where(models.VKStats.client_id == a, models.VKStats.date == DAY).values(conversions=20))
    db.commit()
    assert read()["leads"] == 20


def test_batched_missing_goals_and_group_limit_fallback(summary_db, monkeypatch):
    db, _, a, _, _, _ = summary_db
    scope = SummaryScope.load(db, [a])
    monkeypatch.setattr(SummaryFacts, "MAX_GOAL_GROUPS", 1)
    facts = SummaryFacts(scope)
    assert StatsService.aggregate_summary(db, [a], DAY, DAY, "yandex", integration_scope=scope,
        summary_facts=facts) == StatsService.aggregate_summary(db, [a], DAY, DAY, "yandex")
    assert all(value is None for value in facts.cache.values())
    db.execute(sa.delete(models.MetrikaGoals).where(models.MetrikaGoals.client_id == a))
    db.commit()
    scope = SummaryScope.load(db, [a])
    assert StatsService.aggregate_summary(db, [a], DAY, DAY, "yandex", integration_scope=scope,
        summary_facts=SummaryFacts(scope))["goals_syncing"] is True


def test_batch_memory_and_query_budget_are_page_bounded(summary_db, monkeypatch):
    db, engine, a, b, _, _ = summary_db
    ids = [a, b, *[uuid.uuid4() for _ in range(130)]]
    scope = SummaryScope.load(db, ids)
    facts = SummaryFacts(scope)
    with statements(engine) as queries:
        for cid in sorted(ids, key=str):
            StatsService.aggregate_summary(db, [cid], DAY, DAY, integration_scope=scope, summary_facts=facts)
            assert len(facts.cache) <= 4
    # Three bounded pages, two periods, five facts queries per page/period.
    assert len(queries) == 30


def test_project_batch_endpoint_matches_serialized_summary_and_query_budget(summary_db, monkeypatch):
    from backend_api.stats import get_project_summaries
    from core import schemas
    db, engine, a, b, _, _ = summary_db
    monkeypatch.setattr("backend_api.access_control.get_accessible_client_ids", lambda *_: [a, b])
    with statements(engine) as queries:
        result = get_project_summaries([a, b, a], str(DAY), str(DAY), "this_week", "owner", db)
    assert len(queries) == 11
    assert set(result) == {str(a), str(b)}
    for cid in (a, b):
        for platform in ("all", "yandex", "vk", "avito"):
            expected = StatsService.aggregate_summary(db, [cid], DAY, DAY, platform, period_preset="this_week")
            assert schemas.StatsSummary.model_validate(result[str(cid)][platform]).model_dump() == schemas.StatsSummary.model_validate(expected).model_dump()


@pytest.mark.parametrize("case", ["foreign", "revoked", "empty", "oversized", "date"])
def test_project_batch_rejects_invalid_or_inaccessible_scope_without_stats_sql(summary_db, monkeypatch, case):
    from fastapi import HTTPException
    from backend_api.stats import get_project_summaries
    db, engine, a, b, _, _ = summary_db
    monkeypatch.setattr("backend_api.access_control.get_accessible_client_ids", lambda *_: [] if case == "revoked" else [a])
    ids = {"foreign": [a, b], "revoked": [a], "empty": [], "oversized": [a] * 65, "date": [a]}[case]
    with statements(engine) as queries, pytest.raises(HTTPException) as error:
        get_project_summaries(ids, "invalid" if case == "date" else str(DAY), str(DAY), None, "owner", db)
    assert error.value.status_code == (403 if case in ("foreign", "revoked") else 422)
    assert queries == []


def test_exists_stops_after_first_goal_row(summary_db):
    db, engine, a, _, ids, _ = summary_db
    db.execute(models.MetrikaGoals.__table__.insert(), [
        {"client_id": a, "integration_id": ids["y"], "date": DAY,
         "goal_id": "1", "conversion_count": 1} for _ in range(10000)
    ])
    db.commit()
    matches = db.query(models.MetrikaGoals.id).filter(
        models.MetrikaGoals.client_id == a, models.MetrikaGoals.goal_id == "1",
        models.MetrikaGoals.date == DAY,
    )
    def explain(query):
        sql = query.statement.compile(engine, compile_kwargs={"literal_binds": True})
        return db.execute(sa.text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + str(sql))).scalar()[0]["Plan"]
    def scanned(plan):
        if plan.get("Relation Name") == "metrika_goals":
            return plan["Actual Rows"] * plan["Actual Loops"]
        return sum(scanned(child) for child in plan.get("Plans", []))
    count_plan = explain(matches.with_entities(sa.func.count(models.MetrikaGoals.id)))
    exists_plan = explain(db.query(matches.exists()))
    assert scanned(count_plan) == 10001
    assert scanned(exists_plan) == 1
    print("SUMMARY_EXISTENCE " + json.dumps({"count_rows": scanned(count_plan), "exists_rows": scanned(exists_plan)}))


def test_optional_full_response_comparison_with_previous_release(summary_db):
    # Mount a reviewed prior source file read-only for differential acceptance.
    path = os.getenv("SUMMARY_BASELINE_FILE")
    if not path:
        pytest.skip("optional previous-release differential comparison")
    assert os.getenv("WW_TEST") == "1" and Path(path).is_file()
    before = runpy.run_path(path)["StatsService"]
    db, engine, a, b, ids, campaign = summary_db
    totals = [0, 0]
    cases = 0
    representative = {}
    for clients in ([a], [b], [a, b], []):
        for platform in ("all", "yandex", "vk", "avito"):
            for trends in (True, False):
                for campaigns in (None, [campaign["y"]], [campaign["v"]], [campaign["a"]]):
                    args = (db, clients, DAY, DAY, platform, campaigns)
                    kwargs = {"include_trends": trends}
                    with statements(engine) as old_sql:
                        old = before.aggregate_summary(*args, **kwargs)
                    with statements(engine) as new_sql:
                        new = StatsService.aggregate_summary(*args, **kwargs)
                    old = {**old, "calculation_version": StatsService.CALCULATION_VERSION}
                    if platform == "avito":
                        # The prior performance baseline intentionally preserved
                        # the known denominator bug. Only CPA may change now.
                        old = dict(old)
                        old["cpa"] = new["cpa"]
                        if old.get("trends"):
                            old["trends"] = {**old["trends"], "cpa": new["trends"]["cpa"]}
                        lead_cost = float((new.get("lead_cost_by_platform") or {}).get("avito") or 0)
                        assert new["cpa"] == (round(lead_cost / new["leads"], 2) if new["leads"] else 0)
                    assert new == old, (clients, platform, trends, campaigns, old, new)
                    totals[0] += len(old_sql)
                    totals[1] += len(new_sql)
                    cases += 1
                    if clients == [a] and campaigns is None and trends:
                        representative[platform] = {"old": len(old_sql), "new": len(new_sql)}
    print("SUMMARY_DIFFERENTIAL " + json.dumps({"cases": cases, "old_queries": totals[0], "new_queries": totals[1]}))
    print("SUMMARY_QUERY_COUNTS " + json.dumps(representative))
