"""
Step 3: 技能提取
─────────────────────
加载标准化数据 → 复用后端 RuleSkillExtractor → 规则匹配技能 → 构建技能词典
→ 岗位-技能关联矩阵 → 输出 skill_dict.json + job_skill_matrix.json
"""

from collections import Counter, defaultdict

from skill_extractor import RuleSkillExtractor, normalize_text
from skill_dictionary import SKILL_CATEGORIES

from utils import (
    OUTPUT_MERGED,
    OUTPUT_SKILL_DICT,
    OUTPUT_JOB_SKILL_MATRIX,
    read_json,
    write_json,
    log,
    log_sep,
)


def extract_record(extractor: RuleSkillExtractor, record: dict) -> dict | None:
    """对单条记录执行技能抽取，返回技能列表。"""
    jd_text = record.get("jd_text", "")
    responsibilities = record.get("responsibilities", "")
    requirements = record.get("requirements", "")

    if not jd_text and not responsibilities and not requirements:
        log("WARN", f"JD 文本为空: {record.get('title', '?')}")
        return None

    try:
        result = extractor.extract(
            jd_text=normalize_text(jd_text),
            responsibilities=normalize_text(responsibilities),
            requirements=normalize_text(requirements),
        )
        return {
            "skills": [
                {
                    "name": s.name,
                    "category": s.category,
                    "kind": s.kind.value,
                    "confidence": round(s.confidence, 2),
                    "evidence": s.evidence[:200] if s.evidence else "",
                }
                for s in result.skills
            ],
            "skill_count": len(result.skills),
        }
    except Exception as e:
        log("ERROR", f"抽取失败: {record.get('title', '?')} — {e}")
        return {"skills": [], "skill_count": 0}


def build_job_skill_matrix(records: list[dict]) -> list[dict]:
    """为每条记录构建岗位-技能关联。"""
    extractor = RuleSkillExtractor()
    matrix: list[dict] = []

    for i, record in enumerate(records):
        result = extract_record(extractor, record)
        if result is None:
            continue

        entry = {
            "original_title": record.get("title", ""),
            "standardized_title": record.get("standardized_title", ""),
            "canonical_key": record.get("canonical_key", ""),
            "company": record.get("company", ""),
            "source_tag": record.get("source_tag", ""),
            "level": record.get("level", ""),
            "stack": record.get("stack", ""),
            "core_skills": [s for s in result["skills"] if s["kind"] == "required"],
            "bonus_skills": [s for s in result["skills"] if s["kind"] == "preferred"],
            "total_skills": result["skill_count"],
        }
        matrix.append(entry)

        if (i + 1) % 50 == 0:
            log("EXTRACT", f"已抽取 {i + 1}/{len(records)}")

    log("EXTRACT", f"全部 {len(records)} 条抽取完成")
    return matrix


def build_skill_dict(matrix: list[dict]) -> dict:
    """聚合所有抽取到的技能，计算频次/来源分布/分类统计。"""
    skill_entries: dict[str, dict] = {}
    source_skills: dict[str, set[str]] = defaultdict(set)

    for entry in matrix:
        src = entry["source_tag"]
        for s in entry["core_skills"] + entry["bonus_skills"]:
            name = s["name"]
            if name not in skill_entries:
                skill_entries[name] = {
                    "name": name,
                    "category": s["category"],
                    "total_mentions": 0,
                    "job_count": 0,
                    "as_core": 0,
                    "as_bonus": 0,
                    "sources": set(),
                    "confidence_sum": 0.0,
                }
            se = skill_entries[name]
            se["total_mentions"] += 1
            se["confidence_sum"] += s["confidence"]
            if s["kind"] == "required":
                se["as_core"] += 1
            else:
                se["as_bonus"] += 1
            se["sources"].add(src)

    # 计算 job_count（该技能出现在多少个标准化岗位中）
    skill_jobs: dict[str, set[str]] = defaultdict(set)
    for entry in matrix:
        std_title = entry["standardized_title"]
        for s in entry["core_skills"] + entry["bonus_skills"]:
            skill_jobs[s["name"]].add(std_title)

    for name, se in skill_entries.items():
        se["job_count"] = len(skill_jobs[name])
        se["avg_confidence"] = round(se["confidence_sum"] / se["total_mentions"], 2) if se["total_mentions"] else 0
        se["sources"] = sorted(se["sources"])
        del se["confidence_sum"]

    # 按总提及次数降序排列
    sorted_skills = sorted(skill_entries.values(), key=lambda x: -x["total_mentions"])

    # 分类统计
    cat_counts = Counter(se["category"] for se in sorted_skills)
    cat_labels = {k: v for k, v in SKILL_CATEGORIES.items() if v}

    return {
        "total_skills": len(sorted_skills),
        "total_mentions": sum(se["total_mentions"] for se in sorted_skills),
        "category_distribution": {
            cat_labels.get(cat, cat): cnt
            for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1])
        },
        "skills": sorted_skills,
    }


def summary(matrix: list[dict], skill_dict: dict) -> None:
    """打印技能提取统计。"""
    records_with_skills = sum(1 for e in matrix if e["total_skills"] > 0)
    records_without = sum(1 for e in matrix if e["total_skills"] == 0)
    avg_skills = sum(e["total_skills"] for e in matrix) / max(len(matrix), 1)
    total_core = sum(len(e["core_skills"]) for e in matrix)
    total_bonus = sum(len(e["bonus_skills"]) for e in matrix)

    print(f"\n  岗位记录数: {len(matrix)}")
    print(f"  抽到技能的岗位: {records_with_skills}")
    print(f"  未抽到技能的岗位: {records_without}")
    print(f"  平均每岗位技能数: {avg_skills:.1f}")
    print(f"  核心技能总频次: {total_core}")
    print(f"  加分技能总频次: {total_bonus}")
    print(f"\n  唯一技能数: {skill_dict['total_skills']}")
    print(f"  技能总提及: {skill_dict['total_mentions']}")

    print(f"\n  技能分类分布:")
    for cat, cnt in skill_dict["category_distribution"].items():
        print(f"    {cat}: {cnt}")

    print(f"\n  热门技能 Top 20:")
    for s in skill_dict["skills"][:20]:
        print(f"    {s['name']:<20s}  {s['category']:<20s}  提及={s['total_mentions']:<3d}  岗位={s['job_count']:<2d}")


def main() -> None:
    log_sep("Step 3: 技能提取")

    # 1. 加载
    records = read_json(OUTPUT_MERGED)
    log("LOAD", f"加载 {len(records)} 条标准化记录")

    # 2. 构建岗位-技能矩阵
    matrix = build_job_skill_matrix(records)
    log("MATRIX", f"岗位-技能矩阵: {len(matrix)} 条记录")

    # 3. 聚合技能词典
    skill_dict = build_skill_dict(matrix)
    log("DICT", f"技能词典: {skill_dict['total_skills']} 个唯一技能")

    # 4. 输出
    write_json(skill_dict, OUTPUT_SKILL_DICT)
    write_json(matrix, OUTPUT_JOB_SKILL_MATRIX)

    # 5. 统计
    log_sep("技能提取统计")
    summary(matrix, skill_dict)
    print(f"\n  输出文件:")
    print(f"    {OUTPUT_SKILL_DICT}")
    print(f"    {OUTPUT_JOB_SKILL_MATRIX} ({len(matrix)} 条)")
    log_sep()


if __name__ == "__main__":
    main()
