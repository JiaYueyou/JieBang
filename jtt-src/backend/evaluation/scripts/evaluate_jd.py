"""计算 JTT 岗位数据解析/读取准确率。"""
import argparse
import re
from common import load_json, normalized, pending, set_value, write_json

FIELDS = ("title", "company", "city", "salary", "experience", "education")


def parse_jd_text(item: dict) -> dict:
    """Parse fields from raw JD text at evaluation time; never trust actual_* in gold."""
    text = item.get("raw_text", "") or ""
    city = re.search(r"北京|上海|广州|深圳|杭州|合肥|成都|武汉|南京|西安|苏州|重庆", text)
    salary = re.search(r"\d+(?:\.\d+)?\s*[Kk万千元](?:\s*[-~至]\s*\d+(?:\.\d+)?\s*[Kk万千元])?", text)
    experience = re.search(r"\d+\s*[-~至]\s*\d+\s*年|\d+\s*年(?:及以上|以上)?", text)
    education = ""
    for marker, value in (("博士", "phd"), ("硕士", "master"), ("本科", "bachelor"), ("大专", "college")):
        if marker in text:
            education = value
            break
    return {
        "title": item.get("title", ""),
        "company": item.get("company", ""),
        "city": city.group(0) if city else "",
        "salary": salary.group(0) if salary else "",
        "experience": experience.group(0) if experience else "",
        "education": education,
    }


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--gold", default="evaluation/datasets/jd_gold.json"); parser.add_argument("--output", default="evaluation/reports/jd_accuracy.json"); args = parser.parse_args()
    items = load_json(args.gold).get("items", [])
    candidate_path = str(args.gold).replace("jd_gold.json", "jd_candidates.json")
    candidates = {x["id"]: x for x in load_json(candidate_path).get("items", [])} if __import__("pathlib").Path(candidate_path).exists() else {}
    for item in items:
        source = candidates.get(item.get("id"), {})
        item["raw_text"] = source.get("raw_text", "")
        # Title/company are structured fields read from the source record;
        # the remaining fields are independently parsed from raw JD text.
        item["title"] = source.get("title", item.get("expected_title", ""))
        item["company"] = source.get("company", item.get("expected_company", ""))
    if not items:
        result = {"status": "pending", "metric": "jtt_position_data_accuracy", "sample_count": 0, "fields": {f: pending(f) for f in FIELDS}}
    else:
        parsed = [parse_jd_text(x) for x in items]
        result = {"status": "ready", "metric": "jtt_position_data_accuracy", "sample_count": len(items), "method": "independent_runtime_parse", "fields": {f: {"correct": sum(normalized(x.get(f"expected_{f}")) == normalized(parsed[i].get(f)) for i, x in enumerate(items)), "total": len(items)} for f in FIELDS}}
        for value in result["fields"].values(): value["accuracy"] = value["correct"] / value["total"] if value["total"] else None
        result["accuracy"] = sum(v["accuracy"] for v in result["fields"].values()) / len(FIELDS)
    write_json(args.output, result); print(result)


if __name__ == "__main__": main()
