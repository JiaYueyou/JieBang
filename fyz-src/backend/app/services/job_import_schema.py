"""Canonical job-v1 normalization and validation for crawler imports."""

from __future__ import annotations

from typing import Any


CANONICAL_FIELDS = (
    "title",
    "company",
    "city",
    "salary",
    "experience",
    "education",
    "jd_text",
    "responsibilities",
    "requirements",
    "keywords",
    "posted_at",
    "url",
    "source",
    "crawled_at",
)

LEGACY_ALIASES = {
    "responsibilities": "duty",
    "requirements": "require",
    "posted_at": "post_date",
}


def normalize_job_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return one canonical job-v1 record while accepting the legacy crawler keys."""
    normalized = dict(record)
    for canonical, legacy in LEGACY_ALIASES.items():
        if normalized.get(canonical) in (None, "") and legacy in normalized:
            normalized[canonical] = normalized.get(legacy)

    keywords = normalized.get("keywords", normalized.get("keyword", []))
    if isinstance(keywords, str):
        keywords = [
            value.strip()
            for value in keywords.replace("，", ",").split(",")
            if value.strip()
        ]
    normalized["keywords"] = keywords

    for field in CANONICAL_FIELDS:
        normalized.setdefault(field, None)
    return normalized


def validate_job_record(record: dict[str, Any]) -> list[str]:
    """Validate the fields needed for traceable import and later evolution analysis."""
    errors: list[str] = []
    for field in ("title", "company", "jd_text", "url", "source", "crawled_at"):
        value = record.get(field)
        if value is None or not str(value).strip():
            errors.append(f"字段不能为空: {field}")

    jd_text = record.get("jd_text")
    if isinstance(jd_text, str) and len(jd_text.strip()) < 10:
        errors.append("jd_text 不能少于 10 个字符")
    if not isinstance(record.get("keywords"), list):
        errors.append("keywords 必须是数组")
    return errors


def normalize_and_validate_records(
    payload: Any,
    *,
    filename: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not isinstance(payload, list):
        return [], {
            "file": filename,
            "total": 0,
            "passed": 0,
            "failed": 1,
            "errors": [{"index": None, "title": "", "errors": ["数据文件必须是数组"]}],
        }

    normalized_records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for index, raw in enumerate(payload):
        if not isinstance(raw, dict):
            errors.append(
                {"index": index, "title": "", "errors": ["记录必须是对象"]}
            )
            continue
        record = normalize_job_record(raw)
        record_errors = validate_job_record(record)
        if not str(record.get("posted_at") or "").strip():
            warnings.append(
                {
                    "index": index,
                    "title": str(record.get("title") or ""),
                    "warnings": ["源站未提供 posted_at，已保留为空值"],
                }
            )
        if record_errors:
            errors.append(
                {
                    "index": index,
                    "title": str(record.get("title") or ""),
                    "errors": record_errors,
                }
            )
        else:
            normalized_records.append(record)

    total = len(payload)
    return normalized_records, {
        "file": filename,
        "total": total,
        "passed": total - len(errors),
        "failed": len(errors),
        "errors": errors[:20],
        "warning_count": len(warnings),
        "warnings": warnings[:20],
    }
