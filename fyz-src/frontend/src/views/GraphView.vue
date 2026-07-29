<template>
  <div>
    <DataState :loading="loading" :error="error" @retry="loadGraph" />
    <section class="graph-toolbar anim-fade-up">
      <div class="graph-search">
        <el-icon><Search /></el-icon>
        <input v-model="keyword" placeholder="搜索岗位、技能领域、技术栈或知识点，例如 RAG / Spring Boot / Prompt" />
      </div>
      <el-select v-model="selectedStack" size="default" style="width:130px;">
        <el-option v-for="item in stackOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-select v-model="selectedLevel" size="default" style="width:120px;">
        <el-option v-for="item in levelOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <div class="graph-stats-mini">
        <span>{{ nodeCount }} 节点</span>
        <span>{{ edgeCount }} 边</span>
        <span>{{ activeNode?.frequency ?? activeNode?.importance ?? "-" }} 热度</span>
        <el-button size="small" type="primary" plain :loading="syncing" @click="syncGraph">
          <el-icon><Refresh /></el-icon>同步真实图谱
        </el-button>
      </div>
    </section>
    <el-alert
      v-if="syncMessage"
      class="graph-sync-alert"
      type="success"
      :closable="false"
      show-icon
      :title="syncMessage"
    />

    <section class="graph-layout anim-fade-up anim-delay-3">
      <aside class="graph-side-card">
        <div class="graph-card-title">五层模型</div>
        <div class="graph-layer-list">
          <button
            v-for="layer in layers"
            :key="layer.type"
            class="graph-layer-item"
            :class="{ active: selectedType === layer.type }"
            @click="selectedType = selectedType === layer.type ? 'all' : layer.type"
          >
            <span class="graph-layer-dot" :style="{ background: layer.color }"></span>
            <span>{{ layer.label }}</span>
            <em>{{ layer.desc }}</em>
          </button>
        </div>
      </aside>

      <main class="graph-canvas-card">
        <div class="graph-canvas-head">
          <div>
            <span class="graph-canvas-label">当前视图</span>
            <h3>{{ currentViewTitle }}</h3>
          </div>
          <div class="graph-canvas-actions">
            <button class="graph-overview-btn" @click="resetToOverview">
              <el-icon><View /></el-icon>
              回到概览
            </button>
            <div class="graph-mini-legend">
              <span><i class="solid"></i> 层级关系</span>
            </div>
          </div>
        </div>

        <div class="graph-canvas">
          <Graph3DCanvas
            ref="graphCanvasRef"
            :graph="currentGraph"
            :highlighted-path="highlightedPath"
            :pinned-node-ids="pinnedNodeIds"
            @node-click="handleNodeClick"
            @node-pin="handleNodePin"
          />
        </div>
      </main>

      <aside class="graph-detail-card">
        <div class="graph-card-title">节点详情</div>
        <template v-if="activeNode">
          <div class="graph-detail-head">
            <span class="graph-detail-type" :style="{ color: typeMeta[activeNode.type].color }">
              {{ typeMeta[activeNode.type].label }}
            </span>
            <h3>{{ activeNode.name }}</h3>
            <p>{{ activeNode.description }}</p>
          </div>

          <div class="graph-detail-grid">
            <div>
              <strong>{{ activeNode.stack }}</strong>
              <span>技术方向</span>
            </div>
            <div>
              <strong>{{ activeNode.level }}</strong>
              <span>适配级别</span>
            </div>
            <div>
              <strong>{{ activeNode.frequency ?? activeNode.importance ?? "-" }}</strong>
              <span>频次/权重</span>
            </div>
          </div>

          <div class="graph-card-title with-gap">关联节点</div>
          <div class="graph-related-list">
            <button
              v-for="node in relatedNodes"
              :key="node.id"
              @click="handleRelatedNodeClick(node)"
            >
              <span :style="{ background: typeMeta[node.type].color }"></span>
              {{ node.name }}
            </button>
            <em v-if="relatedNodes.length === 0">暂无直接关联节点</em>
          </div>
        </template>
        <template v-else>
          <div class="graph-detail-empty">
            <el-icon><HelpFilled /></el-icon>
            <p>点击图谱中的节点查看详情</p>
          </div>
        </template>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch, nextTick } from "vue";
import { storeToRefs } from "pinia";
import { Search, View, HelpFilled, Refresh } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import Graph from "graphology";
import Graph3DCanvas from "@/components/graph/Graph3DCanvas.vue";
import { buildGraphFromBackend } from "@/data/graphBuilder";
import DataState from "@/components/common/DataState.vue";
import { dataProvider } from "@/data";
import type { GraphNode, GraphType } from "@/domain/types";

type FilterType = GraphType | "all";
type StackType = "all" | "ai" | "backend" | "data" | "devops";
type LevelType = "all" | "junior" | "middle" | "senior";

const keyword = ref("");
const selectedStack = ref<StackType>("all");
const selectedLevel = ref<LevelType>("all");
const selectedType = ref<FilterType>("all");
const loading = ref(false);
const error = ref("");
const currentGraph = ref<Graph | null>(null);
const activeNode = ref<GraphNode | null>(null);
const highlightedPath = ref<string[]>([]);
const pinnedNodeIds = ref<string[]>([]);
const graphCanvasRef = ref<InstanceType<typeof Graph3DCanvas> | null>(null);
const syncing = ref(false);
const syncMessage = ref("");

onMounted(async () => {
  await loadGraph();
});

async function loadGraph() {
  loading.value = true;
  error.value = "";
  try {
    currentGraph.value = await buildGraphFromBackend();
    activeNode.value = null;
    highlightedPath.value = [];
    pinnedNodeIds.value = [];
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载失败";
    currentGraph.value = null;
  } finally {
    loading.value = false;
  }
}

async function syncGraph() {
  syncing.value = true;
  syncMessage.value = "";
  try {
    const result = await dataProvider.graph.sync();
    syncMessage.value = `同步完成：${result.node_count} 个节点、${result.edge_count} 条关系，使用 ${result.fact_count} 条已确认事实`;
    await loadGraph();
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "图谱同步失败");
  } finally {
    syncing.value = false;
  }
}

function resetToOverview() {
  keyword.value = "";
  selectedStack.value = "all";
  selectedLevel.value = "all";
  selectedType.value = "all";
  activeNode.value = null;
  highlightedPath.value = [];
  pinnedNodeIds.value = [];
  loadGraph();
}

const typeMeta: Record<GraphType, { label: string; short: string; color: string }> = {
  Job: { label: "L1 岗位", short: "L1", color: "#122d6e" },
  SkillArea: { label: "L2 技能领域", short: "L2", color: "#2f47b8" },
  TechStack: { label: "L3 技术栈", short: "L3", color: "#3f5ae0" },
  TechPoint: { label: "L4 技术细节点", short: "L4", color: "#7893de" },
  KnowledgePoint: { label: "L5 知识要点", short: "L5", color: "#b4c2f2" },
  SourceDocument: { label: "来源证据", short: "SRC", color: "#94a3b8" },
  GraphSnapshot: { label: "图谱快照", short: "VER", color: "#64748b" },
};

const layers = [
  { type: "Job" as GraphType, label: "Job", desc: "岗位", color: "#122d6e" },
  { type: "SkillArea" as GraphType, label: "SkillArea", desc: "技能领域", color: "#2f47b8" },
  { type: "TechStack" as GraphType, label: "TechStack", desc: "技术栈", color: "#3f5ae0" },
  { type: "TechPoint" as GraphType, label: "TechPoint", desc: "技术细节点", color: "#7893de" },
  { type: "KnowledgePoint" as GraphType, label: "KnowledgePoint", desc: "知识要点", color: "#b4c2f2" },
];

const stackOptions: { label: string; value: StackType }[] = [
  { label: "全部方向", value: "all" },
  { label: "AI", value: "ai" },
  { label: "后端", value: "backend" },
  { label: "大数据", value: "data" },
  { label: "DevOps", value: "devops" },
];

const levelOptions: { label: string; value: LevelType }[] = [
  { label: "全部级别", value: "all" },
  { label: "初级", value: "junior" },
  { label: "中级", value: "middle" },
  { label: "高级", value: "senior" },
];

const nodeCount = computed(() => currentGraph.value?.order || 0);
const edgeCount = computed(() => currentGraph.value?.size || 0);

const relatedNodes = computed(() => {
  if (!activeNode.value || !currentGraph.value) return [];
  const ids = new Set<string>();
  currentGraph.value.forEachEdge((_edgeId, _attrs, source, target) => {
    if (source === activeNode.value?.id) {
      ids.add(target);
    }
    if (target === activeNode.value?.id) {
      ids.add(source);
    }
  });
  const result: GraphNode[] = [];
  ids.forEach(id => {
    const attrs = currentGraph.value?.getNodeAttributes(id);
    if (attrs) {
      result.push({
        id: attrs.id || id,
        name: attrs.name || attrs.label || id,
        type: attrs.type as GraphType,
        stack: attrs.stack as any,
        level: attrs.level as any,
        x: attrs.x || 0,
        y: attrs.y || 0,
        description: attrs.description || "",
        importance: attrs.importance,
        frequency: attrs.frequency,
      });
    }
  });
  return result;
});

const currentViewTitle = computed(() => {
  const stack = stackOptions.find(item => item.value === selectedStack.value)?.label || "全部方向";
  const level = levelOptions.find(item => item.value === selectedLevel.value)?.label || "全部级别";
  return `${stack} · ${level} · ${selectedType.value === "all" ? "全层级" : typeMeta[selectedType.value].label}`;
});

function handleNodeClick(node: GraphNode | null) {
  activeNode.value = node;
}

function handleNodePin(nodeId: string, pinned: boolean) {
  if (pinned) {
    pinnedNodeIds.value = [nodeId];
  }
}

function handleRelatedNodeClick(node: GraphNode) {
  activeNode.value = node;
}

let filterTimer: ReturnType<typeof setTimeout> | undefined;
watch([keyword, selectedStack, selectedLevel, selectedType], () => {
  clearTimeout(filterTimer);
  filterTimer = setTimeout(async () => {
    await loadGraph();
  }, 250);
});
</script>

<style scoped>
.graph-toolbar {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) auto auto;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

.graph-sync-alert {
  margin: -4px 0 16px;
  border-radius: 12px;
}

.graph-search {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  padding: 11px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
}

.graph-search input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 14px;
}

.graph-stats-mini {
  display: flex; gap: 14px;
  font-size: 14px; color: var(--text-secondary);
  font-family: var(--font-mono);
}
.graph-stats-mini span { white-space: nowrap; }

.graph-layout {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr) 286px;
  gap: 16px;
}

.graph-side-card,
.graph-canvas-card,
.graph-detail-card {
  min-width: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-elevated);
  box-shadow: var(--shadow-sm);
}

.graph-side-card,
.graph-detail-card {
  padding: 18px;
}

.graph-card-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.graph-card-title.with-gap {
  margin-top: 22px;
  margin-bottom: 10px;
}

.graph-layer-list,
.graph-api-list,
.graph-related-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.graph-layer-item {
  display: grid;
  grid-template-columns: 10px 1fr;
  gap: 8px 10px;
  align-items: center;
  width: 100%;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  padding: 10px;
  background: var(--color-bg-muted);
  color: var(--text-secondary);
  text-align: left;
  cursor: pointer;
}

.graph-layer-item.active,
.graph-layer-item:hover {
  border-color: rgba(79,110,246,.22);
  background: var(--color-brand-light);
}

.graph-layer-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.graph-layer-item span:nth-child(2) {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 700;
}

.graph-layer-item em {
  grid-column: 2;
  color: var(--text-muted);
  font-size: 14px;
  font-style: normal;
}

.graph-api-list span {
  padding: 7px 9px;
  border-radius: var(--radius-sm);
  background: var(--color-bg-muted);
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 14px;
}

.graph-canvas-card {
  overflow: hidden;
}

.graph-canvas-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px;
  border-bottom: 1px solid var(--color-border-light);
  background: var(--color-bg-elevated);
}

.graph-canvas-label {
  color: var(--text-muted);
  font-size: 14px;
}

.graph-canvas-head h3 {
  margin-top: 2px;
  color: var(--text-primary);
  font-size: 16px;
}

.graph-canvas-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.graph-overview-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-elevated);
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.graph-overview-btn:hover {
  border-color: var(--color-brand);
  color: var(--color-brand);
  background: var(--color-brand-light);
}

.graph-mini-legend {
  display: flex;
  gap: 12px;
  color: var(--text-secondary);
  font-size: 14px;
}

.graph-mini-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.graph-mini-legend i {
  width: 22px;
  height: 0;
  border-top: 2px solid var(--color-border);
}

.graph-mini-legend i.dashed {
  border-top-style: dashed;
}

.graph-canvas {
  width: 100%;
  height: 600px;
}

.graph-detail-head {
  margin-top: 14px;
}

.graph-detail-type {
  font-size: 14px;
  font-weight: 800;
}

.graph-detail-head h3 {
  margin-top: 4px;
  color: var(--text-primary);
  font-size: 20px;
}

.graph-detail-head p {
  margin-top: 8px;
  color: var(--text-muted);
  font-size: 14px;
  line-height: 1.7;
}

.graph-detail-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-top: 16px;
}

.graph-detail-grid div {
  padding: 10px;
  border-radius: var(--radius-md);
  background: var(--color-bg-muted);
}

.graph-detail-grid strong {
  display: block;
  color: var(--text-primary);
  font-size: 14px;
}

.graph-detail-grid span {
  display: block;
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 14px;
}

.graph-related-list button {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  padding: 9px 10px;
  background: var(--color-bg-muted);
  color: var(--text-secondary);
  text-align: left;
  cursor: pointer;
}

.graph-related-list button:hover {
  color: var(--color-brand);
  background: var(--color-brand-light);
}

.graph-related-list button span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.graph-related-list em {
  color: var(--text-muted);
  font-size: 14px;
  font-style: normal;
}

.graph-detail-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
  color: var(--text-muted);
}

.graph-detail-empty el-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.graph-detail-empty p {
  font-size: 14px;
}

@media (max-width: 1280px) {
  .graph-layout {
    grid-template-columns: 220px minmax(0, 1fr);
  }

  .graph-detail-card {
    grid-column: 1 / -1;
  }
}

@media (max-width: 960px) {
  .graph-toolbar,
  .graph-layout {
    grid-template-columns: 1fr;
  }

  .graph-filter-group {
    overflow-x: auto;
  }
}

@media (max-width: 640px) {
  .graph-detail-grid {
    grid-template-columns: 1fr;
  }

  .graph-mini-legend {
    display: none;
  }
}
</style>
