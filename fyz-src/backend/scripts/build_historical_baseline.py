"""Create a draft or active frozen historical trend baseline from MySQL facts."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import async_session, engine  # noqa: E402
from app.services.historical_baseline_service import HistoricalBaselineService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--end", required=True, type=date.fromisoformat)
    parser.add_argument("--activate", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


async def run(args: argparse.Namespace) -> None:
    async with async_session() as db:
        result = await HistoricalBaselineService(db).build(
            version=args.version,
            period_start=args.start,
            period_end=args.end,
            activate=args.activate,
            persist=not args.dry_run,
        )
    await engine.dispose()
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
