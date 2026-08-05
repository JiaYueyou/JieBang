"""Add traceable job data quality and source trust fields.

Revision ID: 20260730_0013
Revises: 20260730_0012
"""

from alembic import op
import sqlalchemy as sa


revision = "20260730_0013"
down_revision = "20260730_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "skill",
        sa.Column(
            "validation_status",
            sa.String(length=24),
            nullable=False,
            server_default="approved",
        ),
    )
    op.create_index("ix_skill_validation_status", "skill", ["validation_status"])

    op.add_column("raw_job_record", sa.Column("standard_job_id", sa.Integer(), nullable=True))
    op.add_column("raw_job_record", sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("raw_job_record", sa.Column("crawled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "raw_job_record",
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "raw_job_record",
        sa.Column("freshness_score", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "raw_job_record",
        sa.Column("source_trust_score", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "raw_job_record",
        sa.Column("quality_status", sa.String(length=20), nullable=False, server_default="pending"),
    )
    op.add_column(
        "raw_job_record",
        sa.Column("quality_flags", sa.JSON(), nullable=True),
    )
    op.add_column("raw_job_record", sa.Column("content_simhash", sa.String(length=16), nullable=True))
    op.add_column(
        "raw_job_record",
        sa.Column("near_duplicate_group_id", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "raw_job_record",
        sa.Column("near_duplicate_score", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "raw_job_record",
        sa.Column("quality_policy_version", sa.String(length=40), nullable=False, server_default="phase1-v1"),
    )
    op.add_column(
        "raw_job_record",
        sa.Column("quality_evaluated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "raw_job_record",
        sa.Column("is_excluded", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("raw_job_record", sa.Column("exclusion_reason", sa.String(length=500), nullable=True))
    op.add_column("raw_job_record", sa.Column("excluded_by", sa.Integer(), nullable=True))
    op.add_column("raw_job_record", sa.Column("excluded_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE raw_job_record SET quality_flags = JSON_ARRAY() WHERE quality_flags IS NULL")
    op.alter_column(
        "raw_job_record",
        "quality_flags",
        existing_type=sa.JSON(),
        nullable=False,
    )

    op.create_foreign_key(
        "fk_raw_job_record_standard_job",
        "raw_job_record",
        "standard_job",
        ["standard_job_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_raw_job_record_excluded_by_user",
        "raw_job_record",
        "user",
        ["excluded_by"],
        ["id"],
    )
    op.create_index("ix_raw_job_record_standard_job_id", "raw_job_record", ["standard_job_id"])
    op.create_index("ix_raw_job_record_posted_at", "raw_job_record", ["posted_at"])
    op.create_index("ix_raw_job_record_crawled_at", "raw_job_record", ["crawled_at"])
    op.create_index("ix_raw_job_record_quality_status", "raw_job_record", ["quality_status"])
    op.create_index("ix_raw_job_record_content_simhash", "raw_job_record", ["content_simhash"])
    op.create_index(
        "ix_raw_job_record_near_duplicate_group_id",
        "raw_job_record",
        ["near_duplicate_group_id"],
    )
    op.create_index("ix_raw_job_record_is_excluded", "raw_job_record", ["is_excluded"])

    op.create_table(
        "source_trust_policy",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("trust_score", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("freshness_window_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("policy_version", sa.String(length=40), nullable=False, server_default="phase1-v1"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", name="uq_source_trust_policy_source"),
    )
    op.create_index("ix_source_trust_policy_source", "source_trust_policy", ["source"])

    # Legacy rows used the MySQL session's Asia/Shanghai clock for created_at
    # and UTC-naive application values for completion fields. Restrict repair
    # to the impossible bounded ordering that identifies that old write path.
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.execute(
            """
            UPDATE graph_snapshot
            SET created_at = DATE_SUB(created_at, INTERVAL 8 HOUR)
            WHERE completed_at IS NOT NULL
              AND created_at > completed_at
              AND TIMESTAMPDIFF(HOUR, completed_at, created_at) BETWEEN 0 AND 12
            """
        )
        op.execute(
            """
            UPDATE graph_sync_batch
            SET created_at = DATE_SUB(created_at, INTERVAL 8 HOUR)
            WHERE COALESCE(started_at, finished_at) IS NOT NULL
              AND created_at > COALESCE(started_at, finished_at)
              AND TIMESTAMPDIFF(
                    HOUR,
                    COALESCE(started_at, finished_at),
                    created_at
                  ) BETWEEN 0 AND 12
            """
        )


def downgrade() -> None:
    op.drop_table("source_trust_policy")
    op.drop_index("ix_raw_job_record_is_excluded", table_name="raw_job_record")
    op.drop_index(
        "ix_raw_job_record_near_duplicate_group_id",
        table_name="raw_job_record",
    )
    op.drop_index("ix_raw_job_record_content_simhash", table_name="raw_job_record")
    op.drop_index("ix_raw_job_record_quality_status", table_name="raw_job_record")
    op.drop_index("ix_raw_job_record_crawled_at", table_name="raw_job_record")
    op.drop_index("ix_raw_job_record_posted_at", table_name="raw_job_record")
    op.drop_index("ix_raw_job_record_standard_job_id", table_name="raw_job_record")
    op.drop_constraint(
        "fk_raw_job_record_excluded_by_user",
        "raw_job_record",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_raw_job_record_standard_job",
        "raw_job_record",
        type_="foreignkey",
    )
    for column in (
        "excluded_at",
        "excluded_by",
        "exclusion_reason",
        "is_excluded",
        "quality_evaluated_at",
        "quality_policy_version",
        "near_duplicate_score",
        "near_duplicate_group_id",
        "content_simhash",
        "quality_flags",
        "quality_status",
        "source_trust_score",
        "freshness_score",
        "quality_score",
        "crawled_at",
        "posted_at",
        "standard_job_id",
    ):
        op.drop_column("raw_job_record", column)
    op.drop_index("ix_skill_validation_status", table_name="skill")
    op.drop_column("skill", "validation_status")
