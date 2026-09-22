"""Verified, bounded full-history snapshot. No Google IO, no caller commits."""
import calendar
import json
from datetime import date, timedelta
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Session
from core import models, consumer_freshness
from core.data_requirements import DataNotReady, requirements
from automation.work_errors import RejectedBeforeExternalIO


class SheetDataNotReady(RejectedBeforeExternalIO):
    pass


def prepare(factory, client_id, owner_id, target=None, *, viewer_id=None):
    from automation.sheets_snapshot import prepare_snapshot, SnapshotLimits, ExportSnapshotLimitExceeded
    from automation.reports import _period_summary
    target = target or date.today()
    today = date.today()
    if target > today:
        raise SheetDataNotReady("Период экспорта ещё не наступил")
    try:
        with factory() as db:
            db.execute(sa.text("SET LOCAL lock_timeout = '1500ms'"))
            db.execute(sa.text("SET LOCAL statement_timeout = '20000ms'"))
            client = db.scalar(sa.select(models.Client).where(models.Client.id == client_id).with_for_update())
            owner = db.get(models.User, owner_id)
            if not client or client.owner_id != owner_id or not owner or not owner.is_active:
                raise DataNotReady("scope_unavailable")
            # Lock all participating writers before reading either history or report keys.
            required = requirements(db, [client_id], target, target)
            allowed = [uuid.UUID(row["integration_id"]) for row in required]
            for model in (models.YandexStats, models.VKStats, models.AvitoStats):
                bound = sa.exists(sa.select(models.Campaign.id).where(
                    models.Campaign.id == model.campaign_id,
                    models.Campaign.integration_id.in_(allowed)))
                if db.scalar(sa.select(sa.exists(sa.select(model.id).where(model.client_id == client_id, ~bound)))):
                    raise DataNotReady("unbound_history")
            goals = models.MetrikaGoals
            if db.scalar(sa.select(sa.exists(sa.select(goals.id).where(goals.client_id == client_id,
                    sa.or_(goals.integration_id.is_(None), ~goals.integration_id.in_(allowed)))))):
                raise DataNotReady("unbound_goal_history")
            for req in required:
                integration = db.get(models.Integration, uuid.UUID(req["integration_id"]))
                selected = json.loads(integration.selected_goals or "[]")
                if integration.primary_goal_id:
                    selected.append(str(integration.primary_goal_id))
                all_goals = integration.platform == models.IntegrationPlatform.YANDEX_METRIKA and not selected
                if not all_goals and db.scalar(sa.select(sa.exists(sa.select(goals.id).where(
                        goals.client_id == client_id, goals.integration_id == integration.id,
                        ~goals.goal_id.in_([str(g) for g in selected]))))):
                    raise DataNotReady("unverified_goal_history")
            snapshot = prepare_snapshot(client_id, db)
            weeks = {date.fromisoformat(row[0]) for row in snapshot["Weekly Reports"][1:]}
            months = {(int(row[0]), int(row[1])) for row in snapshot["Monthly Report"][1:]}
            weeks.add(target - timedelta(days=target.weekday()))
            months.add((target.year, target.month))
            dates = [date.fromisoformat(row[0]) for name in ("Raw Data", "Goals") for row in snapshot[name][1:]]
            # Derive a continuous history from facts as well as legacy report
            # keys: otherwise a read-only export would forget last week's new
            # report when the calendar moves to the next week.
            anchors = dates + list(weeks) + [date(y, m, 1) for y, m in months]
            first_anchor, last_anchor = min(anchors), max(anchors + [target])
            week = first_anchor - timedelta(days=first_anchor.weekday())
            while week <= last_anchor:
                weeks.add(week)
                if len(weeks) + len(months) > 256:
                    raise DataNotReady("report_history_limit")
                week += timedelta(days=7)
            month = first_anchor.replace(day=1)
            while month <= last_anchor:
                months.add((month.year, month.month))
                if len(weeks) + len(months) > 256:
                    raise DataNotReady("report_history_limit")
                month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
            if len(weeks) + len(months) > 256:
                raise DataNotReady("report_history_limit")
            windows = [(d, d + timedelta(days=6)) for d in weeks]
            windows += [(date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])) for y, m in months]
            if any(d > today for d in dates) or any(a > today for a, _ in windows):
                raise DataNotReady("future_history")
            first = min([a for a, _ in windows] + dates)
            last = max([min(b, today) for _, b in windows] + dates)
            proof = consumer_freshness.verify(db, [client_id], first, last)
            # Stored report totals may predate the latest source revision. Rebuild
            # detached rows, not database aggregates that legacy helpers commit.
            def values(a, b):
                value = _period_summary(db, client_id, a, min(b, today))
                return [value[k] for k in ("total_cost", "total_clicks", "total_conversions", "avg_cpc", "avg_cpa")]
            snapshot["Weekly Reports"] = [snapshot["Weekly Reports"][0]] + [
                [str(d), str(d + timedelta(days=6)), *values(d, d + timedelta(days=6))] for d in sorted(weeks)]
            snapshot["Monthly Report"] = [snapshot["Monthly Report"][0]] + [
                [y, m, *values(date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1]))] for y, m in sorted(months)]
            limits = SnapshotLimits.configured()
            if (sum(len(rows) - 1 for rows in snapshot.values()) > limits.max_rows
                    or len(json.dumps(snapshot, allow_nan=False).encode()) > limits.max_bytes):
                raise ExportSnapshotLimitExceeded("Полная таблица превышает лимит экспорта")
            return client.spreadsheet_id, snapshot, proof
    except DataNotReady as exc:
        from automation.consumer_refresh import enqueue_error
        error = SheetDataNotReady("Полная история ещё не подтверждена синхронизацией; таблица не изменена")
        with factory() as db:
            error.data_readiness = enqueue_error(db, "sheets", viewer_id or owner_id, exc)
        raise error from exc


def recheck(factory, client_id, owner_id, spreadsheet_id, proof):
    try:
        with factory() as db:
            current = consumer_freshness.verify(db, [client_id], date.fromisoformat(proof["date_from"]),
                                                date.fromisoformat(proof["date_to"]))
            client = db.get(models.Client, client_id)
            owner = db.get(models.User, owner_id)
            if (not owner or not owner.is_active or client.owner_id != owner_id
                    or client.spreadsheet_id != spreadsheet_id or current["revision"] != proof["revision"]):
                raise DataNotReady("source_changed")
    except DataNotReady as exc:
        raise SheetDataNotReady("Данные или настройки изменились; повторите подготовку таблицы") from exc


def session_factory(db):
    bind = db.get_bind()
    if not isinstance(bind, sa.engine.Engine):
        raise SheetDataNotReady("Для экспорта требуется отдельная транзакция чтения")
    return lambda: Session(bind=bind, autoflush=False)
