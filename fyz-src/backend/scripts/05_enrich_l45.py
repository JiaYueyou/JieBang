"""Step 5: L4-L5 Agent enrichment using DeepSeek.

Usage:
    python scripts/05_enrich_l45.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv()

from app.core.database import engine, async_session
from app.core.neo4j import health_detail, close_driver
from app.core.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

AGENT_DIR = Path(__file__).resolve().parents[2] / "agent-development"
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from l45_agent.schema import AgentInput, SkillEvidence
from l45_agent.agent import L45Agent
from l45_agent.verify import L45Validator

MIN_CONFIDENCE = 0.75
COVERAGE_THRESHOLD = 0.95  # 累计覆盖证据量达此比例时停止纳入新技能
EVIDENCE_CAP = 20  # 送大模型的证据上限


def select_evidence_proportionally(rows: list[tuple], cap: int = EVIDENCE_CAP) -> list[tuple]:
    """按来源比例选择证据，每个来源至少保底 1 条"""
    if not rows:
        return []

    # 按来源分组，每组内保持原序（已按置信度降序）
    from collections import OrderedDict
    groups: dict[str, list[tuple]] = OrderedDict()
    for r in rows:
        src = str(r[1])  # source_platform
        groups.setdefault(src, []).append(r)

    sources = list(groups.keys())
    num_sources = len(sources)

    # 边界：来源数超过 cap，按来源证据数降序取前 cap 个来源各 1 条
    if num_sources >= cap:
        sorted_srcs = sorted(sources, key=lambda s: len(groups[s]), reverse=True)
        result = []
        for src in sorted_srcs[:cap]:
            result.append(groups[src][0])
        return result

    # 阶段1：每来源保底 1 条
    remaining = cap - num_sources

    # 阶段2：按比例分配剩余名额
    total_rows = len(rows)
    extra: dict[str, int] = {}
    allocated = 0
    for src in sources:
        e = int(len(groups[src]) / total_rows * remaining)
        extra[src] = e
        allocated += e

    # 处理余数（按小数部分从大到小分配）
    remainder = remaining - allocated
    if remainder > 0:
        fracs = [(src, len(groups[src]) / total_rows - extra[src] / remaining)
                 for src in sources]
        fracs.sort(key=lambda x: -x[1])
        for i in range(remainder):
            extra[fracs[i][0]] += 1

    # 组装结果
    result = []
    for src in sources:
        take = 1 + extra.get(src, 0)
        result.extend(groups[src][:take])
    return result


async def enrich() -> dict:
    """Read skills from MySQL -> LLM enrichment -> verify -> write to Neo4j"""
    detail = await asyncio.to_thread(health_detail)
    if not detail.startswith("OK"):
        raise RuntimeError(f"Neo4j unavailable: {detail}")
    print(f"[5/5] {detail}")

    agent = L45Agent(
        api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
    )
    validator = L45Validator(min_confidence=MIN_CONFIDENCE)

    if not agent.enabled:
        print("[5/5] No DeepSeek API key, skipping L4-L5 enrichment")
        return {"status": "skipped", "reason": "no_api_key"}

    print(f"[5/5] Model: {agent.model}, Min confidence: {MIN_CONFIDENCE}")

    # Read skills from MySQL
    import aiomysql
    conn = await aiomysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        db=os.getenv("DB_NAME", "jie_bang"),
    )

    skills_data = []
    async with conn.cursor() as cur:
        # 先查所有技能的证据数，算动态 cutoff
        await cur.execute("""
            SELECT s.id, s.name, s.category, COUNT(jsf.id) AS total_evidence
            FROM skill s
            JOIN job_skill_fact jsf ON jsf.skill_id = s.id
            WHERE s.category != 'soft_skill'
              AND jsf.verification_status = 'verified'
            GROUP BY s.id
            ORDER BY total_evidence DESC
        """)
        all_skills = await cur.fetchall()
        total_evidence = sum(r[3] for r in all_skills)
        cumulative = 0
        cutoff_count = 0
        for r in all_skills:
            cumulative += r[3]
            cutoff_count += 1
            if cumulative / total_evidence >= COVERAGE_THRESHOLD:
                break
        skills = all_skills[:cutoff_count]
        print(f"[5/5] Total skills: {len(all_skills)}, "
              f"selected {cutoff_count} (cover {cumulative/total_evidence*100:.0f}% evidence)")

        for sid, name, category, _evidence_cnt in skills:
            # 先查真实证据数（无 LIMIT），用于置信度计算
            await cur.execute("""
                SELECT COUNT(*) FROM job_skill_fact
                WHERE skill_id = %s
                  AND verification_status = 'verified'
                  AND evidence_text IS NOT NULL AND evidence_text != ''
            """, (sid,))
            real_evidence_count = (await cur.fetchone())[0]
            if real_evidence_count < 2:
                continue

            # 取该技能全部证据（无 LIMIT），再用 Python 按来源比例选择
            await cur.execute("""
                SELECT sd.id, sd.source, jsf.evidence_text
                FROM job_skill_fact jsf
                JOIN raw_job_record rjr ON rjr.id = jsf.raw_job_record_id
                JOIN source_document sd ON sd.id = rjr.source_document_id
                WHERE jsf.skill_id = %s
                  AND jsf.verification_status = 'verified'
                  AND jsf.evidence_text IS NOT NULL AND jsf.evidence_text != ''
                ORDER BY jsf.confidence DESC
            """, (sid,))
            all_evidence = await cur.fetchall()
            evidence = select_evidence_proportionally(all_evidence, EVIDENCE_CAP)

            await cur.execute("""
                SELECT DISTINCT sj.name
                FROM standard_job sj
                JOIN standard_job_source sjs ON sjs.standard_job_id = sj.id
                JOIN job_skill_fact jsf2 ON (
                    (sjs.source_type = 'raw' AND jsf2.raw_job_record_id = sjs.source_id)
                    OR (sjs.source_type = 'internal' AND jsf2.job_id = sjs.source_id)
                )
                WHERE jsf2.skill_id = %s
                LIMIT 5
            """, (sid,))
            jobs = [r[0] for r in await cur.fetchall()]

            skills_data.append({
                "name": name,
                "category": category,
                "jobs": jobs,
                "real_count": real_evidence_count,
                "evidence": [SkillEvidence(
                    source_doc_id=int(r[0]),
                    source_platform=str(r[1])[:50],
                    evidence_text=str(r[2])[:2000],
                ) for r in evidence],
            })
    conn.close()
    print(f"[5/5] Loaded {len(skills_data)} skills for enrichment")

    if not skills_data:
        return {"status": "done", "skills_processed": 0}

    # 按方向(类别)分别计算最大来源数（使用真实证据数，非 LIMIT 截断后）
    from collections import defaultdict
    cat_max: dict[str, int] = defaultdict(int)
    for s in skills_data:
        cat = s["category"]
        cat_max[cat] = max(cat_max[cat], s["real_count"])
    print(f"[5/5] Real max evidence sources per category (unlimited):")
    for cat, mx in sorted(cat_max.items(), key=lambda x: -x[1]):
        print(f"      {cat}: {mx}")
    print(f"[5/5] Global max: {max(cat_max.values())}")

    # Enrich and write to Neo4j
    from datetime import datetime
    from neo4j import GraphDatabase

    version = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    neo4j_driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD) if NEO4J_PASSWORD else None,
    )

    results = []
    for i, skill in enumerate(skills_data, 1):
        name = skill["name"]
        print(f"\n  [{i}/{len(skills_data)}] {name}")

        input_data = AgentInput(
            skill_name=name,
            skill_area=skill["category"],
            job_directions=skill["jobs"],
            evidence=skill["evidence"],
        )

        output = await agent.complete(input_data)
        if not output:
            results.append({"skill": name, "status": "failed"})
            continue

        evidence_count = skill["real_count"]
        category_max = cat_max.get(skill["category"], evidence_count)
        verified = validator.validate(
            output,
            evidence_count=evidence_count,
            max_evidence_count=category_max,
        )
        if not verified.passed:
            results.append({"skill": name, "status": "skipped", "reason": verified.reason})
            continue

        with neo4j_driver.session() as session:
            skill_node = session.run(
                "MATCH (t:TechStack {namespace:'jiebang'}) WHERE t.name = $n RETURN t.id",
                n=name,
            ).single()
            if not skill_node:
                results.append({"skill": name, "status": "skipped", "reason": "not_in_neo4j"})
                continue

            sid = skill_node[0]
            ns = "jiebang"
            l4n, l5n = 0, 0

            for pt in verified.tech_points:
                pid = f"point:{name}:{pt.name.replace(' ', '_')}"
                session.run(
                    f"MERGE (p:TechPoint {{namespace:$ns, id:$id}}) "
                    "SET p.name=$n, p.description=$d, p.confidence=$c, p.syncVersion=$v",
                    ns=ns, id=pid, n=pt.name, d=pt.detail[:200], c=pt.confidence, v=version,
                )
                session.run(
                    f"MERGE (t:TechStack {{namespace:$ns, id:$sid}}) "
                    f"MERGE (p:TechPoint {{namespace:$ns, id:$pid}}) "
                    f"MERGE (t)-[:REFINES_TO {{namespace:$ns}}]->(p)",
                    ns=ns, sid=sid, pid=pid,
                )
                l4n += 1

                for kp in pt.knowledge_points:
                    kid = f"knowledge:{name}:{kp.name.replace(' ', '_')}"
                    session.run(
                        f"MERGE (k:KnowledgePoint {{namespace:$ns, id:$id}}) "
                        "SET k.name=$n, k.description=$d, k.difficulty=$diff, "
                        "k.confidence=$c, k.syncVersion=$v",
                        ns=ns, id=kid, n=kp.name, d=kp.description[:200],
                        diff=kp.difficulty, c=kp.confidence, v=version,
                    )
                    session.run(
                        f"MERGE (p:TechPoint {{namespace:$ns, id:$pid}}) "
                        f"MERGE (k:KnowledgePoint {{namespace:$ns, id:$kid}}) "
                        f"MERGE (p)-[:HAS_KNOWLEDGE {{namespace:$ns}}]->(k)",
                        ns=ns, pid=pid, kid=kid,
                    )
                    l5n += 1

            results.append({"skill": name, "status": "written", "l4": l4n, "l5": l5n})
            print(f"    -> {l4n} L4 + {l5n} L5 written")

    neo4j_driver.close()

    written = sum(1 for r in results if r["status"] == "written")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    failed = sum(1 for r in results if r["status"] == "failed")
    tl4 = sum(r.get("l4", 0) for r in results)
    tl5 = sum(r.get("l5", 0) for r in results)

    summary = {
        "status": "done",
        "total": len(skills_data),
        "written": written,
        "skipped": skipped,
        "failed": failed,
        "l4": tl4,
        "l5": tl5,
    }

    print(f"\n[5/5] Done: {written} skills ({tl4} L4 + {tl5} L5), "
          f"{skipped} skipped, {failed} failed")

    out_path = BACKEND_DIR / "scripts" / "l45_output.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"  Results saved to {out_path}")

    return summary


async def main():
    print("[5/5] L4-L5 Agent Enrichment (DeepSeek)\n")
    try:
        await enrich()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
