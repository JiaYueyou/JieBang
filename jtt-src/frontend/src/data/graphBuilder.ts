/**
 * 图谱数据转换 —— 将 Neo4j 后端数据转为 G6 可渲染格式。
 */
import type { Neo4jGraphSubgraph, Neo4jNodeType } from '@/types'

export interface G6Node {
  id: string
  data: {
    label: string
    nodeType: Neo4jNodeType
    layer: number
    description: string
    stack: string | null
    level: string | null
    importance: number | null
    frequency: number | null
    properties: Record<string, unknown>
  }
}

export interface G6Edge {
  source: string
  target: string
  data: {
    relation: string
    properties: Record<string, unknown>
  }
}

const TYPE_LAYER: Record<string, number> = {
  Job: 1, SkillArea: 2, TechStack: 3,
  TechPoint: 4, KnowledgePoint: 5,
  SourceDocument: 0, GraphSnapshot: 0,
}

export const TYPE_COLORS: Record<string, string> = {
  Job: '#122d6e',
  SkillArea: '#2f47b8',
  TechStack: '#3f5ae0',
  TechPoint: '#7893de',
  KnowledgePoint: '#b4c2f2',
  SourceDocument: '#94a3b8',
  GraphSnapshot: '#64748b',
}

export const TYPE_SIZES: Record<string, [number, number]> = {
  Job: [110, 44],
  SkillArea: [96, 40],
  TechStack: [82, 34],
  TechPoint: [66, 28],
  KnowledgePoint: [50, 24],
  SourceDocument: [60, 26],
  GraphSnapshot: [60, 26],
}

export const TYPE_LABELS: Record<string, string> = {
  Job: '岗位',
  SkillArea: '技能领域',
  TechStack: '技术栈',
  TechPoint: '技术点',
  KnowledgePoint: '知识点',
  SourceDocument: '来源文档',
  GraphSnapshot: '快照',
}

export const RELATION_LABELS: Record<string, string> = {
  REQUIRES_AREA: '需求',
  CONTAINS: '包含',
  REFINES_TO: '细化为',
  HAS_KNOWLEDGE: '包含知识',
  RELATED_TO: '相关',
  PREREQUISITE: '前置',
  SUPPORTS: '支持',
  HAS_SNAPSHOT: '快照',
}

const HIERARCHY_RELATIONS = new Set([
  'REQUIRES_AREA', 'CONTAINS', 'REFINES_TO', 'HAS_KNOWLEDGE',
])

const CROSS_RELATIONS = new Set([
  'RELATED_TO', 'PREREQUISITE', 'SUPPORTS', 'HAS_SNAPSHOT',
])

export function isHierarchyEdge(relation: string): boolean {
  return HIERARCHY_RELATIONS.has(relation)
}

export function isCrossEdge(relation: string): boolean {
  return CROSS_RELATIONS.has(relation)
}

export function transformToG6(subgraph: Neo4jGraphSubgraph): { nodes: G6Node[]; edges: G6Edge[] } {
  const nodes: G6Node[] = subgraph.nodes.map(n => ({
    id: n.id,
    data: {
      label: n.name,
      nodeType: n.type,
      layer: TYPE_LAYER[n.type] ?? 3,
      description: n.description || '',
      stack: n.stack,
      level: n.level,
      importance: n.importance,
      frequency: n.frequency,
      properties: n.properties,
    },
  }))

  const edges: G6Edge[] = subgraph.edges.map(e => ({
    source: e.source,
    target: e.target,
    data: {
      relation: e.relation,
      properties: e.properties,
    },
  }))

  return { nodes, edges }
}
