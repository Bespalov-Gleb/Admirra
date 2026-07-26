"""Индексы под горячие пути чтения и записи статистики.

Часть индексов здесь была объявлена в старых миграциях, но на проде физически
отсутствует: базу пересоздавали через ``Base.metadata.create_all()`` и штамповали
alembic, а всё, что объявлено только в миграции и не продублировано в
``core/models.py``, при таком пересоздании не появляется. Поэтому те же индексы
продублированы в ``__table_args__`` моделей и в ``init_db_with_retry()``.

Все CREATE INDEX выполняются CONCURRENTLY: на боевой базе они не берут
ACCESS EXCLUSIVE и не блокируют синхронизацию.

Revision ID: v3w4x5y6z7a8
Revises: u2v3w4x5y6z
Create Date: 2026-07-26
"""
from typing import Sequence, Union

from alembic import op


revision: str = "v3w4x5y6z7a8"
down_revision: Union[str, Sequence[str], None] = "u2v3w4x5y6z"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (имя индекса, таблица, выражение колонок)
INDEXES: Sequence[tuple[str, str, str]] = (
    # --- Чтение дашборда: фильтр всегда «клиент + диапазон дат» ---
    ("ix_yandex_stats_client_date_campaign", "yandex_stats", "client_id, date, campaign_id"),
    ("ix_vk_stats_client_date_campaign", "vk_stats", "client_id, date, campaign_id"),
    ("ix_avito_stats_client_date_campaign", "avito_stats", "client_id, date, campaign_id"),
    # metrika_goals.client_id вообще не был проиндексирован, хотя таблица —
    # одна из самых читаемых (7.6 млн обращений к индексу по date).
    ("ix_metrika_goals_client_date_goal", "metrika_goals", "client_id, date, goal_id"),
    ("ix_metrika_goals_integration_date", "metrika_goals", "integration_id, date"),

    # --- Внешние ключи без индекса: DELETE кампании/проекта шёл Seq Scan ---
    ("ix_yandex_stats_campaign_id", "yandex_stats", "campaign_id"),
    ("ix_vk_stats_campaign_id", "vk_stats", "campaign_id"),

    # --- Горячий путь записи синхронизации ---
    # Поиск существующей строки при апсерте групп и ключевых слов Директа.
    ("ix_yandex_keywords_lookup", "yandex_keywords", "client_id, date, campaign_name, keyword"),
    ("ix_yandex_groups_lookup", "yandex_groups", "client_id, campaign_id, date, group_id"),
    # Сопоставление кампаний по внешнему id — на каждый синк.
    ("ix_campaigns_integration_external", "campaigns", "integration_id, external_id"),

    # --- Очередь синхронизации: выборка QUEUED в порядке created_at ---
    ("ix_sync_jobs_status_created", "sync_jobs", "status, created_at"),

    # --- Детектор и направления проекта ---
    ("ix_detector_alerts_client_status", "detector_alerts", "client_id, status"),
    ("ix_detector_alerts_owner_status", "detector_alerts", "owner_id, status"),
    ("ix_project_directions_client_position", "project_directions", "client_id, position"),
)


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for name, table, columns in INDEXES:
            op.execute(
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} ON {table} ({columns})"
            )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name, _table, _columns in reversed(INDEXES):
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
