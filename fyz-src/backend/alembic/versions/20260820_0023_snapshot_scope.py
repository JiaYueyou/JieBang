"""add source snapshot collection scope

Revision ID: 20260820_0023
Revises: 20260820_0022
"""

from alembic import op
import sqlalchemy as sa


revision = "20260820_0023"
down_revision = "20260820_0022"
branch_labels = None
depends_on = None


DEFAULT_SCOPE_HASH = "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("source_snapshot")}
    if "scope_hash" not in columns:
        op.add_column(
            "source_snapshot",
            sa.Column("scope_hash", sa.String(64), nullable=True),
        )
    if "scope_json" not in columns:
        op.add_column(
            "source_snapshot",
            sa.Column("scope_json", sa.JSON(), nullable=True),
        )
    op.execute(
        sa.text("UPDATE source_snapshot SET scope_hash = :value WHERE scope_hash IS NULL")
        .bindparams(value=DEFAULT_SCOPE_HASH)
    )
    op.execute(sa.text("UPDATE source_snapshot SET scope_json = '{}' WHERE scope_json IS NULL"))
    op.alter_column(
        "source_snapshot", "scope_hash",
        existing_type=sa.String(64), nullable=False,
    )
    op.alter_column(
        "source_snapshot", "scope_json",
        existing_type=sa.JSON(), nullable=False,
    )
    indexes = {index["name"] for index in inspector.get_indexes("source_snapshot")}
    if "ix_source_snapshot_scope_hash" not in indexes:
        op.create_index("ix_source_snapshot_scope_hash", "source_snapshot", ["scope_hash"])


def downgrade() -> None:
    op.drop_index("ix_source_snapshot_scope_hash", table_name="source_snapshot")
    op.drop_column("source_snapshot", "scope_json")
    op.drop_column("source_snapshot", "scope_hash")
