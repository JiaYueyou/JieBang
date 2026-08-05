"""Allow Agent claims to cite both RAG chunks and saved input evidence.

Revision ID: 20260731_0015
Revises: 20260731_0014
"""

from alembic import op
import sqlalchemy as sa


revision = "20260731_0015"
down_revision = "20260731_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_claim_citation",
        sa.Column(
            "citation_source_type",
            sa.String(length=40),
            nullable=True,
        ),
    )
    op.add_column(
        "agent_claim_citation",
        sa.Column("citation_ref", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "agent_claim_citation",
        sa.Column("source_metadata", sa.JSON(), nullable=True),
    )
    op.execute(
        """
        UPDATE agent_claim_citation
        SET citation_source_type = 'evidence_chunk',
            citation_ref = evidence_id,
            source_metadata = '{}'
        """
    )
    op.alter_column(
        "agent_claim_citation",
        "citation_source_type",
        existing_type=sa.String(length=40),
        nullable=False,
    )
    op.alter_column(
        "agent_claim_citation",
        "citation_ref",
        existing_type=sa.String(length=160),
        nullable=False,
    )
    op.alter_column(
        "agent_claim_citation",
        "source_metadata",
        existing_type=sa.JSON(),
        nullable=False,
    )
    op.alter_column(
        "agent_claim_citation",
        "evidence_id",
        existing_type=sa.String(length=64),
        nullable=True,
    )
    op.drop_constraint(
        "uq_agent_claim_citation",
        "agent_claim_citation",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_agent_claim_citation_source",
        "agent_claim_citation",
        [
            "agent_run_id",
            "claim_id",
            "citation_source_type",
            "citation_ref",
        ],
    )
    op.create_index(
        "ix_agent_claim_citation_citation_source_type",
        "agent_claim_citation",
        ["citation_source_type"],
    )


def downgrade() -> None:
    # Match/input citations cannot satisfy the legacy EvidenceChunk foreign
    # key and are intentionally removed during an explicit downgrade.
    op.execute(
        "DELETE FROM agent_claim_citation WHERE evidence_id IS NULL"
    )
    op.drop_index(
        "ix_agent_claim_citation_citation_source_type",
        table_name="agent_claim_citation",
    )
    op.drop_constraint(
        "uq_agent_claim_citation_source",
        "agent_claim_citation",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_agent_claim_citation",
        "agent_claim_citation",
        ["agent_run_id", "claim_id", "evidence_id"],
    )
    op.alter_column(
        "agent_claim_citation",
        "evidence_id",
        existing_type=sa.String(length=64),
        nullable=False,
    )
    op.drop_column("agent_claim_citation", "source_metadata")
    op.drop_column("agent_claim_citation", "citation_ref")
    op.drop_column("agent_claim_citation", "citation_source_type")
