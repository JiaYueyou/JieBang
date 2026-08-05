"""Schemas for evidence indexing, hybrid retrieval and citation handoff."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.config import RETRIEVAL_VECTOR_BACKEND


class RetrievalRebuildRequest(BaseModel):
    backend: str = Field(
        default=RETRIEVAL_VECTOR_BACKEND,
        pattern="^(local_hash|neo4j_vector|chroma)$",
    )


class RetrievalSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    standard_job_id: int | None = Field(default=None, ge=1)
    skill_ids: list[int] = Field(default_factory=list, max_length=50)
    source_platforms: list[str] = Field(default_factory=list, max_length=20)
    verification_statuses: list[str] = Field(
        default_factory=lambda: ["human_approved", "machine_validated"],
        max_length=5,
    )
    minimum_quality_score: float = Field(default=0.55, ge=0, le=1)
    minimum_retrieval_score: float = Field(default=0.2, ge=0, le=1)
    posted_from: datetime | None = None
    top_k: int = Field(default=5, ge=1, le=50)
    index_version: str | None = Field(default=None, max_length=80)

    @field_validator("skill_ids")
    @classmethod
    def unique_skill_ids(cls, value: list[int]) -> list[int]:
        if any(item <= 0 for item in value):
            raise ValueError("skill_ids 必须为正整数")
        return list(dict.fromkeys(value))

    @field_validator("verification_statuses")
    @classmethod
    def validate_statuses(cls, value: list[str]) -> list[str]:
        allowed = {"human_approved", "machine_validated"}
        if not value or not set(value).issubset(allowed):
            raise ValueError("检索仅允许已人工批准或机器认证的证据")
        return list(dict.fromkeys(value))


class EvidenceChunkResponse(BaseModel):
    evidence_id: str
    job_skill_fact_id: int
    raw_job_record_id: int
    source_document_id: int
    standard_job_id: int
    skill_id: int
    skill_name: str
    chunk_text: str
    char_start: int | None
    char_end: int | None
    source_platform: str
    source_url: str | None
    posted_at: datetime | None
    quality_score: float
    verification_status: str
    near_duplicate_group_id: str | None


class RetrievedEvidence(EvidenceChunkResponse):
    retrieval_score: float
    lexical_score: float
    vector_score: float
    graph_score: float
    index_version: str


class RetrievalSearchResponse(BaseModel):
    query: str
    index_version: str
    backend: str
    items: list[RetrievedEvidence]
    latency_ms: int
    truncated: bool
    warnings: list[str] = Field(default_factory=list)


class RetrievalIndexResponse(BaseModel):
    id: str
    version: str
    backend: str
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int
    chunking_version: str
    status: str
    chunk_count: int
    entry_count: int
    metadata_json: dict
    created_by: int | None
    created_at: datetime
    completed_at: datetime | None
