"""Step 1: create or upgrade all MySQL tables with Alembic migrations."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]


def main() -> None:
    print("[1/4] Applying MySQL schema migrations...")
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", "current"],
        cwd=BACKEND_DIR,
        check=True,
    )
    print("[1/4] MySQL schema is ready.")


if __name__ == "__main__":
    main()
