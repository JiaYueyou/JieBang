"""
全链路输出验证脚本。
对所有产出文件做完整性、结构、数据范围的检查。
"""

import sys
from pathlib import Path

# 确保可以从本目录 import utils
sys.path.insert(0, str(Path(__file__).parent))

from utils import (
    OUTPUT_MERGED,
    OUTPUT_TITLE_MAP,
    OUTPUT_SKILL_DICT,
    OUTPUT_JOB_SKILL_MATRIX,
    OUTPUT_REFERENCE,
    read_json,
    log,
)

PASS = 0
FAIL = 0


def check(condition: bool, msg: str) -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        log("PASS", msg)
    else:
        FAIL += 1
        log("FAIL", msg)


def main() -> None:
    global PASS, FAIL
    print("=" * 60)
    print("  清洗流水线 — 全链路输出验证")
    print("=" * 60)

    # ── 1. merged_jobs.json ──
    print("\n── merged_jobs.json ──")
    records = read_json(OUTPUT_MERGED)
    check(len(records) >= 150, f"记录数 >= 150: {len(records)}")
    check(all(r.get("jd_text") for r in records), "无空 jd_text")
    for field in ["title", "standardized_title", "level", "stack", "source_tag", "quality"]:
        check(all(field in r for r in records), f"所有记录含 {field}")
    valid_levels = {"junior", "middle", "senior"}
    check(set(r["level"] for r in records).issubset(valid_levels), "level 值合法")
    check(all(r["quality"] > 0 for r in records), "quality 均 > 0")
    check(len(set(r["canonical_key"] for r in records)) >= 100, f"唯一 canonical_key >= 100")

    # ── 2. title_mapping.json ──
    print("\n── title_mapping.json ──")
    mapping = read_json(OUTPUT_TITLE_MAP)
    check(len(mapping) >= 100, f"映射条目 >= 100: {len(mapping)}")
    for raw, target in list(mapping.items())[:5]:
        check("standardized" in target, f"条目字段完整: {raw}")

    # ── 3. skill_dict.json ──
    print("\n── skill_dict.json ──")
    sd = read_json(OUTPUT_SKILL_DICT)
    check(sd["total_skills"] == len(sd["skills"]), f"技能数一致: {sd['total_skills']}")
    check(sd["total_skills"] >= 80, f"唯一技能 >= 80: {sd['total_skills']}")
    check(sd["total_mentions"] >= 500, f"总提及 >= 500: {sd['total_mentions']}")
    for s in sd["skills"]:
        check(all(k in s for k in ["name", "category", "total_mentions", "job_count"]),
              f"技能结构完整: {s.get('name', '?')}")
        break  # 只检查第一条

    # ── 4. job_skill_matrix.json ──
    print("\n── job_skill_matrix.json ──")
    matrix = read_json(OUTPUT_JOB_SKILL_MATRIX)
    check(len(matrix) == len(records), f"矩阵记录数匹配: {len(matrix)}")
    with_skills = sum(1 for e in matrix if e["total_skills"] > 0)
    check(with_skills >= len(matrix) * 0.7, f"有技能岗位 >= 70%: {with_skills}/{len(matrix)}")

    # ── 5. reference_dataset.json ──
    print("\n── reference_dataset.json ──")
    ref = read_json(OUTPUT_REFERENCE)
    check(len(ref) >= 80, f"岗位画像 >= 80: {len(ref)}")
    for p in ref[:3]:
        check(all(k in p for k in ["job_title", "core_skills", "sample_requirements", "sources"]),
              f"画像结构完整: {p['job_title']}")
        for s in p["core_skills"]:
            check("frequency" in s, f"核心技能含 frequency: {s.get('name')}")
            break

    # ── 汇总 ──
    print(f"\n{'=' * 60}")
    print(f"  验证结果: {PASS} 通过, {FAIL} 失败")
    if FAIL == 0:
        print("  [OK] 全链路输出验证通过")
    else:
        print(f"  [FAIL] 有 {FAIL} 项验证未通过，请检查")
    print(f"{'=' * 60}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
