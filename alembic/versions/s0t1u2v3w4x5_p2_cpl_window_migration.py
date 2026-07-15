"""Close open P-2 alerts computed by the old sliding-window rule.

Мини-ТЗ «CPL в проверке P-2 — накопительный за период»: при релизе открытые
P-2 алерты закрываются системно («закрыт миграцией», не «вернулся в норму»);
ближайший прогон детектора пересоздаст их по накопительному правилу.

Revision ID: s0t1u2v3w4x5
Revises: r9s0t1u2v3w4
Create Date: 2026-07-15
"""
from typing import Sequence, Union

from alembic import op


revision: str = "s0t1u2v3w4x5"
down_revision: Union[str, Sequence[str], None] = "r9s0t1u2v3w4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE detector_alerts
        SET status = 'closed',
            closed_at = now(),
            meta = (coalesce(meta::jsonb, '{}'::jsonb) || '{"closed_by": "p2_cpl_migration"}'::jsonb)::json
        WHERE status = 'open'
          AND (mode = 'plan_cpl' OR (mode = 'plan' AND meta::text LIKE '%P-2%'))
        """
    )


def downgrade() -> None:
    # Закрытие алертов необратимо по смыслу: старое правило расчёта удалено.
    pass
