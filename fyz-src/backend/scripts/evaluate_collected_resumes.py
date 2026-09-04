"""Evaluate locally collected resume images without publishing personal data."""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from collections import Counter
from hashlib import sha256
from pathlib import Path
from statistics import mean
from typing import Any
from zipfile import ZipFile

from PIL import Image, UnidentifiedImageError


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.resume_parser import ResumeParser  # noqa: E402
from app.services.resume_profile_extractor import ResumeProfileExtractor  # noqa: E402
from app.services.skill_extractor import RuleSkillExtractor  # noqa: E402


FIELD_PATTERNS = {
    "identity": re.compile(r"姓名|个人简历|求职简历|简历|[\u3400-\u9fff·]{2,8}"),
    "education": re.compile(r"教育背景|教育经历|学历|本科|硕士|博士|大专|专科|大学|学院"),
    "career": re.compile(r"工作经历|工作经验|实习经历|项目经历|项目经验|校园经历"),
    "skills": re.compile(r"专业技能|技能证书|技能|技术栈|证书"),
}


def _ordered_raster_images(docx_path: Path) -> list[tuple[str, bytes]]:
    with ZipFile(docx_path) as archive:
        names = [name for name in archive.namelist() if name.startswith("word/media/")]
        def key(name: str) -> tuple[int, str]:
            match = re.search(r"image(\d+)", name, re.I)
            return (int(match.group(1)) if match else 10**9, name)
        rows: list[tuple[str, bytes]] = []
        for name in sorted(names, key=key):
            content = archive.read(name)
            try:
                Image.open(io.BytesIO(content)).verify()
            except UnidentifiedImageError:
                continue
            rows.append((name, content))
        return rows


def _source_images(source_dir: Path) -> list[tuple[str, bytes]]:
    output: list[tuple[str, bytes]] = []
    for docx_path in sorted(source_dir.rglob("*.docx")):
        for media_name, content in _ordered_raster_images(docx_path):
            output.append(
                (f"{docx_path.relative_to(source_dir)}::{media_name}", content)
            )
    raster_paths = sorted(
        path for path in source_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg"}
    )
    output.extend(
        (str(path.relative_to(source_dir)), path.read_bytes())
        for path in raster_paths
    )
    deduplicated: list[tuple[str, bytes]] = []
    seen: set[str] = set()
    for label, content in output:
        digest = sha256(content).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        deduplicated.append((label, content))
    return deduplicated


def _field_flags(text: str, profile: dict[str, Any]) -> dict[str, bool]:
    return {
        "identity": bool(profile.get("name")) and bool(FIELD_PATTERNS["identity"].search(text)),
        "education": bool(FIELD_PATTERNS["education"].search(text)),
        "career": bool(FIELD_PATTERNS["career"].search(text)),
        "skills": bool(FIELD_PATTERNS["skills"].search(text)),
    }


def _quality_score(
    diagnostics: dict[str, Any], field_flags: dict[str, bool], skill_count: int
) -> float:
    completeness = sum(field_flags.values()) / len(field_flags)
    return round(
        diagnostics["mean_confidence"] * 0.50
        + completeness * 0.25
        + min(1.0, diagnostics["character_count"] / 500) * 0.10
        + min(1.0, skill_count / 6) * 0.15,
        6,
    )


def _source_group(label: str) -> str:
    normalized = label.replace("\\", "/")
    if normalized.startswith("test1/"):
        return "test1"
    if normalized.startswith("test2/"):
        return "test2"
    return "resumes_docx"


def evaluate(
    source_dir: Path,
    private_dir: Path,
    public_output: Path,
    selected_count: int,
) -> dict[str, Any]:
    parser = ResumeParser()
    profile_extractor = ResumeProfileExtractor()
    skill_extractor = RuleSkillExtractor()
    private_dir.mkdir(parents=True, exist_ok=True)
    image_dir = private_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    cache_path = private_dir / "ocr_private.json"
    cached_rows: dict[str, dict[str, Any]] = {}
    if cache_path.exists():
        cached_payload = json.loads(cache_path.read_text(encoding="utf-8"))
        cached_rows = {
            row["content_hash"]: row for row in cached_payload.get("records", [])
        }
    rows: list[dict[str, Any]] = []
    for source_label, content in _source_images(source_dir):
            digest = sha256(content).hexdigest()
            if digest in cached_rows:
                cached = cached_rows[digest]
                cached["source_document"] = source_label
                rows.append(cached)
                continue
            record_id = f"collected-{len(rows) + 1:03d}"
            image = Image.open(io.BytesIO(content))
            suffix = ".jpg" if image.format in {"JPEG", "JPG"} else ".png"
            image_path = image_dir / f"{record_id}{suffix}"
            image_path.write_bytes(content)
            optimized_text, optimized = parser.ocr_image_with_diagnostics(
                content, optimized=True
            )
            baseline = next(
                candidate
                for candidate in optimized["candidates"]
                if candidate["variant"] == "original"
            )
            profile = profile_extractor.extract(optimized_text)
            skills = skill_extractor.extract(jd_text=optimized_text).skills
            flags = _field_flags(optimized_text, profile)
            pseudonym = profile_extractor.pseudonym(profile.get("name"), optimized_text)
            rows.append({
                "id": record_id,
                "source_document": source_label,
                "image_path": str(image_path.resolve()),
                "content_hash": digest,
                "width": image.width,
                "height": image.height,
                "baseline": baseline,
                "optimized": optimized,
                "quality_score": _quality_score(optimized, flags, len(skills)),
                "field_flags": flags,
                "profile": profile,
                "pseudonym": pseudonym,
                "skills": [item.name for item in skills],
                "text": optimized_text,
            })

    ranked = sorted(
        rows,
        key=lambda row: (
            row["quality_score"],
            sum(row["field_flags"].values()),
            len(row["skills"]),
            row["optimized"]["character_count"],
        ),
        reverse=True,
    )
    selected: list[dict[str, Any]] = []
    seen_people: set[str] = set()
    for row in ranked:
        person_key = row["pseudonym"]
        if person_key in seen_people:
            continue
        seen_people.add(person_key)
        selected.append(row)
        if len(selected) >= selected_count:
            break
    if len(selected) < selected_count:
        raise RuntimeError(
            f"Only {len(selected)} unique parseable resumes available; expected {selected_count}"
        )

    private_payload = {
        "source_dir": str(source_dir.resolve()),
        "records": rows,
        "selected_ids": [row["id"] for row in selected],
    }
    (private_dir / "ocr_private.json").write_text(
        json.dumps(private_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    def public_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "pseudonym": row["pseudonym"],
            "content_hash": row["content_hash"],
            "dimensions": [row["width"], row["height"]],
            "baseline_confidence": row["baseline"]["mean_confidence"],
            "optimized_confidence": row["optimized"]["mean_confidence"],
            "selected_variant": row["optimized"]["selected_variant"],
            "character_count": row["optimized"]["character_count"],
            "field_flags": row["field_flags"],
            "skill_count": len(row["skills"]),
            "quality_score": row["quality_score"],
        }

    baseline_confidence = mean(row["baseline"]["mean_confidence"] for row in rows)
    optimized_confidence = mean(row["optimized"]["mean_confidence"] for row in rows)
    field_rate = mean(sum(row["field_flags"].values()) / 4 for row in rows)
    result = {
        "dataset": "locally collected resumes from docs/resumes",
        "privacy": "Public report contains hashes and aggregate diagnostics only; OCR text and personal fields stay under ignored tmp/.",
        "records": len(rows),
        "selected_records": len(selected),
        "source_distribution": dict(Counter(_source_group(row["source_document"]) for row in rows)),
        "selected_source_distribution": dict(Counter(_source_group(row["source_document"]) for row in selected)),
        "metric_warning": "OCR confidence and key-field recognition are quality proxies, not character accuracy against human transcription.",
        "baseline_mean_ocr_confidence": round(baseline_confidence, 6),
        "optimized_mean_ocr_confidence": round(optimized_confidence, 6),
        "confidence_delta": round(optimized_confidence - baseline_confidence, 6),
        "key_field_recognition_rate": round(field_rate, 6),
        "selected_variant_distribution": dict(Counter(row["optimized"]["selected_variant"] for row in rows)),
        "mean_skill_count": round(mean(len(row["skills"]) for row in rows), 3),
        "selected_ids": [row["id"] for row in selected],
        "records_summary": [public_row(row) for row in rows],
    }
    public_output.parent.mkdir(parents=True, exist_ok=True)
    public_output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=PROJECT_DIR / "docs" / "resumes")
    parser.add_argument("--private-dir", type=Path, default=PROJECT_DIR / "tmp" / "collected_resume_evaluation")
    parser.add_argument("--public-output", type=Path, default=BACKEND_DIR / "evaluation" / "collected_resume_metrics.json")
    parser.add_argument("--selected-count", type=int, default=15)
    args = parser.parse_args()
    result = evaluate(args.source_dir, args.private_dir, args.public_output, args.selected_count)
    print(json.dumps({key: value for key, value in result.items() if key != "records_summary"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
