/**
 * 图谱数据构建 —— 将 Neo4j 后端数据转为 graphology Graph，供 ECharts 渲染。
 */
import Graph from 'graphology'
import type { Neo4jGraphNode, Neo4jGraphEdge, Neo4jGraphSubgraph, Neo4jNodeType } from '@/types'

// ===== 节点视觉映射 =====
export const TYPE_COLORS: Record<string, string> = {
  Job: '#122d6e',
  SkillArea: '#2f47b8',
  TechStack: '#3f5ae0',
  TechPoint: '#7893de',
  KnowledgePoint: '#b4c2f2',
  SourceDocument: '#94a3b8',
  GraphSnapshot: '#64748b',
}

export const TYPE_SIZES: Record<string, number> = {
  Job: 30,
  SkillArea: 24,
  TechStack: 19,
  TechPoint: 14,
  KnowledgePoint: 10,
  SourceDocument: 12,
  GraphSnapshot: 12,
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

const TYPE_LEVELS: Record<string, string> = {
  Job: 'L1', SkillArea: 'L2', TechStack: 'L3',
  TechPoint: 'L4', KnowledgePoint: 'L5',
  SourceDocument: 'L0', GraphSnapshot: 'L0',
}

const TYPE_IMPORTANCE: Record<string, number> = {
  Job: 5, SkillArea: 4, TechStack: 3, TechPoint: 2, KnowledgePoint: 1,
  SourceDocument: 0, GraphSnapshot: 0,
}

export const RELATION_LABELS: Record<string, string> = {
  REQUIRES_AREA: '需求', CONTAINS: '包含',
  REFINES_TO: '细化为', HAS_KNOWLEDGE: '包含知识',
  RELATED_TO: '相关', PREREQUISITE: '前置',
  SUPPORTS: '支持', HAS_SNAPSHOT: '快照',
}

const HIERARCHY_RELATIONS = new Set(['REQUIRES_AREA', 'CONTAINS', 'REFINES_TO', 'HAS_KNOWLEDGE'])
const CROSS_RELATIONS = new Set(['RELATED_TO', 'PREREQUISITE', 'SUPPORTS', 'HAS_SNAPSHOT'])

export function isHierarchyEdge(relation: string): boolean { return HIERARCHY_RELATIONS.has(relation) }
export function isCrossEdge(relation: string): boolean { return CROSS_RELATIONS.has(relation) }

function getEdgeColor(relation: string): string {
  const map: Record<string, string> = {
    REQUIRES_AREA: 'rgba(76, 29, 149, 0.6)', CONTAINS: 'rgba(79, 110, 246, 0.5)',
    REFINES_TO: 'rgba(6, 182, 212, 0.4)', HAS_KNOWLEDGE: 'rgba(255, 255, 255, 0.3)',
    RELATED_TO: 'rgba(245, 158, 11, 0.4)', PREREQUISITE: 'rgba(232, 93, 93, 0.4)',
    SUPPORTS: 'rgba(52, 179, 126, 0.4)', HAS_SNAPSHOT: 'rgba(148, 163, 184, 0.3)',
  }
  return map[relation] || 'rgba(148, 163, 184, 0.3)'
}

function getRelationLabel(relation: string): string {
  return RELATION_LABELS[relation] || ''
}

function isParentRelation(relation: string): boolean {
  return ['REQUIRES_AREA', 'CONTAINS', 'REFINES_TO', 'HAS_KNOWLEDGE'].includes(relation)
}

// ===== 智能布局（五级分层预排） =====
export function applySmartLayout(graph: Graph): void {
  const nodesByLevel: Record<string, string[]> = { L1: [], L2: [], L3: [], L4: [], L5: [] }
  const nodeAttrs: Record<string, any> = {}
  const centerX = 0, centerY = 0

  graph.forEachNode((nodeId: string, attrs: any) => {
    nodeAttrs[nodeId] = attrs
    const level = attrs.level || 'L3'
    if (nodesByLevel[level]) nodesByLevel[level].push(nodeId)
  })

  // L1: 中心小圆
  const l1Nodes = nodesByLevel['L1'] || []
  l1Nodes.forEach((nodeId, index) => {
    const angle = (index / l1Nodes.length) * Math.PI * 2 - Math.PI / 2
    graph.setNodeAttribute(nodeId, 'x', centerX + Math.cos(angle) * 50)
    graph.setNodeAttribute(nodeId, 'y', centerY + Math.sin(angle) * 50)
    graph.setNodeAttribute(nodeId, 'z', 50)
  })

  // L2: 中环
  const l2Nodes = nodesByLevel['L2'] || []
  l2Nodes.forEach((nodeId, index) => {
    const angle = (index / l2Nodes.length) * Math.PI * 2 - Math.PI / 2
    graph.setNodeAttribute(nodeId, 'x', centerX + Math.cos(angle) * 200)
    graph.setNodeAttribute(nodeId, 'y', centerY + Math.sin(angle) * 200)
    graph.setNodeAttribute(nodeId, 'z', 40)
  })

  // L3: 围绕父节点
  const l3ByParent: Record<string, string[]> = {}
  graph.forEachEdge((_e, _a, source, target) => {
    const sl = nodeAttrs[source]?.level, tl = nodeAttrs[target]?.level
    if ((sl === 'L2' || sl === 'L1') && tl === 'L3') {
      (l3ByParent[source] ||= []).push(target)
    }
  })
  for (const [parentId, children] of Object.entries(l3ByParent)) {
    const px = nodeAttrs[parentId]?.x || 0
    const py = nodeAttrs[parentId]?.y || 0
    children.forEach((nodeId, index) => {
      const angle = (index / children.length) * Math.PI * 2
      graph.setNodeAttribute(nodeId, 'x', px + Math.cos(angle) * 120)
      graph.setNodeAttribute(nodeId, 'y', py + Math.sin(angle) * 120)
      graph.setNodeAttribute(nodeId, 'z', 30)
    })
  }
  // 未分配到父节点的 L3
  nodesByLevel['L3']?.forEach(nodeId => {
    if (graph.getNodeAttribute(nodeId, 'x') === 0 && graph.getNodeAttribute(nodeId, 'y') === 0) {
      const angle = Math.random() * Math.PI * 2
      graph.setNodeAttribute(nodeId, 'x', centerX + Math.cos(angle) * (350 + Math.random() * 100))
      graph.setNodeAttribute(nodeId, 'y', centerY + Math.sin(angle) * (350 + Math.random() * 100))
      graph.setNodeAttribute(nodeId, 'z', 30)
    }
  })

  // L4: 围绕 L3
  const l4ByParent: Record<string, string[]> = {}
  graph.forEachEdge((_e, _a, source, target) => {
    if (nodeAttrs[source]?.level === 'L3' && nodeAttrs[target]?.level === 'L4') {
      (l4ByParent[source] ||= []).push(target)
    }
  })
  for (const [parentId, children] of Object.entries(l4ByParent)) {
    const px = nodeAttrs[parentId]?.x || 0
    const py = nodeAttrs[parentId]?.y || 0
    children.forEach((nodeId, index) => {
      const angle = (index / children.length) * Math.PI * 2
      graph.setNodeAttribute(nodeId, 'x', px + Math.cos(angle) * 80)
      graph.setNodeAttribute(nodeId, 'y', py + Math.sin(angle) * 80)
      graph.setNodeAttribute(nodeId, 'z', 20)
    })
  }

  // L5: 围绕 L4
  const l5ByParent: Record<string, string[]> = {}
  graph.forEachEdge((_e, _a, source, target) => {
    if (nodeAttrs[source]?.level === 'L4' && nodeAttrs[target]?.level === 'L5') {
      (l5ByParent[source] ||= []).push(target)
    }
  })
  for (const [parentId, children] of Object.entries(l5ByParent)) {
    const px = nodeAttrs[parentId]?.x || 0
    const py = nodeAttrs[parentId]?.y || 0
    children.forEach((nodeId, index) => {
      const angle = (index / children.length) * Math.PI * 2
      graph.setNodeAttribute(nodeId, 'x', px + Math.cos(angle) * 50)
      graph.setNodeAttribute(nodeId, 'y', py + Math.sin(angle) * 50)
      graph.setNodeAttribute(nodeId, 'z', 10)
    })
  }
}

// ===== 核心：Neo4j 数据 → graphology Graph =====
export function buildGraphFromSubgraph(subgraph: Neo4jGraphSubgraph, graph: Graph = new Graph()): Graph {
  const addNodeToGraph = (node: Neo4jGraphNode) => {
    const nodeType = node.type || 'TechStack'
    const level = TYPE_LEVELS[nodeType] || 'L3'

    if (!graph.hasNode(node.id)) {
      graph.addNode(node.id, {
        id: node.id,
        name: node.name,
        label: node.name,
        type: nodeType as Neo4jNodeType,
        level,
        stack: node.stack || '',
        x: 0, y: 0, z: 0,
        description: node.description || '',
        color: TYPE_COLORS[nodeType] || '#64748b',
        size: TYPE_SIZES[nodeType] || 20,
        importance: node.importance || TYPE_IMPORTANCE[nodeType] || 3,
        frequency: node.frequency || 0,
        weight: TYPE_IMPORTANCE[nodeType] || 3,
        ...node.properties,
      })
    }
  }

  const addEdgeToGraph = (edge: Neo4jGraphEdge) => {
    if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
      if (!graph.hasEdge(edge.source, edge.target)) {
        graph.addEdge(edge.source, edge.target, {
          relation: edge.relation,
          color: edge.properties?.color || getEdgeColor(edge.relation),
          label: edge.properties?.label || getRelationLabel(edge.relation),
          isParentRelation: isParentRelation(edge.relation),
          ...edge.properties,
        })
      }
    }
  }

  subgraph.nodes.forEach(addNodeToGraph)
  subgraph.edges.forEach(addEdgeToGraph)
  applySmartLayout(graph)
  return graph
}

// ===== 增量合并 =====
export function mergeSubgraph(master: Graph, subgraph: Neo4jGraphSubgraph): Graph {
  const existingIds = new Set<string>()
  master.forEachNode(id => existingIds.add(id))
  for (const n of subgraph.nodes) {
    if (!existingIds.has(n.id)) {
      const nodeType = n.type || 'TechStack'
      const level = TYPE_LEVELS[nodeType] || 'L3'
      master.addNode(n.id, {
        id: n.id, name: n.name, label: n.name,
        type: nodeType, level,
        stack: n.stack || '', x: 0, y: 0, z: 0,
        description: n.description || '',
        color: TYPE_COLORS[nodeType] || '#64748b',
        size: TYPE_SIZES[nodeType] || 20,
        importance: n.importance || TYPE_IMPORTANCE[nodeType] || 3,
        frequency: n.frequency || 0,
        ...n.properties,
      })
    }
  }
  for (const e of subgraph.edges) {
    if (master.hasNode(e.source) && master.hasNode(e.target) && !master.hasEdge(e.source, e.target)) {
      master.addEdge(e.source, e.target, {
        relation: e.relation,
        color: e.properties?.color || getEdgeColor(e.relation),
        label: e.properties?.label || getRelationLabel(e.relation),
        isParentRelation: isParentRelation(e.relation),
        ...e.properties,
      })
    }
  }
  applySmartLayout(master)
  return master
}
