"""Add standard skill extraction pipeline tables.

Revision ID: 20260620_0003
Revises: 20260620_0002
Create Date: 2026-06-20
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "20260620_0003"
down_revision: Union[str, Sequence[str], None] = "20260620_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "skill",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("canonical_name", sa.String(100), nullable=False),
        sa.Column("canonical_key", sa.String(120), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("graph_node_id", sa.String(120), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("canonical_key"),
        sa.UniqueConstraint("graph_node_id"),
    )
    op.create_index("ix_skill_category", "skill", ["category"])
    op.create_table(
        "source_document",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("url", sa.String(1000), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("content_fingerprint", sa.String(64), nullable=False),
        sa.Column("content_summary", sa.Text(), nullable=False),
        sa.Column("source_meta", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_fingerprint"),
    )
    op.create_index("ix_source_document_source", "source_document", ["source"])
    op.create_table(
        "raw_job_record",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_document_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("standardized_title", sa.String(255), nullable=True),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("salary_text", sa.String(100), nullable=True),
        sa.Column("experience_text", sa.String(100), nullable=True),
        sa.Column("education_text", sa.String(100), nullable=True),
        sa.Column("jd_text", sa.Text(), nullable=False),
        sa.Column("responsibilities", sa.Text(), nullable=False),
        sa.Column("requirements", sa.Text(), nullable=False),
        sa.Column("keywords", sa.Text(), nullable=False),
        sa.Column("posted_at_text", sa.String(100), nullable=True),
        sa.Column("crawled_at_text", sa.String(100), nullable=True),
        sa.Column("dedup_status", sa.String(20), nullable=False),
        sa.Column("normalized_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["source_document_id"], ["source_document.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_document_id"),
    )
    op.create_index("ix_raw_job_record_title", "raw_job_record", ["title"])
    op.create_index("ix_raw_job_record_standardized_title", "raw_job_record", ["standardized_title"])
    op.create_table(
        "agent_run",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(50), nullable=False),
        sa.Column("input_summary", sa.Text(), nullable=False),
        sa.Column("structured_output", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_run_agent_type", "agent_run", ["agent_type"])
    op.create_index("ix_agent_run_status", "agent_run", ["status"])
    op.create_table(
        "async_task",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("task_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("request_data", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_async_task_task_type", "async_task", ["task_type"])
    op.create_index("ix_async_task_status", "async_task", ["status"])
    op.create_table(
        "job_skill_fact",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("raw_job_record_id", sa.Integer(), nullable=True),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("importance", sa.Float(), nullable=False),
        sa.Column("frequency", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence_text", sa.Text(), nullable=False),
        sa.Column("verification_status", sa.String(20), nullable=False),
        sa.Column("extraction_method", sa.String(20), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("agent_run_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_run.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["job_posting.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["raw_job_record_id"], ["raw_job_record.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skill.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "skill_id", name="uq_job_skill_fact"),
        sa.UniqueConstraint("raw_job_record_id", "skill_id", name="uq_raw_job_skill_fact"),
    )
    op.create_index("ix_job_skill_fact_job_id", "job_skill_fact", ["job_id"])
    op.create_index("ix_job_skill_fact_raw_job_record_id", "job_skill_fact", ["raw_job_record_id"])
    op.create_index("ix_job_skill_fact_skill_id", "job_skill_fact", ["skill_id"])
    op.create_index("ix_job_skill_fact_verification_status", "job_skill_fact", ["verification_status"])


def downgrade() -> None:
    op.drop_table("job_skill_fact")
    op.drop_table("async_task")
    op.drop_table("agent_run")
    op.drop_table("raw_job_record")
    op.drop_table("source_document")
    op.drop_table("skill")
