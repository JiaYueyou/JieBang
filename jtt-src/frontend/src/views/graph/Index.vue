<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useGraphStore } from '@/stores/graph'
import Graph3DCanvas from '@/components/graph/Graph3DCanvas.vue'
import type { GraphNodeAttrs } from '@/components/graph/Graph3DCanvas.vue'
import { TYPE_COLORS, TYPE_LABELS } from '@/data/graphBuilder'
import type { Neo4jNodeType } from '@/types'

const graphStore = useGraphStore()

// 过滤器状态
const searchKeyword = ref('')
const stackFilter = ref<string>('')
const levelFilter = ref<string>('')
const selectedType = ref<string>('all')

// 图谱交互
const activeNode = ref<GraphNodeAttrs | null>(null)
const pinnedNodeIds = ref<string[]>([])
const searchHighlightedNodeIds = computed(() => {
  const query = searchKeyword.value.trim().toLocaleLowerCase()
  if (!query || !graphStore.graph) return [] as string[]
  const matched: string[] = []
  graphStore.graph.forEachNode((id, attrs: any) => {
    const searchable = [attrs.name, attrs.label, attrs.description, attrs.parent_skill, attrs.parent_tech_point]
      .filter(Boolean).join(' ').toLocaleLowerCase()
    if (searchable.includes(query)) matched.push(id)
  })
  return matched
})

const layers = [
  { type: 'Job' as Neo4jNodeType, label: 'Job', desc: '岗位', color: '#122d6e', level: 'L1' },
  { type: 'SkillArea' as Neo4jNodeType, label: 'SkillArea', desc: '技能领域', color: '#2f47b8', level: 'L2' },
  { type: 'TechStack' as Neo4jNodeType, label: 'TechStack', desc: '技术栈', color: '#3f5ae0', level: 'L3' },
  { type: 'TechPoint' as Neo4jNodeType, label: 'TechPoint', desc: '技术点', color: '#7893de', level: 'L4' },
  { type: 'KnowledgePoint' as Neo4jNodeType, label: 'KnwlPoint', desc: '知识点', color: '#b4c2f2', level: 'L5' },
]

const stackOptions = [
  { label: '全部方向', value: '' },
  { label: 'AI', value: 'ai' },
  { label: '后端', value: 'backend' },
  { label: '大数据', value: 'data' },
  { label: 'DevOps', value: 'devops' },
]

const levelOptions = [
  { label: '全部级别', value: '' },
  { label: '初级', value: 'junior' },
  { label: '中级', value: 'middle' },
  { label: '高级', value: 'senior' },
]

const currentViewTitle = computed(() => {
  const stack = stackOptions.find(s => s.value === stackFilter.value)?.label || '全部方向'
  const level = levelOptions.find(l => l.value === levelFilter.value)?.label || '全部级别'
  return `${stack} · ${level}`
})

// 上下级节点
const parentNodes = computed(() => {
  if (!activeNode.value || !graphStore.graph) return []
  const ids = new Set<string>()
  graphStore.graph.forEachEdge((_e, _a, source, target) => {
    if (target === activeNode.value?.id) ids.add(source)
  })
  return Array.from(ids).map(id => graphStore.graph.getNodeAttributes(id)).filter(Boolean)
})

const childNodes = computed(() => {
  if (!activeNode.value || !graphStore.graph) return []
  const ids = new Set<string>()
  graphStore.graph.forEachEdge((_e, _a, source, target) => {
    if (source === activeNode.value?.id) ids.add(target)
  })
  return Array.from(ids).map(id => graphStore.graph.getNodeAttributes(id)).filter(Boolean)
})

const isActiveNodePinned = computed(() =>
  Boolean(activeNode.value && pinnedNodeIds.value.includes(activeNode.value.id))
)

// 加载图谱
async function loadGraph() {
  await graphStore.fetchPanorama({
    stack: stackFilter.value || undefined,
    level: levelFilter.value || undefined,
    keyword: searchKeyword.value.trim() || undefined,
    limit: graphStore.currentLimit,
  })
  activeNode.value = null
  pinnedNodeIds.value = []
}

async function handleLoadMore() {
  await graphStore.loadMore()
}

function handleReset() {
  searchKeyword.value = ''
  stackFilter.value = ''
  levelFilter.value = ''
  selectedType.value = 'all'
  activeNode.value = null
  pinnedNodeIds.value = []
  graphStore.currentLimit = 50
  graphStore.hasMore = true
  loadGraph()
}

// 节点交互
function handleNodeClick(node: GraphNodeAttrs | null) {
  activeNode.value = node
}

function handleNodePin(nodeId: string, pinned: boolean) {
  if (pinned) {
    pinnedNodeIds.value = [nodeId]
  } else {
    pinnedNodeIds.value = pinnedNodeIds.value.filter(id => id !== nodeId)
  }
}

function toggleActiveNodePin() {
  if (!activeNode.value) return
  const pinned = !pinnedNodeIds.value.includes(activeNode.value.id)
  handleNodePin(activeNode.value.id, pinned)
}

function handleRelatedNodeClick(attrs: any) {
  activeNode.value = attrs as GraphNodeAttrs
}

function handleStackChange() { loadGraph() }
function handleLevelChange() { loadGraph() }

// 搜索防抖
let filterTimer: ReturnType<typeof setTimeout> | undefined
watch([searchKeyword, stackFilter, levelFilter], () => {
  clearTimeout(filterTimer)
  filterTimer = setTimeout(() => loadGraph(), 250)
})

onMounted(async () => {
  if (!graphStore.loaded) await loadGraph()
})

onUnmounted(() => clearTimeout(filterTimer))
</script>

<template>
  <div class="graph-page">
    <!-- 顶部工具栏 -->
    <section class="graph-toolbar">
      <div class="graph-search">
        <input
          v-model="searchKeyword"
          placeholder="搜索岗位、技能领域、技术栈或知识点..."
        />
      </div>
      <select v-model="stackFilter" class="filter-select" @change="handleStackChange">
        <option v-for="s in stackOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
      </select>
      <select v-model="levelFilter" class="filter-select" @change="handleLevelChange">
        <option v-for="l in levelOptions" :key="l.value" :value="l.value">{{ l.label }}</option>
      </select>
      <div class="graph-stats">
        <span>{{ graphStore.nodeCount }} 节点</span>
        <span>{{ graphStore.edgeCount }} 边</span>
        <button
          v-if="graphStore.hasMore"
          class="btn-load-more"
          :disabled="graphStore.loading"
          @click="handleLoadMore"
        >
          {{ graphStore.loading ? '加载中...' : '加载更多' }}
        </button>
        <button class="btn-reset" @click="handleReset">重置</button>
      </div>
    </section>

    <!-- 主体布局：左侧过滤 + 右侧画布（内含节点详情） -->
    <section class="graph-layout">
      <!-- 左侧：层过滤 -->
      <aside class="graph-side-card">
        <div class="card-title">三层模型</div>
        <div class="layer-list">
          <button
            v-for="layer in layers"
            :key="layer.type"
            class="layer-item"
            :class="{ active: selectedType === layer.type }"
            @click="selectedType = selectedType === layer.type ? 'all' : layer.type"
          >
            <span class="layer-dot" :style="{ background: layer.color }"></span>
            <span>{{ layer.label }}</span>
            <em>{{ layer.desc }}</em>
          </button>
        </div>
        <div class="card-divider"></div>
        <div class="enrich-hint">点击节点查看详情，点击层级按钮聚焦对应层级</div>
      </aside>

      <!-- 右侧：画布 + 节点详情 -->
      <main class="graph-canvas-card">
        <div class="canvas-head">
          <div>
            <span class="canvas-label">当前视图</span>
            <h3>{{ currentViewTitle }}</h3>
          </div>
        </div>
        <div class="canvas-body">
          <div class="graph-canvas">
            <Graph3DCanvas
              :graph="graphStore.graph"
              :highlighted-node-ids="searchHighlightedNodeIds"
              :pinned-node-ids="pinnedNodeIds"
              :selected-type="selectedType"
              @node-click="handleNodeClick"
              @node-pin="handleNodePin"
            />
          </div>

          <!-- 节点详情（画布右侧） -->
          <aside class="graph-detail-card">
            <div class="card-title">节点详情</div>
            <div v-if="activeNode" class="detail-content">
              <div class="detail-head">
                <span class="detail-type" :style="{ color: TYPE_COLORS[activeNode.type] || '#64748b' }">
                  {{ TYPE_LABELS[activeNode.type] || activeNode.type }}
                </span>
                <h3>{{ activeNode.name }}</h3>
                <p>{{ activeNode.description }}</p>
                <button class="btn-pin" @click="toggleActiveNodePin">
                  {{ isActiveNodePinned ? '取消锁定' : '锁定节点' }}
                </button>
              </div>

              <div class="detail-grid">
                <div><strong>{{ activeNode.stack || '-' }}</strong><span>技术方向</span></div>
                <div><strong>{{ activeNode.level || '-' }}</strong><span>层级</span></div>
                <div><strong>{{ activeNode.frequency ?? activeNode.importance ?? '-' }}</strong><span>频次/权重</span></div>
              </div>

              <div class="card-title sub-title">上级节点</div>
              <div class="related-list">
                <button v-for="n in parentNodes" :key="n.id" class="related-node-btn" @click="handleRelatedNodeClick(n)">
                  <span :style="{ background: TYPE_COLORS[n.type] || '#94a3b8' }"></span>
                  {{ n.name }}
                </button>
                <em v-if="parentNodes.length === 0">暂无上级节点</em>
              </div>

              <div class="card-title sub-title">下级节点</div>
              <div class="related-list">
                <div v-for="n in childNodes" :key="n.id" class="child-node-row">
                  <button class="related-node-btn" @click="handleRelatedNodeClick(n)">
                    <span :style="{ background: TYPE_COLORS[n.type] || '#94a3b8' }"></span>
                    {{ n.name }}
                  </button>
                </div>
                <em v-if="childNodes.length === 0">暂无下级节点</em>
              </div>
            </div>
            <div v-else class="detail-empty">
              <p>点击图谱中的节点查看详情</p>
            </div>
          </aside>
        </div>
      </main>
    </section>
  </div>
</template>

<style scoped>
.graph-page {
  /* simple wrapper — no viewport math, no negative margins */
}

/* ===== 工具栏 ===== */
.graph-toolbar {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) auto auto;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

.graph-search {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  padding: 11px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
}

.graph-search input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  color: #334155;
  font-size: 14px;
}

.graph-search input:focus { border-color: #4f6ef6; }

.filter-select {
  padding: 9px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  background: #fff;
  color: #475569;
  cursor: pointer;
  outline: none;
}

.graph-stats {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 14px;
  color: #94a3b8;
  white-space: nowrap;
}

.btn-load-more {
  padding: 6px 14px;
  border: 1px solid #4f6ef6;
  border-radius: 6px;
  background: #4f6ef6;
  color: #fff;
  font-size: 12px;
  cursor: pointer;
}
.btn-load-more:hover { background: #3d5bd9; }
.btn-load-more:disabled { background: #94a3b8; border-color: #94a3b8; cursor: not-allowed; }

.btn-reset {
  padding: 6px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #fff;
  color: #64748b;
  font-size: 12px;
  cursor: pointer;
}
.btn-reset:hover { border-color: #4f6ef6; color: #4f6ef6; }

/* ===== 两栏布局：左侧过滤 + 右侧画布（内含节点详情） ===== */
.graph-layout {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 16px;
  align-items: stretch;
}

.graph-side-card,
.graph-canvas-card {
  min-width: 0;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,.05), 0 1px 2px rgba(0,0,0,.04);
}

.graph-side-card,
.graph-canvas-card {
  height: 674px;
}

.graph-side-card {
  padding: 18px;
  overflow: hidden;
}

/* ===== 左侧面板 ===== */
.card-title {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 10px;
}

.card-divider {
  height: 1px;
  background: #e2e8f0;
  margin: 12px 0;
}

.layer-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.layer-item {
  display: grid;
  grid-template-columns: 10px 1fr;
  gap: 8px 10px;
  align-items: center;
  width: 100%;
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 10px;
  background: #f1f5f9;
  color: #64748b;
  text-align: left;
  cursor: pointer;
}

.layer-item.active,
.layer-item:hover {
  border-color: rgba(79, 110, 246, 0.22);
  background: #eef0ff;
}

.layer-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.layer-item span:nth-child(2) {
  color: #1e293b;
  font-size: 14px;
  font-weight: 700;
}

.layer-item em {
  grid-column: 2;
  color: #94a3b8;
  font-size: 14px;
  font-style: normal;
}

.enrich-hint {
  font-size: 11px;
  color: #94a3b8;
  line-height: 1.5;
  padding: 4px;
}

/* ===== 中央画布 ===== */
.graph-canvas-card {
  display: flex;
  min-height: 0;
  flex-direction: column;
  overflow: hidden;
}

.canvas-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px;
  border-bottom: 1px solid #e2e8f0;
  background: #fff;
  flex-shrink: 0;
}

.canvas-label {
  color: #94a3b8;
  font-size: 14px;
}

.canvas-head h3 {
  margin-top: 2px;
  color: #1e293b;
  font-size: 16px;
}

/* 画布主体：左侧图谱 + 右侧详情 */
.canvas-body {
  display: flex;
  min-height: 0;
  flex: 1;
}

.graph-canvas {
  flex: 1;
  min-width: 0;
  min-height: 0;
}

/* ===== 节点详情（画布右侧嵌入） ===== */
.graph-detail-card {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  min-height: 0;
  flex-direction: column;
  padding: 18px;
  border-left: 1px solid #e2e8f0;
  background: #fff;
  overflow: hidden;
}

.detail-content {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  margin-top: 12px;
  padding-right: 8px;
  overflow-x: hidden;
  overflow-y: auto;
}

.sub-title {
  margin-top: 22px;
  margin-bottom: 10px;
}

.detail-head { margin-bottom: 4px; }

.detail-type {
  font-size: 14px;
  font-weight: 800;
}

.detail-head h3 {
  margin-top: 4px;
  color: #1e293b;
  font-size: 20px;
}

.detail-head p {
  margin-top: 8px;
  padding-right: 4px;
  color: #94a3b8;
  font-size: 14px;
  line-height: 1.7;
  max-height: 104px;
  overflow-y: auto;
}

.btn-pin {
  display: block;
  width: 140px;
  margin-top: 8px;
  padding: 8px 0;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #fff;
  color: #64748b;
  font-size: 13px;
  text-align: center;
  cursor: pointer;
}
.btn-pin:hover { border-color: #f59e0b; color: #f59e0b; }

.detail-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-top: 16px;
}

.detail-grid div {
  padding: 10px;
  border-radius: 8px;
  background: #f1f5f9;
}

.detail-grid strong {
  display: block;
  color: #1e293b;
  font-size: 14px;
}

.detail-grid span {
  display: block;
  margin-top: 3px;
  color: #94a3b8;
  font-size: 14px;
}

.related-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  flex: none;
  padding-right: 4px;
}

.related-list .related-node-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 9px 10px;
  background: #f1f5f9;
  color: #475569;
  text-align: left;
  cursor: pointer;
}

.related-list .related-node-btn:hover {
  color: #4f6ef6;
  background: #eef0ff;
}

.related-list .related-node-btn span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.child-node-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.child-node-row .related-node-btn {
  flex: 1;
  min-width: 0;
}

.related-list em {
  color: #94a3b8;
  font-size: 14px;
  font-style: normal;
}

.detail-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 0;
  flex: 1;
  color: #94a3b8;
  font-size: 14px;
}

@media (max-width: 1280px) {
  .graph-detail-card {
    width: 260px;
  }
}

@media (max-width: 960px) {
  .graph-toolbar,
  .graph-layout {
    grid-template-columns: 1fr;
  }

  .graph-side-card {
    height: auto;
  }

  .graph-canvas-card {
    height: 674px;
  }

  .canvas-body {
    flex-direction: column;
  }

  .graph-detail-card {
    width: 100%;
    height: 380px;
    border-left: none;
    border-top: 1px solid #e2e8f0;
  }
}

@media (max-width: 640px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
