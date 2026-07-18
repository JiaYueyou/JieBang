"""规则优先的技能抽取器。"""

from __future__ import annotations

import hashlib
import re

from app.domain.skill_dictionary import SKILL_ALIASES, SKILL_DICT, normalize_skill
from app.schemas.skill import ExtractedSkill, SkillExtractionOutput, SkillKind

PREFERRED_MARKERS = ("优先", "加分", "bonus", "preferred", "者优先")

# 否定词：技能前出现这些词就不抽取
NEGATION_WORDS = (
    "不", "无需", "不需要", "不要", "不用", "不得",
    "不要求", "不作", "不是", "非", "并非",
    "无", "没有", "未经",
)

# 程度词及其权重
PROFICIENCY_LEVELS = [
    (re.compile(r"精通\s*"), 1.0),
    (re.compile(r"深入理解\s*"), 0.95),
    (re.compile(r"深入掌握\s*"), 0.95),
    (re.compile(r"熟练掌握\s*"), 0.90),
    (re.compile(r"熟练\s*"), 0.85),
    (re.compile(r"掌握\s*"), 0.80),
    (re.compile(r"熟悉\s*"), 0.75),
    (re.compile(r"了解\s*"), 0.50),
    (re.compile(r"理解\s*"), 0.55),
    (re.compile(r"用过\s*"), 0.45),
    (re.compile(r"接触过\s*"), 0.40),
    (re.compile(r"会\s*"), 0.50),
    (re.compile(r"能使用\s*"), 0.55),
    (re.compile(r"使用过\s*"), 0.60),
    (re.compile(r"负责.*?技术\s*"), 0.65),
]


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


def _has_negation(text: str, match_start: int) -> bool:
    """检查技能匹配位置前是否有否定词"""
    lookback_start = max(0, match_start - 15)
    prefix = text[lookback_start:match_start].strip()
    if len(prefix) > 10:
        prefix = prefix[-10:]
    for neg in NEGATION_WORDS:
        if neg in prefix:
            return True
    return False


def _detect_proficiency(text: str, match_start: int) -> tuple[float, str]:
    """检测技能前的程度词，返回 (置信度加成, 程度标签)"""
    # 先找到技能前面最近的句子分隔符，只在同1个分句内查找
    sep_pos = -1
    for sep in ("。", "；", "!", "！", "?", "？", "\n"):
        pos = text.rfind(sep, max(0, match_start - 30), match_start)
        if pos > sep_pos:
            sep_pos = pos

    # 从分句开头到技能位置，最多看15字符
    clause_start = max(sep_pos + 1, match_start - 15)
    prefix = text[clause_start:match_start]

    # 从右向左找最近的程度词：找所有程度词，取距离技能最近的
    best_boost = 0.70
    best_label = "familiar"
    best_distance = 999

    for pattern, boost in PROFICIENCY_LEVELS:
        for m in pattern.finditer(prefix):
            # 注意：m.end() 是相对于 prefix 的位置，要转成绝对位置
            abs_end = clause_start + m.end()
            between = text[abs_end:match_start].strip()
            if not between or between in ("，", ",", "、", " "):
                dist = match_start - (clause_start + m.start())
                if dist < best_distance:
                    best_distance = dist
                    best_boost = boost
                    best_label = _proficiency_label(boost)

    return best_boost, best_label


def _proficiency_label(boost: float) -> str:
    if boost >= 0.95:
        return "master"
    elif boost >= 0.85:
        return "expert"
    elif boost >= 0.70:
        return "skilled"
    elif boost >= 0.55:
        return "familiar"
    else:
        return "basic"


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
                    # 否定过滤
                    if _has_negation(text, match.start()):
                        continue

                    evidence = _evidence(text, match.start(), match.end())
                    clause = _clause(text, match.start(), match.end())

                    # 程度识别
                    boost, proficiency = _detect_proficiency(text, match.start())

                    kind = (
                        SkillKind.preferred
                        if any(marker.casefold() in clause.casefold() for marker in PREFERRED_MARKERS)
                        else SkillKind.required
                    )

                    base_conf = 0.96 if term == name else 0.92
                    confidence = round(base_conf * boost, 2)

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
                            proficiency=proficiency,
                        )
                    frequencies[name] = frequencies.get(name, 0) + 1
        return SkillExtractionOutput(
            skills=sorted(found.values(), key=lambda item: (-frequencies[item.name], item.name))
        )
