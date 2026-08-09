"""图谱同步、补全与查询 DTO。"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from app.core.agent_runtime import GraphEnrichmentOutput, KnowledgePointOutput, TechPointOutput
GraphNodeType = Literal[
    "Job", "SkillArea", "TechStack", "TechPoint",
    "KnowledgePoint", "SourceDocument", "GraphSnapshot",
]


class GraphSyncMode(str, Enum):
    full = "full"
    incremental = "incremental"


class GraphSyncRequest(BaseModel):
    mode: GraphSyncMode = GraphSyncMode.incremental
    enrich_top_skills: bool = True


class GraphNode(BaseModel):
    id: str
    name: str
    type: GraphNodeType
    stack: str | None = None
    level: str | None = None
    description: str = ""
    importance: float | None = None
    frequency: int | None = None
    x: float | None = None
    y: float | None = None
    properties: dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relation: str
    properties: dict = Field(default_factory=dict)


class GraphSubgraph(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0
    snapshot_version: str | None = None
    truncated: bool = False
    returned: int = 0
    total_available: int | None = None
    next_cursor: str | None = None
    has_more: bool = False
    query_scope: str | None = None


class GraphSnapshotResponse(BaseModel):
    id: str
    version: str
    snapshot_type: str
    status: str
    node_count: int
    edge_count: int
    fact_count: int
    metadata: dict
    created_at: datetime
    completed_at: datetime | None


class GraphEnrichmentCandidateResponse(BaseModel):
    id: int
    snapshot_id: str
    skill_id: int
    skill_name: str
    candidate_data: dict
    evidence_source_ids: list[str]
    confidence: float
    machine_validation_status: str
    review_status: str
    publication_status: str
    review_note: str | None
    reviewed_at: datetime | None
    published_at: datetime | None
    lock_version: int
    agent_run_id: str | None
    created_at: datetime
    updated_at: datetime


class GraphEnrichmentCandidatePage(BaseModel):
    items: list[GraphEnrichmentCandidateResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    machine_failed_pending_count: int = 0


class GraphEnrichmentBatchRejectResponse(BaseModel):
    rejected_count: int
    candidate_ids: list[int] = Field(default_factory=list)


class GraphEnrichmentReviewRequest(BaseModel):
    action: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=500)
    lock_version: int = Field(ge=0)


class GraphEnrichmentPublishRequest(BaseModel):
    candidate_ids: list[int] = Field(default_factory=list, max_length=100)
