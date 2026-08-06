"""
构建纯字节跳动清洗数据
─────────────────────
从 data/jd_crawl_bytedance.json 原始数据出发，独立跑一遍清洗流程：
  Step 1: 合并清洗 + 结构化解析 + 质量评分
  Step 2: 岗位名称标准化 + 级别/技术栈推断
  Step 3: 技能提取
输出: outputs/bytedance_merged.json (纯字节, 字段与 merged_jobs.json 一致)

不影响仓库现有的融合版 merged_jobs.json。
"""

import json
import re
import sys
from pathlib import Path
from collections import Counter

# 复用 utils 和 backend 领域层
sys.path.insert(0, str(Path(__file__).resolve().parent))
_BACKEND_SRC = Path(__file__).resolve().parents[2] / "fyz-src" / "backend"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))

from utils import (
    DATA_DIR,
    OUTPUT_DIR,
    STANDARD_FIELDS,
    normalize_record,
    content_fingerprint,
    parse_salary,
    parse_experience,
    parse_education,
    quality_score,
    read_json,
    write_json,
    log,
    log_sep,
)
from app.domain.job_standardizer import standardize_job_title, infer_job_stack
from skill_extractor import RuleSkillExtractor, normalize_text as norm_skill


SRC_FILE = DATA_DIR / "jd_crawl_bytedance.json"
OUT_BYTEDANCE = OUTPUT_DIR / "bytedance_merged.json"


def load_and_clean() -> list[dict]:
    """Step 1: 加载 + 字段归一 + 去重 + 解析 + 质量评分。"""
    raw = read_json(SRC_FILE)
    log("LOAD", f"{SRC_FILE.name}: {len(raw)} 条原始字节数据")

    records = [normalize_record(r) for r in raw]

    # 丢弃空 JD
    before = len(records)
    records = [r for r in records if r.get("jd_text")]
    log("CLEAN", f"丢弃 {before - len(records)} 条无 JD 记录")

    # URL 去重
    seen_url = set()
    kept = []
    for r in records:
        url = (r.get("url") or "").strip().lower()
        if url and url in seen_url:
            continue
        if url:
            seen_url.add(url)
        kept.append(r)
    records = kept
    log("DEDUP", f"URL 去重后: {len(records)} 条")

    # 指纹去重
    seen_fp = set()
    kept = []
    for r in records:
        fp = content_fingerprint(r)
        if fp in seen_fp:
            continue
        seen_fp.add(fp)
        kept.append(r)
    records = kept
    log("DEDUP", f"指纹去重后: {len(records)} 条")

    # 来源标签
    for r in records:
        r["source_tag"] = "bytedance"

    # 结构化解析
    for r in records:
        r["parsed"] = {
            "salary": parse_salary(r.get("salary")),
            "experience": parse_experience(r.get("experience")),
            "education": parse_education(r.get("education")),
        }

    # 质量评分
    for r in records:
        r["quality"] = quality_score(r)

    return records


def normalize_titles(records: list[dict]) -> list[dict]:
    """Step 2: 标题标准化 + 级别/技术栈推断。"""
    for i, r in enumerate(records):
        title = r.get("title", "")
        name, canonical_key, level, confidence = standardize_job_title(title)
        r["standardized_title"] = name
        r["canonical_key"] = canonical_key
        r["level"] = level
        r["stack"] = infer_job_stack(name)
        r["title_confidence"] = round(confidence, 2)
        if (i + 1) % 500 == 0:
            log("PROCESS", f"已标准化 {i + 1}/{len(records)}")
    log("PROCESS", f"全部 {len(records)} 条标准化完成")
    return records


def extract_skills(records: list[dict]) -> list[dict]:
    """Step 3: 技能提取（复用后端 RuleSkillExtractor）。"""
    extractor = RuleSkillExtractor()
    for i, r in enumerate(records):
        jd = norm_skill(r.get("jd_text", ""))
        resp = norm_skill(r.get("responsibilities", ""))
        req = norm_skill(r.get("requirements", ""))
        try:
            result = extractor.extract(jd_text=jd, responsibilities=resp, requirements=req)
            r["skills"] = [
                {
                    "name": s.name,
                    "category": s.category,
                    "kind": s.kind.value,
                    "confidence": round(s.confidence, 2),
                    "evidence": (s.evidence or "")[:200],
                }
                for s in result.skills
            ]
            r["skill_count"] = len(result.skills)
        except Exception as e:
            log("ERROR", f"技能抽取失败: {r.get('title','?')} — {e}")
            r["skills"] = []
            r["skill_count"] = 0
        if (i + 1) % 500 == 0:
            log("SKILL", f"已抽取 {i + 1}/{len(records)}")
    log("SKILL", f"全部 {len(records)} 条技能抽取完成")
    return records


def main() -> None:
    log_sep("构建纯字节跳动清洗数据")

    records = load_and_clean()
    records = normalize_titles(records)
    records = extract_skills(records)

    write_json(records, OUT_BYTEDANCE)
    log("SAVE", f"输出 → {OUT_BYTEDANCE}")

    # 统计
    log_sep("统计")
    print(f"  总条数: {len(records)}")
    print(f"  唯一标准岗位: {len(set(r['standardized_title'] for r in records))}")
    levels = Counter(r["level"] for r in records)
    print(f"  级别分布: {dict(levels)}")
    stacks = Counter(r["stack"] for r in records)
    print(f"  技术栈分布: {dict(stacks)}")
    with_skill = sum(1 for r in records if r.get("skill_count", 0) > 0)
    print(f"  有技能标签: {with_skill}/{len(records)}")
    log_sep()


if __name__ == "__main__":
    main()
