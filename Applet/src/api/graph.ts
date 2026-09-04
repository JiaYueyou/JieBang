/**
 * 图谱 API —— Mock 实现（契约与真实接口一致，后续可切回 HTTP）。
 * 节点 shape 与 SkillGraph 组件、fyz GraphView 对齐。
 */
import * as M from '@/mock/data'

export interface GraphNode {
  id: string
  label: string
  type: 'root' | 'position' | 'domain_branch' | 'skillset_branch' | 'module' | 'knowledge'
  layer: 1 | 2 | 3 | 4 | 5
  root_id: string
}

export interface GraphEdge {
  source: string
  target: string
  relation: string
  weight: number
}

export interface GraphSubgraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface GraphNodeDetail extends GraphNode {
  degree: number
  relation: string
}

const delay = (ms = 260) => new Promise((r) => setTimeout(r, ms))

function clone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v))
}

export async function apiGraphPanorama(): Promise<GraphSubgraph> {
  await delay(320)
  return { nodes: clone(M.graphNodes), edges: clone(M.graphEdges) }
}

export async function apiGraphSearch(keyword: string): Promise<GraphSubgraph> {
  await delay(220)
  const kw = keyword.trim().toLowerCase()
  if (!kw) return apiGraphPanorama()
  const matched = M.graphNodes.filter((n) => n.label.toLowerCase().includes(kw))
  if (!matched.length) return { nodes: [], edges: [] }
  // 命中节点 + 一跳邻居，保证视图有结构感
  const ids = new Set(matched.map((n) => n.id))
  for (const e of M.graphEdges) {
    if (ids.has(e.source)) ids.add(e.target)
    if (ids.has(e.target)) ids.add(e.source)
  }
  const nodes = M.graphNodes.filter((n) => ids.has(n.id))
  const edges = M.graphEdges.filter((e) => ids.has(e.source) && ids.has(e.target))
  return { nodes: clone(nodes), edges: clone(edges) }
}

export async function apiGraphExpand(nodeId: string): Promise<GraphSubgraph> {
  await delay(240)
  const ids = new Set<string>([nodeId])
  for (const e of M.graphEdges) {
    if (e.source === nodeId) ids.add(e.target)
    if (e.target === nodeId) ids.add(e.source)
  }
  const nodes = M.graphNodes.filter((n) => ids.has(n.id))
  const edges = M.graphEdges.filter((e) => ids.has(e.source) && ids.has(e.target))
  return { nodes: clone(nodes), edges: clone(edges) }
}

export async function apiGraphNode(nodeId: string): Promise<GraphNodeDetail> {
  await delay(160)
  const node = M.graphNodes.find((n) => n.id === nodeId)
  if (!node) throw new Error('节点不存在')
  const rel = M.graphEdges.find((e) => e.source === nodeId || e.target === nodeId)
  return { ...clone(node), degree: M.graphEdges.filter((e) => e.source === nodeId || e.target === nodeId).length, relation: rel?.relation ?? 'contains' }
}
