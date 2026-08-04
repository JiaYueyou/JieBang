"""Add job title normalization V2 and duplicate clusters.

Revision ID: 20260801_0016
Revises: 20260731_0015
"""

from alembic import op
import sqlalchemy as sa


revision = "20260801_0016"
down_revision = "20260731_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("standard_job", sa.Column("role_family", sa.String(40), nullable=True))
    op.add_column("standard_job", sa.Column("specialization_key", sa.String(160), nullable=True))
    op.add_column("standard_job", sa.Column("occupation_code", sa.String(220), nullable=True))
    op.add_column(
        "standard_job",
        sa.Column("normalization_version", sa.String(40), nullable=False, server_default="job-title-v1"),
    )
    op.create_index("ix_standard_job_role_family", "standard_job", ["role_family"])
    op.create_index("ix_standard_job_specialization_key", "standard_job", ["specialization_key"])
    op.create_index("ix_standard_job_occupation_code", "standard_job", ["occupation_code"])
    op.create_index("ix_standard_job_normalization_version", "standard_job", ["normalization_version"])

    op.create_table(
        "standard_job_alias",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("standard_job_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(255), nullable=False),
        sa.Column("alias_key", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False, server_default="raw"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1"),
        sa.Column("normalization_version", sa.String(40), nullable=False, server_default="job-title-v2"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["standard_job_id"], ["standard_job.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("standard_job_id", "alias_key", name="uq_standard_job_alias_key"),
    )
    op.create_index("ix_standard_job_alias_standard_job_id", "standard_job_alias", ["standard_job_id"])
    op.create_index("ix_standard_job_alias_alias_key", "standard_job_alias", ["alias_key"])

    op.add_column("raw_job_record", sa.Column("city_code", sa.String(40), nullable=True))
    op.add_column("raw_job_record", sa.Column("company_key", sa.String(160), nullable=True))
    op.add_column("raw_job_record", sa.Column("work_mode", sa.String(20), nullable=False, server_default="onsite"))
    op.add_column("raw_job_record", sa.Column("employment_type", sa.String(20), nullable=False, server_default="full_time"))
    op.add_column("raw_job_record", sa.Column("normalization_version", sa.String(40), nullable=False, server_default="job-title-v1"))
    op.add_column("raw_job_record", sa.Column("normalization_status", sa.String(20), nullable=False, server_default="pending"))
    op.add_column("raw_job_record", sa.Column("normalization_confidence", sa.Float(), nullable=False, server_default="0"))
    for column in ("city_code", "company_key", "work_mode", "employment_type", "normalization_version", "normalization_status"):
        op.create_index(f"ix_raw_job_record_{column}", "raw_job_record", [column])

    op.create_table(
        "job_duplicate_cluster",
        sa.Column("id", sa.String(40), nullable=False),
        sa.Column("standard_job_id", sa.Integer(), nullable=False),
        sa.Column("representative_raw_job_id", sa.Integer(), nullable=True),
        sa.Column("company_key", sa.String(160), nullable=True),
        sa.Column("city_code", sa.String(40), nullable=True),
        sa.Column("member_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["standard_job_id"], ["standard_job.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["representative_raw_job_id"], ["raw_job_record.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("standard_job_id", "representative_raw_job_id", "company_key", "city_code"):
        op.create_index(f"ix_job_duplicate_cluster_{column}", "job_duplicate_cluster", [column])
    op.add_column("raw_job_record", sa.Column("duplicate_cluster_id", sa.String(40), nullable=True))
    op.create_foreign_key(
        "fk_raw_job_record_duplicate_cluster",
        "raw_job_record", "job_duplicate_cluster", ["duplicate_cluster_id"], ["id"],
    )
    op.create_index("ix_raw_job_record_duplicate_cluster_id", "raw_job_record", ["duplicate_cluster_id"])


def downgrade() -> None:
    op.drop_index("ix_raw_job_record_duplicate_cluster_id", table_name="raw_job_record")
    op.drop_constraint("fk_raw_job_record_duplicate_cluster", "raw_job_record", type_="foreignkey")
    op.drop_column("raw_job_record", "duplicate_cluster_id")
    for column in ("city_code", "company_key", "work_mode", "employment_type", "normalization_version", "normalization_status"):
        op.drop_index(f"ix_raw_job_record_{column}", table_name="raw_job_record")
    for column in ("normalization_confidence", "normalization_status", "normalization_version", "employment_type", "work_mode", "company_key", "city_code"):
        op.drop_column("raw_job_record", column)
    op.drop_table("job_duplicate_cluster")
    op.drop_table("standard_job_alias")
    for column in ("normalization_version", "occupation_code", "specialization_key", "role_family"):
        index_name = f"ix_standard_job_{column}"
        op.drop_index(index_name, table_name="standard_job")
        op.drop_column("standard_job", column)
