"""Generate and validate the deterministic Phase 0 evaluation seed set."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.evaluation.phase0_golden import build_dataset, validate_dataset


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=BACKEND_ROOT / "evaluation" / "phase0_golden_set.json",
    )
    args = parser.parse_args()
    dataset = build_dataset()
    errors = validate_dataset(dataset)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Validated {len(dataset['cases'])} cases: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
