"""Add frozen historical trend baseline snapshots.

Revision ID: 20260808_0018
Revises: 20260801_0017
"""

from alembic import op
import sqlalchemy as sa


revision = "20260808_0018"
down_revision = "20260801_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_baseline_snapshot",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("source_summary", sa.JSON(), nullable=False),
        sa.Column("quality_summary", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version", name="uq_analysis_baseline_snapshot_version"),
    )
    op.create_index("ix_analysis_baseline_snapshot_status", "analysis_baseline_snapshot", ["status"])
    op.create_index("ix_analysis_baseline_snapshot_created_by", "analysis_baseline_snapshot", ["created_by"])

    op.create_table(
        "analysis_baseline_skill",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("baseline_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("segment_key", sa.String(length=160), nullable=False, server_default="all"),
        sa.Column("cluster_count", sa.Integer(), nullable=False),
        sa.Column("company_count", sa.Integer(), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("active_period_count", sa.Integer(), nullable=False),
        sa.Column("prevalence", sa.Float(), nullable=False),
        sa.Column("maturity_stage", sa.String(length=24), nullable=False),
        sa.Column("evidence_summary", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["baseline_id"], ["analysis_baseline_snapshot.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skill.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("baseline_id", "skill_id", "segment_key", name="uq_analysis_baseline_skill_segment"),
    )
    for column in ("baseline_id", "skill_id", "maturity_stage"):
        op.create_index(f"ix_analysis_baseline_skill_{column}", "analysis_baseline_skill", [column])


def downgrade() -> None:
    for column in ("maturity_stage", "skill_id", "baseline_id"):
        op.drop_index(f"ix_analysis_baseline_skill_{column}", table_name="analysis_baseline_skill")
    op.drop_table("analysis_baseline_skill")
    op.drop_index("ix_analysis_baseline_snapshot_created_by", table_name="analysis_baseline_snapshot")
    op.drop_index("ix_analysis_baseline_snapshot_status", table_name="analysis_baseline_snapshot")
    op.drop_table("analysis_baseline_snapshot")
