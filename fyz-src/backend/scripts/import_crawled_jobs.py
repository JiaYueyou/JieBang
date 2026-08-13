"""Import crawler snapshots into the existing database without LLM enrichment.

The script intentionally uses the established ImportService so quality checks,
deduplication, normalization, and rule-based skill extraction stay identical to
the API import path.  It never recreates schema or drops data.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Permit direct execution from ``backend/scripts`` without environment setup.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import async_session, engine
from app.services import ImportService, SkillService


class DisabledLLMProvider:
    """Signals SkillService to skip remote LLM enrichment entirely."""

    provider_name = "disabled"
    model_name = "rule-only"
    enabled = False


async def run(files: list[str]) -> dict:
    try:
        async with async_session() as db:
            service = ImportService(
                db,
                skill_service=SkillService(db, llm_provider=DisabledLLMProvider()),
            )
            return await service.import_files(files)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import crawler JSON with rule-only skill extraction")
    parser.add_argument("files", nargs="+", help="JSON filename(s) under DATA_DIR")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args.files)), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
