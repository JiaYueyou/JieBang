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
        <el-button size="small" type="primary" :plain="syncing" :loading="syncing" :disabled="graphTasks.anyRunning.value && !syncing" @click="syncGraph">
          <el-icon><Refresh /></el-icon>同步真实图谱
        </el-button>
        <el-button size="small" type="primary" :loading="generating" :disabled="graphTasks.anyRunning.value && !generating" @click="generateDeepCandidates">
          一键生成 L4/L5 候选
        </el-button>
        <el-button v-if="hasMoreOverview" size="small" :loading="loadingMore" @click="loadMoreOverview">
          加载更多岗位
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
    <section v-if="activeBackgroundTask" class="graph-task-progress" role="status" aria-live="polite">
      <div>
        <strong>{{ activeTaskTitle }}</strong>
        <span>{{ activeBackgroundTask.result?.detail || "任务已提交，页面可继续使用" }}</span>
      </div>
      <el-progress :percentage="activeBackgroundTask.progress" :status="activeBackgroundTask.status === 'failed' ? 'exception' : undefined" />
    </section>

    <section class="graph-layout anim-fade-up anim-delay-3">
      <aside class="graph-side-card">
        <div class="graph-card-title">五层模型</div>
        <div class="graph-layer-list">
          <button
            v-for="layer in layers"
            :key="layer.type"
            class="graph-layer-item"
            :class="{ active: selectedType === layer.type }"
            @click="selectLayer(layer.type)"
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
            :highlighted-node-ids="searchHighlightedNodeIds"
            :pinned-node-ids="pinnedNodeIds"
            @node-click="handleNodeClick"
            @node-pin="handleNodePin"
          />
        </div>
      </main>

      <aside class="graph-detail-card">
        <div class="graph-card-title">节点详情</div>
        <div v-if="activeNode" class="graph-detail-content">
          <div class="graph-detail-head">
            <span class="graph-detail-type" :style="{ color: typeMeta[activeNode.type].color }">
              {{ typeMeta[activeNode.type].label }}
            </span>
            <h3>{{ activeNode.name }}</h3>
            <p>{{ activeNode.description }}</p>
            <el-button
              v-if="activeNode.type === 'TechStack'"
              class="deep-expand-btn"
              type="primary"
              plain
              :loading="expandingNodeId === activeNode.id"
              @click="expandSelectedDeep"
            >展开 L4/L5</el-button>
            <el-button
              class="pin-toggle-btn"
              :type="isActiveNodePinned ? 'warning' : 'primary'"
              plain
              @click="toggleActiveNodePin"
            >{{ isActiveNodePinned ? "取消锁定" : "锁定节点" }}</el-button>
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

          <div v-if="activeNode.type === 'KnowledgePoint'" class="knowledge-detail">
            <div class="graph-card-title with-gap">技术内容</div>
            <p>{{ activeNode.description || "该知识点暂未补充详细说明。" }}</p>
            <dl>
              <div><dt>难度</dt><dd>{{ activeNode.difficulty || "未分级" }}</dd></div>
              <div><dt>证据数</dt><dd>{{ activeNode.source_count ?? activeNode.evidence_ids?.length ?? 0 }}</dd></div>
              <div v-if="activeNode.prerequisites?.length"><dt>前置知识</dt><dd>{{ activeNode.prerequisites.join("、") }}</dd></div>
            </dl>
            <div v-if="activeNode.core_stack?.length" class="knowledge-block">
              <strong>核心技术栈</strong>
              <div class="knowledge-tags"><span v-for="item in activeNode.core_stack" :key="item">{{ item }}</span></div>
            </div>
            <div v-if="activeNode.common_solutions?.length" class="knowledge-block">
              <strong>常用方案</strong>
              <article v-for="solution in activeNode.common_solutions" :key="solution.name">
                <b>{{ solution.name }}</b><p>{{ solution.purpose }}</p>
              </article>
            </div>
            <el-button class="knowledge-more-btn" type="primary" plain @click="knowledgeDialogVisible = true">
              查看知识要点详情
            </el-button>
          </div>

          <div class="graph-card-title with-gap">上级节点</div>
          <div class="graph-related-list">
            <button
              v-for="node in parentNodes"
              :key="node.id"
              @click="handleRelatedNodeClick(node)"
            >
              <span :style="{ background: typeMeta[node.type].color }"></span>
              {{ node.name }}
            </button>
            <em v-if="parentNodes.length === 0">暂无上级节点</em>
          </div>
          <div class="graph-card-title with-gap">下级节点</div>
          <div class="graph-related-list">
            <button
              v-for="node in childNodes"
              :key="node.id"
              @click="handleRelatedNodeClick(node)"
            >
              <span :style="{ background: typeMeta[node.type].color }"></span>
              {{ node.name }}
            </button>
            <em v-if="childNodes.length === 0">暂无下级节点</em>
          </div>
        </div>
        <div v-else class="graph-detail-empty">
          <el-icon><HelpFilled /></el-icon>
          <p>点击图谱中的节点查看详情</p>
        </div>
      </aside>
    </section>

    <el-dialog
      v-model="knowledgeDialogVisible"
      class="knowledge-dialog"
      width="min(720px, 92vw)"
      title="知识要点详情"
      append-to-body
    >
      <div v-if="activeNode?.type === 'KnowledgePoint'" class="knowledge-dialog-body">
        <div class="knowledge-dialog-kicker">L5 · {{ activeNode.parent_tech_point || "知识要点" }}</div>
        <h2>{{ activeNode.name }}</h2>
        <p class="knowledge-dialog-description">{{ activeNode.description || "该知识要点暂未补充详细说明。" }}</p>
        <section v-if="activeNode.core_stack?.length">
          <h3>核心概念与组件</h3>
          <div class="knowledge-tags"><span v-for="item in activeNode.core_stack" :key="item">{{ item }}</span></div>
        </section>
        <section v-if="activeNode.common_solutions?.length">
          <h3>常用方案</h3>
          <article v-for="solution in activeNode.common_solutions" :key="solution.name" class="knowledge-solution-card">
            <strong>{{ solution.name }}</strong>
            <p>{{ solution.purpose }}</p>
          </article>
        </section>
        <section class="knowledge-dialog-meta">
          <span>难度：{{ activeNode.difficulty || "未分级" }}</span>
          <span>证据数：{{ activeNode.source_count ?? activeNode.evidence_ids?.length ?? 0 }}</span>
          <span v-if="activeNode.prerequisites?.length">前置知识：{{ activeNode.prerequisites.join("、") }}</span>
        </section>
      </div>
      <template #footer><el-button @click="knowledgeDialogVisible = false">关闭</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Search, View, HelpFilled, Refresh } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import Graph from "graphology";
import Graph3DCanvas from "@/components/graph/Graph3DCanvas.vue";
import { buildGraphFromSubgraph } from "@/data/graphBuilder";
import { getNodeNeighbors, getOverview, getPanorama } from "@/api/graph";
import DataState from "@/components/common/DataState.vue";
import { useGraphTasks } from "@/composables/useGraphTasks";
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
const masterGraph = ref<Graph | null>(null);
const currentGraph = ref<Graph | null>(null);
const activeNode = ref<GraphNode | null>(null);
const highlightedPath = ref<string[]>([]);
const searchHighlightedNodeIds = computed(() => {
  const query = keyword.value.trim().toLocaleLowerCase();
  if (!query || !currentGraph.value) return [];
  const matched: string[] = [];
  currentGraph.value.forEachNode((id, attrs) => {
    const searchable = [attrs.name, attrs.label, attrs.description, attrs.parent_skill, attrs.parent_tech_point]
      .filter(Boolean).join(" ").toLocaleLowerCase();
    if (searchable.includes(query)) matched.push(id);
  });
  return matched;
});
const pinnedNodeIds = ref<string[]>([]);
const knowledgeDialogVisible = ref(false);
const graphCanvasRef = ref<InstanceType<typeof Graph3DCanvas> | null>(null);
const graphTasks = useGraphTasks();
const syncing = computed(() => ["queued", "running"].includes(graphTasks.tasks.sync?.status || ""));
const generating = computed(() => ["queued", "running"].includes(graphTasks.tasks.enrichment?.status || ""));
const syncMessage = ref("");
let syncMessageTimer: number | undefined;
const overviewCursor = ref<string | null>(null);
const hasMoreOverview = ref(false);
const loadingMore = ref(false);
const expandingNodeId = ref("");
const expandedScopes = new Set<string>();

onMounted(async () => {
  graphTasks.resume();
  await loadGraph();
});
onBeforeUnmount(() => window.clearTimeout(syncMessageTimer));

const activeBackgroundTask = computed(() => {
  const enrichment = graphTasks.tasks.enrichment;
  const sync = graphTasks.tasks.sync;
  if (enrichment && ["queued", "running"].includes(enrichment.status)) return enrichment;
  if (sync && ["queued", "running"].includes(sync.status)) return sync;
  return null;
});
const activeTaskTitle = computed(() => graphTasks.tasks.enrichment ? "正在生成 L4/L5 候选" : "正在同步真实图谱");

watch(() => graphTasks.tasks.sync?.status, async status => {
  if (status === "succeeded") {
    const result = graphTasks.tasks.sync?.result;
    syncMessage.value = `同步完成：${result?.node_count ?? 0} 个节点、${result?.edge_count ?? 0} 条关系，使用 ${result?.fact_count ?? 0} 条已确认事实`;
    await loadGraph();
    window.clearTimeout(syncMessageTimer);
    syncMessageTimer = window.setTimeout(() => {
      syncMessage.value = "";
      graphTasks.clear("sync");
    }, 5000);
  } else if (status === "failed") {
    ElMessage.error(graphTasks.tasks.sync?.error_message || "图谱同步失败");
  }
});

watch(() => graphTasks.tasks.enrichment?.status, status => {
  if (status === "succeeded") {
    ElMessage.success("L4/L5 候选已生成，请到系统管理的“图谱审核”中确认并发布");
  } else if (status === "failed") {
    ElMessage.error(graphTasks.tasks.enrichment?.error_message || "L4/L5 候选生成失败");
  }
});

async function loadGraph() {
  loading.value = true;
  error.value = "";
  try {
    if (selectedType.value === "TechPoint" || selectedType.value === "KnowledgePoint") {
      await loadDeepLayer(selectedType.value);
      return;
    }
    const response = await getOverview({
      keyword: keyword.value.trim() || undefined,
      stack: selectedStack.value === "all" ? undefined : selectedStack.value,
      level: selectedLevel.value === "all" ? undefined : selectedLevel.value,
      page_size: 24,
      max_layer: 3,
    });
    masterGraph.value = buildGraphFromSubgraph(response);
    applyLayerFilter();
    overviewCursor.value = response.next_cursor || null;
    hasMoreOverview.value = Boolean(response.has_more);
    expandedScopes.clear();
    activeNode.value = null;
    highlightedPath.value = [];
    pinnedNodeIds.value = [];
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载失败";
    masterGraph.value = null;
    currentGraph.value = null;
  } finally {
    loading.value = false;
  }
}

async function loadMoreOverview() {
  if (!overviewCursor.value || !masterGraph.value) return;
  loadingMore.value = true;
  try {
    const response = await getOverview({
      cursor: overviewCursor.value, page_size: 24, max_layer: 3,
      keyword: keyword.value.trim() || undefined,
      stack: selectedStack.value === "all" ? undefined : selectedStack.value,
      level: selectedLevel.value === "all" ? undefined : selectedLevel.value,
    });
    const merged = buildGraphFromSubgraph(response, masterGraph.value);
    masterGraph.value = merged.copy();
    applyLayerFilter();
    overviewCursor.value = response.next_cursor || null;
    hasMoreOverview.value = Boolean(response.has_more);
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "加载更多图谱失败");
  } finally {
    loadingMore.value = false;
  }
}

async function loadDeepLayer(type: "TechPoint" | "KnowledgePoint") {
  const response = await getPanorama({
    node_type: type,
    keyword: keyword.value.trim() || undefined,
    stack: selectedStack.value === "all" ? undefined : selectedStack.value,
    level: selectedLevel.value === "all" ? undefined : selectedLevel.value,
    limit: 1000,
  });
  masterGraph.value = buildGraphFromSubgraph(response);
  applyLayerFilter();
  overviewCursor.value = null;
  hasMoreOverview.value = false;
  expandedScopes.clear();
  activeNode.value = null;
  highlightedPath.value = [];
  pinnedNodeIds.value = [];
}

async function syncGraph() {
  syncMessage.value = "";
  try {
    await graphTasks.startSync();
    ElMessage.success("图谱同步任务已提交，可继续使用当前页面");
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "图谱同步失败");
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

function graphNodeFromAttributes(id: string, attrs: Record<string, any>): GraphNode {
  return {
    ...attrs,
    id: attrs.id || id,
    name: attrs.name || attrs.label || id,
    type: attrs.type as GraphType,
    x: attrs.x || 0,
    y: attrs.y || 0,
    description: attrs.description || "",
  } as GraphNode;
}

function relatedNodesByDirection(direction: "parent" | "child") {
  if (!activeNode.value || !masterGraph.value) return [];
  const ids = new Set<string>();
  masterGraph.value.forEachEdge((_edgeId, _attrs, source, target) => {
    if (direction === "parent" && target === activeNode.value?.id) ids.add(source);
    if (direction === "child" && source === activeNode.value?.id) ids.add(target);
  });
  const result: GraphNode[] = [];
  ids.forEach(id => {
    const attrs = masterGraph.value?.getNodeAttributes(id);
    if (attrs) result.push(graphNodeFromAttributes(id, attrs));
  });
  return result;
}

const parentNodes = computed(() => relatedNodesByDirection("parent"));
const childNodes = computed(() => relatedNodesByDirection("child"));
const isActiveNodePinned = computed(() => Boolean(
  activeNode.value && pinnedNodeIds.value.includes(activeNode.value.id),
));

const currentViewTitle = computed(() => {
  const stack = stackOptions.find(item => item.value === selectedStack.value)?.label || "全部方向";
  const level = levelOptions.find(item => item.value === selectedLevel.value)?.label || "全部级别";
  return `${stack} · ${level} · ${selectedType.value === "all" ? "全层级" : typeMeta[selectedType.value].label}`;
});

async function handleNodeClick(node: GraphNode | null) {
  activeNode.value = node;
  if (node) await expandNodeScope(node, node.type === "TechPoint" || node.type === "KnowledgePoint" ? 5 : 3);
}

async function generateDeepCandidates() {
  try {
    await graphTasks.startEnrichment();
    ElMessage.success("L4/L5 候选生成任务已提交，可继续使用当前页面");
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "L4/L5 候选生成失败");
  }
}

async function expandNodeScope(node: GraphNode, maxLayer: 3 | 5) {
  if (!masterGraph.value) return;
  const scope = `${node.id}:${maxLayer}`;
  if (expandedScopes.has(scope)) return;
  expandingNodeId.value = node.id;
  try {
    const response = await getNodeNeighbors(node.id, { page_size: 60, max_layer: maxLayer });
    const merged = buildGraphFromSubgraph(response, masterGraph.value);
    masterGraph.value = merged.copy();
    applyLayerFilter();
    expandedScopes.add(scope);
    if (response.has_more) ElMessage.info("该节点还有更多关联内容，可继续按需展开");
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "节点扩展失败");
  } finally {
    expandingNodeId.value = "";
  }
}

async function expandSelectedDeep() {
  if (activeNode.value) await expandNodeScope(activeNode.value, 5);
}

function handleNodePin(nodeId: string, pinned: boolean) {
  if (pinned) {
    pinnedNodeIds.value = [nodeId];
  } else {
    pinnedNodeIds.value = pinnedNodeIds.value.filter(id => id !== nodeId);
  }
}

function toggleActiveNodePin() {
  if (!activeNode.value) return;
  const pinned = !pinnedNodeIds.value.includes(activeNode.value.id);
  handleNodePin(activeNode.value.id, pinned);
}

function handleRelatedNodeClick(node: GraphNode) {
  activeNode.value = node;
  expandNodeScope(node, 3);
}

function applyLayerFilter() {
  if (!masterGraph.value) {
    currentGraph.value = null;
    return;
  }
  const graph = masterGraph.value.copy();
  if (selectedType.value !== "all") {
    const hiddenIds: string[] = [];
    graph.forEachNode((nodeId, attrs) => {
      if (attrs.type !== selectedType.value) hiddenIds.push(nodeId);
    });
    hiddenIds.forEach(nodeId => graph.dropNode(nodeId));
  }
  currentGraph.value = graph;
  if (activeNode.value && !graph.hasNode(activeNode.value.id)) activeNode.value = null;
}

async function selectLayer(type: GraphType) {
  selectedType.value = selectedType.value === type ? "all" : type;
  await loadGraph();
}

let filterTimer: ReturnType<typeof setTimeout> | undefined;
watch([keyword, selectedStack, selectedLevel], () => {
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
  align-items: stretch;
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
.graph-canvas-card,
.graph-detail-card {
  height: 674px;
}

.graph-side-card,
.graph-detail-card {
  padding: 18px;
  overflow: hidden;
}

.graph-detail-card {
  display: flex;
  min-height: 0;
  flex-direction: column;
}

.graph-detail-content {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  margin-top: 12px;
  padding-right: 8px;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
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

.deep-expand-btn {
  width: 100%;
  margin-top: 14px;
}

.knowledge-more-btn { width: 100%; margin-top: 14px; }

:global(.knowledge-dialog .el-dialog__body) { padding-top: 8px; }
.knowledge-dialog-body h2 { margin: 6px 0 12px; color: var(--text-primary); font-size: 24px; }
.knowledge-dialog-body section { margin-top: 22px; }
.knowledge-dialog-body h3 { margin: 0 0 10px; font-size: 15px; }
.knowledge-dialog-kicker { color: var(--color-brand); font-weight: 700; }
.knowledge-dialog-description { margin: 0; color: var(--text-secondary); line-height: 1.8; white-space: pre-wrap; }
.knowledge-solution-card { margin-top: 10px; padding: 14px; border: 1px solid var(--color-border-light); border-radius: 12px; background: var(--color-bg-muted); }
.knowledge-solution-card p { margin: 6px 0 0; color: var(--text-secondary); line-height: 1.65; }
.knowledge-dialog-meta { display: flex; flex-wrap: wrap; gap: 10px 18px; padding-top: 16px; border-top: 1px solid var(--color-border-light); color: var(--text-muted); font-size: 13px; }

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
  display: flex;
  min-height: 0;
  flex-direction: column;
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
  min-height: 0;
  flex: 1;
}

.graph-detail-head {
  margin-top: 0;
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
  max-height: 104px;
  margin-top: 8px;
  padding-right: 4px;
  overflow-y: auto;
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

.pin-toggle-btn {
  margin-top: 8px;
}

.knowledge-detail > p {
  margin-top: 8px;
  padding: 10px 11px;
  border-left: 3px solid var(--color-brand);
  border-radius: 0 8px 8px 0;
  background: var(--color-bg-muted);
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.65;
}

.knowledge-detail dl {
  display: grid;
  gap: 6px;
  margin-top: 8px;
}

.knowledge-detail dl > div {
  display: grid;
  grid-template-columns: 64px 1fr;
  gap: 8px;
  font-size: 12px;
}

.knowledge-detail dt { color: var(--text-muted); }
.knowledge-detail dd { margin: 0; color: var(--text-secondary); }

.graph-task-progress {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) minmax(280px, 42%);
  align-items: center;
  gap: 24px;
  margin: 12px 0;
  padding: 14px 18px;
  border: 1px solid rgba(79, 110, 246, 0.22);
  border-radius: var(--radius-lg);
  background: linear-gradient(100deg, #f5f7ff, #fff);
}

.graph-task-progress strong,
.graph-task-progress span { display: block; }
.graph-task-progress span { margin-top: 4px; color: var(--text-muted); font-size: 13px; }

.knowledge-block { margin-top: 12px; }
.knowledge-block > strong { color: var(--text-primary); font-size: 13px; }
.knowledge-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 7px; }
.knowledge-tags span {
  padding: 4px 8px; border-radius: 999px; background: var(--color-brand-light);
  color: var(--color-brand); font-size: 12px;
}
.knowledge-block article { margin-top: 7px; padding: 9px; border-radius: 8px; background: var(--color-bg-muted); }
.knowledge-block article b { font-size: 12px; }
.knowledge-block article p { margin: 3px 0 0; color: var(--text-muted); font-size: 12px; line-height: 1.55; }

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

.graph-related-list {
  min-height: 0;
  flex: none;
  padding-right: 4px;
  overflow: visible;
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
  min-height: 0;
  flex: 1;
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
    height: min(420px, 58vh);
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

  .graph-side-card {
    height: auto;
  }

  .graph-canvas-card {
    height: 674px;
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
