"""add external job identity, version, snapshot and lifecycle observations

Revision ID: 20260820_0022
Revises: 20260820_0021
"""

from alembic import op
import hashlib
import sqlalchemy as sa
import uuid


revision = "20260820_0022"
down_revision = "20260820_0021"
branch_labels = None
depends_on = None


def _backfill_existing_jobs() -> None:
    """Build identities and ordered versions for the pre-0022 source documents."""
    bind = op.get_bind()
    rows = list(bind.execute(sa.text("""
        SELECT sd.id, sd.source, sd.external_id, sd.url, sd.title,
               sd.content_fingerprint, sd.created_at, r.crawled_at
        FROM source_document AS sd
        LEFT JOIN raw_job_record AS r ON r.source_document_id = sd.id
        ORDER BY sd.source, sd.id
    """)).mappings())
    groups: dict[tuple[str, str], list] = {}
    for row in rows:
        stable = str(row["external_id"] or row["url"] or row["title"] or row["id"])
        source = str(row["source"])
        identity_key = hashlib.sha256(
            f"{source.casefold()}|{stable}".encode("utf-8")
        ).hexdigest()
        groups.setdefault((source, identity_key), []).append(row)

    identity_rows = []
    version_rows = []
    document_links = []
    observation_links = []
    for (source, identity_key), documents in groups.items():
        documents.sort(key=lambda row: (row["crawled_at"] or row["created_at"], row["id"]))
        identity_id = str(uuid.uuid4())
        version_ids = [str(uuid.uuid4()) for _ in documents]
        observed = [row["crawled_at"] or row["created_at"] for row in documents]
        identity_rows.append({
            "id": identity_id,
            "source": source,
            "identity_key": identity_key,
            "external_id": documents[-1]["external_id"],
            "canonical_url": documents[-1]["url"],
            "current_version_id": version_ids[-1],
            "first_seen_at": observed[0],
            "last_seen_at": observed[-1],
        })
        for index, (row, version_id) in enumerate(zip(documents, version_ids)):
            version_rows.append({
                "id": version_id,
                "identity_id": identity_id,
                "source_document_id": row["id"],
                "version_no": index + 1,
                "content_fingerprint": row["content_fingerprint"],
                "change_type": "created" if index == 0 else "updated",
                "valid_from": observed[index],
                "valid_to": observed[index + 1] if index + 1 < len(observed) else None,
                "is_current": index + 1 == len(documents),
            })
            document_links.append({"identity_id": identity_id, "document_id": row["id"]})
            observation_links.append({"identity_id": identity_id, "document_id": row["id"]})

    if identity_rows:
        bind.execute(sa.text("""
            INSERT INTO external_job_identity
              (id, source, identity_key, external_id, canonical_url, lifecycle_status,
               missing_streak, current_version_id, first_seen_at, last_seen_at)
            VALUES
              (:id, :source, :identity_key, :external_id, :canonical_url, 'active',
               0, :current_version_id, :first_seen_at, :last_seen_at)
        """), identity_rows)
        bind.execute(sa.text("""
            UPDATE source_document
            SET external_job_identity_id = :identity_id
            WHERE id = :document_id
        """), document_links)
        bind.execute(sa.text("""
            INSERT INTO external_job_version
              (id, identity_id, source_document_id, version_no, content_fingerprint,
               change_type, valid_from, valid_to, is_current)
            VALUES
              (:id, :identity_id, :source_document_id, :version_no, :content_fingerprint,
               :change_type, :valid_from, :valid_to, :is_current)
        """), version_rows)
        bind.execute(sa.text("""
            UPDATE job_source_observation
            SET external_job_identity_id = :identity_id
            WHERE source_document_id = :document_id
        """), observation_links)


def upgrade() -> None:
    op.create_table(
        "external_job_identity",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("identity_key", sa.String(64), nullable=False),
        sa.Column("external_id", sa.String(255)),
        sa.Column("canonical_url", sa.String(1000)),
        sa.Column("lifecycle_status", sa.String(24), nullable=False, server_default="active"),
        sa.Column("missing_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_version_id", sa.String(36)),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source", "identity_key", name="uq_external_job_identity_source_key"),
    )
    for column in ("source", "external_id", "lifecycle_status", "current_version_id", "last_seen_at", "closed_at"):
        op.create_index(f"ix_external_job_identity_{column}", "external_job_identity", [column])

    op.create_table(
        "source_snapshot",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("snapshot_key", sa.String(255), nullable=False),
        sa.Column("snapshot_type", sa.String(20), nullable=False, server_default="delta"),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="processing"),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source", "snapshot_key", name="uq_source_snapshot_source_key"),
    )
    for column in ("source", "observed_at", "status"):
        op.create_index(f"ix_source_snapshot_{column}", "source_snapshot", [column])

    op.add_column("source_document", sa.Column("external_job_identity_id", sa.String(36)))
    op.create_foreign_key(
        "fk_source_document_external_job_identity", "source_document", "external_job_identity",
        ["external_job_identity_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_source_document_external_job_identity_id", "source_document", ["external_job_identity_id"])

    op.create_table(
        "external_job_version",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("identity_id", sa.String(36), sa.ForeignKey("external_job_identity.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_document_id", sa.Integer(), sa.ForeignKey("source_document.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("content_fingerprint", sa.String(64), nullable=False),
        sa.Column("change_type", sa.String(24), nullable=False, server_default="created"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True)),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("identity_id", "version_no", name="uq_external_job_version_number"),
        sa.UniqueConstraint("identity_id", "content_fingerprint", name="uq_external_job_version_content"),
    )
    for column in ("identity_id", "content_fingerprint", "valid_to", "is_current"):
        op.create_index(f"ix_external_job_version_{column}", "external_job_version", [column])

    op.add_column("job_source_observation", sa.Column("external_job_identity_id", sa.String(36)))
    op.add_column("job_source_observation", sa.Column("source_snapshot_id", sa.String(36)))
    op.add_column("job_source_observation", sa.Column("event_type", sa.String(20), nullable=False, server_default="seen"))
    op.create_foreign_key(
        "fk_job_observation_external_identity", "job_source_observation", "external_job_identity",
        ["external_job_identity_id"], ["id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_job_observation_source_snapshot", "job_source_observation", "source_snapshot",
        ["source_snapshot_id"], ["id"], ondelete="SET NULL",
    )
    for column in ("external_job_identity_id", "source_snapshot_id", "event_type"):
        op.create_index(f"ix_job_source_observation_{column}", "job_source_observation", [column])
    _backfill_existing_jobs()


def downgrade() -> None:
    for column in ("event_type", "source_snapshot_id", "external_job_identity_id"):
        op.drop_index(f"ix_job_source_observation_{column}", table_name="job_source_observation")
    op.drop_constraint("fk_job_observation_source_snapshot", "job_source_observation", type_="foreignkey")
    op.drop_constraint("fk_job_observation_external_identity", "job_source_observation", type_="foreignkey")
    op.drop_column("job_source_observation", "event_type")
    op.drop_column("job_source_observation", "source_snapshot_id")
    op.drop_column("job_source_observation", "external_job_identity_id")
    op.drop_table("external_job_version")
    op.drop_index("ix_source_document_external_job_identity_id", table_name="source_document")
    op.drop_constraint("fk_source_document_external_job_identity", "source_document", type_="foreignkey")
    op.drop_column("source_document", "external_job_identity_id")
    op.drop_table("source_snapshot")
    op.drop_table("external_job_identity")
