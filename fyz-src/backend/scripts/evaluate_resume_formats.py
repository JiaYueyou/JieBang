"""Generate and evaluate a privacy-safe multi-format resume corpus.

The labelled profiles are derived from public fictional/open-source resume
examples. The script generates PDF, DOCX, PNG, JPG and JPEG variants, invokes
the production ResumeParser, and reports text recognition and skill extraction
metrics by format.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.domain.skill_dictionary import canonical_key  # noqa: E402
from app.services.resume_parser import ResumeParser  # noqa: E402
from app.services.skill_extractor import RuleSkillExtractor  # noqa: E402


FORMATS = ("pdf", "docx", "png", "jpg", "jpeg")
DEFAULT_CASES = BACKEND_DIR / "evaluation" / "resume_format_cases.json"
DEFAULT_OUTPUT = BACKEND_DIR / "evaluation" / "resume_format_metrics.json"


def _normalize_text(value: str) -> str:
    return re.sub(r"[^0-9a-z\u3400-\u9fff]+", "", value.casefold())


def _edit_distance(left: str, right: str) -> int:
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for row, char_left in enumerate(left, 1):
        current = [row]
        for column, char_right in enumerate(right, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (char_left != char_right),
                )
            )
        previous = current
    return previous[-1]


def _text_metrics(actual: str, expected: str) -> tuple[float, float]:
    actual_norm = _normalize_text(actual)
    expected_norm = _normalize_text(expected)
    cer = _edit_distance(actual_norm, expected_norm) / max(1, len(expected_norm))
    expected_tokens = set(re.findall(r"[a-z0-9+#.]+|[\u3400-\u9fff]{2,}", expected.casefold()))
    actual_tokens = set(re.findall(r"[a-z0-9+#.]+|[\u3400-\u9fff]{2,}", actual.casefold()))
    recall = len(expected_tokens & actual_tokens) / max(1, len(expected_tokens))
    return max(0.0, 1.0 - cer), recall


def _write_docx(path: Path, text: str) -> None:
    from docx import Document

    document = Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    document.save(path)


def _font_path() -> str:
    candidates = (
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/arialuni.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    )
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    raise RuntimeError("No CJK font found; install SimHei or Noto Sans CJK")


def _write_pdf(path: Path, text: str) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen.canvas import Canvas

    font_name = "ResumeCorpusCJK"
    if font_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font_name, _font_path()))
    canvas = Canvas(str(path), pagesize=A4)
    canvas.setFont(font_name, 13)
    y = A4[1] - 64
    for line in text.splitlines():
        canvas.drawString(64, y, line)
        y -= 25
    canvas.save()


def _write_image(path: Path, text: str, image_format: str) -> None:
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1654, 2339), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(_font_path(), 36)
    y = 100
    for line in text.splitlines():
        draw.text((100, y), line, fill="black", font=font)
        y += 62
    image.save(path, format=image_format, quality=95)


def generate_case_files(case: dict[str, Any], directory: Path) -> dict[str, Path]:
    paths = {suffix: directory / f"{case['id']}.{suffix}" for suffix in FORMATS}
    _write_pdf(paths["pdf"], case["text"])
    _write_docx(paths["docx"], case["text"])
    _write_image(paths["png"], case["text"], "PNG")
    _write_image(paths["jpg"], case["text"], "JPEG")
    _write_image(paths["jpeg"], case["text"], "JPEG")
    return paths


def evaluate(cases_path: Path = DEFAULT_CASES, artifact_dir: Path | None = None) -> dict[str, Any]:
    payload = json.loads(cases_path.read_text(encoding="utf-8"))
    parser = ResumeParser()
    extractor = RuleSkillExtractor()
    temporary = tempfile.TemporaryDirectory(prefix="jiebang-resume-formats-") if artifact_dir is None else None
    root = artifact_dir or Path(temporary.name)
    root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for case in payload["cases"]:
        for suffix, path in generate_case_files(case, root).items():
            actual_text, warnings = parser.parse(path.read_bytes(), path.name)
            text_accuracy, token_recall = _text_metrics(actual_text, case["text"])
            predicted = {canonical_key(item.name) for item in extractor.extract(jd_text=actual_text).skills}
            expected = {canonical_key(item) for item in case["expected_skills"]}
            tp = len(predicted & expected)
            fp = len(predicted - expected)
            fn = len(expected - predicted)
            rows.append({
                "id": case["id"], "role": case["role"], "format": suffix,
                "text_accuracy": round(text_accuracy, 6),
                "token_recall": round(token_recall, 6),
                "skill_tp": tp, "skill_fp": fp, "skill_fn": fn,
                "predicted_skills": sorted(predicted),
                "expected_skills": sorted(expected),
                "warnings": warnings,
            })
            bucket = totals[suffix]
            bucket["records"] += 1
            bucket["text_accuracy"] += text_accuracy
            bucket["token_recall"] += token_recall
            bucket["tp"] += tp
            bucket["fp"] += fp
            bucket["fn"] += fn

    def summarize(values: dict[str, float]) -> dict[str, Any]:
        precision = values["tp"] / max(1, values["tp"] + values["fp"])
        recall = values["tp"] / max(1, values["tp"] + values["fn"])
        f1 = 2 * precision * recall / max(1e-12, precision + recall)
        return {
            "records": int(values["records"]),
            "mean_text_accuracy": round(values["text_accuracy"] / values["records"], 6),
            "mean_token_recall": round(values["token_recall"] / values["records"], 6),
            "skill_precision": round(precision, 6),
            "skill_recall": round(recall, 6),
            "skill_micro_f1": round(f1, 6),
        }

    by_format = {name: summarize(values) for name, values in totals.items()}
    aggregate: dict[str, float] = defaultdict(float)
    for values in totals.values():
        for key, value in values.items():
            aggregate[key] += value
    overall = summarize(aggregate)
    gates = {
        "text_accuracy_at_least_90_percent": overall["mean_text_accuracy"] >= 0.90,
        "skill_micro_f1_at_least_90_percent": overall["skill_micro_f1"] >= 0.90,
        "every_format_skill_f1_at_least_90_percent": all(
            value["skill_micro_f1"] >= 0.90 for value in by_format.values()
        ),
    }
    result = {
        "dataset_version": payload["dataset_version"],
        "privacy": payload["privacy"],
        "sources": payload["sources"],
        "formats": list(FORMATS),
        "profile_count": len(payload["cases"]),
        "file_count": len(rows),
        "metric_definition": {
            "text_accuracy": "1 - normalized character error rate",
            "token_recall": "expected normalized token recall",
            "skill_micro_f1": "micro F1 against manually labelled skill sets using production extractor",
        },
        "limitation": (
            "Controlled clean fixtures validate format support and labelled extraction, "
            "but do not estimate accuracy on the full population of real-world resumes."
        ),
        "by_format": by_format,
        "overall": overall,
        "gates": gates,
        "all_gates_passed": all(gates.values()),
        "failures": [row for row in rows if row["text_accuracy"] < 0.90 or row["skill_fn"] or row["skill_fp"]],
    }
    if temporary is not None:
        temporary.cleanup()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--artifact-dir", type=Path)
    args = parser.parse_args()
    result = evaluate(args.cases, args.artifact_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["all_gates_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
