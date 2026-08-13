"""add version-aware public job observations

Revision ID: 20260809_0019
Revises: 20260808_0018
"""

from alembic import op
import sqlalchemy as sa


revision = "20260809_0019"
down_revision = "20260808_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_source_observation",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_document_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("observed_on", sa.Date(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_event_type", sa.String(length=24), nullable=False),
        sa.Column("content_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("snapshot_key", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["source_document_id"], ["source_document.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_document_id",
            "observed_on",
            name="uq_job_source_observation_document_day",
        ),
    )
    for column in (
        "source_document_id",
        "source",
        "external_id",
        "observed_on",
        "observed_at",
        "source_event_at",
        "source_event_type",
        "content_fingerprint",
        "snapshot_key",
        "status",
    ):
        op.create_index(
            f"ix_job_source_observation_{column}",
            "job_source_observation",
            [column],
        )


def downgrade() -> None:
    op.drop_table("job_source_observation")
