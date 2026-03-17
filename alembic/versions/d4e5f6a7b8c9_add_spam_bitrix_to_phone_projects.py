"""add enable_spam_check and enable_bitrix_check to phone_projects

Revision ID: d4e5f6a7b8c9
Revises: a2b3c4d5e6f8
Create Date: 2026-03-16

"""
from alembic import op
import sqlalchemy as sa
from typing import Union, Sequence


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'a2b3c4d5e6f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('phone_projects', sa.Column('enable_spam_check', sa.Boolean(), server_default='true'))
    op.add_column('phone_projects', sa.Column('enable_bitrix_check', sa.Boolean(), server_default='false'))


def downgrade() -> None:
    op.drop_column('phone_projects', 'enable_bitrix_check')
    op.drop_column('phone_projects', 'enable_spam_check')
