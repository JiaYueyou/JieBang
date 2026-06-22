"""图谱同步、补全与查询 DTO。"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

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


class KnowledgePointOutput(BaseModel):
    name: str
    description: str
    difficulty: Literal["easy", "medium", "hard"]
    confidence: float = Field(ge=0, le=1)
    source_ids: list[int] = Field(min_length=2)
    prerequisites: list[str] = Field(default_factory=list)


class TechPointOutput(BaseModel):
    name: str
    detail: str
    confidence: float = Field(ge=0, le=1)
    source_ids: list[int] = Field(min_length=2)
    knowledge_points: list[KnowledgePointOutput] = Field(default_factory=list)


class GraphEnrichmentOutput(BaseModel):
    skill_name: str
    tech_points: list[TechPointOutput] = Field(default_factory=list)
