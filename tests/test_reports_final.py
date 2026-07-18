from pathlib import Path
from types import SimpleNamespace
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock

import pytest

from backend_api.reports.scheduler import (
    _delivery_succeeded,
    _retry_channels,
    delivery_status_from_results,
    send_report_delivery,
)
from core.models import ReportChatTarget, ReportDelivery, ReportSchedule
from core.schemas import ReportDeliveryCreate, ReportScheduleCreate


def test_error_metadata_never_counts_as_delivery():
    results = {
        "telegram": False,
        "max": False,
        "email": False,
        "email_error": "SMTP timeout",
        "errors": {"email": "SMTP timeout"},
    }
    assert _delivery_succeeded(results) is False
    assert delivery_status_from_results(results, ["email"], []) == "failed"


def test_all_routes_must_succeed_for_sent_status():
    results = {"telegram": True, "email": False, "targets": {}}
    assert delivery_status_from_results(results, ["telegram", "email"], []) == "partial"
    assert delivery_status_from_results({"telegram": True, "email": True}, ["telegram", "email"], []) == "sent"


def test_target_results_participate_in_overall_status():
    target_ids = ["a", "b"]
    results = {
        "targets": {
            "a": {"ok": True, "kind": "telegram"},
            "b": {"ok": False, "kind": "max"},
        }
    }
    assert delivery_status_from_results(results, [], target_ids) == "partial"


def test_retry_only_selects_failed_routes():
    delivery = SimpleNamespace(
        channels='["telegram", "email"]',
        chat_targets='["a", "b"]',
        delivery_results={
            "telegram": True,
            "email": False,
            "targets": {"a": {"ok": True}, "b": {"ok": False}},
        },
    )
    channels, targets = _retry_channels(delivery, True)
    assert channels == ["email"]
    assert targets == ["b"]


def test_retry_can_select_one_exact_failed_route():
    delivery = SimpleNamespace(
        channels='["telegram", "max", "email"]',
        chat_targets='["a", "b"]',
        delivery_results={
            "telegram": False,
            "max": False,
            "email": False,
            "targets": {"a": {"ok": False}, "b": {"ok": False}},
        },
    )
    channels, targets = _retry_channels(delivery, True, retry_channel="max")
    assert channels == ["max"]
    assert targets == []

    channels, targets = _retry_channels(delivery, True, retry_chat_target_id="b")
    assert channels == []
    assert targets == ["b"]

    channels, targets = _retry_channels(delivery, True, retry_email="client@example.ru")
    assert channels == ["email"]
    assert targets == []


def test_delivery_has_immutable_snapshot_fields():
    columns = ReportDelivery.__table__.columns
    assert {"snapshot_data", "pdf_snapshot", "png_snapshot", "snapshot_created_at"}.issubset(columns.keys())
    assert "uq_report_deliveries_schedule_period" in {
        index.name for index in ReportDelivery.__table__.indexes if index.unique
    }


def test_chat_target_is_scoped_to_project_or_folder():
    columns = ReportChatTarget.__table__.columns
    assert {"client_id", "folder_id", "target_type"}.issubset(columns.keys())


def test_schedule_has_one_scope_unique_indexes():
    index_names = {index.name for index in ReportSchedule.__table__.indexes if index.unique}
    assert {
        "uq_report_schedules_project_scope",
        "uq_report_schedules_folder_scope",
    }.issubset(index_names)


def test_project_email_recipients_are_part_of_schedule_and_delivery_contracts():
    schedule = ReportScheduleCreate(email_recipients=["client@example.ru"])
    delivery = ReportDeliveryCreate(
        start_date="2026-07-01",
        end_date="2026-07-07",
        channels=["email"],
        email_recipients=["client@example.ru"],
    )
    assert str(schedule.email_recipients[0]) == "client@example.ru"
    assert str(delivery.email_recipients[0]) == "client@example.ru"


def test_legacy_account_scheduler_is_not_registered():
    source = Path("backend_api/main.py").read_text(encoding="utf-8")
    assert 'id="report_scheduled_send"' not in source
    assert 'id="report_schedule_rules"' in source


def test_frontend_does_not_call_sent_delivered():
    source = Path("admin-panel-vue-main/admin-panel-vue-main/src/views/Reports/Reports.vue").read_text(encoding="utf-8")
    assert "sent: 'Отправлен'" in source
    assert "partial: 'Частично отправлен'" in source
    assert "Доставлен" not in source


@pytest.mark.asyncio
async def test_partial_retry_does_not_duplicate_successful_channel(monkeypatch):
    from lead_validator.services.telegram import telegram_notifier
    from backend_api.services import max_reports_bot

    telegram_send = AsyncMock(return_value=True)
    max_send = AsyncMock(return_value=True)
    monkeypatch.setattr(telegram_notifier, "send_photo", telegram_send)
    monkeypatch.setattr(max_reports_bot, "send_document", max_send)

    class FakeDb:
        def commit(self):
            return None

    delivery = SimpleNamespace(
        id="delivery-1",
        pdf_snapshot=b"pdf",
        png_snapshot=b"png",
        snapshot_data={"summary": {"expenses": 100, "clicks": 10, "leads": 2}},
        public_token="secret",
        public_expires_at=datetime.now(timezone.utc),
        snapshot_created_at=datetime.now(timezone.utc),
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 7),
        platform="all",
        channels='["telegram", "max"]',
        chat_targets="[]",
        delivery_results={"telegram": True, "max": False, "targets": {}, "errors": {"max": "old"}},
        email_recipients="[]",
        comment=None,
        include_ai_comment=False,
    )
    user = SimpleNamespace(report_telegram_chat_id="tg", report_max_chat_id="mx", report_max_user_id=None)
    results = await send_report_delivery(FakeDb(), delivery, user, retry_failed_only=True)
    telegram_send.assert_not_awaited()
    max_send.assert_awaited_once()
    assert max_send.await_args.args[:2] == (b"png", "report_2026-07-01_2026-07-07.png")
    assert max_send.await_args.kwargs["content_type"] == "image/png"
    assert results["telegram"] is True
    assert results["max"] is True
    assert delivery_status_from_results(results, ["telegram", "max"], []) == "sent"


def test_delivery_comment_normaliser_rejects_markdown_and_short_result():
    from ai.report_generator import _normalise_delivery_comment

    value = _normalise_delivery_comment(
        "**Первый вывод.** | Второй вывод. Третий [вывод](https://example.test)."
    )
    assert value == "Первый вывод. Второй вывод. Третий вывод."
    assert _normalise_delivery_comment("Только один вывод.") == ""
