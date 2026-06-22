"""规则优先的技能抽取器。"""

from __future__ import annotations

import hashlib
import re

from app.domain.skill_dictionary import SKILL_ALIASES, SKILL_DICT, normalize_skill
from app.schemas.skill import ExtractedSkill, SkillExtractionOutput, SkillKind

PREFERRED_MARKERS = ("优先", "加分", "bonus", "preferred", "者优先")


def normalize_text(value: str | list | None) -> str:
    if isinstance(value, list):
        value = "\n".join(str(item) for item in value)
    return re.sub(r"\s+", " ", str(value or "")).strip()


def content_fingerprint(record: dict) -> str:
    payload = "|".join(
        normalize_text(record.get(key)).casefold()
        for key in ("source", "url", "title", "company", "posted_at", "jd_text")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _pattern(term: str) -> re.Pattern:
    escaped = re.escape(term)
    if term.isascii() and term.replace(" ", "").replace(".", "").replace("/", "").replace("+", "").replace("#", "").isalnum():
        return re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", re.IGNORECASE)
    return re.compile(escaped, re.IGNORECASE)


def _evidence(text: str, start: int, end: int, radius: int = 55) -> str:
    return text[max(0, start - radius): min(len(text), end + radius)].strip()


def _clause(text: str, start: int, end: int) -> str:
    separators = "，,。；;.!！？?\n"
    left = max((text.rfind(char, 0, start) for char in separators), default=-1)
    right_candidates = [text.find(char, end) for char in separators]
    right_candidates = [value for value in right_candidates if value >= 0]
    right = min(right_candidates) if right_candidates else len(text)
    return text[left + 1:right].strip()


class RuleSkillExtractor:
    def extract(self, *, jd_text: str, responsibilities: str = "", requirements: str = "") -> SkillExtractionOutput:
        sections = [
            ("required", normalize_text(jd_text)),
            ("required", normalize_text(responsibilities)),
            ("required", normalize_text(requirements)),
        ]
        terms = [(name, name) for name in SKILL_DICT]
        terms.extend((alias, canonical) for alias, canonical in SKILL_ALIASES.items())
        found: dict[str, ExtractedSkill] = {}
        frequencies: dict[str, int] = {}
        for _, text in sections:
            for term, canonical in terms:
                normalized = normalize_skill(canonical)
                if not normalized:
                    continue
                name, category = normalized
                for match in _pattern(term).finditer(text):
                    evidence = _evidence(text, match.start(), match.end())
                    clause = _clause(text, match.start(), match.end())
                    kind = (
                        SkillKind.preferred
                        if any(marker.casefold() in clause.casefold() for marker in PREFERRED_MARKERS)
                        else SkillKind.required
                    )
                    confidence = 0.96 if term == name else 0.92
                    existing = found.get(name)
                    if existing is None or (
                        existing.kind == SkillKind.preferred and kind == SkillKind.required
                    ):
                        found[name] = ExtractedSkill(
                            name=name,
                            category=category,
                            kind=kind,
                            confidence=confidence,
                            evidence=evidence,
                        )
                    frequencies[name] = frequencies.get(name, 0) + 1
        return SkillExtractionOutput(
            skills=sorted(found.values(), key=lambda item: (-frequencies[item.name], item.name))
        )
