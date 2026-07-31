"""Machine-validate a bounded set of skill facts for Phase 2 coverage.

The script is dry-run by default. It only promotes facts that can be
re-extracted from the authoritative raw JD by the current rule extractor.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import async_session, engine
from app.core.time import utc_now
from app.models import (
    JobSkillFact,
    RawJobRecord,
    Skill,
    SourceDocument,
    StandardJob,
)
from app.services.skill_extractor import RuleSkillExtractor

POLICY_VERSION = "phase2-machine-validation-v1"
DEFAULT_JOB_IDS = (1, 2, 5, 26, 29, 32)


async def validate_facts(
    *,
    job_ids: set[int],
    minimum_confidence: float,
    apply_changes: bool,
) -> dict[str, Any]:
    async with async_session() as session:
        rows = (
            await session.execute(
                select(
                    JobSkillFact,
                    RawJobRecord,
                    Skill,
                    StandardJob,
                    SourceDocument,
                )
                .join(
                    RawJobRecord,
                    JobSkillFact.raw_job_record_id == RawJobRecord.id,
                )
                .join(Skill, JobSkillFact.skill_id == Skill.id)
                .join(
                    StandardJob,
                    RawJobRecord.standard_job_id == StandardJob.id,
                )
                .join(
                    SourceDocument,
                    RawJobRecord.source_document_id == SourceDocument.id,
                )
                .where(
                    RawJobRecord.standard_job_id.in_(job_ids),
                    JobSkillFact.verification_status == "unverified",
                    RawJobRecord.quality_status.in_(("accepted", "warning")),
                    RawJobRecord.is_excluded.is_(False),
                    Skill.validation_status == "approved",
                )
                .order_by(StandardJob.id, RawJobRecord.id, JobSkillFact.id)
                .with_for_update()
            )
        ).all()

        found_job_ids = {job.id for _, _, _, job, _ in rows}
        missing_job_ids = sorted(job_ids - found_job_ids)
        if missing_job_ids:
            raise ValueError(
                "No eligible unverified facts found for standard job IDs: "
                + ", ".join(str(value) for value in missing_job_ids)
            )

        extractor = RuleSkillExtractor()
        extracted_by_raw: dict[int, dict[str, Any]] = {}
        rejected = Counter()
        approved_fact_ids: list[int] = []
        by_job: dict[tuple[int, str], dict[str, Any]] = defaultdict(
            lambda: {
                "fact_count": 0,
                "skill_names": set(),
                "raw_job_ids": set(),
                "sources": set(),
            }
        )
        reviewed_at = utc_now()

        for fact, raw, skill, job, source in rows:
            if raw.id not in extracted_by_raw:
                output = extractor.extract(
                    jd_text=raw.jd_text,
                    responsibilities=raw.responsibilities,
                    requirements=raw.requirements,
                )
                extracted_by_raw[raw.id] = {
                    item.name: item for item in output.skills
                }

            extracted = extracted_by_raw[raw.id].get(skill.canonical_name)
            if extracted is None:
                rejected["not_reextracted"] += 1
                continue
            if extracted.confidence < minimum_confidence:
                rejected["low_confidence"] += 1
                continue

            approved_fact_ids.append(fact.id)
            summary = by_job[(job.id, job.name)]
            summary["fact_count"] += 1
            summary["skill_names"].add(skill.canonical_name)
            summary["raw_job_ids"].add(raw.id)
            summary["sources"].add(source.source)

            if apply_changes:
                fact.verification_status = "verified"
                fact.reviewed_by = None
                fact.reviewed_at = reviewed_at
                fact.review_note = (
                    f"{POLICY_VERSION}; rule re-extracted "
                    f"{skill.canonical_name}; confidence="
                    f"{extracted.confidence:.2f}; authority=mysql"
                )

        if apply_changes:
            await session.commit()
        else:
            await session.rollback()

        jobs = [
            {
                "standard_job_id": job_id,
                "standard_job_name": job_name,
                "fact_count": values["fact_count"],
                "skill_count": len(values["skill_names"]),
                "raw_job_count": len(values["raw_job_ids"]),
                "sources": sorted(values["sources"]),
            }
            for (job_id, job_name), values in sorted(by_job.items())
        ]
        return {
            "policy_version": POLICY_VERSION,
            "mode": "apply" if apply_changes else "dry_run",
            "minimum_confidence": minimum_confidence,
            "selected_job_ids": sorted(job_ids),
            "candidate_count": len(rows),
            "approved_count": len(approved_fact_ids),
            "rejected_count": sum(rejected.values()),
            "rejected_reasons": dict(rejected),
            "coverage": {
                "standard_job_count": len(jobs),
                "skill_count": len(
                    {
                        skill_name
                        for values in by_job.values()
                        for skill_name in values["skill_names"]
                    }
                ),
                "source_platform_count": len(
                    {
                        source
                        for values in by_job.values()
                        for source in values["sources"]
                    }
                ),
            },
            "jobs": jobs,
        }


async def revert_policy() -> dict[str, Any]:
    async with async_session() as session:
        facts = list(
            (
                await session.execute(
                    select(JobSkillFact)
                    .where(
                        JobSkillFact.verification_status == "verified",
                        JobSkillFact.reviewed_by.is_(None),
                        JobSkillFact.review_note.like(
                            f"{POLICY_VERSION};%"
                        ),
                    )
                    .with_for_update()
                )
            ).scalars()
        )
        for fact in facts:
            fact.verification_status = "unverified"
            fact.reviewed_at = None
            fact.review_note = None
        await session.commit()
        return {
            "policy_version": POLICY_VERSION,
            "mode": "revert",
            "reverted_count": len(facts),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--job-id",
        type=int,
        action="append",
        help=(
            "Standard job ID to validate; repeat as needed. "
            "Defaults to the reviewed Phase 2 coverage set."
        ),
    )
    parser.add_argument(
        "--minimum-confidence",
        type=float,
        default=0.70,
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist approved facts. Without this flag the run is read-only.",
    )
    parser.add_argument(
        "--revert",
        action="store_true",
        help="Revert only facts promoted by this policy version.",
    )
    args = parser.parse_args()
    if args.apply and args.revert:
        parser.error("--apply and --revert are mutually exclusive")
    if not 0 <= args.minimum_confidence <= 1:
        parser.error("--minimum-confidence must be between 0 and 1")

    async def run() -> dict[str, Any]:
        try:
            if args.revert:
                return await revert_policy()
            return await validate_facts(
                job_ids=set(args.job_id or DEFAULT_JOB_IDS),
                minimum_confidence=args.minimum_confidence,
                apply_changes=args.apply,
            )
        finally:
            await engine.dispose()

    print(json.dumps(asyncio.run(run()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
