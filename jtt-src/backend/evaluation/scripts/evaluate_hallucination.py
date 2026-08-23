"""计算防幻觉案例通过率；actual_response 由人工或 Agent 测试填入。"""
import argparse
from common import load_json, write_json


def should_reject(item):
    suggested = str(item.get("suggested", "")).casefold()
    graph_skills = {str(skill).casefold() for skill in item.get("graph_skills", [])}
    return not any(skill and skill in suggested for skill in graph_skills)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--gold", default="evaluation/datasets/hallucination_cases.json"); parser.add_argument("--output", default="evaluation/reports/hallucination_report.json"); args = parser.parse_args(); items = load_json(args.gold).get("items", [])
    results = [{**x, "actual_reject": should_reject(x), "passed": should_reject(x) == bool(x.get("expected_reject"))} for x in items]
    passed = sum(bool(x.get("passed")) for x in results)
    result = {"status": "pending" if not items else "ready", "metric": "hallucination_resistance", "sample_count": len(items), "passed": passed, "correct_rejection_rate": passed / len(items) if items else None, "items": results}
    write_json(args.output, result); print(result)


if __name__ == "__main__": main()
