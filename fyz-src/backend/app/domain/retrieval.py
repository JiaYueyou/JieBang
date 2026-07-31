"""Portable retrieval contracts, deterministic chunking and baseline vectors."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Protocol

CHUNKING_VERSION = "evidence-window-v1"
INDEX_TEXT_VERSION = "job-skill-evidence-v2"
HASH_EMBEDDING_MODEL = "signed-token-hash-v1"
HASH_EMBEDDING_DIMENSION = 256

SKILL_SEARCH_CONTEXTS = {
    "Git": "分布式版本控制、分支协作、提交历史与代码变更追踪",
    "Java": "JVM 生态的面向对象编程语言、服务端开发与工程化",
    "MyBatis": "Java 持久化层、SQL 映射器、ORM DAO 与数据库访问框架",
    "MySQL": "关系型数据库、表结构设计、SQL 查询、事务与性能优化",
    "Redis": "内存键值数据库、高并发缓存、数据结构与分布式协调",
    "Spring": "Java 企业应用框架、IoC 依赖注入、容器与事务管理",
    "Spring Boot": "Java 服务快速启动、自动配置、Starter 与微服务工程",
    "技术文档": "接口说明、架构决策、研发规范与交付材料编写",
    "需求分析": "业务场景理解、软件需求拆解、功能边界与验收标准",
}


class EmbeddingProvider(Protocol):
    name: str
    model: str
    dimension: int

    async def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


def retrieval_tokens(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", (text or "").casefold()).strip()
    latin = re.findall(r"[a-z0-9+#.]{2,}", normalized)
    chinese_runs = re.findall(r"[\u4e00-\u9fff]+", normalized)
    chinese = [
        run[index : index + 2]
        for run in chinese_runs
        for index in range(max(len(run) - 1, 1))
        if run[index : index + 2]
    ]
    return latin + chinese


class HashEmbeddingProvider:
    """Deterministic offline baseline; replaceable by a semantic provider."""

    name = "local_deterministic"
    model = HASH_EMBEDDING_MODEL

    def __init__(self, dimension: int = HASH_EMBEDDING_DIMENSION) -> None:
        if dimension < 32:
            raise ValueError("embedding dimension must be at least 32")
        self.dimension = dimension

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in retrieval_tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            return [round(value / norm, 8) for value in vector]
        return vector


@dataclass(frozen=True)
class EvidenceWindow:
    evidence_id: str
    text: str
    char_start: int | None
    char_end: int | None


def build_evidence_window(
    *,
    fact_id: int,
    raw_job_record_id: int,
    skill_id: int,
    jd_text: str,
    evidence_text: str,
    skill_name: str,
    radius: int = 220,
) -> EvidenceWindow:
    source = jd_text or evidence_text or ""
    anchor = (evidence_text or "").strip()
    start = source.find(anchor) if anchor else -1
    if start < 0 and skill_name:
        start = source.casefold().find(skill_name.casefold())
        anchor = skill_name if start >= 0 else ""
    if start >= 0:
        end = start + len(anchor)
        window_start = max(0, start - radius)
        window_end = min(len(source), end + radius)
        text = source[window_start:window_end].strip()
        char_start = window_start
        char_end = window_end
    else:
        text = source[: radius * 2].strip()
        char_start = 0 if text else None
        char_end = len(text) if text else None
    stable = f"{fact_id}:{raw_job_record_id}:{skill_id}"
    evidence_id = "ev_" + hashlib.sha256(stable.encode("utf-8")).hexdigest()[:40]
    return EvidenceWindow(
        evidence_id=evidence_id,
        text=text,
        char_start=char_start,
        char_end=char_end,
    )


def embedding_checksum(vector: list[float]) -> str:
    payload = ",".join(f"{value:.8f}" for value in vector)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    score = sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)
    return round(max(0.0, min(1.0, score)), 6)


def lexical_score(query: str, text: str) -> float:
    query_tokens = set(retrieval_tokens(query))
    if not query_tokens:
        return 0.0
    text_tokens = set(retrieval_tokens(text))
    return round(len(query_tokens & text_tokens) / len(query_tokens), 6)


def build_index_text(
    *,
    standard_job_name: str,
    skill_name: str,
    chunk_text: str,
    skill_aliases: list[str] | None = None,
) -> str:
    """Add authoritative labels to the searchable document, not the citation."""

    skill_context = SKILL_SEARCH_CONTEXTS.get(skill_name, "")
    aliases = " ".join(
        alias.strip()
        for alias in (skill_aliases or [])
        if alias and alias.strip()
    )
    return "\n".join(
        value.strip()
        for value in (
            standard_job_name,
            skill_name,
            aliases,
            skill_context,
            chunk_text,
        )
        if value and value.strip()
    )


def match_authoritative_labels(
    query: str,
    *,
    standard_jobs: dict[int, str],
    skills: dict[int, str],
) -> tuple[set[int], set[int]]:
    """Resolve explicit job/skill mentions without treating job text as skill."""

    remainder = (query or "").casefold()

    def label_pattern(label: str) -> re.Pattern[str]:
        escaped = re.escape(label)
        if label.isascii():
            return re.compile(
                rf"(?<![a-z0-9]){escaped}(?![a-z0-9])",
                re.IGNORECASE,
            )
        return re.compile(escaped, re.IGNORECASE)

    matched_jobs: set[int] = set()
    for job_id, label in sorted(
        standard_jobs.items(),
        key=lambda item: len(item[1]),
        reverse=True,
    ):
        normalized = label.strip().casefold()
        pattern = label_pattern(normalized)
        if normalized and pattern.search(remainder):
            matched_jobs.add(job_id)
            remainder = pattern.sub(" ", remainder)

    matched_skills: set[int] = set()
    for skill_id, label in sorted(
        skills.items(),
        key=lambda item: len(item[1]),
        reverse=True,
    ):
        normalized = label.strip().casefold()
        pattern = label_pattern(normalized)
        if normalized and pattern.search(remainder):
            matched_skills.add(skill_id)
            remainder = pattern.sub(" ", remainder)
    return matched_jobs, matched_skills
