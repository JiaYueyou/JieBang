"""add persistent automatic pipeline runs

Revision ID: 20260809_0020
Revises: 20260809_0019
"""

from alembic import op
import sqlalchemy as sa


revision = "20260809_0020"
down_revision = "20260809_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pipeline_run",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("trigger", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("stage", sa.String(length=40), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("requested_sources", sa.JSON(), nullable=False),
        sa.Column("stage_results", sa.JSON(), nullable=False),
        sa.Column("quality_summary", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("requested_by", sa.Integer(), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    for column in (
        "trigger", "status", "stage", "requested_by", "scheduled_for",
        "heartbeat_at", "created_at",
    ):
        op.create_index(f"ix_pipeline_run_{column}", "pipeline_run", [column])


def downgrade() -> None:
    op.drop_table("pipeline_run")
