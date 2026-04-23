"""add stats performance indexes

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-03-31
"""

from alembic import op
from typing import Sequence, Union


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_vk_stats_client_date_campaign", "vk_stats", ["client_id", "date", "campaign_id"], unique=False)
    op.create_index("ix_yandex_stats_client_date_campaign", "yandex_stats", ["client_id", "date", "campaign_id"], unique=False)
    op.create_index("ix_campaigns_integration_external", "campaigns", ["integration_id", "external_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_campaigns_integration_external", table_name="campaigns")
    op.drop_index("ix_yandex_stats_client_date_campaign", table_name="yandex_stats")
    op.drop_index("ix_vk_stats_client_date_campaign", table_name="vk_stats")

