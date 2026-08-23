"""Build deterministic JTT matching cases from explicit resume/JD skill evidence."""
import json
from pathlib import Path


SKILLS = ["Python", "FastAPI", "SQL", "Docker", "Linux", "Vue", "React", "RAG", "Git", "Neo4j"]


def label(resume, job):
    required = set(job["required_skills"])
    owned = set(resume["skills"])
    ratio = len(required & owned) / len(required) if required else 1
    if ratio >= 0.8:
        return "high"
    if ratio >= 0.4:
        return "medium"
    return "low"


def main():
    root = Path(__file__).resolve().parents[2]
    items = []
    for i in range(100):
        required = SKILLS[(i * 3) % len(SKILLS): (i * 3) % len(SKILLS) + 3]
        mode = i % 3
        owned = required[:] if mode == 0 else (required[:1] if mode == 1 else [SKILLS[(i + 5) % len(SKILLS)]])
        resume = {"skills": owned}
        job = {"required_skills": required}
        expected = label(resume, job)
        items.append({"id": f"match-{i+1:04d}", "resume": resume, "job": job,
                      "expected_label": expected, "evidence": {"matched_skills": sorted(set(owned) & set(required))}})
    out = root / "evaluation/datasets/match_gold.json"
    out.write_text(json.dumps({"version": "match-gold-v2-rule-independent", "status": "pseudo_gold", "items": items}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"generated {len(items)} matching cases -> {out}")


if __name__ == "__main__":
    main()
