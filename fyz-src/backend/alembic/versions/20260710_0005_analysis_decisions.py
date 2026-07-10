"""Add analysis insight decision audit table.

Revision ID: 20260710_0005
Revises: 20260620_0004
Create Date: 2026-07-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260710_0005"
down_revision: Union[str, Sequence[str], None] = "20260620_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_insight_decision",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("insight_type", sa.String(40), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "insight_type", "target_id", "created_by", name="uq_analysis_decision_user_target"
        ),
    )
    op.create_index("ix_analysis_decision_type", "analysis_insight_decision", ["insight_type"])
    op.create_index("ix_analysis_decision_target", "analysis_insight_decision", ["target_id"])
    op.create_index("ix_analysis_decision_decision", "analysis_insight_decision", ["decision"])
    op.create_index("ix_analysis_decision_created_by", "analysis_insight_decision", ["created_by"])


def downgrade() -> None:
    op.drop_table("analysis_insight_decision")
