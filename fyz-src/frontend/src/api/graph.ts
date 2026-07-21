import request from "./request";
import type { ApiResponse } from "./types";

export interface GraphNode {
  id: string;
  name: string;
  type: "Job" | "SkillArea" | "TechStack" | "TechPoint" | "KnowledgePoint" | "SourceDocument" | "GraphSnapshot";
  stack: string | null;
  level: string | null;
  description: string;
  importance: number | null;
  frequency: number | null;
  x: number | null;
  y: number | null;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  properties: Record<string, unknown>;
}

export interface GraphSubgraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  node_count: number;
  edge_count: number;
  snapshot_version: string | null;
  truncated: boolean;
}

export async function getPanorama(
  params?: {
    stack?: string;
    level?: string;
    node_type?: string;
    keyword?: string;
    limit?: number;
  }
): Promise<GraphSubgraph> {
  const res = await request.get<ApiResponse<GraphSubgraph>>("/graph/panorama", { params });
  return res.data.data || { nodes: [], edges: [], node_count: 0, edge_count: 0, snapshot_version: null, truncated: false };
}

export async function getNodeDetail(nodeId: string): Promise<GraphSubgraph> {
  const res = await request.get<ApiResponse<GraphSubgraph>>(`/graph/nodes/${nodeId}`);
  return res.data.data || { nodes: [], edges: [], node_count: 0, edge_count: 0, snapshot_version: null, truncated: false };
}

export async function expandNode(nodeId: string, depth: number = 2, limit: number = 300): Promise<GraphSubgraph> {
  const res = await request.get<ApiResponse<GraphSubgraph>>("/graph/expand", {
    params: { node_id: nodeId, depth, limit }
  });
  return res.data.data || { nodes: [], edges: [], node_count: 0, edge_count: 0, snapshot_version: null, truncated: false };
}

export async function searchNodes(q: string, types?: string, limit: number = 20): Promise<GraphSubgraph> {
  const res = await request.get<ApiResponse<GraphSubgraph>>("/graph/search", {
    params: { q, types, limit }
  });
  return res.data.data || { nodes: [], edges: [], node_count: 0, edge_count: 0, snapshot_version: null, truncated: false };
}

export async function getPath(fromId: string, toId: string, maxDepth: number = 6): Promise<GraphSubgraph> {
  const res = await request.get<ApiResponse<GraphSubgraph>>("/graph/path", {
    params: { from_id: fromId, to_id: toId, max_depth: maxDepth }
  });
  return res.data.data || { nodes: [], edges: [], node_count: 0, edge_count: 0, snapshot_version: null, truncated: false };
}

export async function getJobTree(jobId: number, depth: number = 5): Promise<GraphSubgraph> {
  const res = await request.get<ApiResponse<GraphSubgraph>>(`/graph/jobs/${jobId}/tree`, {
    params: { depth }
  });
  return res.data.data || { nodes: [], edges: [], node_count: 0, edge_count: 0, snapshot_version: null, truncated: false };
}
