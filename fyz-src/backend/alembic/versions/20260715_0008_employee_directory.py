"""add enterprise employee directory for talent autocomplete

Revision ID: 20260715_0008
Revises: 20260715_0007
"""

from alembic import op
import sqlalchemy as sa

revision = "20260715_0008"
down_revision = "20260715_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enterprise_employee_directory",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_no", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("department", sa.String(100), nullable=False),
        sa.Column("current_position", sa.String(120), nullable=False),
        sa.Column("level", sa.String(30), nullable=False, server_default="mid"),
        sa.Column("location", sa.String(100)),
        sa.Column("tenure_months", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("position_tenure_months", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("project_highlights", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("source", sa.String(40), nullable=False, server_default="hr_sync"),
        sa.Column("synced_by", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("synced_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    for column in ("employee_no", "name", "department", "status"):
        op.create_index(
            f"ix_enterprise_employee_directory_{column}",
            "enterprise_employee_directory",
            [column],
        )
    op.execute(sa.text("""
        INSERT INTO enterprise_employee_directory (
            employee_no, name, department, current_position, level, location,
            tenure_months, position_tenure_months, skills, project_highlights,
            status, source, synced_by, synced_at
        )
        SELECT employee_no, name, department, current_position, level, location,
               tenure_months, position_tenure_months, skills, project_highlights,
               status, 'talent_pool_backfill', created_by, updated_at
        FROM enterprise_talent
    """))


def downgrade() -> None:
    op.drop_table("enterprise_employee_directory")
