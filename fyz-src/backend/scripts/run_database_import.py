"""Restore MySQL, Chroma and Neo4j with one command."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from db_transfer_common import load_manifest  # noqa: E402


def preflight_snapshot_package() -> None:
    """Validate the complete package before any target-side command can run.

    ``load_manifest`` is deliberately offline: it reads repository files and
    Alembic migration metadata only. It does not connect to MySQL, Chroma, or
    Neo4j and therefore remains safe to run before the destructive workflow.
    """
    manifest = load_manifest()
    print(
        "[0/5] Snapshot package verified: "
        f"revision={manifest['alembic_revision']}, "
        f"tables={manifest['table_count']}, rows={manifest['total_rows']}."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Import the MySQL snapshot, restore persistent Chroma vectors and "
            "rebuild the Neo4j read model."
        )
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Required confirmation because the MySQL import replaces existing rows.",
    )
    args = parser.parse_args()
    if not args.replace:
        parser.error("--replace is required; verify the target .env before continuing")

    # Fail closed before spawning Alembic or any process that can connect to or
    # mutate the target services.
    preflight_snapshot_package()

    local_embedding = os.getenv(
        "RETRIEVAL_EMBEDDING_PROVIDER", ""
    ).strip().casefold() in {"local_hash", "local_deterministic"}
    retrieval_command = (
        [
            sys.executable,
            str(SCRIPTS_DIR / "rebuild_retrieval_index.py"),
            "--backend",
            "local_hash",
        ]
        if local_embedding
        else [
            sys.executable,
            str(SCRIPTS_DIR / "restore_chroma_from_mysql.py"),
            "--replace",
        ]
    )
    commands = (
        [sys.executable, str(SCRIPTS_DIR / "01_prepare_mysql_schema.py")],
        [sys.executable, str(SCRIPTS_DIR / "02_import_mysql_snapshot.py"), "--replace"],
        retrieval_command,
        [sys.executable, str(SCRIPTS_DIR / "03_rebuild_neo4j.py")],
        [sys.executable, str(SCRIPTS_DIR / "04_verify_database_import.py")],
    )
    for command in commands:
        subprocess.run(command, cwd=SCRIPTS_DIR.parent, check=True)
    print("MySQL, Chroma and Neo4j import workflow completed successfully.")


if __name__ == "__main__":
    main()
