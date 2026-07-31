"""Add authoritative evidence and rebuildable retrieval index metadata.

Revision ID: 20260731_0014
Revises: 20260730_0013
"""

from alembic import op
import sqlalchemy as sa


revision = "20260731_0014"
down_revision = "20260730_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evidence_chunk",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("job_skill_fact_id", sa.Integer(), nullable=False),
        sa.Column("source_document_id", sa.Integer(), nullable=False),
        sa.Column("raw_job_record_id", sa.Integer(), nullable=False),
        sa.Column("standard_job_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
        sa.Column("source_platform", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column("content_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("near_duplicate_group_id", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_skill_fact_id"],
            ["job_skill_fact.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["raw_job_record_id"],
            ["raw_job_record.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"],
            ["skill.id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["source_document.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["standard_job_id"],
            ["standard_job.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_skill_fact_id",
            name="uq_evidence_chunk_job_skill_fact_id",
        ),
    )
    for column in (
        "source_document_id",
        "raw_job_record_id",
        "standard_job_id",
        "skill_id",
        "source_platform",
        "posted_at",
        "verification_status",
        "content_fingerprint",
        "near_duplicate_group_id",
    ):
        op.create_index(f"ix_evidence_chunk_{column}", "evidence_chunk", [column])

    op.create_table(
        "retrieval_index_version",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.String(length=80), nullable=False),
        sa.Column("backend", sa.String(length=40), nullable=False),
        sa.Column("embedding_provider", sa.String(length=80), nullable=False),
        sa.Column("embedding_model", sa.String(length=120), nullable=False),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False),
        sa.Column("chunking_version", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("entry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version", name="uq_retrieval_index_version_version"),
    )
    op.create_index(
        "ix_retrieval_index_version_status",
        "retrieval_index_version",
        ["status"],
    )

    op.create_table(
        "retrieval_index_entry",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("index_version_id", sa.String(length=36), nullable=False),
        sa.Column("evidence_id", sa.String(length=64), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.Column("embedding_checksum", sa.String(length=64), nullable=False),
        sa.Column("lexical_text", sa.Text(), nullable=False),
        sa.Column("backend_document_id", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence_chunk.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["index_version_id"],
            ["retrieval_index_version.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "index_version_id",
            "evidence_id",
            name="uq_retrieval_index_entry_version_evidence",
        ),
    )
    op.create_index(
        "ix_retrieval_index_entry_index_version_id",
        "retrieval_index_entry",
        ["index_version_id"],
    )
    op.create_index(
        "ix_retrieval_index_entry_evidence_id",
        "retrieval_index_entry",
        ["evidence_id"],
    )

    op.create_table(
        "retrieval_query_log",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("index_version_id", sa.String(length=36), nullable=False),
        sa.Column("query_hash", sa.String(length=64), nullable=False),
        sa.Column("query_summary", sa.String(length=500), nullable=False),
        sa.Column("filters_json", sa.JSON(), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("result_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.ForeignKeyConstraint(
            ["index_version_id"],
            ["retrieval_index_version.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_retrieval_query_log_index_version_id",
        "retrieval_query_log",
        ["index_version_id"],
    )
    op.create_index(
        "ix_retrieval_query_log_query_hash",
        "retrieval_query_log",
        ["query_hash"],
    )

    op.create_table(
        "agent_claim_citation",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("agent_run_id", sa.String(length=36), nullable=False),
        sa.Column("claim_id", sa.String(length=80), nullable=False),
        sa.Column("claim_type", sa.String(length=50), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("evidence_id", sa.String(length=64), nullable=False),
        sa.Column("grounding_score", sa.Float(), nullable=False),
        sa.Column("validation_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["agent_run_id"],
            ["agent_run.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence_chunk.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "agent_run_id",
            "claim_id",
            "evidence_id",
            name="uq_agent_claim_citation",
        ),
    )
    op.create_index(
        "ix_agent_claim_citation_agent_run_id",
        "agent_claim_citation",
        ["agent_run_id"],
    )
    op.create_index(
        "ix_agent_claim_citation_evidence_id",
        "agent_claim_citation",
        ["evidence_id"],
    )
    op.create_index(
        "ix_agent_claim_citation_validation_status",
        "agent_claim_citation",
        ["validation_status"],
    )


def downgrade() -> None:
    op.drop_table("agent_claim_citation")
    op.drop_table("retrieval_query_log")
    op.drop_table("retrieval_index_entry")
    op.drop_table("retrieval_index_version")
    op.drop_table("evidence_chunk")
