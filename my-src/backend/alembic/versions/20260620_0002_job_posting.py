"""Add job posting, skill, and version tables.

Revision ID: 20260620_0002
Revises: 20260619_0001
Create Date: 2026-06-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260620_0002"
down_revision: Union[str, Sequence[str], None] = "20260619_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_posting",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("standardized_title", sa.String(length=120), nullable=True),
        sa.Column("level", sa.String(length=30), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=False),
        sa.Column("company", sa.String(length=150), nullable=True),
        sa.Column("location", sa.String(length=100), nullable=True),
        sa.Column("experience", sa.String(length=50), nullable=True),
        sa.Column("education", sa.String(length=50), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("salary_months", sa.Integer(), nullable=False),
        sa.Column("headcount", sa.Integer(), nullable=False),
        sa.Column("responsibilities", sa.JSON(), nullable=False),
        sa.Column("requirements", sa.JSON(), nullable=False),
        sa.Column("jd_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("urgent", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_posting_title", "job_posting", ["title"])
    op.create_index("ix_job_posting_standardized_title", "job_posting", ["standardized_title"])
    op.create_index("ix_job_posting_location", "job_posting", ["location"])
    op.create_index("ix_job_posting_status", "job_posting", ["status"])
    op.create_index("ix_job_posting_deleted_at", "job_posting", ["deleted_at"])

    op.create_table(
        "job_posting_skill",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(["job_id"], ["job_posting.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "name", "kind", name="uq_job_skill_kind"),
    )
    op.create_index("ix_job_posting_skill_job_id", "job_posting_skill", ["job_id"])
    op.create_index("ix_job_posting_skill_name", "job_posting_skill", ["name"])

    op.create_table(
        "job_posting_version",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("change_reason", sa.String(length=255), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["job_posting.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "version_no", name="uq_job_version_no"),
    )
    op.create_index("ix_job_posting_version_job_id", "job_posting_version", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_job_posting_version_job_id", table_name="job_posting_version")
    op.drop_table("job_posting_version")
    op.drop_index("ix_job_posting_skill_name", table_name="job_posting_skill")
    op.drop_index("ix_job_posting_skill_job_id", table_name="job_posting_skill")
    op.drop_table("job_posting_skill")
    op.drop_index("ix_job_posting_deleted_at", table_name="job_posting")
    op.drop_index("ix_job_posting_status", table_name="job_posting")
    op.drop_index("ix_job_posting_location", table_name="job_posting")
    op.drop_index("ix_job_posting_standardized_title", table_name="job_posting")
    op.drop_index("ix_job_posting_title", table_name="job_posting")
    op.drop_table("job_posting")
