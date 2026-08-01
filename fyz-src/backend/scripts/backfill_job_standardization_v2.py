"""Preview or apply deterministic job-title V2 backfill.

The default is read-only. Use ``--apply`` only after reviewing the collision
summary; ambiguous standard-job merges are deliberately left for review.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select

from app.core.database import async_session, engine
from app.domain.job_standardizer import normalize_job_title
from app.models import RawJobRecord, StandardJob, StandardJobAlias


async def run(*, apply: bool) -> dict[str, int]:
    summary: Counter[str] = Counter()
    async with async_session() as db:
        standards = list((await db.execute(select(StandardJob).order_by(StandardJob.id))).scalars())
        occupied = {row.canonical_key: row.id for row in standards}
        for row in standards:
            normalized = normalize_job_title(row.name)
            owner = occupied.get(normalized.canonical_key)
            if owner not in (None, row.id):
                summary["standard_collisions"] += 1
                continue
            summary["standard_jobs"] += 1
            if apply:
                occupied.pop(row.canonical_key, None)
                occupied[normalized.canonical_key] = row.id
                row.canonical_key = normalized.canonical_key
                row.level = normalized.level
                row.role_family = normalized.role_family
                row.specialization_key = normalized.specialization_key
                row.occupation_code = normalized.occupation_code
                row.normalization_version = normalized.version

        raws = list((await db.execute(select(RawJobRecord).order_by(RawJobRecord.id))).scalars())
        for raw in raws:
            normalized = normalize_job_title(
                raw.title, city=raw.city, company=raw.company, jd_text=raw.jd_text
            )
            summary[normalized.status] += 1
            if not apply:
                continue
            raw.standardized_title = normalized.name
            raw.city_code = normalized.city_code
            raw.company_key = normalized.company_key
            raw.work_mode = normalized.work_mode
            raw.employment_type = normalized.employment_type
            raw.normalization_version = normalized.version
            raw.normalization_status = normalized.status
            raw.normalization_confidence = normalized.confidence
            raw.normalized_data = {
                **(raw.normalized_data or {}),
                "job_title": {
                    "role_family": normalized.role_family,
                    "specialization_key": normalized.specialization_key,
                    "occupation_code": normalized.occupation_code,
                    "level": normalized.level,
                    "city_code": normalized.city_code,
                    "work_mode": normalized.work_mode,
                    "employment_type": normalized.employment_type,
                    "version": normalized.version,
                },
            }
            if raw.standard_job_id:
                alias_key = "".join(ch for ch in raw.title.casefold() if ch.isalnum())
                exists = await db.scalar(select(StandardJobAlias.id).where(
                    StandardJobAlias.standard_job_id == raw.standard_job_id,
                    StandardJobAlias.alias_key == alias_key,
                ))
                if exists is None:
                    db.add(StandardJobAlias(
                        standard_job_id=raw.standard_job_id,
                        alias=raw.title,
                        alias_key=alias_key,
                        source_type="raw",
                        confidence=normalized.confidence,
                        normalization_version=normalized.version,
                    ))
        if apply:
            await db.commit()
    await engine.dispose()
    return dict(summary)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill job normalization V2")
    parser.add_argument("--apply", action="store_true", help="Persist non-conflicting updates")
    args = parser.parse_args()
    summary = asyncio.run(run(apply=args.apply))
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] {summary}")
    if summary.get("standard_collisions"):
        print("Colliding standard jobs were not merged; review them before applying a manual merge.")


if __name__ == "__main__":
    main()
