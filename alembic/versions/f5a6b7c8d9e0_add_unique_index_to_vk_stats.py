"""add_unique_index_to_vk_stats

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-02-01 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5a6b7c8d9e0'
down_revision: Union[str, Sequence[str], None] = 'e4f5a6b7c8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unique index on (client_id, campaign_id, date) to vk_stats table to prevent duplicates."""
    # CRITICAL: Сначала удаляем дубликаты, оставляя только одну запись для каждой комбинации
    # Это необходимо, так как уникальный индекс не может быть создан на таблице с дубликатами
    # 
    # Удаляем все дубликаты, оставляя запись с минимальным id для каждой комбинации
    op.execute("""
        DELETE FROM vk_stats
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM vk_stats
            WHERE campaign_id IS NOT NULL
            GROUP BY client_id, campaign_id, date
        )
        AND campaign_id IS NOT NULL
    """)
    
    # Также удаляем дубликаты для записей с NULL campaign_id (если есть)
    # Оставляем только одну запись для каждой комбинации (client_id, date) где campaign_id IS NULL
    op.execute("""
        DELETE FROM vk_stats
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM vk_stats
            WHERE campaign_id IS NULL
            GROUP BY client_id, date
        )
        AND campaign_id IS NULL
    """)
    
    # CRITICAL: Теперь создаем уникальный индекс для предотвращения дубликатов в будущем
    # Это гарантирует, что для каждой комбинации (client_id, campaign_id, date) будет только одна запись
    # 
    # Примечание: В PostgreSQL уникальный индекс с NULL значениями работает так, что NULL != NULL,
    # поэтому для записей с NULL campaign_id могут быть дубликаты, но это редкость
    # В sync.py campaign_id всегда устанавливается, так что для новых записей дубликаты будут блокироваться
    op.create_index(
        'uq_vk_stats_client_campaign_date',
        'vk_stats',
        ['client_id', 'campaign_id', 'date'],
        unique=True
    )


def downgrade() -> None:
    """Remove unique index from vk_stats table."""
    op.drop_index('uq_vk_stats_client_campaign_date', table_name='vk_stats')

