"""计算人工标注的人岗推荐准确率。"""
import argparse
from common import load_json, normalized, write_json


def classify(item):
    required = set(item.get("job", {}).get("required_skills", []))
    owned = set(item.get("resume", {}).get("skills", []))
    ratio = len(required & owned) / len(required) if required else 1
    return "high" if ratio >= 0.8 else ("medium" if ratio >= 0.4 else "low")


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--gold", default="evaluation/datasets/match_gold.json"); parser.add_argument("--output", default="evaluation/reports/match_accuracy.json"); args = parser.parse_args(); items = load_json(args.gold).get("items", [])
    if not items: result = {"status": "pending", "metric": "match_accuracy", "sample_count": 0, "accuracy": None}
    else:
        actual = [classify(x) for x in items]
        correct = sum(normalized(x.get("expected_label")) == normalized(actual[i]) for i, x in enumerate(items)); result = {"status": "ready", "metric": "match_accuracy", "sample_count": len(items), "method": "independent_runtime_skill_ratio", "correct": correct, "accuracy": correct / len(items), "labels": {"high": sum(a == "high" for a in actual), "medium": sum(a == "medium" for a in actual), "low": sum(a == "low" for a in actual)}}
    write_json(args.output, result); print(result)


if __name__ == "__main__": main()
