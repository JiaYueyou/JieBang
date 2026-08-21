"""Offline, read-only validation for the checked-in MySQL snapshot package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from db_transfer_common import (
    MANIFEST_PATH,
    SNAPSHOT_PATH,
    VERIFICATION_PATH,
    repository_alembic_head,
    validate_snapshot_package,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT_PATH)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--summary", type=Path, default=VERIFICATION_PATH)
    parser.add_argument(
        "--expected-revision",
        help="Expected revision (defaults to the repository's unique Alembic head).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    expected_revision = args.expected_revision or repository_alembic_head()
    manifest = validate_snapshot_package(
        args.snapshot.resolve(),
        args.manifest.resolve(),
        args.summary.resolve(),
        expected_revision=expected_revision,
    )
    print(
        json.dumps(
            {
                "status": "passed",
                "alembic_revision": manifest["alembic_revision"],
                "table_count": manifest["table_count"],
                "total_rows": manifest["total_rows"],
                "sha256": manifest["sha256"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
