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
  returned?: number;
  total_available?: number | null;
  next_cursor?: string | null;
  has_more?: boolean;
  query_scope?: string | null;
}

const EMPTY_GRAPH: GraphSubgraph = {
  nodes: [], edges: [], node_count: 0, edge_count: 0,
  snapshot_version: null, truncated: false, returned: 0, has_more: false,
  next_cursor: null,
};

export async function getOverview(params?: {
  cursor?: string;
  page_size?: number;
  max_layer?: 1 | 2 | 3;
  stack?: string;
  level?: string;
  keyword?: string;
}): Promise<GraphSubgraph> {
  const res = await request.get<ApiResponse<GraphSubgraph>>("/graph/overview", { params });
  return res.data.data || EMPTY_GRAPH;
}

export async function getNodeNeighbors(
  nodeId: string,
  params?: { cursor?: string; page_size?: number; max_layer?: 1 | 2 | 3 | 4 | 5 },
): Promise<GraphSubgraph> {
  const res = await request.get<ApiResponse<GraphSubgraph>>(
    `/graph/nodes/${encodeURIComponent(nodeId)}/neighbors`, { params },
  );
  return res.data.data || EMPTY_GRAPH;
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
