"""Add standard jobs and graph synchronization audit tables.

Revision ID: 20260620_0004
Revises: 20260620_0003
Create Date: 2026-06-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260620_0004"
down_revision: Union[str, Sequence[str], None] = "20260620_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "standard_job",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("canonical_key", sa.String(220), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("stack", sa.String(30), nullable=False),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("canonical_key"),
    )
    op.create_index("ix_standard_job_stack", "standard_job", ["stack"])
    op.create_index("ix_standard_job_level", "standard_job", ["level"])
    op.create_index("ix_standard_job_status", "standard_job", ["status"])
    op.create_table(
        "standard_job_source",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("standard_job_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("original_title", sa.String(255), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["standard_job_id"], ["standard_job.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_type", "source_id", name="uq_standard_job_source"),
    )
    op.create_index("ix_standard_job_source_standard_job_id", "standard_job_source", ["standard_job_id"])
    op.create_index("ix_standard_job_source_source_type", "standard_job_source", ["source_type"])
    op.create_table(
        "graph_snapshot",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("version", sa.String(80), nullable=False),
        sa.Column("snapshot_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("node_count", sa.Integer(), nullable=False),
        sa.Column("edge_count", sa.Integer(), nullable=False),
        sa.Column("fact_count", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version"),
    )
    op.create_index("ix_graph_snapshot_status", "graph_snapshot", ["status"])
    op.create_table(
        "graph_sync_batch",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("async_task_id", sa.String(36), nullable=True),
        sa.Column("snapshot_id", sa.String(36), nullable=False),
        sa.Column("sync_mode", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("node_count", sa.Integer(), nullable=False),
        sa.Column("edge_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["async_task_id"], ["async_task.id"]),
        sa.ForeignKeyConstraint(["snapshot_id"], ["graph_snapshot.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("async_task_id"),
    )
    op.create_index("ix_graph_sync_batch_snapshot_id", "graph_sync_batch", ["snapshot_id"])
    op.create_index("ix_graph_sync_batch_status", "graph_sync_batch", ["status"])
    op.create_table(
        "graph_enrichment_candidate",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("snapshot_id", sa.String(36), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("candidate_data", sa.JSON(), nullable=False),
        sa.Column("evidence_source_ids", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("verification_status", sa.String(20), nullable=False),
        sa.Column("agent_run_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_run.id"]),
        sa.ForeignKeyConstraint(["skill_id"], ["skill.id"]),
        sa.ForeignKeyConstraint(["snapshot_id"], ["graph_snapshot.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_id", "skill_id", name="uq_graph_candidate_snapshot_skill"),
    )
    op.create_index("ix_graph_candidate_snapshot_id", "graph_enrichment_candidate", ["snapshot_id"])
    op.create_index("ix_graph_candidate_skill_id", "graph_enrichment_candidate", ["skill_id"])
    op.create_index("ix_graph_candidate_status", "graph_enrichment_candidate", ["verification_status"])
    op.execute("UPDATE async_task SET status='queued' WHERE status='pending'")
    op.execute("UPDATE async_task SET status='succeeded' WHERE status='success'")


def downgrade() -> None:
    op.drop_table("graph_enrichment_candidate")
    op.drop_table("graph_sync_batch")
    op.drop_table("graph_snapshot")
    op.drop_table("standard_job_source")
    op.drop_table("standard_job")
