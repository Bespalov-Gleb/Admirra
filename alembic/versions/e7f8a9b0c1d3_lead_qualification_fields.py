"""lead qualification: has_viber, lead_score, qualification_tier, enable_lead_scoring

Revision ID: e7f8a9b0c1d3
Revises: d4e5f6a7b8c9
Create Date: 2026-03-16

"""
from alembic import op
import sqlalchemy as sa
from typing import Union, Sequence


revision: str = "e7f8a9b0c1d3"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("phone_projects", sa.Column("enable_lead_scoring", sa.Boolean(), server_default="false"))
    op.add_column("leads", sa.Column("has_viber", sa.Boolean(), nullable=True))
    op.add_column("leads", sa.Column("lead_score", sa.Integer(), nullable=True))
    op.add_column("leads", sa.Column("qualification_tier", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "qualification_tier")
    op.drop_column("leads", "lead_score")
    op.drop_column("leads", "has_viber")
    op.drop_column("phone_projects", "enable_lead_scoring")
