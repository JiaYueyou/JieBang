"""
Step 4: 构建参考数据集
─────────────────────
加载岗位-技能矩阵 → 按 standardized_title 聚合 → 计算技能频次/重要性/来源分布
→ 提取样本需求 → 输出 reference_dataset.json
"""

from collections import Counter, defaultdict

from utils import (
    OUTPUT_JOB_SKILL_MATRIX,
    OUTPUT_MERGED,
    OUTPUT_REFERENCE,
    read_json,
    write_json,
    log,
    log_sep,
)


def aggregate_by_title(matrix: list[dict], records: list[dict]) -> dict[str, dict]:
    """按 standardized_title 聚合所有岗位记录。"""
    # 将 records 以 standardized_title 索引
    record_pool: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        std = r.get("standardized_title", "")
        if std:
            record_pool[std].append(r)

    # 将 matrix 以 standardized_title 索引
    title_groups: dict[str, list[dict]] = defaultdict(list)
    for entry in matrix:
        std = entry.get("standardized_title", "")
        if std:
            title_groups[std].append(entry)

    aggregated: dict[str, dict] = {}
    for std_title, entries in title_groups.items():
        core_counter: dict[str, dict] = {}
        bonus_counter: dict[str, dict] = {}
        source_set: set[str] = set()
        level_counter: Counter = Counter()
        stack_counter: Counter = Counter()
        total_count = len(entries)

        # 各种本要求
        education_samples: list[str] = []
        experience_ranges: list[dict] = []
        salary_ranges: list[dict] = []

        # 从原始 records 中收集需求信息
        for r in record_pool.get(std_title, []):
            parsed = r.get("parsed", {})
            if isinstance(parsed, dict):
                if parsed.get("education"):
                    education_samples.append(parsed["education"])
                if parsed.get("experience"):
                    experience_ranges.append(parsed["experience"])
                if parsed.get("salary"):
                    salary_ranges.append(parsed["salary"])

        for entry in entries:
            source_set.add(entry.get("source_tag", "unknown"))
            level_counter[entry.get("level", "middle")] += 1
            stack_counter[entry.get("stack", "unknown")] += 1

            for s in entry.get("core_skills", []):
                name = s["name"]
                if name not in core_counter:
                    core_counter[name] = {
                        "name": name,
                        "category": s["category"],
                        "count": 0,
                        "confidence_sum": 0.0,
                        "sources": set(),
                    }
                core_counter[name]["count"] += 1
                core_counter[name]["confidence_sum"] += s.get("confidence", 0.9)
                core_counter[name]["sources"].add(entry.get("source_tag", "unknown"))

            for s in entry.get("bonus_skills", []):
                name = s["name"]
                if name not in bonus_counter:
                    bonus_counter[name] = {
                        "name": name,
                        "category": s["category"],
                        "count": 0,
                        "confidence_sum": 0.0,
                        "sources": set(),
                    }
                bonus_counter[name]["count"] += 1
                bonus_counter[name]["confidence_sum"] += s.get("confidence", 0.9)
                bonus_counter[name]["sources"].add(entry.get("source_tag", "unknown"))

        # 计算频次 = 出现次数 / 总记录数
        core_skills = []
        for s in sorted(core_counter.values(), key=lambda x: -x["count"]):
            core_skills.append({
                "name": s["name"],
                "category": s["category"],
                "frequency": round(s["count"] / total_count, 2),
                "avg_confidence": round(s["confidence_sum"] / s["count"], 2),
                "sources": sorted(s["sources"]),
            })

        bonus_skills = []
        for s in sorted(bonus_counter.values(), key=lambda x: -x["count"]):
            bonus_skills.append({
                "name": s["name"],
                "category": s["category"],
                "frequency": round(s["count"] / total_count, 2),
                "avg_confidence": round(s["confidence_sum"] / s["count"], 2),
                "sources": sorted(s["sources"]),
            })

        # 样本需求统计（取众数或中位数）
        sample_education = _mode(education_samples) if education_samples else None
        sample_experience = _median_range(experience_ranges) if experience_ranges else None
        sample_salary = _median_range(salary_ranges) if salary_ranges else None

        # 来源分布
        sources = sorted(source_set)

        # 主流级别和栈
        main_level = level_counter.most_common(1)[0][0] if level_counter else "middle"
        main_stack = stack_counter.most_common(1)[0][0] if stack_counter else "backend"

        aggregated[std_title] = {
            "job_title": std_title,
            "canonical_key": entries[0].get("canonical_key", ""),
            "level": main_level,
            "stack": main_stack,
            "total_records": total_count,
            "sources": sources,
            "core_skills": core_skills,
            "bonus_skills": bonus_skills,
            "sample_requirements": {
                "education": sample_education,
                "experience": sample_experience,
                "salary": sample_salary,
            },
        }

    return aggregated


def _mode(items: list[str]) -> str | None:
    """返回列表中出现最多的元素。"""
    if not items:
        return None
    return Counter(items).most_common(1)[0][0]


def _median_range(ranges: list[dict]) -> dict | None:
    """取一系列 {min, max} 范围的中位值。"""
    if not ranges:
        return None
    mins = sorted(r["min"] for r in ranges if r.get("min") is not None)
    maxs = sorted(r["max"] for r in ranges if r.get("max") is not None)
    if not mins or not maxs:
        return None
    mid = len(mins) // 2
    return {
        "min": mins[mid],
        "max": maxs[mid],
    }


def summary(ref_list: list[dict]) -> None:
    """打印参考数据集统计。"""
    total_profiles = len(ref_list)
    total_records = sum(p["total_records"] for p in ref_list)
    multi_source = sum(1 for p in ref_list if len(p["sources"]) > 1)

    print(f"\n  岗位画像数: {total_profiles}")
    print(f"  覆盖记录数: {total_records}")
    print(f"  跨源岗位画像: {multi_source}")
    print()

    # Top profiles by record count
    sorted_by_size = sorted(ref_list, key=lambda x: -x["total_records"])
    print("  最大岗位画像 Top 10:")
    for p in sorted_by_size[:10]:
        cs_count = len(p["core_skills"])
        bs_count = len(p["bonus_skills"])
        print(f"    {p['job_title']:<25s}  {p['total_records']:>2d} 条  "
              f"核心={cs_count} 加分={bs_count}  "
              f"来源={','.join(p['sources'])}")

    # Level distribution
    levels = Counter(p["level"] for p in ref_list)
    print(f"\n  岗位级别分布:")
    for lv, cnt in levels.most_common():
        print(f"    {lv}: {cnt}")

    # Stack distribution
    stacks = Counter(p["stack"] for p in ref_list)
    print(f"\n  技术栈分布:")
    for st, cnt in stacks.most_common():
        print(f"    {st}: {cnt}")

    # Skill coverage stats
    all_core = set()
    for p in ref_list:
        for s in p["core_skills"]:
            all_core.add(s["name"])
    all_bonus = set()
    for p in ref_list:
        for s in p["bonus_skills"]:
            all_bonus.add(s["name"])
    print(f"\n  核心技能总去重: {len(all_core)}")
    print(f"  加分技能总去重: {len(all_bonus)}")


def main() -> None:
    log_sep("Step 4: 构建参考数据集")

    # 1. 加载
    matrix = read_json(OUTPUT_JOB_SKILL_MATRIX)
    records = read_json(OUTPUT_MERGED)
    log("LOAD", f"加载技能矩阵: {len(matrix)} 条, 原始记录: {len(records)} 条")

    # 2. 聚合
    aggregated = aggregate_by_title(matrix, records)
    log("AGGREGATE", f"聚合出 {len(aggregated)} 个岗位画像")

    # 3. 转为有序列表（按记录数降序）
    ref_list = sorted(aggregated.values(), key=lambda x: -x["total_records"])

    # 4. 输出
    write_json(ref_list, OUTPUT_REFERENCE)

    # 5. 统计
    log_sep("参考数据集统计")
    summary(ref_list)
    print(f"\n  输出文件:")
    print(f"    {OUTPUT_REFERENCE} ({len(ref_list)} 个岗位画像)")
    log_sep()


if __name__ == "__main__":
    main()
