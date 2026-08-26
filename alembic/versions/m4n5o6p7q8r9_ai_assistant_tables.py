"""ai assistant conversations and messages

Revision ID: m4n5o6p7q8r9
Revises: l3m4n5o6p7q8
Create Date: 2026-08-25 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "m4n5o6p7q8r9"
down_revision = "l3m4n5o6p7q8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Идемпотентно: init_db_with_retry() параллельно создаёт таблицы через
    # Base.metadata.create_all() (они объявлены в core/models.py), поэтому к
    # моменту миграции таблицы/индексы могут уже существовать — не падаем.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    def _indexes(table: str) -> set:
        return {ix["name"] for ix in inspector.get_indexes(table)} if table in existing_tables else set()

    if "ai_conversations" not in existing_tables:
        op.create_table(
            "ai_conversations",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("title", sa.String(length=200), nullable=True),
            sa.Column("model", sa.String(length=64), nullable=True),
            sa.Column("effort", sa.String(length=16), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    conv_ix = _indexes("ai_conversations")
    for name, cols in (
        ("ix_ai_conversations_user_id", ["user_id"]),
        ("ix_ai_conversations_client_id", ["client_id"]),
        ("ix_ai_conversations_created_at", ["created_at"]),
    ):
        if name not in conv_ix:
            op.create_index(name, "ai_conversations", cols)

    if "ai_messages" not in existing_tables:
        op.create_table(
            "ai_messages",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("role", sa.String(length=16), nullable=False),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column("tool_calls", sa.JSON(), nullable=True),
            sa.Column("tool_call_id", sa.String(length=128), nullable=True),
            sa.Column("name", sa.String(length=96), nullable=True),
            sa.Column("tokens_in", sa.Integer(), nullable=True),
            sa.Column("tokens_out", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    msg_ix = _indexes("ai_messages")
    for name, cols in (
        ("ix_ai_messages_conversation_id", ["conversation_id"]),
        ("ix_ai_messages_created_at", ["created_at"]),
    ):
        if name not in msg_ix:
            op.create_index(name, "ai_messages", cols)


def downgrade() -> None:
    op.drop_index("ix_ai_messages_created_at", table_name="ai_messages")
    op.drop_index("ix_ai_messages_conversation_id", table_name="ai_messages")
    op.drop_table("ai_messages")
    op.drop_index("ix_ai_conversations_created_at", table_name="ai_conversations")
    op.drop_index("ix_ai_conversations_client_id", table_name="ai_conversations")
    op.drop_index("ix_ai_conversations_user_id", table_name="ai_conversations")
    op.drop_table("ai_conversations")
