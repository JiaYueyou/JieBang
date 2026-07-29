"""Add minimal human-review audit fields to skill facts.

Revision ID: 20260729_0010
Revises: 20260721_0009
Create Date: 2026-07-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260729_0010"
down_revision: Union[str, Sequence[str], None] = "20260721_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "job_skill_fact",
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
    )
    op.add_column(
        "job_skill_fact",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "job_skill_fact",
        sa.Column("review_note", sa.String(length=500), nullable=True),
    )
    op.create_foreign_key(
        "fk_job_skill_fact_reviewed_by_user",
        "job_skill_fact",
        "user",
        ["reviewed_by"],
        ["id"],
    )
    op.create_index(
        "ix_job_skill_fact_reviewed_by",
        "job_skill_fact",
        ["reviewed_by"],
    )


def downgrade() -> None:
    op.drop_index("ix_job_skill_fact_reviewed_by", table_name="job_skill_fact")
    op.drop_constraint(
        "fk_job_skill_fact_reviewed_by_user",
        "job_skill_fact",
        type_="foreignkey",
    )
    op.drop_column("job_skill_fact", "review_note")
    op.drop_column("job_skill_fact", "reviewed_at")
    op.drop_column("job_skill_fact", "reviewed_by")
