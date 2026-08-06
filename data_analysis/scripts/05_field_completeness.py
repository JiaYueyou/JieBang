"""Step 5: 字段完整率报告
────────────────────────
遍历 data/ 下所有源 JSON，统计每个文件的 14 个标准字段完整率，
输出 field_completeness_report.json / .csv 到 outputs/。
"""

import csv
import json
from datetime import date
from pathlib import Path

from utils import DATA_DIR, OUTPUT_DIR, STANDARD_FIELDS, read_json, log, log_sep


# 文件显示名（label）映射
FILE_LABELS = {
    "jd_crawl_ifly.json": "学长-科大讯飞官网(清洗后)",
    "jd_crawl_ifly_full.json": "李亚铮-科大讯飞全部(原始)",
    "jd_crawl_ifly_merged.json": "李亚铮-科大讯飞合并(学长+新增)",
    "jd_crawl_zl.json": "学长-智联招聘(清洗后)",
    "jd_crawl_zl_new.json": "李亚铮-智联招聘(新爬)",
    "jd_crawl2.json": "学长-智联招聘旧版",
    "科大讯飞.json": "学长-科大讯飞官网(原始)",
    "jd_crawl_bytedance.json": "成员D-字节跳动官网(新爬)",
}

# 需要统计的源文件（按顺序）
FILES_TO_INCLUDE = [
    "jd_crawl_ifly.json",
    "jd_crawl_ifly_full.json",
    "jd_crawl_ifly_merged.json",
    "jd_crawl_zl.json",
    "jd_crawl_zl_new.json",
    "jd_crawl2.json",
    "科大讯飞.json",
    "jd_crawl_bytedance.json",
]


def field_completeness(records: list[dict]) -> dict:
    """统计单个文件每个字段的填充率。"""
    n = len(records)
    if n == 0:
        return {f: {"filled": 0, "rate_pct": 0.0} for f in STANDARD_FIELDS}
    result = {}
    for field in STANDARD_FIELDS:
        filled = sum(1 for r in records if r.get(field))
        result[field] = {"filled": filled, "rate_pct": round(filled / n * 100, 1)}
    return result


def main() -> None:
    log_sep("Step 5: 字段完整率报告")

    reports = []
    for name in FILES_TO_INCLUDE:
        path = DATA_DIR / name
        if not path.exists():
            log("SKIP", f"{name} 不存在，跳过")
            continue
        records = read_json(path)
        if not isinstance(records, list):
            log("WARN", f"{name} 不是数组，跳过")
            continue
        comp = field_completeness(records)
        overall = round(
            sum(c["rate_pct"] for c in comp.values()) / len(comp), 1
        )
        reports.append({
            "file": name,
            "label": FILE_LABELS.get(name, name),
            "total_records": len(records),
            "overall_completeness_pct": overall,
            "field_completeness": comp,
        })
        log("REPORT", f"{name}: {len(records)} 条, 综合完整率 {overall}%")

    # ── JSON ──
    json_out = {
        "generated_at": date.today().isoformat(),
        "description": "所有数据源字段完整率报告",
        "standard_fields": STANDARD_FIELDS,
        "files": reports,
    }
    json_path = OUTPUT_DIR / "field_completeness_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_out, f, ensure_ascii=False, indent=2)
    log("SAVE", f"JSON → {json_path}")

    # ── CSV ──
    csv_path = OUTPUT_DIR / "field_completeness_report.csv"
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["文件", "标签", "总条数", "综合完整率%"] + STANDARD_FIELDS)
        for r in reports:
            row = [
                r["file"], r["label"], r["total_records"],
                r["overall_completeness_pct"],
            ]
            row += [r["field_completeness"][f]["rate_pct"] for f in STANDARD_FIELDS]
            writer.writerow(row)
    log("SAVE", f"CSV → {csv_path}")

    log_sep()


if __name__ == "__main__":
    main()
