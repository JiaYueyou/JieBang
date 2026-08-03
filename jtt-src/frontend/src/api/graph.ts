import api from './index'
import type { ApiResponse, Neo4jGraphSubgraph } from '@/types'

function emptySubgraph(): Neo4jGraphSubgraph {
  return { nodes: [], edges: [], node_count: 0, edge_count: 0, snapshot_version: null, truncated: false }
}

export async function getPanorama(params?: {
  stack?: string; level?: string; node_type?: string; keyword?: string; limit?: number
}): Promise<Neo4jGraphSubgraph> {
  const res = await api.get<ApiResponse<Neo4jGraphSubgraph>>('/graph/panorama', { params })
  return (res as any).data || emptySubgraph()
}

export async function getNodeDetail(nodeId: string): Promise<Neo4jGraphSubgraph> {
  const res = await api.get<ApiResponse<Neo4jGraphSubgraph>>(`/graph/nodes/${nodeId}`)
  return (res as any).data || emptySubgraph()
}

export async function expandNode(nodeId: string, depth = 2, limit = 300): Promise<Neo4jGraphSubgraph> {
  const res = await api.get<ApiResponse<Neo4jGraphSubgraph>>('/graph/expand', {
    params: { node_id: nodeId, depth, limit }
  })
  return (res as any).data || emptySubgraph()
}

export async function searchNodes(q: string, types?: string, limit = 20): Promise<Neo4jGraphSubgraph> {
  const res = await api.get<ApiResponse<Neo4jGraphSubgraph>>('/graph/search', {
    params: { q, types, limit }
  })
  return (res as any).data || emptySubgraph()
}

export async function getPath(fromId: string, toId: string, maxDepth = 6): Promise<Neo4jGraphSubgraph> {
  const res = await api.get<ApiResponse<Neo4jGraphSubgraph>>('/graph/path', {
    params: { from_id: fromId, to_id: toId, max_depth: maxDepth }
  })
  return (res as any).data || emptySubgraph()
}

export async function getJobTree(jobId: number, depth = 5): Promise<Neo4jGraphSubgraph> {
  const res = await api.get<ApiResponse<Neo4jGraphSubgraph>>(`/graph/jobs/${jobId}/tree`, {
    params: { depth }
  })
  return (res as any).data || emptySubgraph()
}
