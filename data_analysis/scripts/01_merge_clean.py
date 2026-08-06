"""
Step 1: 数据合并与清洗
─────────────────────
读取多源 JSON → 字段统一 → 去重 → 字段标准化 → 质量评分 → 输出 merged_jobs.json
"""

import re
from pathlib import Path

from utils import (
    DATA_FILES,
    OUTPUT_MERGED,
    DEDUP_THRESHOLD,
    normalize_record,
    content_fingerprint,
    text_similarity,
    parse_salary,
    parse_experience,
    parse_education,
    quality_score,
    read_json,
    write_json,
    log,
    log_sep,
)


def load_all_records(file_paths: list[Path]) -> list[dict]:
    """读取所有源 JSON，字段统一化。"""
    all_records: list[dict] = []
    for path in file_paths:
        records = read_json(path)
        if not isinstance(records, list):
            log("WARN", f"{path.name} 不是数组，跳过")
            continue
        normalized = [normalize_record(r) for r in records]
        all_records.extend(normalized)
        log("LOAD", f"{path.name}: {len(records)} 条 → 已归一化")
    log("LOAD", f"合计加载: {len(all_records)} 条")
    return all_records


def drop_empty_jd(records: list[dict]) -> list[dict]:
    """丢弃 jd_text 为空的记录。"""
    before = len(records)
    records = [r for r in records if r.get("jd_text")]
    dropped = before - len(records)
    if dropped:
        log("CLEAN", f"丢弃 {dropped} 条无 JD 文本的记录")
    return records


def dedup_by_url(records: list[dict]) -> list[dict]:
    """URL 完全相同 → 只保留第一条。"""
    seen: set[str] = set()
    kept: list[dict] = []
    for r in records:
        url = (r.get("url") or "").strip().lower()
        if not url:
            kept.append(r)
            continue
        if url not in seen:
            seen.add(url)
            kept.append(r)
    dropped = len(records) - len(kept)
    if dropped:
        log("DEDUP", f"URL 去重: 移除 {dropped} 条")
    return kept


def dedup_by_fingerprint(records: list[dict]) -> list[dict]:
    """内容指纹去重（source+url+title+company+posted_at+jd_text 的 SHA256）。"""
    seen: set[str] = set()
    kept: list[dict] = []
    for r in records:
        fp = content_fingerprint(r)
        if fp not in seen:
            seen.add(fp)
            kept.append(r)
    dropped = len(records) - len(kept)
    if dropped:
        log("DEDUP", f"指纹去重: 移除 {dropped} 条")
    return kept


def dedup_by_similarity(records: list[dict], threshold: int = DEDUP_THRESHOLD) -> list[dict]:
    """title+company 复合相似度去重（相似度高于阈值且来自不同源的视为重复）。"""
    if not records:
        return records
    kept: list[dict] = [records[0]]
    for r in records[1:]:
        title_a = (r.get("title") or "").casefold().strip()
        company_a = (r.get("company") or "").casefold().strip()
        is_dup = False
        for k in kept:
            title_b = (k.get("title") or "").casefold().strip()
            company_b = (k.get("company") or "").casefold().strip()
            title_sim = text_similarity(title_a, title_b)
            company_sim = text_similarity(company_a, company_b) if company_a and company_b else 0
            # 标题相似度高 且（公司相同或高度相似）
            if title_sim >= threshold and (company_a == company_b or company_sim >= threshold):
                is_dup = True
                break
        if not is_dup:
            kept.append(r)
    dropped = len(records) - len(kept)
    if dropped:
        log("DEDUP", f"相似度去重: 移除 {dropped} 条")
    return kept


def parse_structured_fields(records: list[dict]) -> list[dict]:
    """将薪资/经验/学历解析为结构化字段，存入 parsed 子对象。"""
    for r in records:
        r["parsed"] = {
            "salary": parse_salary(r.get("salary")),
            "experience": parse_experience(r.get("experience")),
            "education": parse_education(r.get("education")),
        }
    log("PARSE", f"字段解析完成: 共 {len(records)} 条")
    return records


def tag_source(records: list[dict]) -> list[dict]:
    """根据 source 字段打上统一来源标签。"""
    source_tag_map = {
        "iflytek": "iflytek",
        "讯飞": "iflytek",
        "zhilian": "zhilian",
        "智联": "zhilian",
        "zhaopin": "zhilian",
        "bytedance": "bytedance",
        "字节": "bytedance",
    }
    for r in records:
        src = (r.get("source") or "").lower()
        tag = "unknown"
        for keyword, label in source_tag_map.items():
            if keyword in src:
                tag = label
                break
        r["source_tag"] = tag
    return records


def compute_quality(records: list[dict]) -> list[dict]:
    """计算每条记录的质量评分，过滤低质量数据。"""
    for r in records:
        r["quality"] = quality_score(r)
    low = [r for r in records if r["quality"] < 0.3]
    if low:
        log("QUALITY", f"低质量记录 (<0.3): {len(low)} 条")
    return records


def summary_stats(records: list[dict]) -> dict:
    """输出统计摘要。"""
    sources = {}
    for r in records:
        tag = r.get("source_tag", "unknown")
        sources[tag] = sources.get(tag, 0) + 1
    return {
        "total": len(records),
        "by_source": sources,
        "fields": list(records[0].keys()) if records else [],
    }


def main() -> None:
    log_sep("Step 1: 数据合并与清洗")

    # 1. 加载
    records = load_all_records(DATA_FILES)
    records = drop_empty_jd(records)

    # 2. 去重（三级去重）
    records = dedup_by_url(records)
    records = dedup_by_fingerprint(records)
    records = dedup_by_similarity(records)

    # 3. 字段解析
    records = tag_source(records)
    records = parse_structured_fields(records)
    records = compute_quality(records)

    # 4. 输出
    write_json(records, OUTPUT_MERGED)

    # 5. 统计
    stats = summary_stats(records)
    log_sep("统计摘要")
    print(f"  输出文件: {OUTPUT_MERGED}")
    print(f"  总记录数: {stats['total']}")
    for src, count in sorted(stats["by_source"].items()):
        print(f"    {src}: {count} 条")
    print(f"  字段列表: {', '.join(stats['fields'])}")
    log_sep()


if __name__ == "__main__":
    main()
