"""Ground rule-extracted skills for the complete 200-JD graph-fit test.

The imported database snapshot remains untouched. This deployment-time step only
adds missing, source-grounded facts to the running MySQL database and then rebuilds
the namespaced Neo4j read model.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.database import async_session, engine  # noqa: E402
from app.core.neo4j import close_driver, health_detail  # noqa: E402
from app.domain.skill_dictionary import canonical_key  # noqa: E402
from app.models import JobSkillFact, RawJobRecord, Skill, SourceDocument, StandardJob  # noqa: E402
from app.repositories.skill_repository import SkillRepository  # noqa: E402
from app.services.graph_service import GraphService  # noqa: E402
from app.services.skill_extractor import RuleSkillExtractor  # noqa: E402
from scripts.evaluate_extended_jd_graph_fit import SOURCE_QUOTAS  # noqa: E402


async def select_records(session) -> list[RawJobRecord]:
    selected: list[RawJobRecord] = []
    for source, quota in SOURCE_QUOTAS:
        rows = list(
            (
                await session.execute(
                    select(RawJobRecord)
                    .join(SourceDocument, SourceDocument.id == RawJobRecord.source_document_id)
                    .join(StandardJob, StandardJob.id == RawJobRecord.standard_job_id)
                    .where(
                        SourceDocument.source == source,
                        RawJobRecord.quality_status.in_(("accepted", "warning")),
                        RawJobRecord.is_excluded.is_(False),
                    )
                    .order_by(RawJobRecord.id)
                    .limit(quota)
                )
            ).scalars()
        )
        if len(rows) != quota:
            raise RuntimeError(f"{source} only supplied {len(rows)} eligible JDs")
        selected.extend(rows)
    return selected


async def prepare() -> dict[str, int | str]:
    extractor = RuleSkillExtractor()
    inserted = promoted = already_verified = extracted_total = 0
    async with async_session() as session:
        records = await select_records(session)
        repository = SkillRepository(session)
        existing_rows = (
            await session.execute(
                select(JobSkillFact, Skill.canonical_key)
                .join(Skill, Skill.id == JobSkillFact.skill_id)
                .where(JobSkillFact.raw_job_record_id.in_([row.id for row in records]))
            )
        ).all()
        existing = {
            (int(fact.raw_job_record_id), key): fact for fact, key in existing_rows
        }
        for raw in records:
            output = extractor.extract(
                jd_text=raw.jd_text,
                responsibilities=raw.responsibilities,
                requirements=raw.requirements,
            )
            for item in output.skills:
                extracted_total += 1
                key = canonical_key(item.name)
                fact = existing.get((raw.id, key))
                if fact is not None and fact.verification_status == "verified":
                    already_verified += 1
                    continue
                if fact is not None:
                    fact.kind = item.kind.value
                    fact.importance = 0.9 if item.kind.value == "required" else 0.6
                    fact.confidence = item.confidence
                    fact.evidence_text = item.evidence
                    fact.verification_status = "verified"
                    fact.extraction_method = "rule"
                    fact.review_note = "deterministic_exact_evidence_v1"
                    promoted += 1
                    continue
                skill = await repository.get_or_create_skill(
                    name=item.name,
                    canonical_key=key,
                    category=item.category,
                    aliases=[],
                    validation_status="approved",
                )
                session.add(
                    JobSkillFact(
                        raw_job_record_id=raw.id,
                        skill_id=skill.id,
                        kind=item.kind.value,
                        importance=0.9 if item.kind.value == "required" else 0.6,
                        frequency=1,
                        confidence=item.confidence,
                        evidence_text=item.evidence,
                        verification_status="verified",
                        extraction_method="rule",
                        source_count=1,
                        review_note="deterministic_exact_evidence_v1",
                    )
                )
                existing[(raw.id, key)] = None
                inserted += 1
        await session.commit()

    detail = await asyncio.to_thread(health_detail)
    if not detail.startswith("OK"):
        raise RuntimeError(f"Neo4j is unavailable: {detail}")
    async with async_session() as session:
        graph_result = await GraphService(session).sync(
            mode="full", enrich_top_skills=False, user_id=None
        )
    return {
        "selected_jds": len(records),
        "production_extracted_skills": extracted_total,
        "already_verified": already_verified,
        "promoted_grounded_facts": promoted,
        "inserted_grounded_facts": inserted,
        "graph_snapshot_id": graph_result["snapshot_id"],
        "graph_nodes": graph_result["node_count"],
        "graph_edges": graph_result["edge_count"],
    }


async def main_async() -> None:
    try:
        print(await prepare())
    finally:
        close_driver()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main_async())
