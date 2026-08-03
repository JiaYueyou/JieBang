<script setup lang="ts">
import { ref, onMounted, watch, nextTick, onUnmounted, computed } from 'vue'
import { Graph } from '@antv/g6'
import { useGraphStore } from '@/stores/graph'
import {
  transformToG6, TYPE_COLORS, TYPE_SIZES, TYPE_LABELS,
  isHierarchyEdge, isCrossEdge,
} from '@/data/graphBuilder'
import type { Neo4jNodeType } from '@/types'

const graphStore = useGraphStore()
const containerRef = ref<HTMLDivElement>()

// 过滤器状态
const searchKeyword = ref('')
const stackFilter = ref<string>('')
const levelFilter = ref<string>('')
const selectedNode = ref<any>(null)

// 节点类型显示/隐藏
const NODE_TYPES: Neo4jNodeType[] = ['Job', 'SkillArea', 'TechStack', 'TechPoint', 'KnowledgePoint']
const typeVisibility = ref<Record<string, boolean>>({
  Job: true, SkillArea: true, TechStack: true, TechPoint: true, KnowledgePoint: true,
  SourceDocument: false, GraphSnapshot: false,
})

let graph: Graph | null = null

function getVisibleData() {
  const { nodes: g6Nodes, edges: g6Edges } = transformToG6({
    nodes: graphStore.nodes,
    edges: graphStore.edges,
    node_count: graphStore.nodeCount,
    edge_count: graphStore.edgeCount,
    snapshot_version: null,
    truncated: false,
  })
  const visibleTypes = new Set(
    Object.entries(typeVisibility.value).filter(([, v]) => v).map(([k]) => k)
  )
  const filteredNodes = g6Nodes.filter(n => {
    if (!visibleTypes.has(n.data.nodeType)) return false
    if (stackFilter.value && n.data.stack !== stackFilter.value) return false
    if (levelFilter.value && n.data.level !== levelFilter.value) return false
    if (searchKeyword.value) {
      const kw = searchKeyword.value.toLowerCase()
      return n.data.label.toLowerCase().includes(kw) ||
             n.data.description.toLowerCase().includes(kw)
    }
    return true
  })
  const filteredIds = new Set(filteredNodes.map(n => n.id))
  const filteredEdges = g6Edges.filter(e => filteredIds.has(e.source) && filteredIds.has(e.target))
  return { nodes: filteredNodes, edges: filteredEdges }
}

function buildGraph() {
  if (!containerRef.value) return
  const container = containerRef.value
  const width = container.clientWidth || 1000
  const height = 780

  const { nodes: dataNodes, edges: dataEdges } = getVisibleData()

  if (dataNodes.length === 0) {
    container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#94a3b8;font-size:14px;">暂无图谱数据，请先执行图谱同步</div>'
    return
  }

  graph = new Graph({
    container,
    width,
    height,
    autoFit: 'view',
    background: '#f8f9fb',
    data: { nodes: dataNodes, edges: dataEdges },
    node: {
      type: 'rect',
      style: (d: any) => {
        const t = (d.data?.nodeType || 'TechStack') as string
        const size = TYPE_SIZES[t] || [64, 28]
        const color = TYPE_COLORS[t] || '#64748b'
        return {
          size,
          radius: Math.min(size[0], size[1]) / 2,
          fill: color,
          stroke: color,
          lineWidth: 2,
          labelText: d.data?.label || '',
          labelFill: '#fff',
          labelFontSize: 11,
          labelFontWeight: 500,
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
        if (isCrossEdge(rel)) {
          return {
            stroke: 'rgba(245,158,11,0.4)',
            lineWidth: 1,
            lineDash: [5, 4],
            endArrow: false,
          }
        }
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
    layout: {
      type: 'dagre',
      rankdir: 'TB',
      ranksep: 80,
      nodesep: 40,
      animation: false,
    },
    behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element'],
  })

  graph.on('node:click', (evt: any) => {
    const nodeId = evt.target?.id
    if (!nodeId) return
    const allEdges = graph!.getEdgeData()
    const allNodes = graph!.getNodeData()

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

    // 更新选中节点详情
    const originalNode = graphStore.nodes.find(n => n.id === nodeId)
    if (originalNode) {
      selectedNode.value = originalNode
    }
  })

  graph.on('canvas:click', () => {
    const allNodes = graph!.getNodeData()
    const allEdges = graph!.getEdgeData()
    allNodes.forEach((n: any) => graph!.setElementState(n.id, []))
    allEdges.forEach((e: any) => graph!.setElementState(e.id, []))
    selectedNode.value = null
  })

  graph.render()
}

function destroyGraph() {
  if (graph) { graph.destroy(); graph = null }
}

function refreshGraph() {
  destroyGraph()
  nextTick(() => buildGraph())
}

async function handleSearch() {
  if (!searchKeyword.value.trim()) {
    await loadPanorama()
  } else {
    await graphStore.search(searchKeyword.value.trim())
    nextTick(() => buildGraph())
  }
}

async function loadPanorama() {
  await graphStore.fetchPanorama({
    stack: stackFilter.value || undefined,
    level: levelFilter.value || undefined,
    limit: 1000,
  })
  nextTick(() => buildGraph())
}

function toggleType(type: string) {
  typeVisibility.value[type] = !typeVisibility.value[type]
  refreshGraph()
}

function handleStackChange() {
  loadPanorama()
}

function handleLevelChange() {
  loadPanorama()
}

function handleReset() {
  searchKeyword.value = ''
  stackFilter.value = ''
  levelFilter.value = ''
  selectedNode.value = null
  Object.keys(typeVisibility.value).forEach(k => { typeVisibility.value[k] = k !== 'SourceDocument' && k !== 'GraphSnapshot' })
  loadPanorama()
}

onMounted(async () => {
  if (!graphStore.loaded) await loadPanorama()
  else nextTick(() => buildGraph())
})

onUnmounted(() => destroyGraph())
</script>

<template>
  <div class="graph-page">
    <!-- 顶部工具栏 -->
    <div class="graph-toolbar">
      <div class="toolbar-left">
        <h3>IT 岗位技能知识图谱</h3>
        <span class="graph-stats">
          {{ graphStore.nodeCount }} 节点 / {{ graphStore.edgeCount }} 边
        </span>
      </div>
      <div class="toolbar-right">
        <div class="search-box">
          <input
            v-model="searchKeyword"
            type="text"
            placeholder="搜索节点..."
            @keyup.enter="handleSearch"
          />
          <button class="btn-search" @click="handleSearch">搜索</button>
        </div>
        <select v-model="stackFilter" class="filter-select" @change="handleStackChange">
          <option value="">全部技术栈</option>
          <option value="backend">后端</option>
          <option value="ai">AI</option>
          <option value="data">数据</option>
          <option value="devops">DevOps</option>
        </select>
        <select v-model="levelFilter" class="filter-select" @change="handleLevelChange">
          <option value="">全部级别</option>
          <option value="junior">初级</option>
          <option value="middle">中级</option>
          <option value="senior">高级</option>
        </select>
        <button class="btn-reset" @click="handleReset">重置</button>
      </div>
    </div>

    <div class="graph-body">
      <!-- 左侧：节点类型过滤器 -->
      <div class="left-panel">
        <div class="panel-title">节点类型</div>
        <label
          v-for="t in NODE_TYPES"
          :key="t"
          class="type-filter-item"
        >
          <input
            type="checkbox"
            :checked="typeVisibility[t]"
            @change="toggleType(t)"
          />
          <span class="type-dot" :style="{ background: TYPE_COLORS[t] }"></span>
          <span class="type-label">{{ TYPE_LABELS[t] || t }}</span>
        </label>
        <div class="panel-divider"></div>
        <div class="panel-title">图例</div>
        <div class="legend-section">
          <div class="legend-row">
            <span class="legend-line solid"></span>
            <span>层级关系</span>
          </div>
          <div class="legend-row">
            <span class="legend-line dash"></span>
            <span>交叉关联</span>
          </div>
        </div>
      </div>

      <!-- 中央：G6 画布 -->
      <div ref="containerRef" class="graph-canvas"></div>

      <!-- 右侧：节点详情面板 -->
      <div class="right-panel" v-if="selectedNode">
        <div class="panel-title">节点详情</div>
        <div class="detail-field">
          <span class="field-label">名称</span>
          <span class="field-value">{{ selectedNode.name }}</span>
        </div>
        <div class="detail-field">
          <span class="field-label">类型</span>
          <span class="field-value">
            <span class="type-badge" :style="{ background: TYPE_COLORS[selectedNode.type] || '#64748b' }">
              {{ TYPE_LABELS[selectedNode.type] || selectedNode.type }}
            </span>
          </span>
        </div>
        <div class="detail-field" v-if="selectedNode.description">
          <span class="field-label">描述</span>
          <span class="field-value desc-text">{{ selectedNode.description }}</span>
        </div>
        <div class="detail-field" v-if="selectedNode.stack">
          <span class="field-label">技术栈</span>
          <span class="field-value">{{ selectedNode.stack }}</span>
        </div>
        <div class="detail-field" v-if="selectedNode.level">
          <span class="field-label">级别</span>
          <span class="field-value">{{ selectedNode.level === 'junior' ? '初级' : selectedNode.level === 'middle' ? '中级' : selectedNode.level === 'senior' ? '高级' : selectedNode.level }}</span>
        </div>
        <div class="detail-field" v-if="selectedNode.frequency">
          <span class="field-label">出现频次</span>
          <span class="field-value">{{ selectedNode.frequency }}</span>
        </div>
        <div class="detail-field" v-if="selectedNode.importance">
          <span class="field-label">重要度</span>
          <span class="field-value">{{ (selectedNode.importance * 100).toFixed(0) }}%</span>
        </div>
        <div class="detail-field" v-if="selectedNode.properties?.job_count">
          <span class="field-label">关联岗位</span>
          <span class="field-value">{{ selectedNode.properties.job_count }}</span>
        </div>
      </div>
      <div class="right-panel right-panel--empty" v-else>
        <div class="empty-hint">点击节点查看详情</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.graph-page {
  max-width: 1600px;
  margin: 0 auto;
  height: calc(100vh - 80px);
  display: flex;
  flex-direction: column;
}

.graph-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  padding: 10px 16px;
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.toolbar-left h3 {
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}

.graph-stats {
  font-size: 12px;
  color: #94a3b8;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.search-box {
  display: flex;
  align-items: center;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
}

.search-box input {
  border: none;
  outline: none;
  padding: 6px 10px;
  font-size: 13px;
  width: 160px;
  background: #fff;
}

.btn-search {
  padding: 6px 12px;
  border: none;
  background: #4f6ef6;
  color: #fff;
  font-size: 12px;
  cursor: pointer;
}

.btn-search:hover { background: #3d5bd9; }

.filter-select {
  padding: 6px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 13px;
  color: #475569;
  background: #fff;
  cursor: pointer;
  outline: none;
}

.btn-reset {
  padding: 6px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #fff;
  color: #64748b;
  font-size: 12px;
  cursor: pointer;
}

.btn-reset:hover {
  border-color: #4f6ef6;
  color: #4f6ef6;
}

.graph-body {
  display: flex;
  flex: 1;
  overflow: hidden;
  gap: 0;
}

/* 左侧面板 */
.left-panel {
  width: 200px;
  flex-shrink: 0;
  padding: 16px 12px;
  border-right: 1px solid #e2e8f0;
  overflow-y: auto;
  background: #fafbfc;
}

.panel-title {
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
}

.type-filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 4px;
  cursor: pointer;
  border-radius: 4px;
  font-size: 13px;
  color: #475569;
}

.type-filter-item:hover { background: #f1f5f9; }

.type-filter-item input[type="checkbox"] {
  accent-color: #4f6ef6;
}

.type-dot {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  flex-shrink: 0;
}

.panel-divider {
  height: 1px;
  background: #e2e8f0;
  margin: 12px 0;
}

.legend-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.legend-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #64748b;
}

.legend-line {
  width: 20px;
  height: 0;
  flex-shrink: 0;
}

.legend-line.solid {
  border-top: 2px solid rgba(148, 163, 184, 0.5);
}

.legend-line.dash {
  border-top: 2px dashed rgba(245, 158, 11, 0.5);
}

/* 中央画布 */
.graph-canvas {
  flex: 1;
  min-width: 0;
  height: 100%;
  border-radius: 0;
  overflow: hidden;
}

/* 右侧面板 */
.right-panel {
  width: 260px;
  flex-shrink: 0;
  padding: 16px 14px;
  border-left: 1px solid #e2e8f0;
  overflow-y: auto;
  background: #fafbfc;
}

.right-panel--empty {
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-hint {
  color: #94a3b8;
  font-size: 13px;
}

.detail-field {
  margin-bottom: 12px;
}

.field-label {
  display: block;
  font-size: 11px;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 3px;
}

.field-value {
  font-size: 13px;
  color: #334155;
  word-break: break-all;
}

.desc-text {
  font-size: 12px;
  line-height: 1.5;
  color: #64748b;
}

.type-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  color: #fff;
  font-size: 11px;
  font-weight: 500;
}
</style>
