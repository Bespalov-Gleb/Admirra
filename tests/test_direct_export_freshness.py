from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock
import uuid

import pytest
import sqlalchemy as sa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import Response

from core import models, security
from core.database import get_db
from core.data_requirements import DataNotReady, requirements
from core.runtime import get_runtime
from backend_api.reports import direct_freshness as gate, pdf_service, export_service, router
from tests.test_durable_work import pg
from tests.test_metrika_goal_work import goals, DAY
from tests.test_sync_coverage import write


@pytest.fixture
def export(goals, monkeypatch):
    g = goals
    for flag in ("DIRECT_EXPORT_FRESHNESS_GUARDS", "REPORT_FRESHNESS_GUARDS", "REPORT_DELIVERY_GUARDS", "DURABLE_TASKS"):
        monkeypatch.setenv(flag, "true")
    with g.factory() as db:
        g.owner = db.get(models.Client, g.client).owner_id
    g.queries = []
    def summary(db, ids, *args):
        g.queries.append(tuple(ids))
        assert ids == [g.client]
        return {"leads": 34, "expenses": 3400}
    monkeypatch.setattr(pdf_service.StatsService, "aggregate_summary", summary)
    monkeypatch.setattr(pdf_service.StatsService, "get_campaign_stats", lambda *_: [])
    monkeypatch.setattr(pdf_service, "_daily_series", lambda *_: [])
    return g


def cover(g, *, start=None, observed=None):
    for stage in ("campaigns", "metrika_goals"):
        write(g, start or DAY - timedelta(days=1), DAY, stage=stage,
              observed=observed or datetime.now(timezone.utc))


def capture(g, reader=lambda *_: "ready", **kwargs):
    with g.factory() as db:
        return gate.capture(db, g.owner, g.client, None, str(DAY), str(DAY), reader, **kwargs)


@pytest.mark.parametrize("mode", ["missing", "previous_missing", "stale", "settings_changed", "paused", "inactive_user"])
def test_rejects_before_reading_numbers(export, mode):
    g = export
    if mode != "missing":
        cover(g, start=DAY if mode == "previous_missing" else None,
              observed=datetime.now(timezone.utc) - timedelta(days=2) if mode == "stale" else None)
    with g.factory.begin() as db:
        if mode == "settings_changed":
            db.get(models.Integration, g.id).selected_goals = '["2"]'
        if mode == "paused":
            db.get(models.Client, g.client).status = models.ClientStatus.PAUSED
        if mode == "inactive_user":
            db.get(models.User, g.owner).is_active = False
    reader = Mock(side_effect=AssertionError("No partial read"))
    with pytest.raises(DataNotReady):
        capture(g, reader)
    reader.assert_not_called()
    assert g.engine.pool.checkedout() == 0


def test_snapshot_render_after_unlock_without_committing_caller(export, monkeypatch):
    g = export
    cover(g)
    def render(data, comment):
        # Caller has its own pending SQL change, but capture Session is closed.
        assert g.engine.pool.checkedout() == 1
        with g.factory.begin() as other:
            other.execute(sa.select(models.Integration).where(models.Integration.id == g.id).with_for_update(nowait=True))
        assert data["summary"]["leads"] == 34 and comment == "Готовый текст"
        return b"%PDF synthetic"
    monkeypatch.setattr(pdf_service, "generate_report_pdf_from_snapshot", render)
    with g.factory() as db:
        user = db.get(models.User, g.owner)
        user.email = "pending@example.test"
        result = pdf_service.generate_report_pdf(db, g.owner, g.client, str(DAY), str(DAY), "Готовый текст")
        assert result == b"%PDF synthetic" and user in db.dirty
    with g.factory() as db:
        assert db.get(models.User, g.owner).email != "pending@example.test"
        assert db.scalar(sa.select(sa.func.count()).select_from(models.ReportDelivery)) == 0


def test_docx_and_link_data_are_detached_and_match_legacy_tuple(export):
    g = export
    cover(g)
    with g.factory() as db:
        values = export_service._get_report_data(db, g.owner, g.client, str(DAY), str(DAY), "Текст", include_scope=True)
        assert g.engine.pool.checkedout() == 0
        assert values[0]["leads"] == 34 and values[-1] == [g.client]
        assert values[3] == "Текст"


def test_optional_chart_failure_is_not_silently_exported(export, monkeypatch):
    g = export
    cover(g)
    monkeypatch.setattr(pdf_service, "_daily_series", Mock(side_effect=RuntimeError("synthetic query failure")))
    render = Mock(side_effect=AssertionError("No partial render"))
    monkeypatch.setattr(pdf_service, "generate_report_pdf_from_snapshot", render)
    with g.factory() as db, pytest.raises(RuntimeError, match="synthetic query"):
        pdf_service.generate_report_pdf(db, g.owner, g.client, str(DAY), str(DAY))
    render.assert_not_called()


def test_access_rechecked_after_data_capture(export, monkeypatch):
    g = export
    cover(g)
    original = gate.scope
    calls = []
    def scope(*args):
        calls.append(1)
        return original(*args) if len(calls) == 1 else []
    monkeypatch.setattr(gate, "scope", scope)
    with pytest.raises(DataNotReady, match="ещё не готовы"):
        capture(g)
    assert len(calls) == 2


def test_source_is_locked_during_capture_and_lock_wait_is_bounded(export):
    g = export
    cover(g)
    def reader(read, ids):
        with g.factory() as other, pytest.raises(sa.exc.DBAPIError) as error:
            other.execute(sa.select(models.Integration).where(models.Integration.id == g.id).with_for_update(nowait=True))
        assert error.value.orig.pgcode == "55P03"
        return "ready"
    assert capture(g, reader) == "ready"
    with g.factory() as holder:
        holder.execute(sa.select(models.Integration).where(models.Integration.id == g.id).with_for_update())
        with pytest.raises(DataNotReady) as error:
            capture(g)
        assert error.value.reason == "source_busy"
        assert holder.scalar(sa.select(sa.literal(1))) == 1
    assert g.engine.pool.checkedout() == 0


def test_all_clients_must_have_statistical_sources(export):
    g = export
    with g.factory.begin() as db:
        empty = models.Client(owner_id=g.owner, name="Disconnected")
        db.add(empty)
        db.flush()
        with pytest.raises(DataNotReady) as error:
            requirements(db, [g.client, empty.id], DAY, DAY)
        assert error.value.reason == "no_statistical_sources"


def test_folder_link_never_expands_to_all_projects(export, monkeypatch):
    g = export
    cover(g)
    monkeypatch.setenv("DURABLE_REPORT_LINKS", "false")
    monkeypatch.setenv("LEGACY_REPORT_LINK_READS", "true")
    with g.factory.begin() as db:
        folder = models.Folder(account_id=g.owner, name="Exact scope")
        db.add(folder)
        db.flush()
        folder_id = folder.id
        db.get(models.Client, g.client).folder_id = folder_id
        db.add(models.Client(owner_id=g.owner, name="Outside folder, no sources"))
    saved = []
    monkeypatch.setattr(router, "save_report_view_data", lambda **kw: saved.append(kw) or "synthetic-token")
    with g.factory() as db:
        user = db.get(models.User, g.owner)
        result = router.create_report_link(router.CreateLinkRequest(start_date=str(DAY), end_date=str(DAY),
            folder_id=str(folder_id)), Response(), user, db)
    assert result["token"] == "synthetic-token"
    assert saved[0]["summary"]["leads"] == 34
    assert g.queries == [(g.client,)]


def test_foreign_project_is_not_read(export):
    g = export
    cover(g)
    with g.factory.begin() as db:
        other = models.User(email="foreign@example.test", password_hash="synthetic")
        db.add(other)
        db.flush()
        foreign = models.Client(owner_id=other.id, name="Private")
        db.add(foreign)
        db.flush()
        foreign_id = foreign.id
    reader = Mock(side_effect=AssertionError("Never read foreign values"))
    with g.factory() as db, pytest.raises(DataNotReady):
        gate.capture(db, g.owner, foreign_id, None, str(DAY), str(DAY), reader)
    reader.assert_not_called()


def test_period_includes_previous_and_optional_dynamics():
    assert gate.period("2026-09-10", "2026-09-10") == (date(2026, 9, 9), date(2026, 9, 10))
    assert gate.period("2026-09-10", "2026-09-10", True)[0] == date(2026, 4, 1)
    for start, end in [("bad", "2026-01-01"), ("2026-02-01", "2026-01-01"), ("2000-01-01", "2026-01-01")]:
        with pytest.raises(DataNotReady):
            gate.period(start, end)


def test_dynamics_requires_older_coverage(export):
    cover(export)
    with pytest.raises(DataNotReady):
        capture(export, dynamics=True)
    cover(export, start=date(2026, 4, 1))
    assert capture(export, dynamics=True) == "ready"


@pytest.mark.parametrize("method,path,ai", [(method, path, ai) for method in ("GET", "POST")
    for path in ("pdf", "png", "docx") for ai in (False, True)] + [("POST", "link", False), ("POST", "send", False)])
def test_http_missing_data_409_before_paid_ai_or_external_output(export, monkeypatch, method, path, ai):
    g = export
    app = FastAPI()
    app.include_router(router.router)
    def db_dependency():
        with g.factory() as db:
            yield db
    with g.factory() as db:
        user = db.get(models.User, g.owner)
        db.expunge(user)
    app.dependency_overrides[get_db] = db_dependency
    app.dependency_overrides[security.get_current_user] = lambda: user
    llm = AsyncMock(side_effect=AssertionError("No paid AI on missing data"))
    monkeypatch.setattr("ai.report_generator.generate_report", llm)
    data = {"client_id": str(g.client), "start_date": str(DAY), "end_date": str(DAY), "ai": ai}
    with TestClient(app) as http:
        response = http.request(method, "/reports/" + path, **({"params": data} if method == "GET" else {"json": data}))
    assert response.status_code == 409, response.text
    assert "не готовы" in response.json()["detail"]
    assert response.headers["cache-control"] == "no-store"
    assert not g.queries
    llm.assert_not_awaited()


def test_flag_off_is_legacy_and_misconfiguration_rejected(monkeypatch):
    monkeypatch.delenv("DIRECT_EXPORT_FRESHNESS_GUARDS", raising=False)
    assert not gate.enabled()
    monkeypatch.setenv("DIRECT_EXPORT_FRESHNESS_GUARDS", "true")
    monkeypatch.setenv("REPORT_FRESHNESS_GUARDS", "false")
    with pytest.raises(RuntimeError):
        gate.enabled()
    with pytest.raises(ValueError):
        get_runtime({"APP_PROCESS_ROLE": "api", "DIRECT_EXPORT_FRESHNESS_GUARDS": "true"})
