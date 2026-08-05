"""Run and persist the transparent engineering review for Phase 0 cases."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.time import utc_isoformat, utc_now
from app.evaluation.phase0_golden import (
    finalize_engineering_review,
    validate_dataset,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=BACKEND_ROOT / "evaluation" / "phase0_golden_set.json",
    )
    parser.add_argument("--reviewer", default="engineering-review")
    parser.add_argument(
        "--authorization",
        required=True,
        help="Human review authorization or ticket reference.",
    )
    args = parser.parse_args()

    dataset = json.loads(args.input.read_text(encoding="utf-8"))
    finalize_engineering_review(
        dataset,
        reviewer=args.reviewer,
        reviewed_at=utc_isoformat(utc_now()),
        authorization=args.authorization,
    )
    errors = validate_dataset(dataset)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    args.input.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = dataset["review_summary"]
    print(
        f"Reviewed {summary['total']} cases: "
        f"approved={summary['approved']} rejected={summary['rejected']} "
        f"release_gate={dataset['release_gate']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
