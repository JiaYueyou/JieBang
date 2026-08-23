"""从仓库 data/ 中提取去重后的 JD 候选集，不生成 Gold 答案。"""
import argparse
import hashlib
import json
from pathlib import Path


def records(value):
    if isinstance(value, list): return value
    if isinstance(value, dict):
        for key in ("data", "jobs", "records", "items"):
            if isinstance(value.get(key), list): return value[key]
    return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--data-dir", default="../../../data")
    parser.add_argument("--output", default="evaluation/datasets/jd_candidates.json")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[4] / "data"
    if args.data_dir != "../../../data": root = Path(args.data_dir)
    seen, items = set(), []
    for file in sorted(root.glob("*.json")):
        try: raw = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError): continue
        for row in records(raw):
            title = row.get("title") or row.get("job_title") or row.get("standardized_title") or ""
            text = row.get("jd_text") or row.get("description") or row.get("requirements") or ""
            company = row.get("company") or ""
            key = hashlib.sha256(f"{title}|{company}|{text}".encode()).hexdigest()
            if not title or not text or key in seen: continue
            seen.add(key)
            items.append({"id": f"jd-{len(items)+1:04d}", "source_file": file.name, "title": title, "company": company, "raw_text": text, "status": "pending_annotation"})
            if len(items) >= args.limit: break
        if len(items) >= args.limit: break
    output = Path(args.output)
    if not output.is_absolute(): output = Path(__file__).resolve().parents[2] / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"version": "jd-candidates-v1", "count": len(items), "items": items}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"generated {len(items)} JD candidates -> {output}")


if __name__ == "__main__": main()
