from datetime import date
import uuid

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from core import models
from core.config import get_config


def _enum_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value or "")


def is_project_paused(client: models.Client | None) -> bool:
    return _enum_value(getattr(client, "status", "")).upper() == models.ClientStatus.PAUSED.value


def get_integration_state(client: models.Client | None) -> str:
    integrations = list(getattr(client, "integrations", None) or [])
    if not integrations:
        return "A"
    all_syncing = all(
        _enum_value(getattr(integration, "sync_status", "")).upper() in {"PENDING", "NEVER"}
        for integration in integrations
    )
    return "B" if all_syncing else "C"


def get_detector_state(client: models.Client | None) -> dict:
    actual_start = getattr(client, "actual_start_date", None)
    if not getattr(client, "detector_enabled", False):
        status = "disabled"
    elif is_project_paused(client):
        status = "paused"
    elif not actual_start:
        status = "waiting_for_data"
    else:
        days_since_start = max((date.today() - actual_start).days + 1, 0)
        status = "ready" if days_since_start >= get_config().detector.warmup_days else "warming_up"

    days_since_start = None
    if actual_start:
        days_since_start = max((date.today() - actual_start).days + 1, 0)

    messages = {
        "disabled": "Детектор выключен.",
        "paused": "Проект на паузе, детектор остановлен.",
        "waiting_for_data": "Ждём первые данные интеграций для запуска прогрева.",
        "warming_up": f"Идёт прогрев детектора: нужно {get_config().detector.warmup_days} дней данных.",
        "ready": "Детектор готов к работе.",
    }
    return {
        "status": status,
        "actual_start_date": str(actual_start) if actual_start else None,
        "days_since_start": days_since_start,
        "warmup_days": get_config().detector.warmup_days,
        "message": messages[status],
    }


def find_actual_start_date(db: Session, client_id: uuid.UUID):
    yandex_date = (
        db.query(func.min(models.YandexStats.date))
        .filter(
            models.YandexStats.client_id == client_id,
            or_(
                models.YandexStats.impressions > 0,
                models.YandexStats.clicks > 0,
                models.YandexStats.cost > 0,
                models.YandexStats.conversions > 0,
            ),
        )
        .scalar()
    )
    vk_date = (
        db.query(func.min(models.VKStats.date))
        .filter(
            models.VKStats.client_id == client_id,
            or_(
                models.VKStats.impressions > 0,
                models.VKStats.clicks > 0,
                models.VKStats.cost > 0,
                models.VKStats.conversions > 0,
            ),
        )
        .scalar()
    )
    metrika_date = (
        db.query(func.min(models.MetrikaGoals.date))
        .filter(
            models.MetrikaGoals.client_id == client_id,
            models.MetrikaGoals.conversion_count > 0,
        )
        .scalar()
    )
    dates = [value for value in (yandex_date, vk_date, metrika_date) if value]
    return min(dates) if dates else None


def update_actual_start_date(db: Session, client_id: uuid.UUID):
    actual_start = find_actual_start_date(db, client_id)
    if not actual_start:
        return None
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if client and client.actual_start_date != actual_start:
        client.actual_start_date = actual_start
        db.flush()
    return actual_start
