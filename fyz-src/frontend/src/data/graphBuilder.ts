import Graph from 'graphology'
import type { GraphType } from '@/domain/types'
import { getPanorama, expandNode, type GraphNode as BackendGraphNode, type GraphEdge as BackendGraphEdge, type GraphSubgraph } from '@/api/graph'



function applySmartLayout(graph: Graph): void {
  const nodesByLevel: Record<string, string[]> = {
    'L1': [],
    'L2': [],
    'L3': [],
    'L4': [],
    'L5': []
  }

  const nodeAttrs: Record<string, any> = {}
  graph.forEachNode((nodeId: string, attrs: any) => {
    nodeAttrs[nodeId] = attrs
    const level = attrs.level || 'L3'
    if (nodesByLevel[level]) {
      nodesByLevel[level].push(nodeId)
    }
  })

  const centerX = 0
  const centerY = 0

  const l1Nodes = nodesByLevel['L1']
  if (l1Nodes.length > 0) {
    const radius = 50
    l1Nodes.forEach((nodeId, index) => {
      const angle = (index / l1Nodes.length) * Math.PI * 2 - Math.PI / 2
      graph.setNodeAttribute(nodeId, 'x', centerX + Math.cos(angle) * radius)
      graph.setNodeAttribute(nodeId, 'y', centerY + Math.sin(angle) * radius)
      graph.setNodeAttribute(nodeId, 'z', 50)
    })
  }

  const l2Nodes = nodesByLevel['L2']
  if (l2Nodes.length > 0) {
    const radius = 200
    l2Nodes.forEach((nodeId, index) => {
      const angle = (index / l2Nodes.length) * Math.PI * 2 - Math.PI / 2
      graph.setNodeAttribute(nodeId, 'x', centerX + Math.cos(angle) * radius)
      graph.setNodeAttribute(nodeId, 'y', centerY + Math.sin(angle) * radius)
      graph.setNodeAttribute(nodeId, 'z', 40)
    })
  }

  const l3Nodes = nodesByLevel['L3']
  if (l3Nodes.length > 0) {
    const l3ByParent: Record<string, string[]> = {}
    
    graph.forEachEdge((_edgeId, attrs, source, target) => {
      const sourceLevel = nodeAttrs[source]?.level || 'L3'
      const targetLevel = nodeAttrs[target]?.level || 'L3'
      if ((sourceLevel === 'L2' && targetLevel === 'L3') || 
          (sourceLevel === 'L1' && targetLevel === 'L3')) {
        if (!l3ByParent[source]) {
          l3ByParent[source] = []
        }
        l3ByParent[source].push(target)
      }
    })

    Object.keys(l3ByParent).forEach(parentId => {
      const children = l3ByParent[parentId]
      const parentX = nodeAttrs[parentId]?.x || 0
      const parentY = nodeAttrs[parentId]?.y || 0
      
      children.forEach((nodeId, index) => {
        const angle = (index / children.length) * Math.PI * 2
        const radius = 120
        graph.setNodeAttribute(nodeId, 'x', parentX + Math.cos(angle) * radius)
        graph.setNodeAttribute(nodeId, 'y', parentY + Math.sin(angle) * radius)
        graph.setNodeAttribute(nodeId, 'z', 30)
      })
    })

    l3Nodes.forEach(nodeId => {
      if (graph.getNodeAttribute(nodeId, 'x') === 0 && 
          graph.getNodeAttribute(nodeId, 'y') === 0) {
        const angle = Math.random() * Math.PI * 2
        const radius = 350 + Math.random() * 100
        graph.setNodeAttribute(nodeId, 'x', centerX + Math.cos(angle) * radius)
        graph.setNodeAttribute(nodeId, 'y', centerY + Math.sin(angle) * radius)
        graph.setNodeAttribute(nodeId, 'z', 30)
      }
    })
  }

  const l4Nodes = nodesByLevel['L4']
  if (l4Nodes.length > 0) {
    const l4ByParent: Record<string, string[]> = {}
    
    graph.forEachEdge((_edgeId, attrs, source, target) => {
      const sourceLevel = nodeAttrs[source]?.level || 'L3'
      const targetLevel = nodeAttrs[target]?.level || 'L4'
      if (sourceLevel === 'L3' && targetLevel === 'L4') {
        if (!l4ByParent[source]) {
          l4ByParent[source] = []
        }
        l4ByParent[source].push(target)
      }
    })

    Object.keys(l4ByParent).forEach(parentId => {
      const children = l4ByParent[parentId]
      const parentX = nodeAttrs[parentId]?.x || 0
      const parentY = nodeAttrs[parentId]?.y || 0
      
      children.forEach((nodeId, index) => {
        const angle = (index / children.length) * Math.PI * 2
        const radius = 80
        graph.setNodeAttribute(nodeId, 'x', parentX + Math.cos(angle) * radius)
        graph.setNodeAttribute(nodeId, 'y', parentY + Math.sin(angle) * radius)
        graph.setNodeAttribute(nodeId, 'z', 20)
      })
    })

    l4Nodes.forEach(nodeId => {
      if (graph.getNodeAttribute(nodeId, 'x') === 0 && 
          graph.getNodeAttribute(nodeId, 'y') === 0) {
        const angle = Math.random() * Math.PI * 2
        const radius = 450 + Math.random() * 150
        graph.setNodeAttribute(nodeId, 'x', centerX + Math.cos(angle) * radius)
        graph.setNodeAttribute(nodeId, 'y', centerY + Math.sin(angle) * radius)
        graph.setNodeAttribute(nodeId, 'z', 20)
      }
    })
  }

  const l5Nodes = nodesByLevel['L5']
  if (l5Nodes.length > 0) {
    const l5ByParent: Record<string, string[]> = {}
    
    graph.forEachEdge((_edgeId, attrs, source, target) => {
      const sourceLevel = nodeAttrs[source]?.level || 'L4'
      const targetLevel = nodeAttrs[target]?.level || 'L5'
      if (sourceLevel === 'L4' && targetLevel === 'L5') {
        if (!l5ByParent[source]) {
          l5ByParent[source] = []
        }
        l5ByParent[source].push(target)
      }
    })

    Object.keys(l5ByParent).forEach(parentId => {
      const children = l5ByParent[parentId]
      const parentX = nodeAttrs[parentId]?.x || 0
      const parentY = nodeAttrs[parentId]?.y || 0
      
      children.forEach((nodeId, index) => {
        const angle = (index / children.length) * Math.PI * 2
        const radius = 50
        graph.setNodeAttribute(nodeId, 'x', parentX + Math.cos(angle) * radius)
        graph.setNodeAttribute(nodeId, 'y', parentY + Math.sin(angle) * radius)
        graph.setNodeAttribute(nodeId, 'z', 10)
      })
    })

    l5Nodes.forEach(nodeId => {
      if (graph.getNodeAttribute(nodeId, 'x') === 0 && 
          graph.getNodeAttribute(nodeId, 'y') === 0) {
        const angle = Math.random() * Math.PI * 2
        const radius = 500 + Math.random() * 200
        graph.setNodeAttribute(nodeId, 'x', centerX + Math.cos(angle) * radius)
        graph.setNodeAttribute(nodeId, 'y', centerY + Math.sin(angle) * radius)
        graph.setNodeAttribute(nodeId, 'z', 10)
      }
    })
  }
}

export async function buildGraphFromBackend(): Promise<Graph> {
  const graph = new Graph()

  console.log('Starting to build graph from backend...')
  
  const subgraph = await getPanorama({ limit: 1000 })
  
  console.log('Panorama response:', {
    nodeCount: subgraph.nodes.length,
    edgeCount: subgraph.edges.length,
    truncated: subgraph.truncated,
    snapshotVersion: subgraph.snapshot_version
  })

  const typeColors: Record<string, string> = {
    'Job': '#122d6e',
    'SkillArea': '#2f47b8',
    'TechStack': '#3f5ae0',
    'TechPoint': '#7893de',
    'KnowledgePoint': '#b4c2f2',
    'SourceDocument': '#94a3b8',
    'GraphSnapshot': '#64748b'
  }

  const typeSizes: Record<string, number> = {
    'Job': 30,
    'SkillArea': 24,
    'TechStack': 19,
    'TechPoint': 14,
    'KnowledgePoint': 10,
    'SourceDocument': 12,
    'GraphSnapshot': 12
  }

  const typeLevels: Record<string, string> = {
    'Job': 'L1',
    'SkillArea': 'L2',
    'TechStack': 'L3',
    'TechPoint': 'L4',
    'KnowledgePoint': 'L5',
    'SourceDocument': 'L0',
    'GraphSnapshot': 'L0'
  }

  const typeImportance: Record<string, number> = {
    'Job': 5,
    'SkillArea': 4,
    'TechStack': 3,
    'TechPoint': 2,
    'KnowledgePoint': 1,
    'SourceDocument': 0,
    'GraphSnapshot': 0
  }

  const addNodeToGraph = (node: BackendGraphNode) => {
    const nodeType = node.type || 'TechStack'
    const level = typeLevels[nodeType] || 'L3'
    
    if (!graph.hasNode(node.id)) {
      graph.addNode(node.id, {
        id: node.id,
        name: node.name,
        label: node.name,
        type: nodeType as GraphType,
        level: level,
        stack: node.stack || '',
        x: node.x || 0,
        y: node.y || 0,
        z: 0,
        description: node.description || '',
        color: typeColors[nodeType] || '#64748b',
        size: node.properties?.size || typeSizes[nodeType] || 26,
        importance: node.importance || typeImportance[nodeType] || 3,
        frequency: node.frequency || 0,
        weight: typeImportance[nodeType] || 3,
        level_label: node.properties?.level_label || '',
        total_records: node.properties?.total_records || 0,
        category_key: node.properties?.category_key || '',
        job_count: node.properties?.job_count || 0,
        category: node.properties?.category || '',
        parent_skill: node.properties?.parent_skill || '',
        parent_tech_point: node.properties?.parent_tech_point || '',
        ...node.properties
      })
    }
  }

  const addEdgeToGraph = (edge: BackendGraphEdge) => {
    if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
      if (!graph.hasEdge(edge.source, edge.target)) {
        graph.addEdge(edge.source, edge.target, {
          relation: edge.relation,
          color: edge.properties?.color || getEdgeColor(edge.relation),
          label: edge.properties?.label || getRelationLabel(edge.relation),
          isParentRelation: isParentRelation(edge.relation),
          ...edge.properties
        })
      }
    }
  }

  subgraph.nodes.forEach(addNodeToGraph)
  subgraph.edges.forEach(addEdgeToGraph)

  console.log(`After panorama: ${graph.order} nodes, ${graph.size} edges`)

  const jobNodeIds = subgraph.nodes
    .filter(node => node.type === 'Job')
    .map(node => node.id)

  console.log(`Found ${jobNodeIds.length} Job nodes`)

  const isolatedJobIds = jobNodeIds.filter(jobId => {
    return graph.degree(jobId) === 0
  })

  if (isolatedJobIds.length > 0) {
    console.log(`Expanding ${isolatedJobIds.length} isolated Job nodes in parallel...`)
    
    const expandPromises = isolatedJobIds.map(jobId => {
      return expandNode(jobId, 3, 200)
    })
    
    const results = await Promise.all(expandPromises)
    
    results.forEach((jobSubgraph, index) => {
      jobSubgraph.nodes.forEach(addNodeToGraph)
      jobSubgraph.edges.forEach(addEdgeToGraph)
      console.log(`Expanded Job ${isolatedJobIds[index]}: ${jobSubgraph.nodes.length} nodes, ${jobSubgraph.edges.length} edges`)
    })
  }

  console.log(`After expanding isolated jobs: ${graph.order} nodes, ${graph.size} edges`)

  applySmartLayout(graph)

  console.log(`图谱从后端构建完成: ${graph.order} 个节点, ${graph.size} 条边`)

  return graph
}

function getEdgeColor(relation: string): string {
  const relationColors: Record<string, string> = {
    'REQUIRES_AREA': 'rgba(76, 29, 149, 0.6)',
    'CONTAINS': 'rgba(79, 110, 246, 0.5)',
    'REFINES_TO': 'rgba(6, 182, 212, 0.4)',
    'HAS_KNOWLEDGE': 'rgba(255, 255, 255, 0.3)',
    'RELATED_TO': 'rgba(245, 158, 11, 0.4)',
    'PREREQUISITE': 'rgba(232, 93, 93, 0.4)',
    'SUPPORTS': 'rgba(52, 179, 126, 0.4)',
    'HAS_SNAPSHOT': 'rgba(148, 163, 184, 0.3)'
  }
  return relationColors[relation] || 'rgba(148, 163, 184, 0.3)'
}

function getRelationLabel(relation: string): string {
  const relationLabels: Record<string, string> = {
    'REQUIRES_AREA': '需求',
    'CONTAINS': '包含',
    'REFINES_TO': '细化为',
    'HAS_KNOWLEDGE': '包含',
    'RELATED_TO': '相关',
    'PREREQUISITE': '前置',
    'SUPPORTS': '支持',
    'HAS_SNAPSHOT': '快照'
  }
  return relationLabels[relation] || ''
}

function isParentRelation(relation: string): boolean {
  return ['REQUIRES_AREA', 'CONTAINS', 'REFINES_TO', 'HAS_KNOWLEDGE'].includes(relation)
}
