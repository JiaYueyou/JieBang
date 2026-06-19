<template>
  <div>
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
        <span>{{ filteredNodes.length }} 节点</span>
        <span>{{ filteredEdges.length }} 边</span>
        <span>{{ activeNode?.frequency ?? activeNode?.importance ?? "-" }} 热度</span>
      </div>
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
            @click="selectedType = selectedType === layer.type ? 'all' : layer.type"
          >
            <span class="graph-layer-dot" :style="{ background: layer.color }"></span>
            <span>{{ layer.label }}</span>
            <em>{{ layer.desc }}</em>
          </button>
        </div>

        <div class="graph-card-title with-gap">图谱查询能力</div>
        <div class="graph-api-list">
          <span>panorama：全景过滤</span>
          <span>node：节点详情</span>
          <span>expand：展开子树</span>
          <span>search：模糊搜索</span>
          <span>path：路径高亮</span>
        </div>
      </aside>

      <main class="graph-canvas-card">
        <div class="graph-canvas-head">
          <div>
            <span class="graph-canvas-label">当前视图</span>
            <h3>{{ currentViewTitle }}</h3>
          </div>
          <div class="graph-mini-legend">
            <span><i class="solid"></i> 层级关系</span>
            <span><i class="dashed"></i> 跨树共享</span>
          </div>
        </div>

        <div class="graph-canvas">
          <svg viewBox="0 0 920 520" role="img" aria-label="技能图谱可视化">
            <defs>
              <filter id="graphGlow" x="-40%" y="-40%" width="180%" height="180%">
                <feGaussianBlur stdDeviation="4" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            <g class="graph-svg-grid">
              <path v-for="line in 8" :key="`h-${line}`" :d="`M 0 ${line * 64} H 920`" />
              <path v-for="line in 12" :key="`v-${line}`" :d="`M ${line * 76} 0 V 520`" />
            </g>

            <g>
              <line
                v-for="edge in filteredEdges"
                :key="edge.id"
                :x1="nodeMap[edge.source]?.x"
                :y1="nodeMap[edge.source]?.y"
                :x2="nodeMap[edge.target]?.x"
                :y2="nodeMap[edge.target]?.y"
                class="graph-edge"
                :class="{ weak: edge.relation === 'RELATED_TO' || edge.relation === 'SAME_AS', active: isActiveEdge(edge) }"
              />
            </g>

            <g>
              <g
                v-for="node in filteredNodes"
                :key="node.id"
                :transform="`translate(${node.x}, ${node.y})`"
              >
                <g
                  class="graph-node"
                  :class="{ active: node.id === activeNodeId, dimmed: !isNodeHighlighted(node) }"
                  @click="activeNodeId = node.id"
                >
                  <circle
                    :r="nodeRadius(node)"
                    :fill="typeMeta[node.type].color"
                    :filter="node.id === activeNodeId ? 'url(#graphGlow)' : undefined"
                  />
                  <circle :r="nodeRadius(node) + 8" class="graph-node-ring" />
                  <text text-anchor="middle" :y="nodeRadius(node) + 22">{{ node.name }}</text>
                  <text text-anchor="middle" y="5" class="graph-node-layer">{{ typeMeta[node.type].short }}</text>
                </g>
              </g>
            </g>
          </svg>
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
              @click="activeNodeId = node.id"
            >
              <span :style="{ background: typeMeta[node.type].color }"></span>
              {{ node.name }}
            </button>
            <em v-if="relatedNodes.length === 0">暂无直接关联节点</em>
          </div>
        </template>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { Search } from "@element-plus/icons-vue";

type GraphType = "Job" | "SkillArea" | "TechStack" | "TechPoint" | "KnowledgePoint";
type FilterType = GraphType | "all";
type StackType = "all" | "ai" | "backend" | "data" | "devops";
type LevelType = "all" | "junior" | "middle" | "senior";

interface GraphNode {
  id: string;
  name: string;
  type: GraphType;
  stack: StackType;
  level: Exclude<LevelType, "all">;
  x: number;
  y: number;
  description: string;
  importance?: number;
  frequency?: number;
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relation: "REQUIRES_AREA" | "CONTAINS" | "REFINES_TO" | "HAS_KNOWLEDGE" | "RELATED_TO" | "SAME_AS";
}

const keyword = ref("");
const selectedStack = ref<StackType>("all");
const selectedLevel = ref<LevelType>("all");
const selectedType = ref<FilterType>("all");
const activeNodeId = ref("job-ai");

const typeMeta: Record<GraphType, { label: string; short: string; color: string }> = {
  Job: { label: "L1 岗位", short: "L1", color: "var(--g6-l1)" },
  SkillArea: { label: "L2 技能领域", short: "L2", color: "var(--g6-l2)" },
  TechStack: { label: "L3 技术栈", short: "L3", color: "var(--g6-l3)" },
  TechPoint: { label: "L4 技术细节点", short: "L4", color: "var(--g6-l4)" },
  KnowledgePoint: { label: "L5 知识要点", short: "L5", color: "var(--g6-l5)" },
};

const layers = [
  { type: "Job" as GraphType, label: "Job", desc: "岗位", color: "var(--g6-l1)" },
  { type: "SkillArea" as GraphType, label: "SkillArea", desc: "技能领域", color: "var(--g6-l2)" },
  { type: "TechStack" as GraphType, label: "TechStack", desc: "技术栈", color: "var(--g6-l3)" },
  { type: "TechPoint" as GraphType, label: "TechPoint", desc: "技术细节点", color: "var(--g6-l4)" },
  { type: "KnowledgePoint" as GraphType, label: "KnowledgePoint", desc: "知识要点", color: "var(--g6-l5)" },
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

const graphNodes: GraphNode[] = [
  { id: "job-ai", name: "AI 应用开发", type: "Job", stack: "ai", level: "senior", x: 115, y: 124, importance: 0.94, description: "面向企业知识库、智能问答和业务 Agent 的 AI 应用岗位。" },
  { id: "job-java", name: "Java 高级开发", type: "Job", stack: "backend", level: "senior", x: 115, y: 260, importance: 0.88, description: "负责后端服务、微服务架构与业务平台稳定性建设。" },
  { id: "job-data", name: "大数据工程师", type: "Job", stack: "data", level: "middle", x: 115, y: 396, importance: 0.82, description: "负责数据采集、数仓建模、离线与实时计算链路。" },

  { id: "area-llm", name: "大模型应用", type: "SkillArea", stack: "ai", level: "senior", x: 300, y: 92, importance: 0.95, description: "围绕 LLM API、Agent、RAG 与模型应用工程化的能力域。" },
  { id: "area-service", name: "服务架构", type: "SkillArea", stack: "backend", level: "senior", x: 300, y: 238, importance: 0.89, description: "高并发后端服务、微服务拆分与稳定性治理能力域。" },
  { id: "area-pipeline", name: "数据链路", type: "SkillArea", stack: "data", level: "middle", x: 300, y: 396, importance: 0.84, description: "覆盖数据接入、清洗、计算、调度与指标产出的能力域。" },

  { id: "stack-rag", name: "RAG", type: "TechStack", stack: "ai", level: "senior", x: 486, y: 72, frequency: 78, description: "检索增强生成，用于降低幻觉并绑定企业知识源。" },
  { id: "stack-agent", name: "LangChain Agent", type: "TechStack", stack: "ai", level: "senior", x: 486, y: 142, frequency: 63, description: "工具调用、任务规划和多步推理编排框架。" },
  { id: "stack-spring", name: "Spring Cloud", type: "TechStack", stack: "backend", level: "senior", x: 486, y: 238, frequency: 86, description: "Java 微服务体系，覆盖注册发现、配置、网关和服务治理。" },
  { id: "stack-redis", name: "Redis", type: "TechStack", stack: "backend", level: "middle", x: 486, y: 310, frequency: 74, description: "缓存、分布式锁、限流和高性能数据结构。" },
  { id: "stack-flink", name: "Flink", type: "TechStack", stack: "data", level: "middle", x: 486, y: 396, frequency: 58, description: "实时计算引擎，适合流式指标、实时风控和数据管道。" },

  { id: "point-vector", name: "向量检索", type: "TechPoint", stack: "ai", level: "senior", x: 674, y: 64, frequency: 51, description: "Embedding、召回、重排和向量数据库查询优化。" },
  { id: "point-prompt", name: "Prompt 编排", type: "TechPoint", stack: "ai", level: "middle", x: 674, y: 146, frequency: 67, description: "提示模板、上下文注入、输出约束和评测闭环。" },
  { id: "point-gateway", name: "网关治理", type: "TechPoint", stack: "backend", level: "senior", x: 674, y: 224, frequency: 46, description: "鉴权、限流、灰度、熔断和链路追踪入口治理。" },
  { id: "point-cache", name: "缓存一致性", type: "TechPoint", stack: "backend", level: "middle", x: 674, y: 310, frequency: 55, description: "缓存穿透、击穿、雪崩与数据一致性策略。" },
  { id: "point-window", name: "窗口计算", type: "TechPoint", stack: "data", level: "middle", x: 674, y: 396, frequency: 39, description: "滚动窗口、滑动窗口、会话窗口及水位线机制。" },

  { id: "knowledge-rerank", name: "召回与重排评估", type: "KnowledgePoint", stack: "ai", level: "senior", x: 836, y: 64, frequency: 32, description: "评估检索命中率、MRR、上下文覆盖率和答案引用质量。" },
  { id: "knowledge-template", name: "结构化输出约束", type: "KnowledgePoint", stack: "ai", level: "middle", x: 836, y: 146, frequency: 44, description: "通过 JSON schema、few-shot 和校验器约束模型输出。" },
  { id: "knowledge-resilience", name: "熔断降级策略", type: "KnowledgePoint", stack: "backend", level: "senior", x: 836, y: 224, frequency: 36, description: "高可用系统中的超时、重试、隔离和降级设计。" },
  { id: "knowledge-cache", name: "热点 Key 治理", type: "KnowledgePoint", stack: "backend", level: "middle", x: 836, y: 310, frequency: 42, description: "热点发现、本地缓存、分片和预热策略。" },
  { id: "knowledge-watermark", name: "Watermark 机制", type: "KnowledgePoint", stack: "data", level: "middle", x: 836, y: 396, frequency: 28, description: "处理乱序数据、延迟数据和窗口触发语义。" },
];

const graphEdges: GraphEdge[] = [
  { id: "e1", source: "job-ai", target: "area-llm", relation: "REQUIRES_AREA" },
  { id: "e2", source: "job-java", target: "area-service", relation: "REQUIRES_AREA" },
  { id: "e3", source: "job-data", target: "area-pipeline", relation: "REQUIRES_AREA" },
  { id: "e4", source: "area-llm", target: "stack-rag", relation: "CONTAINS" },
  { id: "e5", source: "area-llm", target: "stack-agent", relation: "CONTAINS" },
  { id: "e6", source: "area-service", target: "stack-spring", relation: "CONTAINS" },
  { id: "e7", source: "area-service", target: "stack-redis", relation: "CONTAINS" },
  { id: "e8", source: "area-pipeline", target: "stack-flink", relation: "CONTAINS" },
  { id: "e9", source: "stack-rag", target: "point-vector", relation: "REFINES_TO" },
  { id: "e10", source: "stack-agent", target: "point-prompt", relation: "REFINES_TO" },
  { id: "e11", source: "stack-spring", target: "point-gateway", relation: "REFINES_TO" },
  { id: "e12", source: "stack-redis", target: "point-cache", relation: "REFINES_TO" },
  { id: "e13", source: "stack-flink", target: "point-window", relation: "REFINES_TO" },
  { id: "e14", source: "point-vector", target: "knowledge-rerank", relation: "HAS_KNOWLEDGE" },
  { id: "e15", source: "point-prompt", target: "knowledge-template", relation: "HAS_KNOWLEDGE" },
  { id: "e16", source: "point-gateway", target: "knowledge-resilience", relation: "HAS_KNOWLEDGE" },
  { id: "e17", source: "point-cache", target: "knowledge-cache", relation: "HAS_KNOWLEDGE" },
  { id: "e18", source: "point-window", target: "knowledge-watermark", relation: "HAS_KNOWLEDGE" },
  { id: "e19", source: "stack-rag", target: "stack-redis", relation: "RELATED_TO" },
  { id: "e20", source: "point-vector", target: "point-cache", relation: "SAME_AS" },
];

const nodeMap = computed(() => Object.fromEntries(graphNodes.map(node => [node.id, node])));

const filteredNodes = computed(() => {
  const text = keyword.value.trim().toLowerCase();
  return graphNodes.filter((node) => {
    const matchesStack = selectedStack.value === "all" || node.stack === selectedStack.value;
    const matchesLevel = selectedLevel.value === "all" || node.level === selectedLevel.value;
    const matchesType = selectedType.value === "all" || node.type === selectedType.value;
    const matchesKeyword = !text || [node.name, node.description, node.type, node.stack, node.level]
      .join(" ")
      .toLowerCase()
      .includes(text);
    return matchesStack && matchesLevel && matchesType && matchesKeyword;
  });
});

const visibleIds = computed(() => new Set(filteredNodes.value.map(node => node.id)));

const filteredEdges = computed(() => graphEdges.filter(edge => visibleIds.value.has(edge.source) && visibleIds.value.has(edge.target)));

const activeNode = computed(() => graphNodes.find(node => node.id === activeNodeId.value) || filteredNodes.value[0]);

const relatedNodes = computed(() => {
  if (!activeNode.value) return [];
  const ids = graphEdges
    .filter(edge => edge.source === activeNode.value?.id || edge.target === activeNode.value?.id)
    .map(edge => edge.source === activeNode.value?.id ? edge.target : edge.source);
  return graphNodes.filter(node => ids.includes(node.id));
});

const currentViewTitle = computed(() => {
  const stack = stackOptions.find(item => item.value === selectedStack.value)?.label || "全部方向";
  const level = levelOptions.find(item => item.value === selectedLevel.value)?.label || "全部级别";
  return `${stack} · ${level} · ${selectedType.value === "all" ? "全层级" : typeMeta[selectedType.value].label}`;
});

function nodeRadius(node: GraphNode) {
  const radiusMap: Record<GraphType, number> = {
    Job: 30,
    SkillArea: 25,
    TechStack: 22,
    TechPoint: 19,
    KnowledgePoint: 16,
  };
  return radiusMap[node.type];
}

function isActiveEdge(edge: GraphEdge) {
  return edge.source === activeNode.value?.id || edge.target === activeNode.value?.id;
}

function isNodeHighlighted(node: GraphNode) {
  if (!activeNode.value) return true;
  if (node.id === activeNode.value.id) return true;
  return relatedNodes.value.some(item => item.id === node.id);
}
</script>

<style scoped>
.graph-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 18px;
  margin-bottom: 16px;
  padding: 24px;
  border: 1px solid rgba(79,110,246,.20);
  border-radius: var(--radius-lg);
  background:
    radial-gradient(circle at 18% 12%, rgba(79,110,246,.18), transparent 34%),
    radial-gradient(circle at 82% 16%, rgba(52,179,126,.16), transparent 30%),
    linear-gradient(135deg, #10172a, #17203a 46%, #f8fafc 46.2%, var(--color-bg-elevated));
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.graph-kicker {
  display: inline-flex;
  margin-bottom: 10px;
  color: #a9bbff;
  font-family: var(--font-mono);
  font-size: 14px;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.graph-hero-main h2 {
  max-width: 620px;
  color: #fff;
  font-size: 26px;
  line-height: 1.25;
  letter-spacing: -.03em;
}

.graph-hero-main p {
  max-width: 660px;
  margin-top: 12px;
  color: rgba(255,255,255,.72);
  font-size: 14px;
}

.graph-hero-main code {
  color: #dbe4ff;
  font-family: var(--font-mono);
}

.graph-hero-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  align-self: end;
}

.graph-stat {
  padding: 16px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  background: rgba(255,255,255,.82);
  backdrop-filter: blur(14px);
}

.graph-stat strong {
  display: block;
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 24px;
  line-height: 1;
}

.graph-stat span {
  display: block;
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 14px;
}

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
  border-bottom: 1px solid rgba(255,255,255,.08);
  background: #111827;
}

.graph-canvas-label {
  color: rgba(255,255,255,.48);
  font-size: 14px;
}

.graph-canvas-head h3 {
  margin-top: 2px;
  color: #fff;
  font-size: 16px;
}

.graph-mini-legend {
  display: flex;
  gap: 12px;
  color: rgba(255,255,255,.60);
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
  border-top: 2px solid rgba(255,255,255,.45);
}

.graph-mini-legend i.dashed {
  border-top-style: dashed;
}

.graph-canvas {
  background:
    radial-gradient(circle at 50% 20%, rgba(79,110,246,.18), transparent 34%),
    linear-gradient(180deg, #111827, #0b1020);
}

.graph-canvas svg {
  display: block;
  width: 100%;
  min-height: 540px;
}

.graph-svg-grid path {
  stroke: rgba(255,255,255,.045);
  stroke-width: 1;
}

.graph-edge {
  stroke: rgba(174,190,255,.30);
  stroke-width: 2.5;
  transition: all var(--duration-fast) var(--ease-out);
}

.graph-edge.weak {
  stroke-dasharray: 8 8;
  stroke: rgba(52,179,126,.36);
}

.graph-edge.active {
  stroke: #dbe4ff;
  stroke-width: 4;
}

@keyframes nodeFloat {
  0%, 100% { transform: translateY(0); }
  50%      { transform: translateY(-3px); }
}

.graph-node {
  cursor: pointer;
  transition: opacity var(--duration-fast) var(--ease-out);
  animation: nodeFloat 4s ease-in-out infinite;
}
.graph-node:nth-child(3n)   { animation-delay: 0s; }
.graph-node:nth-child(3n+1) { animation-delay: 1.3s; }
.graph-node:nth-child(3n+2) { animation-delay: 2.7s; }
.graph-node:hover { animation-play-state: paused; }

.graph-node.dimmed {
  opacity: .38;
}

.graph-node circle:first-child {
  stroke: rgba(255,255,255,.78);
  stroke-width: 2;
}

.graph-node-ring {
  fill: transparent;
  stroke: rgba(255,255,255,.12);
  stroke-width: 1;
}

.graph-node.active .graph-node-ring {
  stroke: #fff;
  stroke-width: 2;
}

.graph-node text {
  fill: rgba(255,255,255,.82);
  font-size: 14px;
  font-weight: 700;
  paint-order: stroke;
  stroke: rgba(11,16,32,.80);
  stroke-width: 4px;
}

.graph-node-layer {
  fill: #fff !important;
  font-size: 14px !important;
  font-family: var(--font-mono);
  stroke: transparent !important;
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

@media (max-width: 1280px) {
  .graph-layout {
    grid-template-columns: 220px minmax(0, 1fr);
  }

  .graph-detail-card {
    grid-column: 1 / -1;
  }
}

@media (max-width: 960px) {
  .graph-hero,
  .graph-toolbar,
  .graph-layout {
    grid-template-columns: 1fr;
  }

  .graph-hero-stats {
    grid-template-columns: repeat(3, 1fr);
  }

  .graph-filter-group {
    overflow-x: auto;
  }
}

@media (max-width: 640px) {
  .graph-hero-stats,
  .graph-detail-grid {
    grid-template-columns: 1fr;
  }

  .graph-mini-legend {
    display: none;
  }
}
</style>
