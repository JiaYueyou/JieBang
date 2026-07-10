"""Run the four numbered database import steps with one command."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Import MySQL and rebuild Neo4j.")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Required confirmation because the MySQL import replaces existing rows.",
    )
    args = parser.parse_args()
    if not args.replace:
        parser.error("--replace is required; verify the target .env before continuing")

    commands = (
        [sys.executable, str(SCRIPTS_DIR / "01_prepare_mysql_schema.py")],
        [sys.executable, str(SCRIPTS_DIR / "02_import_mysql_snapshot.py"), "--replace"],
        [sys.executable, str(SCRIPTS_DIR / "03_rebuild_neo4j.py")],
        [sys.executable, str(SCRIPTS_DIR / "04_verify_database_import.py")],
    )
    for command in commands:
        subprocess.run(command, cwd=SCRIPTS_DIR.parent, check=True)
    print("Database import workflow completed successfully.")


if __name__ == "__main__":
    main()
