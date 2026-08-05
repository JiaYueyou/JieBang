"""add user favorites and browse history

Revision ID: 20260730_0012
Revises: 20260730_0011
"""

from alembic import op
import sqlalchemy as sa

revision = "20260730_0012"
down_revision = "20260730_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_favorite",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "target_type",
            "target_id",
            name="uq_user_favorite_target",
        ),
    )
    op.create_index("ix_user_favorite_user_id", "user_favorite", ["user_id"])
    op.create_index("ix_user_favorite_target_type", "user_favorite", ["target_type"])
    op.create_index("ix_user_favorite_target_id", "user_favorite", ["target_id"])

    op.create_table(
        "user_browse_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("target_key", sa.String(length=255), nullable=False),
        sa.Column("target_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("source", sa.String(length=120), nullable=False, server_default="智联职引"),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("visit_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("first_viewed_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("last_viewed_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "event_type",
            "target_key",
            name="uq_user_history_target",
        ),
    )
    op.create_index("ix_user_browse_history_user_id", "user_browse_history", ["user_id"])
    op.create_index("ix_user_browse_history_event_type", "user_browse_history", ["event_type"])
    op.create_index("ix_user_browse_history_last_viewed_at", "user_browse_history", ["last_viewed_at"])


def downgrade() -> None:
    op.drop_table("user_browse_history")
    op.drop_table("user_favorite")
