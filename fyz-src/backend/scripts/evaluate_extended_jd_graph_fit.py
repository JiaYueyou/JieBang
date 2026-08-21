"""Evaluate 100 additional official-source JDs and their graph grounding."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.database import async_session, engine  # noqa: E402
from app.core.neo4j import close_driver, run_read  # noqa: E402
from app.models import (  # noqa: E402
    JobSkillFact,
    RawJobRecord,
    Skill,
    SourceDocument,
    StandardJob,
)
from app.services.skill_extractor import RuleSkillExtractor  # noqa: E402


SOURCE_QUOTAS = (
    ("字节跳动招聘", 39),
    ("京东官方社会招聘门户（zhaopin.jd.com）", 25),
    ("美团官方社会招聘门户（zhaopin.meituan.com）", 18),
    ("智谱AI官网招聘（官网加入我们页跳转的Moka招聘站）", 12),
    ("DeepSeek官方招聘门户（talent.deepseek.com）", 3),
    ("长鑫存储官方招聘门户（北森；由 cxmt.com/join.html 链接）", 3),
)


def ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


async def evaluate() -> tuple[dict[str, Any], dict[str, Any]]:
    selected: list[tuple[RawJobRecord, SourceDocument, StandardJob]] = []
    async with async_session() as session:
        for source, quota in SOURCE_QUOTAS:
            rows = (
                await session.execute(
                    select(RawJobRecord, SourceDocument, StandardJob)
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
            ).all()
            if len(rows) != quota:
                raise RuntimeError(f"{source} only supplied {len(rows)} eligible JDs")
            selected.extend(rows)

        raw_ids = [raw.id for raw, _, _ in selected]
        fact_rows = (
            await session.execute(
                select(JobSkillFact, Skill)
                .join(Skill, Skill.id == JobSkillFact.skill_id)
                .where(
                    JobSkillFact.raw_job_record_id.in_(raw_ids),
                    JobSkillFact.verification_status == "verified",
                    Skill.validation_status == "approved",
                )
                .order_by(JobSkillFact.raw_job_record_id, JobSkillFact.id)
            )
        ).all()

    facts_by_raw: dict[int, list[tuple[JobSkillFact, Skill]]] = defaultdict(list)
    graph_checks: list[dict[str, Any]] = []
    for fact, skill in fact_rows:
        facts_by_raw[int(fact.raw_job_record_id)].append((fact, skill))
    for raw, document, _ in selected:
        for fact, skill in facts_by_raw[raw.id]:
            graph_checks.append({
                "raw_id": raw.id,
                "document_id": document.id,
                "standard_job_id": raw.standard_job_id,
                "skill_id": skill.id,
                "category": skill.category,
            })

    graph_rows = run_read(
        """
        UNWIND $checks AS c
        OPTIONAL MATCH (job:Job {namespace:$namespace, id:'job:' + toString(c.standard_job_id)})
        OPTIONAL MATCH (area:SkillArea {namespace:$namespace, id:'area:' + c.category})
        OPTIONAL MATCH (skill:TechStack {namespace:$namespace, id:'skill:' + toString(c.skill_id)})
        OPTIONAL MATCH (source:SourceDocument {namespace:$namespace, id:'source:' + toString(c.document_id)})
        OPTIONAL MATCH (job)-[r1:REQUIRES_AREA {namespace:$namespace}]->(area)
        OPTIONAL MATCH (area)-[r2:CONTAINS {namespace:$namespace}]->(skill)
        OPTIONAL MATCH (source)-[r3:SUPPORTS {namespace:$namespace}]->(skill)
        OPTIONAL MATCH (source)-[r4:SUPPORTS {namespace:$namespace}]->(job)
        RETURN c.raw_id AS raw_id, c.skill_id AS skill_id,
               job IS NOT NULL AND area IS NOT NULL AND skill IS NOT NULL
                 AND r1 IS NOT NULL AND r2 IS NOT NULL AS graph_path,
               source IS NOT NULL AND r3 IS NOT NULL AND r4 IS NOT NULL AS source_trace
        """,
        {"checks": graph_checks, "namespace": "jiebang"},
    )
    graph_lookup = {
        (int(row["raw_id"]), int(row["skill_id"])): row for row in graph_rows
    }

    extractor = RuleSkillExtractor()
    cases: list[dict[str, Any]] = []
    total_facts = graph_paths = source_traces = grounded_facts = 0
    extracted_total = extracted_confirmed = complete_fields = 0
    source_counts: dict[str, int] = defaultdict(int)
    for index, (raw, document, standard_job) in enumerate(selected, 1):
        source_counts[document.source] += 1
        extracted = extractor.extract(
            jd_text=raw.jd_text,
            responsibilities=raw.responsibilities,
            requirements=raw.requirements,
        )
        extracted_names = {item.name for item in extracted.skills}
        facts = facts_by_raw[raw.id]
        fact_names = {skill.canonical_name for _, skill in facts}
        extracted_total += len(extracted_names)
        extracted_confirmed += len(extracted_names & fact_names)
        required_fields = {
            "title": bool(raw.title.strip()),
            "company": bool((raw.company or "").strip()),
            "jd_text": len(raw.jd_text.strip()) >= 50,
            "source_url": bool((document.url or "").strip()),
            "standard_job": raw.standard_job_id is not None,
        }
        complete_fields += int(all(required_fields.values()))
        fact_outputs = []
        for fact, skill in facts:
            graph = graph_lookup.get((raw.id, skill.id), {})
            evidence_grounded = bool(fact.evidence_text.strip()) and (
                fact.evidence_text.strip() in raw.jd_text
            )
            total_facts += 1
            grounded_facts += int(evidence_grounded)
            graph_paths += int(bool(graph.get("graph_path")))
            source_traces += int(bool(graph.get("source_trace")))
            fact_outputs.append({
                "skill_id": skill.id,
                "skill_name": skill.canonical_name,
                "skill_category": skill.category,
                "importance": fact.importance,
                "confidence": fact.confidence,
                "evidence_text": fact.evidence_text,
                "evidence_in_original_jd": evidence_grounded,
                "job_area_skill_path_exists": bool(graph.get("graph_path")),
                "source_support_edges_exist": bool(graph.get("source_trace")),
            })
        raw_input = {
            "source": document.source,
            "source_url": document.url,
            "external_id": document.external_id,
            "title": raw.title,
            "company": raw.company,
            "city": raw.city,
            "salary": raw.salary_text,
            "experience": raw.experience_text,
            "education": raw.education_text,
            "responsibilities": raw.responsibilities,
            "requirements": raw.requirements,
            "jd_text": raw.jd_text,
            "posted_at": raw.posted_at.isoformat() if raw.posted_at else raw.posted_at_text,
            "crawled_at": raw.crawled_at.isoformat() if raw.crawled_at else raw.crawled_at_text,
        }
        cases.append({
            "case_id": f"ADD-JD-{index:03d}",
            "input_sha256": hashlib.sha256(
                json.dumps(raw_input, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "input": raw_input,
            "standard_job": {
                "id": standard_job.id,
                "name": standard_job.name,
                "stack": standard_job.stack,
                "level": standard_job.level,
            },
            "field_checks": required_fields,
            "production_extracted_skills": sorted(extracted_names),
            "verified_graph_skills": fact_outputs,
        })

    metrics = {
        "jd_count": len(cases),
        "source_count": len(source_counts),
        "source_distribution": dict(source_counts),
        "unique_url_count": len({case["input"]["source_url"] for case in cases}),
        "unique_content_count": len({case["input_sha256"] for case in cases}),
        "complete_record_rate": ratio(complete_fields, len(cases)),
        "standard_job_mapping_rate": ratio(
            sum(case["standard_job"]["id"] is not None for case in cases), len(cases)
        ),
        "verified_skill_fact_count": total_facts,
        "jd_evidence_grounding_rate": ratio(grounded_facts, total_facts),
        "job_area_skill_graph_path_rate": ratio(graph_paths, total_facts),
        "source_traceability_rate": ratio(source_traces, total_facts),
        "production_extraction_confirmation_rate": ratio(
            extracted_confirmed, extracted_total
        ),
    }
    fit_components = (
        metrics["jd_evidence_grounding_rate"],
        metrics["job_area_skill_graph_path_rate"],
        metrics["source_traceability_rate"],
        metrics["production_extraction_confirmation_rate"],
    )
    metrics["job_requirement_graph_fit_score"] = round(
        sum(fit_components) / len(fit_components), 6
    )
    gates = {
        "additional_100_real_jds": len(cases) == 100,
        "six_new_official_sources": len(source_counts) == 6,
        # Official portals may reuse a generic detail URL; content identity is the
        # correct deduplication key for raw JD records.
        "all_jd_contents_unique": metrics["unique_content_count"] == len(cases),
        "complete_record_rate_at_least_95_percent": metrics["complete_record_rate"] >= 0.95,
        "standard_job_mapping_at_least_95_percent": metrics["standard_job_mapping_rate"] >= 0.95,
        "jd_evidence_grounding_at_least_95_percent": metrics["jd_evidence_grounding_rate"] >= 0.95,
        "graph_path_at_least_95_percent": metrics["job_area_skill_graph_path_rate"] >= 0.95,
        "source_traceability_at_least_95_percent": metrics["source_traceability_rate"] >= 0.95,
        "extraction_confirmation_at_least_90_percent": metrics["production_extraction_confirmation_rate"] >= 0.90,
        "job_requirement_graph_fit_at_least_95_percent": metrics["job_requirement_graph_fit_score"] >= 0.95,
    }
    generated = datetime.now(timezone.utc).isoformat()
    raw_report = {
        "dataset_version": "competition-additional-jd-100-v1",
        "generated_at": generated,
        "scope": "100 additional technical JDs from six official recruitment portals",
        "metrics": metrics,
        "gates": gates,
        "passed": all(gates.values()),
        "cases": cases,
    }
    graph_report = {
        "dataset_version": "competition-graph-job-fit-100-v1",
        "generated_at": generated,
        "test_chain": "original JD -> verified skill fact -> standard job/skill-area/skill graph path -> source support edges",
        "metric_definitions": {
            "jd_evidence_grounding_rate": "verified skill facts whose evidence text appears in the original JD / all verified skill facts",
            "job_area_skill_graph_path_rate": "verified skill facts represented by complete Job->SkillArea->TechStack paths / all verified skill facts",
            "source_traceability_rate": "verified skill facts with SourceDocument->Skill and SourceDocument->Job support edges / all verified skill facts",
            "production_extraction_confirmation_rate": "production-extracted skills confirmed by verified job facts / all production-extracted skills",
            "job_requirement_graph_fit_score": "mean of evidence grounding, complete graph path, source traceability, and production extraction confirmation rates",
        },
        "metrics": metrics,
        "gates": gates,
        "passed": all(gates.values()),
        "case_reference": "additional_jd_100_cases.json",
    }
    return raw_report, graph_report


async def main_async(args: argparse.Namespace) -> int:
    try:
        raw_report, graph_report = await evaluate()
    finally:
        await engine.dispose()
        close_driver()
    args.jd_output.parent.mkdir(parents=True, exist_ok=True)
    args.jd_output.write_text(json.dumps(raw_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.graph_output.write_text(json.dumps(graph_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"metrics": raw_report["metrics"], "gates": raw_report["gates"]}, ensure_ascii=False))
    return 0 if raw_report["passed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jd-output", type=Path, default=BACKEND / "evaluation" / "additional_jd_100_cases.json")
    parser.add_argument("--graph-output", type=Path, default=BACKEND / "evaluation" / "graph_job_fit_report.json")
    return asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
