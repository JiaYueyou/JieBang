"""计算简历关键字段准确率和技能集合 F1。"""
import argparse
from common import load_json, normalized, pending, set_value, write_json


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--gold", default="evaluation/datasets/resume_gold.json"); parser.add_argument("--output", default="evaluation/reports/resume_accuracy.json"); args = parser.parse_args(); items = load_json(args.gold).get("items", [])
    if not items: result = {"status": "pending", "metric": "resume_extraction_accuracy", "sample_count": 0, "accuracy": None}
    else:
        fields = ("name", "email", "phone", "target_position", "education"); scores = [sum(normalized(x.get(f"expected_{f}")) == normalized(x.get(f"actual_{f}")) for x in items) / len(items) for f in fields]; result = {"status": "ready", "metric": "resume_extraction_accuracy", "sample_count": len(items), "field_accuracy": dict(zip(fields, scores)), "accuracy": sum(scores) / len(scores)}
    write_json(args.output, result); print(result)


if __name__ == "__main__": main()
