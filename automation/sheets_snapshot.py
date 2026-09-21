"""Bounded SQL-only preparation for the scoped Sheets export worker.

Never truncate history into a successful export. The complete snapshot must fit
before the Google SDK is constructed or any destination is cleared/written.
Legacy interactive exports keep their existing interfaces.
"""
from dataclasses import dataclass
from contextlib import closing
import json

import sqlalchemy as sa

from core import models
from core.runtime import env_int
from automation.work_errors import RejectedBeforeExternalIO

FETCH_ROWS = 128
MAX_CELL_CHARS = 16_384


class ExportSnapshotLimitExceeded(RejectedBeforeExternalIO):
    """The complete history cannot be exported within the worker's budget."""


@dataclass(frozen=True)
class SnapshotLimits:
    max_rows: int = 50_000
    max_bytes: int = 8 * 1024 * 1024

    def __post_init__(self):
        if type(self.max_rows) is not int or not 1 <= self.max_rows <= 200_000:
            raise ValueError("Invalid Sheets snapshot row limit")
        if type(self.max_bytes) is not int or not 1 <= self.max_bytes <= 32 * 1024 * 1024:
            raise ValueError("Invalid Sheets snapshot byte limit")

    @classmethod
    def configured(cls):
        return cls(
            max_rows=env_int("SHEETS_SNAPSHOT_MAX_ROWS", 50_000, 1, 200_000),
            max_bytes=env_int("SHEETS_SNAPSHOT_MAX_BYTES", 8 * 1024 * 1024, 1, 32 * 1024 * 1024),
        )


def _text(column):
    # Bound even the DB driver's fetch batch. A giant text value never reaches
    # Python: SQL returns a failure marker, not a silently shortened cell.
    oversized = sa.func.length(column) > MAX_CELL_CHARS
    return sa.case((oversized, None), else_=column), oversized


def _stream(db, query):
    result = db.execute(query.execution_options(yield_per=FETCH_ROWS))
    try:
        yield from result
    finally:
        result.close()


def _raw(db, client_id):
    for model, platform in ((models.YandexStats, "Yandex Direct"), (models.VKStats, "VK Ads"),
                            (models.AvitoStats, "Avito")):
        name, too_long = _text(model.campaign_name)
        query = sa.select(model.date, name, model.impressions, model.clicks, model.cost,
                          model.conversions, too_long).where(model.client_id == client_id).order_by(
                              model.date, model.campaign_name, model.id)
        with closing(_stream(db, query)) as records:
            for day, campaign, impressions, clicks, cost, conversions, invalid in records:
                if invalid:
                    raise ExportSnapshotLimitExceeded("Название кампании превышает лимит ячейки экспорта")
                yield [str(day), platform, campaign or "", int(impressions or 0), int(clicks or 0),
                       float(cost or 0), int(conversions or 0)]


def _reports(db, client_id, *, monthly):
    model = models.MonthlyReport if monthly else models.WeeklyReport
    dates = (model.year, model.month) if monthly else (model.week_start, model.week_end)
    query = sa.select(*dates, model.total_cost, model.total_clicks, model.total_conversions,
                      model.avg_cpc, model.avg_cpa).where(model.client_id == client_id).order_by(*dates, model.id)
    with closing(_stream(db, query)) as records:
        for first, second, cost, clicks, leads, cpc, cpa in records:
            yield [int(first or 0) if monthly else str(first), int(second or 0) if monthly else str(second),
                   float(cost or 0), int(clicks or 0), int(leads or 0), float(cpc or 0), float(cpa or 0)]


def _goals(db, client_id):
    model = models.MetrikaGoals
    name, long_name = _text(model.goal_name)
    goal, long_id = _text(model.goal_id)
    query = sa.select(model.date, goal, name, model.conversion_count, model.integration_id,
                      sa.or_(long_name, long_id)).where(model.client_id == client_id).order_by(
                          model.date, model.goal_name, model.id)
    with closing(_stream(db, query)) as records:
        for day, goal_id, goal_name, count, integration, invalid in records:
            if invalid:
                raise ExportSnapshotLimitExceeded("Цель превышает лимит ячейки экспорта")
            yield [str(day), goal_id, goal_name or "", int(count or 0), str(integration) if integration else ""]


def prepare_snapshot(client_id, db, *, limits=None):
    limits = limits or SnapshotLimits.configured()
    sources = (
        ("Raw Data", ["Date", "Platform", "Campaign", "Impressions", "Clicks", "Cost", "Conversions"], _raw(db, client_id)),
        ("Weekly Reports", ["Week Start", "Week End", "Cost", "Clicks", "Conversions", "CPC", "CPA"], _reports(db, client_id, monthly=False)),
        ("Monthly Report", ["Year", "Month", "Cost", "Clicks", "Conversions", "CPC", "CPA"], _reports(db, client_id, monthly=True)),
        ("Goals", ["Date", "Goal ID", "Goal Name", "Conversions", "Integration ID"], _goals(db, client_id)),
    )
    snapshot, rows, size = {}, 0, 2
    try:
        for name, header, source in sources:
            snapshot[name] = [header]
            # Conservative serialized JSON budget, including headers/keys and
            # ASCII escaping used by the SDK. Row cap bounds Python object cost.
            size += len(json.dumps(name)) + len(json.dumps(header)) + 8
            if size > limits.max_bytes:
                raise ExportSnapshotLimitExceeded("Превышен лимит размера экспорта Google Sheets")
            for row in source:
                rows += 1
                size += len(json.dumps(row, allow_nan=False)) + 2
                if rows > limits.max_rows or size > limits.max_bytes:
                    raise ExportSnapshotLimitExceeded("История проекта превышает лимит полного экспорта Google Sheets")
                snapshot[name].append(row)
    finally:
        # Release streaming cursors on limit/invalid data and on success.
        for _, _, source in sources:
            source.close()
    return snapshot
