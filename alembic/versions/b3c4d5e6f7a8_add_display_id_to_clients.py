"""add display_id to clients

Revision ID: b3c4d5e6f7a8
Revises: a8b9c0d1e2f3
Create Date: 2026-05-14

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, None] = 'a8b9c0d1e2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS clients_display_id_seq START 100001")
    op.add_column('clients',
        sa.Column('display_id', sa.Integer(), nullable=True,
                  server_default=sa.text("nextval('clients_display_id_seq')"))
    )
    op.execute("UPDATE clients SET display_id = nextval('clients_display_id_seq') WHERE display_id IS NULL")
    op.alter_column('clients', 'display_id', nullable=False)
    op.create_unique_constraint('uq_clients_display_id', 'clients', ['display_id'])


def downgrade() -> None:
    op.drop_constraint('uq_clients_display_id', 'clients', type_='unique')
    op.drop_column('clients', 'display_id')
    op.execute("DROP SEQUENCE IF EXISTS clients_display_id_seq")
