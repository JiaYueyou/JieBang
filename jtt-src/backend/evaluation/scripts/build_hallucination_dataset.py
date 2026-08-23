"""Build graph-grounded anti-hallucination cases."""
import json
from pathlib import Path


def main():
    cases = []
    for i in range(20):
        graph = ["Python", "FastAPI", "Docker"] if i % 2 == 0 else ["Java", "Spring"]
        if i % 5 == 0:
            suggested = graph[0]
            expected_reject = False
        else:
            suggested = ["Kubernetes", "量子计算", "不存在技能", "Rust", "区块链"][i % 5]
            expected_reject = True
        cases.append({"id": f"hall-{i+1:03d}", "position": "Test Position",
                      "graph_skills": graph, "suggested": suggested,
                      "expected_reject": expected_reject})
    path = Path(__file__).resolve().parents[2] / "evaluation/datasets/hallucination_cases.json"
    path.write_text(json.dumps({"version": "hallucination-v2", "status": "pseudo_gold", "items": cases}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"generated {len(cases)} hallucination cases -> {path}")


if __name__ == "__main__":
    main()
