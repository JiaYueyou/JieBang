"""用可解释规则生成 JD pseudo-gold；仅用于无人工标注时的回归基线。"""
import argparse, json, re
from pathlib import Path

EDU = [("博士", "phd"), ("硕士", "master"), ("本科", "bachelor"), ("大专", "college")]
SKILLS = "Python Java Go C++ Rust JavaScript TypeScript SQL MySQL Redis MongoDB PostgreSQL Docker Kubernetes Git Linux FastAPI Django Spring Boot Vue React PyTorch TensorFlow LangChain LlamaIndex Kafka Spark Elasticsearch Neo4j RAG NLP LLM".split()

def first(pattern, text):
    m = re.search(pattern, text, re.I)
    return m.group(0) if m else ""

def annotate(item):
    text = item.get("raw_text", "")
    exp = first(r"(?:\d+\s*[-~至]\s*\d+\s*年|\d+\s*年(?:及以上|以上)?)", text)
    salary = first(r"\d+(?:\.\d+)?\s*[Kk万](?:\s*[-~至]\s*\d+(?:\.\d+)?\s*[Kk万])?", text)
    city = first(r"北京|上海|广州|深圳|杭州|合肥|成都|武汉|南京|西安|苏州|重庆", text)
    education = next((value for marker, value in EDU if marker in text), "")
    skills = [skill for skill in SKILLS if skill.lower() in text.lower()]
    return {
        "id": item["id"], "source_file": item.get("source_file", ""),
        "expected_title": item.get("title", ""), "expected_company": item.get("company", ""),
        "expected_city": city, "expected_salary": salary, "expected_experience": exp,
        "expected_education": education, "required_skills": skills,
        "preferred_skills": [], "evidence": [{"field": "raw_text", "text": text[:240]}],
        "actual_title": item.get("title", ""), "actual_company": item.get("company", ""),
        "actual_city": city, "actual_salary": salary, "actual_experience": exp,
        "actual_education": education, "annotation_method": "rule_auto", "status": "pseudo_gold",
    }

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--input", default="evaluation/datasets/jd_candidates.json"); parser.add_argument("--output", default="evaluation/datasets/jd_gold.json"); args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]; source = json.loads((root / args.input).read_text(encoding="utf-8")); result = {"version": "jd-gold-v1-auto", "status": "pseudo_gold_rule_auto", "warning": "未经过人工审核，不作为最终竞赛准确率证明", "items": [annotate(x) for x in source.get("items", [])]}; (root / args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"); print(f"annotated {len(result['items'])} pseudo-gold JD records")

if __name__ == "__main__": main()
