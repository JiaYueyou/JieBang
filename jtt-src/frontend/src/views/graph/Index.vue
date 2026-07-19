<script setup lang="ts">
import { ref, onMounted, watch, nextTick, onUnmounted, computed } from 'vue'
import { Graph } from '@antv/g6'
import { usePositionsStore } from '@/stores/positions'
import type { GraphNodeType } from '@/types'

const positionsStore = usePositionsStore()
const containerRef = ref<HTMLDivElement>()
const rootTech = ref<string>('all')

const graphNodes = computed(() => positionsStore.graphNodes)
const graphEdges = computed(() => positionsStore.graphEdges)

// 从数据中提取可用的根技术列表
const availableRoots = computed(() =>
  graphNodes.value.filter((n) => n.type === 'root').map((n) => ({ id: n.id, label: n.label })),
)

let graph: Graph | null = null

// BFS 过滤：从选中根节点出发，收集所有可达节点和边
function getFilteredData() {
  if (rootTech.value === 'all') {
    return { nodes: graphNodes.value, edges: graphEdges.value }
  }
  const reachable = new Set<string>([rootTech.value])
  let changed = true
  while (changed) {
    changed = false
    for (const e of graphEdges.value) {
      if (reachable.has(e.source) && !reachable.has(e.target)) {
        reachable.add(e.target); changed = true
      }
      if (reachable.has(e.target) && !reachable.has(e.source)) {
        reachable.add(e.source); changed = true
      }
    }
  }
  return {
    nodes: graphNodes.value.filter((n) => reachable.has(n.id)),
    edges: graphEdges.value.filter((e) => reachable.has(e.source) && reachable.has(e.target)),
  }
}

// 节点样式配置 —— 每层不同尺寸和颜色
const NODE_STYLES: Record<GraphNodeType, { size: [number, number]; fill: string; stroke: string; fontSize: number; fontWeight: number; radius: number }> = {
  root:             { size: [110, 44], fill: '#1e40af', stroke: '#1e3a8a', fontSize: 13, fontWeight: 700, radius: 22 },
  position:         { size: [92, 38], fill: '#4f6ef6', stroke: '#3d5bd9', fontSize: 12, fontWeight: 600, radius: 19 },
  domain_branch:    { size: [78, 34], fill: '#059669', stroke: '#047857', fontSize: 11, fontWeight: 500, radius: 17 },
  skillset_branch:  { size: [78, 34], fill: '#7c3aed', stroke: '#6d28d9', fontSize: 11, fontWeight: 500, radius: 17 },
  module:           { size: [64, 28], fill: '#0891b2', stroke: '#0e7490', fontSize: 10, fontWeight: 500, radius: 14 },
  knowledge:        { size: [50, 24], fill: '#d97706', stroke: '#b45309', fontSize: 9, fontWeight: 500, radius: 12 },
}

function buildGraph() {
  if (!containerRef.value) return
  const container = containerRef.value
  const width = container.clientWidth || 1200
  const height = 780

  const { nodes: dataNodes, edges: dataEdges } = getFilteredData()

  if (dataNodes.length === 0) {
    // 无数据时清空容器
    container.innerHTML = ''
    return
  }

  // 准备 dagre 布局所需数据（无随机位置，由算法自动计算）
  const mappedNodes = dataNodes.map((n) => ({
    id: n.id,
    data: { label: n.label, nodeType: n.type, layer: n.layer },
  }))

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
    background: '#f8f9fb',
    data: { nodes: mappedNodes, edges: mappedEdges },
    node: {
      type: 'rect',
      style: (d: any) => {
        const t = (d.data?.nodeType || 'module') as GraphNodeType
        const s = NODE_STYLES[t] || NODE_STYLES.module
        return {
          size: s.size,
          radius: s.radius,
          fill: s.fill,
          stroke: s.stroke,
          lineWidth: 2,
          labelText: d.data?.label || '',
          labelFill: '#fff',
          labelFontSize: s.fontSize,
          labelFontWeight: s.fontWeight,
          labelPlacement: 'center',
          cursor: 'pointer',
        }
      },
      state: {
        selected: {
          stroke: '#f59e0b',
          lineWidth: 4,
          shadowColor: 'rgba(245,158,11,0.4)',
          shadowBlur: 20,
        },
        highlighted: { opacity: 1 },
        dimmed: { opacity: 0.08 },
      },
    },
    edge: {
      type: 'cubic-vertical',
      style: (d: any) => {
        const rel = d.data?.relation || ''
        if (rel === 'cross_ref') {
          // 跨分支虚线（琥珀色）
          return {
            stroke: 'rgba(245,158,11,0.4)',
            lineWidth: 1,
            lineDash: [5, 4],
            endArrow: false,
          }
        }
        // 层级边实线（蓝灰色 + 箭头）
        return {
          stroke: 'rgba(148,163,184,0.45)',
          lineWidth: 1.5,
          endArrow: true,
        }
      },
      state: {
        highlighted: {
          stroke: 'rgba(79,110,246,0.5)',
          lineWidth: 2.5,
        },
        dimmed: { opacity: 0.03 },
      },
    },
    // dagre 布局替代 force —— 从上到下五级层级
    layout: {
      type: 'dagre',
      rankdir: 'TB',
      ranksep: 90,
      nodesep: 50,
      animation: false,
    },
    behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element'],
  })

  // 点击节点：高亮完整上下游链路
  graph.on('node:click', (evt: any) => {
    const nodeId = evt.target?.id
    if (!nodeId) return
    const allEdges = graph!.getEdgeData()
    const allNodes = graph!.getNodeData()

    // BFS 收集所有关联节点（上下游完整链路）
    const connectedIds = new Set<string>([nodeId])
    let changed = true
    while (changed) {
      changed = false
      for (const e of allEdges) {
        if (connectedIds.has(e.source) && !connectedIds.has(e.target)) {
          connectedIds.add(e.target); changed = true
        }
        if (connectedIds.has(e.target) && !connectedIds.has(e.source)) {
          connectedIds.add(e.source); changed = true
        }
      }
    }

    allNodes.forEach((n: any) => {
      if (n.id === nodeId) graph!.setElementState(n.id, 'selected')
      else if (connectedIds.has(n.id)) graph!.setElementState(n.id, 'highlighted')
      else graph!.setElementState(n.id, 'dimmed')
    })
    allEdges.forEach((e: any) => {
      if (connectedIds.has(e.source) && connectedIds.has(e.target)) graph!.setElementState(e.id, 'highlighted')
      else graph!.setElementState(e.id, 'dimmed')
    })
  })

  // 点击空白取消高亮
  graph.on('canvas:click', () => {
    const allNodes = graph!.getNodeData()
    const allEdges = graph!.getEdgeData()
    allNodes.forEach((n: any) => graph!.setElementState(n.id, []))
    allEdges.forEach((e: any) => graph!.setElementState(e.id, []))
  })

  graph.render()
}

function destroyGraph() {
  if (graph) { graph.destroy(); graph = null }
}

onMounted(async () => {
  if (graphNodes.value.length === 0) await positionsStore.fetchGraph()
  nextTick(() => buildGraph())
})
watch(rootTech, () => { destroyGraph(); nextTick(() => buildGraph()) })
onUnmounted(() => destroyGraph())
</script>

<template>
  <div class="graph-page">
    <div class="graph-toolbar">
      <div class="toolbar-left">
        <h3>IT 岗位技能知识图谱</h3>
      </div>
      <div class="toolbar-right">
        <!-- 图例 -->
        <div class="legend">
          <span class="legend-item"><span class="legend-dot" style="background:#1e40af"></span>根技术</span>
          <span class="legend-item"><span class="legend-dot" style="background:#4f6ef6"></span>岗位</span>
          <span class="legend-item"><span class="legend-dot" style="background:#059669"></span>应用领域</span>
          <span class="legend-item"><span class="legend-dot" style="background:#7c3aed"></span>技能集合</span>
          <span class="legend-item"><span class="legend-dot" style="background:#0891b2"></span>能力模块</span>
          <span class="legend-item"><span class="legend-dot" style="background:#d97706"></span>知识点</span>
          <span class="legend-edge"><span class="legend-line dash"></span>交叉关联</span>
        </div>
        <!-- 根技术过滤器 -->
        <div class="root-filters">
          <button
            class="filter-chip"
            :class="{ active: rootTech === 'all' }"
            @click="rootTech = 'all'"
          >
            全部
          </button>
          <button
            v-for="rt in availableRoots"
            :key="rt.id"
            class="filter-chip"
            :class="{ active: rootTech === rt.id }"
            @click="rootTech = rt.id"
          >
            {{ rt.label }}
          </button>
        </div>
      </div>
    </div>
    <div ref="containerRef" class="graph-container"></div>
  </div>
</template>

<style scoped>
.graph-page {
  max-width: 1400px;
  margin: 0 auto;
}

.graph-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  padding: 12px 16px;
  margin-bottom: 8px;
}

.toolbar-left h3 {
  font-size: 16px;
  font-weight: 700;
  color: var(--ink);
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.legend {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--muted);
}

.legend-dot {
  width: 9px;
  height: 9px;
  border-radius: 3px;
  flex-shrink: 0;
}

.legend-edge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--muted);
}

.legend-line.dash {
  width: 18px;
  height: 0;
  border-top: 2px dashed rgba(245, 158, 11, 0.5);
  flex-shrink: 0;
}

.root-filters {
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
  height: 780px;
  border-radius: 8px;
  overflow: hidden;
}
</style>
