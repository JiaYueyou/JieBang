"""Generate the Phase 2 retrieval and duplicate-negative engineering set."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import async_session, engine
from app.evaluation.phase2_golden import build_dataset, validate_dataset
from app.models import EvidenceChunk, Skill, StandardJob


async def load_evidence_rows() -> list[dict]:
    async with async_session() as session:
        rows = (
            await session.execute(
                select(EvidenceChunk, Skill, StandardJob)
                .join(Skill, EvidenceChunk.skill_id == Skill.id)
                .join(
                    StandardJob,
                    EvidenceChunk.standard_job_id == StandardJob.id,
                )
                .where(
                    EvidenceChunk.verification_status.in_(
                        ("human_approved", "machine_validated")
                    )
                )
                .order_by(
                    Skill.canonical_name,
                    EvidenceChunk.quality_score.desc(),
                    EvidenceChunk.id,
                )
            )
        ).all()
        return [
            {
                "evidence_id": chunk.id,
                "standard_job_id": standard_job.id,
                "standard_job_name": standard_job.name,
                "skill_id": skill.id,
                "skill_name": skill.canonical_name,
                "source_platform": chunk.source_platform,
                "quality_score": float(chunk.quality_score),
                "verification_status": chunk.verification_status,
                "near_duplicate_group_id": (
                    chunk.near_duplicate_group_id
                ),
                "posted_at": (
                    chunk.posted_at.isoformat() if chunk.posted_at else None
                ),
            }
            for chunk, skill, standard_job in rows
        ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            BACKEND_ROOT
            / "evaluation"
            / "phase2_retrieval_golden_set.json"
        ),
    )
    args = parser.parse_args()

    async def run() -> list[dict]:
        try:
            return await load_evidence_rows()
        finally:
            await engine.dispose()

    evidence_rows = asyncio.run(run())
    dataset = build_dataset(evidence_rows)
    validate_dataset(dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "duplicate_negative_cases": len(
                    dataset["duplicate_negative_cases"]
                ),
                "retrieval_cases": len(dataset["retrieval_cases"]),
                "coverage": dataset["coverage"],
                "coverage_gate": dataset["coverage_gate"],
                "release_gate": dataset["release_gate"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
