"""
Step 2: 岗位名称标准化
─────────────────────
加载合并数据 → 复用 backend job_standardizer → 标题清洗/级别推断/技术栈推断
→ 构建映射表 → 回写 merged_jobs.json → 输出 title_mapping.json
"""

import sys
from pathlib import Path
from collections import Counter

# 添加 backend 源码路径以复用领域层
_BACKEND_SRC = Path(__file__).resolve().parents[2] / "fyz-src" / "backend"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))

from app.domain.job_standardizer import standardize_job_title, infer_job_level, infer_job_stack

from utils import (
    OUTPUT_MERGED,
    OUTPUT_TITLE_MAP,
    read_json,
    write_json,
    log,
    log_sep,
)


def process_record(record: dict) -> dict:
    """对单条记录执行标题标准化，回写 standardized_title / level / stack。"""
    title = record.get("title", "")
    # 标准化标题
    name, canonical_key, level, confidence = standardize_job_title(title)
    # 推断技术栈
    stack = infer_job_stack(name)
    # 回写
    record["standardized_title"] = name
    record["canonical_key"] = canonical_key
    record["level"] = level
    record["stack"] = stack
    record["title_confidence"] = round(confidence, 2)
    return record


def build_title_mapping(records: list[dict]) -> dict[str, dict]:
    """构建原始标题 → 标准标题/级别/栈 的映射表。"""
    mapping: dict[str, dict] = {}
    for r in records:
        raw = r.get("title", "")
        # 已处理过且 confidence 更高则覆盖
        if raw in mapping and mapping[raw]["confidence"] >= r.get("title_confidence", 0):
            continue
        mapping[raw] = {
            "standardized": r["standardized_title"],
            "canonical_key": r["canonical_key"],
            "level": r["level"],
            "stack": r["stack"],
            "confidence": r["title_confidence"],
            "sample_company": r.get("company", ""),
        }
    return mapping


def summary(records: list[dict]) -> None:
    """打印标准化统计。"""
    titles = [r["standardized_title"] for r in records]
    unique = set(titles)
    top = Counter(titles).most_common(15)
    levels = Counter(r["level"] for r in records)
    stacks = Counter(r["stack"] for r in records)

    print(f"\n  记录总数: {len(records)}")
    print(f"  去重标准岗位: {len(unique)}")
    print(f"\n  级别分布:")
    for lv, cnt in levels.most_common():
        print(f"    {lv}: {cnt}")
    print(f"\n  技术栈分布:")
    for st, cnt in stacks.most_common():
        print(f"    {st}: {cnt}")
    print(f"\n  热门标准岗位 Top 15:")
    for title, cnt in top:
        print(f"    {title}: {cnt} 条")


def main() -> None:
    log_sep("Step 2: 岗位名称标准化")

    # 1. 加载
    records = read_json(OUTPUT_MERGED)
    log("LOAD", f"加载 {len(records)} 条记录")

    # 2. 标准化
    for i, r in enumerate(records):
        process_record(r)
        if (i + 1) % 50 == 0:
            log("PROCESS", f"已处理 {i + 1}/{len(records)}")
    log("PROCESS", f"全部 {len(records)} 条处理完成")

    # 3. 构建映射表
    mapping = build_title_mapping(records)

    # 4. 输出
    write_json(records, OUTPUT_MERGED)           # 回写 merged_jobs.json（含 standardized_title）
    write_json(mapping, OUTPUT_TITLE_MAP)         # 输出 title_mapping.json

    # 5. 统计
    log_sep("标准化统计")
    summary(records)
    print(f"\n  输出文件:")
    print(f"    {OUTPUT_MERGED}")
    print(f"    {OUTPUT_TITLE_MAP} ({len(mapping)} 个原始标题映射)")
    log_sep()


if __name__ == "__main__":
    main()
