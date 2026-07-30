"""Agent audit status and started time.

Revision ID: 20260730_0011
Revises: 20260729_0010
"""

from alembic import op
import sqlalchemy as sa


revision = "20260730_0011"
down_revision = "20260729_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_run",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE agent_run SET status = 'succeeded' WHERE status = 'success'")
    op.execute("UPDATE async_task SET status = 'succeeded' WHERE status = 'success'")
    op.add_column(
        "async_task",
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
    )
    op.create_unique_constraint(
        "uq_async_task_idempotency",
        "async_task",
        ["created_by", "task_type", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_async_task_idempotency", "async_task", type_="unique"
    )
    op.drop_column("async_task", "idempotency_key")
    op.drop_column("agent_run", "started_at")
