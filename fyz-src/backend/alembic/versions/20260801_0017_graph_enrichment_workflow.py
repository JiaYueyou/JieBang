"""Add machine validation, review and publication states to graph candidates.

Revision ID: 20260801_0017
Revises: 20260801_0016
"""

from alembic import op
import sqlalchemy as sa


revision = "20260801_0017"
down_revision = "20260801_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = (
        sa.Column("machine_validation_status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("review_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("publication_status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("review_note", sa.String(500), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("lock_version", sa.Integer(), nullable=False, server_default="0"),
    )
    for column in columns:
        op.add_column("graph_enrichment_candidate", column)
    op.create_foreign_key(
        "fk_graph_candidate_reviewer", "graph_enrichment_candidate", "user",
        ["reviewed_by"], ["id"],
    )
    for column in ("machine_validation_status", "review_status", "publication_status", "reviewed_by"):
        op.create_index(f"ix_graph_enrichment_candidate_{column}", "graph_enrichment_candidate", [column])
    op.execute(
        "UPDATE graph_enrichment_candidate SET "
        "machine_validation_status = CASE WHEN verification_status = 'machine_validated' THEN 'passed' ELSE 'pending' END, "
        "review_status = CASE WHEN verification_status = 'verified' THEN 'approved' ELSE 'pending' END, "
        "publication_status = CASE WHEN verification_status = 'verified' THEN 'approved' ELSE 'draft' END"
    )


def downgrade() -> None:
    for column in ("reviewed_by", "publication_status", "review_status", "machine_validation_status"):
        op.drop_index(f"ix_graph_enrichment_candidate_{column}", table_name="graph_enrichment_candidate")
    op.drop_constraint("fk_graph_candidate_reviewer", "graph_enrichment_candidate", type_="foreignkey")
    for column in (
        "lock_version", "published_at", "review_note", "reviewed_at", "reviewed_by",
        "publication_status", "review_status", "machine_validation_status",
    ):
        op.drop_column("graph_enrichment_candidate", column)
