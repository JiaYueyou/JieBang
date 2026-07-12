"""add persisted resume matching and evidence tables

Revision ID: 20260712_0006
Revises: 20260710_0005
"""

from alembic import op
import sqlalchemy as sa

revision = "20260712_0006"
down_revision = "20260710_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resume",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("current_position", sa.String(120)),
        sa.Column("experience", sa.String(100)),
        sa.Column("education", sa.String(100)),
        sa.Column("department", sa.String(100)),
        sa.Column("company", sa.String(150)),
        sa.Column("location", sa.String(100)),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False, unique=True),
        sa.Column("content_type", sa.String(120)),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("deleted_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("created_by", "content_hash", name="uq_resume_owner_hash"),
    )
    for column in ("content_hash", "status", "created_by", "deleted_at"):
        op.create_index(f"ix_resume_{column}", "resume", [column])
    op.create_table(
        "resume_parse_result",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resume_id", sa.Integer(), sa.ForeignKey("resume.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("parsed_text", sa.Text(), nullable=False),
        sa.Column("profile", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("parser_version", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "resume_skill",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resume_id", sa.Integer(), sa.ForeignKey("resume.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("canonical_key", sa.String(120), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence_text", sa.Text(), nullable=False),
        sa.Column("extraction_method", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("resume_id", "canonical_key", name="uq_resume_skill_key"),
    )
    op.create_index("ix_resume_skill_resume_id", "resume_skill", ["resume_id"])
    op.create_table(
        "match_record",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resume_id", sa.Integer(), sa.ForeignKey("resume.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("job_posting.id", ondelete="CASCADE"), nullable=False),
        sa.Column("algorithm_version", sa.String(50), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("matched_skills", sa.JSON(), nullable=False),
        sa.Column("missing_skills", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("explanation_agent_run_id", sa.String(36), sa.ForeignKey("agent_run.id")),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("resume_id", "job_id", "algorithm_version", name="uq_match_snapshot"),
    )
    for column in ("resume_id", "job_id", "status"):
        op.create_index(f"ix_match_record_{column}", "match_record", [column])
    op.create_table(
        "match_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("match_record.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_type", sa.String(30), nullable=False),
        sa.Column("skill_name", sa.String(100), nullable=False),
        sa.Column("evidence_text", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_match_evidence_match_id", "match_evidence", ["match_id"])


def downgrade() -> None:
    op.drop_table("match_evidence")
    op.drop_table("match_record")
    op.drop_table("resume_skill")
    op.drop_table("resume_parse_result")
    op.drop_table("resume")
