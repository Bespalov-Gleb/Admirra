"""Add CAPTCHA fields to PhoneProject and merge heads

Revision ID: add_captcha_fields
Revises: f5a6b7c8d9e0, 3f9c7a1b2d34
Create Date: 2026-02-09

"""
from alembic import op
import sqlalchemy as sa
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = 'add_captcha_fields'
down_revision: Union[str, Sequence[str], None] = ('f5a6b7c8d9e0', '3f9c7a1b2d34')  # Объединяем две головы
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Добавляем новые колонки для CAPTCHA
    op.add_column('phone_projects', sa.Column('captcha_provider', sa.String(), nullable=True, server_default='none'))
    op.add_column('phone_projects', sa.Column('captcha_site_key', sa.String(), nullable=True))
    op.add_column('phone_projects', sa.Column('captcha_secret_key', sa.String(), nullable=True))


def downgrade():
    # Удаляем колонки при откате миграции
    op.drop_column('phone_projects', 'captcha_secret_key')
    op.drop_column('phone_projects', 'captcha_site_key')
    op.drop_column('phone_projects', 'captcha_provider')
