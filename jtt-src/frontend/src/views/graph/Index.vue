<script setup lang="ts">
import { ref, onMounted, watch, nextTick, onUnmounted } from 'vue'
import { Graph } from '@antv/g6'
import { mockGraphNodes, mockGraphEdges } from '@/mock/data/skills'

const containerRef = ref<HTMLDivElement>()
const domain = ref<'all' | 'backend' | 'frontend' | 'ai'>('all')

let graph: Graph | null = null
const anchorPositions = new Map<string, { x: number; y: number }>()
const MAX_DRAG_DISTANCE = 160

function getDomainFilteredData() {
  if (domain.value === 'all') {
    return { nodes: mockGraphNodes, edges: mockGraphEdges }
  }
  const domainPositions: Record<string, string[]> = {
    backend: ['pos-java', 'pos-de'],
    frontend: ['pos-fe'],
    ai: ['pos-agent', 'pos-ctx'],
  }
  const allowedPosIds = domainPositions[domain.value]
  const reachable = new Set<string>(allowedPosIds)
  const allEdges = mockGraphEdges
  let changed = true
  while (changed) {
    changed = false
    for (const e of allEdges) {
      if (reachable.has(e.source) && !reachable.has(e.target)) { reachable.add(e.target); changed = true }
      if (reachable.has(e.target) && !reachable.has(e.source)) { reachable.add(e.source); changed = true }
    }
  }
  return {
    nodes: mockGraphNodes.filter((n) => reachable.has(n.id)),
    edges: allEdges.filter((e) => reachable.has(e.source) && reachable.has(e.target)),
  }
}

function buildGraph() {
  if (!containerRef.value) return
  const container = containerRef.value
  const width = container.clientWidth || 1200
  const height = 650

  const { nodes: dataNodes, edges: dataEdges } = getDomainFilteredData()

  const mappedNodes = dataNodes.map((n) => {
    let yBase: number
    let spread: number
    switch (n.layer) {
      case 1: yBase = 110; spread = 140; break
      case 2: yBase = 310; spread = 220; break
      case 3: yBase = 510; spread = 240; break
      default: yBase = 325; spread = 200
    }
    const angle = Math.random() * Math.PI * 2
    const r = spread * (0.3 + Math.random() * 0.7)
    const x = width / 2 + r * Math.cos(angle)
    const y = yBase + (Math.random() - 0.5) * 30
    return {
      id: n.id,
      data: { label: n.label, nodeType: n.type, layer: n.layer },
      style: { x, y },
    }
  })

  const mappedEdges = dataEdges.map((e) => ({
    source: e.source,
    target: e.target,
    data: { relation: e.relation, weight: e.weight },
  }))

  graph = new Graph({
    container,
    width,
    height,
    autoFit: 'view',
    background: '#f2f3f5',
    data: { nodes: mappedNodes, edges: mappedEdges },
    node: {
      type: 'circle',
      style: (d: any) => {
        const label = d.data?.label || ''
        const t = d.data?.nodeType
        if (t === 'position') {
          return {
            size: 56,
            fill: '#4f6ef6',
            stroke: '#3d5bd9',
            lineWidth: 2,
            labelText: label,
            labelFill: '#fff',
            labelFontSize: 12,
            labelFontWeight: 600,
            labelPlacement: 'center',
            shadowColor: 'rgba(79,110,246,0.1)',
            shadowBlur: 6,
          }
        }
        if (t === 'technology') {
          return {
            size: 42,
            fill: '#0891b2',
            stroke: '#0e7490',
            lineWidth: 1.5,
            labelText: label,
            labelFill: '#fff',
            labelFontSize: 10,
            labelFontWeight: 500,
            labelPlacement: 'center',
          }
        }
        // skill
        return {
          size: 32,
          fill: '#d97706',
          stroke: '#b45309',
          lineWidth: 1,
          labelText: label,
          labelFill: '#fff',
          labelFontSize: 9,
          labelFontWeight: 500,
          labelPlacement: 'center',
        }
      },
      state: {
        selected: {
          stroke: '#4f6ef6',
          lineWidth: 4,
          shadowColor: 'rgba(79,110,246,0.5)',
          shadowBlur: 24,
        },
        highlighted: { opacity: 1 },
        dimmed: { opacity: 0.08 },
      },
    },
    edge: {
      type: 'cubic',
      style: {
        stroke: 'rgba(147,180,245,0.28)',
        lineWidth: 1,
        endArrow: false,
      },
      state: {
        highlighted: {
          stroke: 'rgba(79,110,246,0.5)',
          lineWidth: 2.2,
        },
        dimmed: { opacity: 0.03 },
      },
    },
    layout: {
      type: 'force',
      preventOverlap: true,
      linkDistance: 100,
      nodeStrength: -650,
      edgeStrength: 0.1,
      gravity: 0.28,
      animation: true,
    },
    behaviors: ['drag-canvas', 'zoom-canvas', { type: 'drag-element', enableTransient: false }],
  })

  // ---- Click highlight ----
  graph.on('node:click', (evt: any) => {
    const nodeId = evt.target?.id
    if (!nodeId) return
    const allEdges = graph!.getEdgeData()
    const allNodes = graph!.getNodeData()

    const connectedIds = new Set<string>([nodeId])
    allEdges.forEach((e: any) => {
      if (e.source === nodeId) connectedIds.add(e.target)
      if (e.target === nodeId) connectedIds.add(e.source)
    })

    allNodes.forEach((n: any) => {
      if (n.id === nodeId) graph!.setElementState(n.id, 'selected')
      else if (connectedIds.has(n.id)) graph!.setElementState(n.id, 'highlighted')
      else graph!.setElementState(n.id, 'dimmed')
    })
    allEdges.forEach((e: any) => {
      if (e.source === nodeId || e.target === nodeId) graph!.setElementState(e.id, 'highlighted')
      else graph!.setElementState(e.id, 'dimmed')
    })
  })

  graph.on('canvas:click', () => {
    const allNodes = graph!.getNodeData()
    const allEdges = graph!.getEdgeData()
    allNodes.forEach((n: any) => graph!.setElementState(n.id, []))
    allEdges.forEach((e: any) => graph!.setElementState(e.id, []))
  })

  // ---- Drag constraint ----
  graph.on('node:dragstart', (evt: any) => {
    const id = evt.target?.id
    if (!id) return
    const pos = graph!.getElementPosition(id)
    anchorPositions.set(id, { x: pos[0], y: pos[1] })
  })

  graph.on('node:drag', (evt: any) => {
    const id = evt.target?.id
    if (!id) return
    const anchor = anchorPositions.get(id)
    if (!anchor) return
    const pos = graph!.getElementPosition(id)
    const dx = pos[0] - anchor.x
    const dy = pos[1] - anchor.y
    const dist = Math.sqrt(dx * dx + dy * dy)
    if (dist > MAX_DRAG_DISTANCE) {
      const ratio = MAX_DRAG_DISTANCE / dist
      graph!.translateElementTo(id, [anchor.x + dx * ratio, anchor.y + dy * ratio], false)
    }
  })

  graph.on('node:dragend', () => {
    graph!.layout()
  })

  graph.render().then(() => {
    setTimeout(() => {
      const nodes = graph!.getNodeData()
      nodes.forEach((n: any) => {
        const pos = graph!.getElementPosition(n.id)
        anchorPositions.set(n.id, { x: pos[0], y: pos[1] })
      })
    }, 1500)
  })
}

function destroyGraph() {
  if (graph) { graph.destroy(); graph = null }
}

onMounted(() => nextTick(() => buildGraph()))
watch(domain, () => { destroyGraph(); nextTick(() => buildGraph()) })
onUnmounted(() => destroyGraph())
</script>

<template>
  <div class="graph-page">
    <div class="graph-toolbar">
      <div class="toolbar-left">
        <h3>IT 岗位技能知识图谱</h3>
      </div>
      <div class="toolbar-right">
        <div class="legend">
          <span class="legend-item"><span class="legend-dot pos"></span>岗位</span>
          <span class="legend-item"><span class="legend-dot tech"></span>技术</span>
          <span class="legend-item"><span class="legend-dot skill"></span>技能</span>
        </div>
        <div class="domain-filters">
          <button
            v-for="opt in [
              { key: 'all', label: '全部' },
              { key: 'backend', label: '后端' },
              { key: 'frontend', label: '前端' },
              { key: 'ai', label: 'AI' },
            ]"
            :key="opt.key"
            class="filter-chip"
            :class="{ active: domain === opt.key }"
            @click="domain = opt.key as any"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>
    </div>
    <div ref="containerRef" class="graph-container"></div>
  </div>
</template>

<style scoped>
.graph-page {
  max-width: 1200px;
  margin: 0 auto;
}

.graph-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  margin-bottom: 8px;
  background: transparent;
}

.toolbar-left h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink);
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 18px;
}

.legend {
  display: flex;
  align-items: center;
  gap: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--muted);
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-dot.pos { background: #4f6ef6; }
.legend-dot.tech { background: #0891b2; }
.legend-dot.skill { background: #d97706; }

.domain-filters {
  display: flex;
  gap: 4px;
}

.filter-chip {
  padding: 5px 14px;
  border-radius: 16px;
  border: 1px solid var(--hairline);
  background: #fff;
  color: var(--muted);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.filter-chip:hover {
  border-color: var(--brand);
  color: var(--brand);
}

.filter-chip.active {
  background: var(--brand);
  border-color: var(--brand);
  color: #fff;
}

.graph-container {
  width: 100%;
  height: 650px;
  border-radius: 8px;
  overflow: hidden;
}
</style>
