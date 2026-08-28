"""add record-level job import quarantine

Revision ID: 20260820_0024
Revises: 20260820_0023
"""

from alembic import op
import sqlalchemy as sa


revision = "20260820_0024"
down_revision = "20260820_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("data_source", sa.Column("last_success_at", sa.DateTime(), nullable=True))
    op.add_column("data_source", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column(
        "data_source",
        sa.Column("freshness_slo_minutes", sa.Integer(), nullable=False, server_default="2880"),
    )
    op.create_index("ix_data_source_last_success_at", "data_source", ["last_success_at"])
    op.create_table(
        "job_import_quarantine",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_file", sa.String(255), nullable=False),
        sa.Column("record_index", sa.Integer(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("error_codes", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "source_file", "record_index", "payload_hash",
            name="uq_job_import_quarantine_record",
        ),
    )
    op.create_index("ix_job_import_quarantine_source_file", "job_import_quarantine", ["source_file"])
    op.create_index("ix_job_import_quarantine_source", "job_import_quarantine", ["source"])
    op.create_index("ix_job_import_quarantine_external_id", "job_import_quarantine", ["external_id"])
    op.create_index("ix_job_import_quarantine_status", "job_import_quarantine", ["status"])


def downgrade() -> None:
    op.drop_table("job_import_quarantine")
    op.drop_index("ix_data_source_last_success_at", table_name="data_source")
    op.drop_column("data_source", "freshness_slo_minutes")
    op.drop_column("data_source", "last_error")
    op.drop_column("data_source", "last_success_at")
