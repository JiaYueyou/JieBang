"""add enterprise department master data

Revision ID: 20260820_0021
Revises: 20260809_0020
"""

from alembic import op
import sqlalchemy as sa


revision = "20260820_0021"
down_revision = "20260809_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enterprise_department",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(30), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("manager", sa.String(100)),
        sa.Column("location", sa.String(100)),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    for column in ("code", "name", "status"):
        op.create_index(f"ix_enterprise_department_{column}", "enterprise_department", [column])


def downgrade() -> None:
    op.drop_table("enterprise_department")
