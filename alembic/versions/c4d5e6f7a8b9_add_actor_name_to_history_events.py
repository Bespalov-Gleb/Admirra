"""add actor_name to history_events

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-05-15

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, None] = 'b3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('history_events',
        sa.Column('actor_name', sa.String(255), nullable=True)
    )
    op.execute("""
        UPDATE history_events he
        SET actor_name = COALESCE(
            NULLIF(TRIM(COALESCE(u.first_name, '') || ' ' || COALESCE(u.last_name, '')), ''),
            he.actor_email,
            u.email
        )
        FROM users u
        WHERE he.actor_user_id = u.id
    """)
    op.execute("""
        UPDATE history_events
        SET actor_name = actor_email
        WHERE actor_name IS NULL
          AND actor_email IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_column('history_events', 'actor_name')
