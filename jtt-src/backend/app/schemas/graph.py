"""图谱查询 DTO。"""
from typing import Literal

from pydantic import BaseModel, Field

GraphNodeType = Literal[
    "Job", "SkillArea", "TechStack", "TechPoint",
    "KnowledgePoint", "SourceDocument", "GraphSnapshot",
]


class GraphNode(BaseModel):
    id: str
    name: str
    type: GraphNodeType
    stack: str | None = None
    level: str | None = None
    description: str = ""
    importance: float | None = None
    frequency: int | None = None
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
