"""add isolated internal transfer domain

Revision ID: 20260715_0007
Revises: 20260712_0006
"""

from alembic import op
import sqlalchemy as sa

revision = "20260715_0007"
down_revision = "20260712_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enterprise_talent",
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
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    for column in ("employee_no", "name", "department", "status"):
        op.create_index(f"ix_enterprise_talent_{column}", "enterprise_talent", [column])

    op.create_table(
        "internal_position",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("standardized_title", sa.String(120)),
        sa.Column("department", sa.String(100), nullable=False),
        sa.Column("receiving_manager", sa.String(100)),
        sa.Column("level", sa.String(30), nullable=False, server_default="mid"),
        sa.Column("headcount", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("open_reason", sa.String(300), nullable=False, server_default="组织人才配置"),
        sa.Column("responsibilities", sa.JSON(), nullable=False),
        sa.Column("requirements", sa.JSON(), nullable=False),
        sa.Column("required_skills", sa.JSON(), nullable=False),
        sa.Column("trainable_skills", sa.JSON(), nullable=False),
        sa.Column("transfer_profile", sa.JSON(), nullable=False),
        sa.Column("manager_confirmations", sa.JSON(), nullable=False),
        sa.Column("min_tenure_months", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_position_tenure_months", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("allowed_departments", sa.JSON(), nullable=False),
        sa.Column("restrictions", sa.JSON(), nullable=False),
        sa.Column("target_start_date", sa.Date()),
        sa.Column("open_from", sa.Date()),
        sa.Column("open_until", sa.Date()),
        sa.Column("internal_description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    for column in ("title", "standardized_title", "department", "status"):
        op.create_index(f"ix_internal_position_{column}", "internal_position", [column])

    op.create_table(
        "transfer_rule_set",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("min_tenure_months", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_position_tenure_months", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_match_score", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("skill_weight", sa.Integer(), nullable=False, server_default="85"),
        sa.Column("tenure_weight", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_transfer_rule_set_status", "transfer_rule_set", ["status"])

    op.create_table(
        "transfer_decision",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("talent_id", sa.Integer(), sa.ForeignKey("enterprise_talent.id"), nullable=False),
        sa.Column("position_id", sa.Integer(), sa.ForeignKey("internal_position.id"), nullable=False),
        sa.Column("match_score", sa.Integer(), nullable=False),
        sa.Column("matched_skills", sa.JSON(), nullable=False),
        sa.Column("missing_skills", sa.JSON(), nullable=False),
        sa.Column("rule_snapshot", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="confirmed"),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    for column in ("talent_id", "position_id", "status"):
        op.create_index(f"ix_transfer_decision_{column}", "transfer_decision", [column])


def downgrade() -> None:
    op.drop_table("transfer_decision")
    op.drop_table("transfer_rule_set")
    op.drop_table("internal_position")
    op.drop_table("enterprise_talent")
