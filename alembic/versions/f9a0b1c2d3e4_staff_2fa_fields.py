"""Staff TOTP 2FA fields on users

Revision ID: f9a0b1c2d3e4
Revises: f8a9b0c1d2e3
Create Date: 2026-05-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


revision: str = "f9a0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "f8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("staff_totp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("staff_totp_secret_encrypted", sa.String(), nullable=True))
    op.add_column("users", sa.Column("staff_totp_pending_secret_encrypted", sa.String(), nullable=True))
    op.add_column("users", sa.Column("staff_recovery_codes_hashed", JSON, nullable=True))


def downgrade() -> None:
    op.drop_column("users", "staff_recovery_codes_hashed")
    op.drop_column("users", "staff_totp_pending_secret_encrypted")
    op.drop_column("users", "staff_totp_secret_encrypted")
    op.drop_column("users", "staff_totp_enabled")
