"""L4-L5 智能体：主运行脚本

从 MySQL 读取技能和证据 → 调用 DeepSeek 生成 L4-L5 → 验证 → 写入 Neo4j

用法：
    python -m l45_agent.runner
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# 添加项目路径
BACKEND_DIR = Path(__file__).resolve().parents[2] / "fyz-src" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DEEPSEEK_API_KEY", "")
os.environ.setdefault("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
os.environ.setdefault("DEEPSEEK_MODEL", "deepseek-v4-flash")

from dotenv import load_dotenv
load_dotenv()

import aiomysql
from neo4j import GraphDatabase

from .schema import AgentInput, SkillEvidence, AgentOutput
from .agent import L45Agent
from .verify import L45Validator


# ========== 配置（从环境变量读取，不硬编码）==========
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "db": os.getenv("DB_NAME", "jie_bang"),
}

NEO4J_CONFIG = {
    "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    "auth": (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")) if os.getenv("NEO4J_PASSWORD") else None,
}

DEEPSEEK_CONFIG = {
    "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
    "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    "model": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
}

MIN_CONFIDENCE = 0.75
MAX_SKILLS = 20  # 一次跑多少个技能


async def get_skills_from_mysql() -> list[dict]:
    """从 MySQL 读取技能及其证据"""
    conn = await aiomysql.connect(**DB_CONFIG)
    async with conn.cursor() as cur:
        # 找 Top N 非软技能（按关联岗位数排序）
        await cur.execute("""
            SELECT s.id, s.name, s.category,
                   COUNT(DISTINCT jsf.raw_job_record_id) AS evidence_count
            FROM skill s
            JOIN job_skill_fact jsf ON jsf.skill_id = s.id
            WHERE s.category != 'soft_skill'
              AND jsf.verification_status = 'verified'
            GROUP BY s.id, s.name, s.category
            ORDER BY evidence_count DESC
            LIMIT %s
        """, (MAX_SKILLS,))
        skills = await cur.fetchall()

        result = []
        for skill_id, name, category, _ in skills:
            # 获取该技能的证据文本
            await cur.execute("""
                SELECT sd.id, sd.source, jsf.evidence_text
                FROM job_skill_fact jsf
                JOIN raw_job_record rjr ON rjr.id = jsf.raw_job_record_id
                JOIN source_document sd ON sd.id = rjr.source_document_id
                WHERE jsf.skill_id = %s
                  AND jsf.verification_status = 'verified'
                  AND jsf.evidence_text IS NOT NULL
                  AND jsf.evidence_text != ''
                ORDER BY sd.source, jsf.confidence DESC
                LIMIT 8
            """, (skill_id,))
            evidence_rows = await cur.fetchall()

            if len(evidence_rows) < 2:
                continue

            # 关联的岗位方向
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
            """, (skill_id,))
            job_names = [r[0] for r in await cur.fetchall()]

            evidence_list = [
                SkillEvidence(
                    source_doc_id=row[0],
                    source_platform=str(row[1])[:50],
                    evidence_text=str(row[2])[:2000],
                )
                for row in evidence_rows
            ]

            result.append({
                "id": skill_id,
                "name": name,
                "category": category,
                "job_directions": job_names,
                "evidence": evidence_list,
            })

    conn.close()
    return result


def write_to_neo4j(skill_name: str, tech_points: list) -> bool:
    """将验证通过的 L4-L5 写入 Neo4j（同步函数）"""
    from datetime import datetime
    version = datetime.utcnow().strftime("%Y%m%dT%H%M%S")

    driver = GraphDatabase.driver(**NEO4J_CONFIG)
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (t:TechStack {namespace:'jiebang'}) "
                "WHERE t.name = $name RETURN t.id AS id",
                name=skill_name,
            )
            row = result.single()
            if not row:
                print(f"  [WARN] Neo4j 中未找到技能: {skill_name}")
                return False

            skill_id = row["id"]
            ns = "jiebang"

            for pt in tech_points:
                point_id = f"point:{skill_name}:{pt.name.replace(' ', '_')}"

                session.run(
                    f"MERGE (p:TechPoint {{namespace:$ns, id:$id}}) "
                    "SET p.name=$name, p.description=$desc, "
                    "p.confidence=$conf, p.syncVersion=$ver",
                    ns=ns, id=point_id, name=pt.name,
                    desc=pt.detail[:200], conf=pt.confidence,
                    ver=version,
                )
                session.run(
                    f"MERGE (t:TechStack {{namespace:$ns, id:$sid}}) "
                    f"MERGE (p:TechPoint {{namespace:$ns, id:$pid}}) "
                    f"MERGE (t)-[:REFINES_TO {{namespace:$ns}}]->(p)",
                    ns=ns, sid=skill_id, pid=point_id,
                )

                for kp in pt.knowledge_points:
                    kid = f"knowledge:{skill_name}:{kp.name.replace(' ', '_')}"
                    session.run(
                        f"MERGE (k:KnowledgePoint {{namespace:$ns, id:$id}}) "
                        "SET k.name=$name, k.description=$desc, "
                        "k.difficulty=$diff, k.confidence=$conf, "
                        "k.syncVersion=$ver",
                        ns=ns, id=kid, name=kp.name,
                        desc=kp.description[:200], diff=kp.difficulty,
                        conf=kp.confidence,
                        ver=version,
                    )
                    session.run(
                        f"MERGE (p:TechPoint {{namespace:$ns, id:$pid}}) "
                        f"MERGE (k:KnowledgePoint {{namespace:$ns, id:$kid}}) "
                        f"MERGE (p)-[:HAS_KNOWLEDGE {{namespace:$ns}}]->(k)",
                        ns=ns, pid=point_id, kid=kid,
                    )

        return True
    finally:
        driver.close()


async def main():
    print("=" * 55)
    print("  L4-L5 智能体补全")
    print("=" * 55)

    # 1. 读取技能
    print("\n[1/4] 从 MySQL 读取技能...")
    skills = await get_skills_from_mysql()
    print(f"  读取到 {len(skills)} 个技能")

    if not skills:
        print("  没有可处理的技能")
        return

    # 2. 初始化 Agent
    print("\n[2/4] 初始化智能体...")
    agent = L45Agent(**DEEPSEEK_CONFIG)
    validator = L45Validator(min_confidence=MIN_CONFIDENCE)

    if not agent.enabled:
        print("  [ERROR] DeepSeek API Key 未配置")
        return

    print(f"  模型: {DEEPSEEK_CONFIG['model']}")
    print(f"  最低置信度: {MIN_CONFIDENCE}")

    # 3. 逐技能处理
    print(f"\n[3/4] 开始补全 ({len(skills)} 个技能)...")
    results = []
    for i, skill in enumerate(skills, 1):
        name = skill["name"]
        category = skill["category"]
        evidence_count = len(skill["evidence"])

        print(f"\n  [{i}/{len(skills)}] {name}")
        print(f"    领域: {category} | 证据: {evidence_count} 条")

        # 准备输入
        input_data = AgentInput(
            skill_name=name,
            skill_area=category,
            job_directions=skill["job_directions"],
            evidence=skill["evidence"],
        )

        # 调用 DeepSeek
        output = await agent.complete(input_data)

        if not output:
            print(f"  [FAIL] 生成失败")
            results.append({"skill": name, "status": "failed", "reason": "API调用失败"})
            continue

        # 验证
        verified = validator.validate(output)

        if not verified.passed:
            print(f"  [SKIP] {verified.reason}")
            results.append({"skill": name, "status": "skipped", "reason": verified.reason})
            continue

        print(f"  [PASS] 通过 {len(verified.tech_points)} 个技术点")
        for pt in verified.tech_points:
            print(f"    L4: {pt.name} (conf={pt.confidence})")
            for kp in pt.knowledge_points:
                print(f"      L5: {kp.name} [{kp.difficulty}]")

        # 写入 Neo4j
        print(f"  [WRITE] 写入 Neo4j...")
        success = write_to_neo4j(name, verified.tech_points)
        status = "written" if success else "write_failed"
        results.append({"skill": name, "status": status, "reason": verified.reason})

    # 4. 总结
    print(f"\n[4/4] 完成!")
    print(f"\n  汇总:")
    passed = sum(1 for r in results if r["status"] == "written")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    failed = sum(1 for r in results if r["status"] == "failed")
    print(f"  ✅ 已写入: {passed}")
    print(f"  ⏭️  跳过: {skipped}")
    print(f"  ❌ 失败: {failed}")

    # 保存结果
    output_path = Path(__file__).parent / "output.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n  结果已保存: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
