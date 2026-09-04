/**
 * 管理决策端 Mock 数据集 —— 纯前端演示，无后端依赖。
 * 数据形态对齐 fyz-src 管理与决策端（Dashboard / JobManagement / GraphView / Trends / Admin）。
 */

export type JobCategory = 'emerging' | 'existing'
export type JobStatus = '在招' | '急缺' | '评估中' | '已下线'

export interface AdminJob {
  id: string
  name: string
  category: JobCategory
  status: JobStatus
  salary: string
  city: string
  seats: number
  talentPool: number
  sources: number
  updatedAt: string
  summary: string
  duties: string[]
  skills: { name: string; level: '必备' | '加分' | '精通' }[]
}

export interface KpiItem {
  key: string
  label: string
  value: number
  delta: string
  trend: 'up' | 'down'
  unit?: string
}

/* ── 工作台 KPI ── */
export const kpis: KpiItem[] = [
  { key: 'jobs', label: '管理岗位', value: 1284, delta: '+6.2%', trend: 'up' },
  { key: 'seats', label: '需求席位', value: 316, delta: '+12', trend: 'up', unit: '席' },
  { key: 'pool', label: '当前人才池', value: 4720, delta: '+3.8%', trend: 'up' },
  { key: 'review', label: '待审核事实', value: 12, delta: '-3', trend: 'down' },
]

/* ── 近 30 天趋势（岗位入库 / 匹配评估） ── */
export const trendDays = ['08-06', '08-09', '08-12', '08-15', '08-18', '08-21', '08-24', '08-27', '08-30', '09-02']
export const trendJobs = [42, 58, 51, 76, 69, 88, 95, 84, 108, 121]
export const trendMatches = [18, 26, 31, 24, 40, 36, 52, 61, 58, 73]

/* ── 待办事项 ── */
export interface TodoItem {
  key: string
  title: string
  desc: string
  count: number
  tone: 'danger' | 'warning' | 'brand' | 'success'
  path?: string
}
export const todos: TodoItem[] = [
  { key: 'review', title: '图谱审核', desc: '技能事实待审核入库', count: 12, tone: 'warning', path: '/pages/profile/profile' },
  { key: 'import', title: '数据导入', desc: '1 个数据源校验完成待发布', count: 1, tone: 'brand' },
  { key: 'urgent', title: '急缺岗位', desc: '需求席位缺口超过 50%', count: 4, tone: 'danger', path: '/pages/positions/positions' },
]

/* ── 最近动态 ── */
export interface ActivityItem {
  id: number
  time: string
  actor: string
  action: string
  target: string
  tone: 'brand' | 'success' | 'warning'
}
export const activities: ActivityItem[] = [
  { id: 1, time: '09:42', actor: '系统', action: '完成每日图谱同步', target: 'namespace=jiebang', tone: 'success' },
  { id: 2, time: '09:15', actor: 'admin', action: '确认入图发布', target: '技能「向量检索」· L4', tone: 'brand' },
  { id: 3, time: '08:50', actor: '数据管线', action: '新增岗位快照', target: 'jd_crawl_ifly · 86 条', tone: 'brand' },
  { id: 4, time: '08:23', actor: 'admin', action: '驳回技能合并', target: '「K8s」与「Kubernetes」重复', tone: 'warning' },
  { id: 5, time: '昨天', actor: '系统', action: '质量门禁通过', target: '滚动基线 v0.9.3', tone: 'success' },
]

/* ── 职位管理 ── */
export const adminJobs: AdminJob[] = [
  {
    id: 'job-101', name: '大模型应用工程师', category: 'emerging', status: '急缺', salary: '35-60K·16薪', city: '上海',
    seats: 12, talentPool: 31, sources: 4, updatedAt: '09-02 10:24',
    summary: '面向智能体与 RAG 场景的大模型应用研发，负责模型选型、检索链路与 Agent 编排的工程化落地。',
    duties: ['负责 LLM 应用架构设计与 Agent 编排链路研发', '搭建 RAG 检索增强管线并持续优化召回质量', '与算法团队协作完成模型评测与效果迭代', '建设提示词工程规范与效果基线'],
    skills: [
      { name: 'Python', level: '必备' }, { name: 'LangChain', level: '必备' }, { name: 'RAG', level: '必备' },
      { name: '向量检索', level: '必备' }, { name: 'Prompt 工程', level: '加分' }, { name: 'CUDA', level: '加分' },
    ],
  },
  {
    id: 'job-102', name: '服务端开发工程师', category: 'existing', status: '在招', salary: '28-45K·15薪', city: '北京',
    seats: 8, talentPool: 64, sources: 5, updatedAt: '09-01 18:40',
    summary: '与智能共演化，让工程即作品。构建与 AI 协同进步的软件系统，让模型智能稳定高效地驱动业务。',
    duties: ['负责核心业务服务的架构设计与研发', '建设高可用、可观测的分布式服务体系', '推动服务性能优化与稳定性治理'],
    skills: [
      { name: 'Go', level: '必备' }, { name: 'MySQL', level: '必备' }, { name: 'Redis', level: '必备' },
      { name: 'Kubernetes', level: '加分' }, { name: '消息队列', level: '加分' },
    ],
  },
  {
    id: 'job-103', name: '知识图谱算法工程师', category: 'emerging', status: '急缺', salary: '40-70K·16薪', city: '深圳',
    seats: 6, talentPool: 18, sources: 3, updatedAt: '09-02 09:12',
    summary: '负责多源异构数据驱动的岗位能力图谱构建，覆盖实体抽取、关系融合与五层技能森林建模。',
    duties: ['设计技能实体抽取与标准化流水线', '负责图谱层级建模与质量评估体系', '优化关系抽取与实体对齐算法'],
    skills: [
      { name: 'Neo4j', level: '必备' }, { name: 'NLP', level: '必备' }, { name: '实体抽取', level: '必备' },
      { name: '图算法', level: '精通' }, { name: 'Python', level: '必备' },
    ],
  },
  {
    id: 'job-104', name: '数据产品经理', category: 'existing', status: '在招', salary: '25-40K·14薪', city: '杭州',
    seats: 3, talentPool: 42, sources: 2, updatedAt: '08-31 16:05',
    summary: '负责数据智能产品的规划与落地，串联数据管线、分析洞察与业务决策场景。',
    duties: ['规划岗位智能适配产品的功能路线', '设计数据指标体系与决策看板', '协调研发、算法与业务方推进交付'],
    skills: [
      { name: 'SQL', level: '必备' }, { name: '数据分析', level: '必备' }, { name: '产品设计', level: '必备' },
      { name: 'A/B 实验', level: '加分' },
    ],
  },
  {
    id: 'job-105', name: 'AI 训练师（数据标注方向）', category: 'emerging', status: '评估中', salary: '15-25K·13薪', city: '成都',
    seats: 20, talentPool: 88, sources: 2, updatedAt: '08-30 11:32',
    summary: '负责大模型微调数据集的建设与质量把控，制定标注规范并驱动标注效能提升。',
    duties: ['制定标注规范与质检标准', '建设微调/对齐数据集', '分析badcase并反哺模型迭代'],
    skills: [
      { name: '数据标注', level: '必备' }, { name: 'Prompt 工程', level: '加分' }, { name: 'NLP 基础', level: '加分' },
    ],
  },
  {
    id: 'job-106', name: '前端开发工程师', category: 'existing', status: '在招', salary: '22-38K·14薪', city: '上海',
    seats: 5, talentPool: 76, sources: 6, updatedAt: '08-29 14:20',
    summary: '负责管理与决策端、求职者端的 Web/小程序研发，打造高质量数据可视化体验。',
    duties: ['负责 Vue 3 前端架构与组件体系建设', '开发图谱、图表等数据可视化模块', '持续优化性能与交互体验'],
    skills: [
      { name: 'Vue', level: '必备' }, { name: 'TypeScript', level: '必备' }, { name: 'ECharts', level: '加分' },
      { name: 'Canvas', level: '加分' },
    ],
  },
  {
    id: 'job-107', name: '12K网络运维工程师', category: 'existing', status: '在招', salary: '12-18K·13薪', city: '全国',
    seats: 10, talentPool: 120, sources: 3, updatedAt: '08-28 09:00',
    summary: '可食宿+带薪培养，负责 IDC 与云上网络设施的运维保障与自动化建设。',
    duties: ['负责网络设备与链路的日常运维', '建设自动化巡检与告警体系', '参与容灾演练与故障复盘'],
    skills: [
      { name: '网络协议', level: '必备' }, { name: 'Linux', level: '必备' }, { name: 'DevOps', level: '加分' },
    ],
  },
  {
    id: 'job-108', name: '多模态算法工程师', category: 'emerging', status: '急缺', salary: '45-80K·16薪', city: '北京',
    seats: 4, talentPool: 12, sources: 4, updatedAt: '09-02 08:45',
    summary: '负责图文/音视频多模态大模型的训练与推理优化，推动能力在业务场景的规模化应用。',
    duties: ['负责多模态表征学习与对齐训练', '优化推理性能并压缩部署成本', '跟踪前沿论文并快速落地验证'],
    skills: [
      { name: 'PyTorch', level: '精通' }, { name: '多模态', level: '必备' }, { name: 'CUDA', level: '加分' },
      { name: '分布式训练', level: '加分' },
    ],
  },
  {
    id: 'job-109', name: '数据仓库工程师', category: 'existing', status: '在招', salary: '25-40K·14薪', city: '深圳',
    seats: 6, talentPool: 55, sources: 4, updatedAt: '08-27 17:10',
    summary: '负责岗位与技能数据的数仓建模与治理，支撑管理决策看板与趋势分析。',
    duties: ['设计维度建模与分层治理方案', '保障数据质量与SLA', '优化ETL任务调度效率'],
    skills: [
      { name: 'Hive', level: '必备' }, { name: 'SQL', level: '精通' }, { name: 'Spark', level: '加分' },
      { name: '数据治理', level: '加分' },
    ],
  },
  {
    id: 'job-110', name: '智能体产品运营', category: 'emerging', status: '评估中', salary: '18-30K·13薪', city: '上海',
    seats: 2, talentPool: 26, sources: 1, updatedAt: '08-26 10:55',
    summary: '负责 AI 智能体产品的用户增长与内容生态运营，沉淀最佳实践案例。',
    duties: ['策划智能体使用场景与内容运营', '分析用户行为并驱动产品迭代', '建设外部合作与创作者生态'],
    skills: [
      { name: '用户增长', level: '必备' }, { name: '数据分析', level: '必备' }, { name: 'Prompt 工程', level: '加分' },
    ],
  },
]

/* ── 趋势洞察 ── */
export interface SkillTrend {
  name: string
  score: number
  delta: number
  lifecycle: '上升期' | '成熟期' | '萌芽期'
  sources: number
}
export const skillTrends: SkillTrend[] = [
  { name: '大模型应用', score: 96, delta: 8.4, lifecycle: '上升期', sources: 12 },
  { name: 'RAG', score: 91, delta: 11.2, lifecycle: '上升期', sources: 9 },
  { name: 'Agent 编排', score: 85, delta: 14.6, lifecycle: '上升期', sources: 7 },
  { name: '向量检索', score: 82, delta: 6.8, lifecycle: '上升期', sources: 8 },
  { name: 'Python', score: 78, delta: 1.2, lifecycle: '成熟期', sources: 15 },
  { name: 'Prompt 工程', score: 71, delta: 9.5, lifecycle: '萌芽期', sources: 6 },
  { name: 'Kubernetes', score: 66, delta: -0.8, lifecycle: '成熟期', sources: 11 },
  { name: '数据治理', score: 58, delta: 2.4, lifecycle: '成熟期', sources: 5 },
  { name: '多模态对齐', score: 52, delta: 16.3, lifecycle: '萌芽期', sources: 4 },
  { name: '传统ETL', score: 44, delta: -3.1, lifecycle: '成熟期', sources: 6 },
]

export const cityHeat = [
  { name: '上海', value: 312 },
  { name: '北京', value: 286 },
  { name: '深圳', value: 241 },
  { name: '杭州', value: 198 },
  { name: '成都', value: 154 },
]

export const categoryDonut = [
  { name: '既有岗位', value: 62, color: '#2f47b8' },
  { name: '新兴岗位', value: 38, color: '#7c6ff7' },
]

/* ── 管理中心 ── */
export interface ReviewStat { label: string; count: number; tone: 'warning' | 'success' | 'danger' }
export const reviewStats: ReviewStat[] = [
  { label: '待审核', count: 12, tone: 'warning' },
  { label: '已确认', count: 48, tone: 'success' },
  { label: '已驳回', count: 3, tone: 'danger' },
]

export interface ImportSource {
  id: number
  name: string
  file: string
  records: number
  status: '校验完成' | '已入库' | '同步中'
  time: string
}
export const importSources: ImportSource[] = [
  { id: 1, name: '讯飞招聘数据', file: 'jd_crawl_ifly.json', records: 86, status: '校验完成', time: '09-02 08:50' },
  { id: 2, name: '智联招聘数据', file: 'jd_crawl_zl.json', records: 132, status: '已入库', time: '09-01 21:12' },
  { id: 3, name: '自采岗位集', file: 'jd_crawl2.json', records: 54, status: '同步中', time: '09-02 09:30' },
]

export interface SystemRow { label: string; value: string; ok: boolean }
export const systemStatus: SystemRow[] = [
  { label: '质量门禁', value: '通过 · v0.9.3', ok: true },
  { label: '滚动基线', value: '2026-09-02 核验', ok: true },
  { label: '趋势验收', value: '8/9 通过 · 1 项观察', ok: true },
  { label: 'Neo4j 图谱同步', value: '6 小时前', ok: true },
  { label: 'Celery 队列', value: '2 个任务运行中', ok: true },
]

export interface AuditLog {
  id: number
  time: string
  user: string
  action: string
  detail: string
}
export const auditLogs: AuditLog[] = [
  { id: 1, time: '09-02 10:24', user: 'admin', action: '入图发布', detail: '技能「向量检索」L4 节点合并' },
  { id: 2, time: '09-02 09:15', user: 'reviewer1', action: '事实审核', detail: '确认 6 条技能事实' },
  { id: 3, time: '09-01 18:40', user: 'admin', action: '驳回', detail: '「K8s」与「Kubernetes」合并申请：证据不足' },
  { id: 4, time: '09-01 16:02', user: 'system', action: '自动同步', detail: 'MySQL → Neo4j 增量同步 1284 节点' },
  { id: 5, time: '09-01 10:30', user: 'admin', action: '账号管理', detail: '新建账号 reviewer1（图谱审核员）' },
]

export interface AdminUser {
  id: number
  username: string
  role: '超级管理员' | '图谱审核员' | '数据运营'
  lastActive: string
  active: boolean
}
export const adminUsers: AdminUser[] = [
  { id: 1, username: 'admin', role: '超级管理员', lastActive: '刚刚', active: true },
  { id: 2, username: 'reviewer1', role: '图谱审核员', lastActive: '2 小时前', active: true },
  { id: 3, username: 'reviewer2', role: '图谱审核员', lastActive: '昨天', active: true },
  { id: 4, username: 'ops01', role: '数据运营', lastActive: '3 天前', active: false },
]

/* ── 五层技能图谱（供 SkillGraph 组件，shape 对齐 GraphView） ── */
export interface MockGraphNode {
  id: string
  label: string
  type: 'root' | 'position' | 'domain_branch' | 'skillset_branch' | 'knowledge'
  layer: 1 | 2 | 3 | 4 | 5
  root_id: string
}
export interface MockGraphEdge {
  source: string
  target: string
  relation: string
  weight: number
}

export const graphNodes: MockGraphNode[] = [
  { id: 'root', label: '岗位能力图谱', type: 'root', layer: 1, root_id: 'root' },

  { id: 'pos-ai', label: '大模型应用', type: 'position', layer: 2, root_id: 'root' },
  { id: 'pos-graph', label: '知识图谱', type: 'position', layer: 2, root_id: 'root' },
  { id: 'pos-server', label: '服务端研发', type: 'position', layer: 2, root_id: 'root' },
  { id: 'pos-data', label: '数据工程', type: 'position', layer: 2, root_id: 'root' },

  { id: 'dom-agent', label: '智能体', type: 'domain_branch', layer: 3, root_id: 'root' },
  { id: 'dom-llm', label: '模型工程', type: 'domain_branch', layer: 3, root_id: 'root' },
  { id: 'dom-kg', label: '图谱构建', type: 'domain_branch', layer: 3, root_id: 'root' },
  { id: 'dom-infra', label: '基础设施', type: 'domain_branch', layer: 3, root_id: 'root' },
  { id: 'dom-dw', label: '数仓治理', type: 'domain_branch', layer: 3, root_id: 'root' },
  { id: 'dom-web', label: '业务研发', type: 'domain_branch', layer: 3, root_id: 'root' },

  { id: 'ss-rag', label: 'RAG 链路', type: 'skillset_branch', layer: 4, root_id: 'root' },
  { id: 'ss-orch', label: 'Agent 编排', type: 'skillset_branch', layer: 4, root_id: 'root' },
  { id: 'ss-train', label: '训练与对齐', type: 'skillset_branch', layer: 4, root_id: 'root' },
  { id: 'ss-serve', label: '推理服务', type: 'skillset_branch', layer: 4, root_id: 'root' },
  { id: 'ss-extract', label: '实体抽取', type: 'skillset_branch', layer: 4, root_id: 'root' },
  { id: 'ss-align', label: '实体对齐', type: 'skillset_branch', layer: 4, root_id: 'root' },
  { id: 'ss-k8s', label: '容器编排', type: 'skillset_branch', layer: 4, root_id: 'root' },
  { id: 'ss-db', label: '存储选型', type: 'skillset_branch', layer: 4, root_id: 'root' },
  { id: 'ss-model', label: '维度建模', type: 'skillset_branch', layer: 4, root_id: 'root' },

  { id: 'kn-emb', label: 'Embedding', type: 'knowledge', layer: 5, root_id: 'root' },
  { id: 'kn-vec', label: '向量检索', type: 'knowledge', layer: 5, root_id: 'root' },
  { id: 'kn-rerank', label: '重排序', type: 'knowledge', layer: 5, root_id: 'root' },
  { id: 'kn-tool', label: '工具调用', type: 'knowledge', layer: 5, root_id: 'root' },
  { id: 'kn-plan', label: '任务规划', type: 'knowledge', layer: 5, root_id: 'root' },
  { id: 'kn-sft', label: 'SFT', type: 'knowledge', layer: 5, root_id: 'root' },
  { id: 'kn-rlhf', label: 'RLHF', type: 'knowledge', layer: 5, root_id: 'root' },
  { id: 'kn-quant', label: '量化压缩', type: 'knowledge', layer: 5, root_id: 'root' },
  { id: 'kn-vllm', label: 'vLLM', type: 'knowledge', layer: 5, root_id: 'root' },
  { id: 'kn-ner', label: 'NER', type: 'knowledge', layer: 5, root_id: 'root' },
  { id: 'kn-re', label: '关系抽取', type: 'knowledge', layer: 5, root_id: 'root' },
  { id: 'kn-block', label: '分块策略', type: 'knowledge', layer: 5, root_id: 'root' },
  { id: 'kn-cypher', label: 'Cypher', type: 'knowledge', layer: 5, root_id: 'root' },
  { id: 'kn-helm', label: 'Helm', type: 'knowledge', layer: 5, root_id: 'root' },
  { id: 'kn-idx', label: '索引优化', type: 'knowledge', layer: 5, root_id: 'root' },
  { id: 'kn-dwd', label: 'DWD 分层', type: 'knowledge', layer: 5, root_id: 'root' },
  { id: 'kn-dim', label: '缓慢变化维', type: 'knowledge', layer: 5, root_id: 'root' },
]

export const graphEdges: MockGraphEdge[] = [
  { source: 'root', target: 'pos-ai', relation: 'contains', weight: 1 },
  { source: 'root', target: 'pos-graph', relation: 'contains', weight: 1 },
  { source: 'root', target: 'pos-server', relation: 'contains', weight: 1 },
  { source: 'root', target: 'pos-data', relation: 'contains', weight: 1 },

  { source: 'pos-ai', target: 'dom-agent', relation: 'requires', weight: 0.9 },
  { source: 'pos-ai', target: 'dom-llm', relation: 'requires', weight: 0.9 },
  { source: 'pos-graph', target: 'dom-kg', relation: 'requires', weight: 0.9 },
  { source: 'pos-server', target: 'dom-infra', relation: 'requires', weight: 0.8 },
  { source: 'pos-server', target: 'dom-web', relation: 'requires', weight: 0.7 },
  { source: 'pos-data', target: 'dom-dw', relation: 'requires', weight: 0.9 },
  { source: 'pos-data', target: 'dom-infra', relation: 'requires', weight: 0.6 },

  { source: 'dom-agent', target: 'ss-rag', relation: 'includes', weight: 0.8 },
  { source: 'dom-agent', target: 'ss-orch', relation: 'includes', weight: 0.9 },
  { source: 'dom-llm', target: 'ss-train', relation: 'includes', weight: 0.8 },
  { source: 'dom-llm', target: 'ss-serve', relation: 'includes', weight: 0.9 },
  { source: 'dom-kg', target: 'ss-extract', relation: 'includes', weight: 0.9 },
  { source: 'dom-kg', target: 'ss-align', relation: 'includes', weight: 0.8 },
  { source: 'dom-infra', target: 'ss-k8s', relation: 'includes', weight: 0.8 },
  { source: 'dom-infra', target: 'ss-db', relation: 'includes', weight: 0.7 },
  { source: 'dom-dw', target: 'ss-model', relation: 'includes', weight: 0.9 },
  { source: 'dom-web', target: 'ss-db', relation: 'includes', weight: 0.6 },

  { source: 'ss-rag', target: 'kn-emb', relation: 'depends_on', weight: 0.7 },
  { source: 'ss-rag', target: 'kn-vec', relation: 'depends_on', weight: 0.9 },
  { source: 'ss-rag', target: 'kn-rerank', relation: 'depends_on', weight: 0.7 },
  { source: 'ss-rag', target: 'kn-block', relation: 'depends_on', weight: 0.6 },
  { source: 'ss-orch', target: 'kn-tool', relation: 'depends_on', weight: 0.9 },
  { source: 'ss-orch', target: 'kn-plan', relation: 'depends_on', weight: 0.8 },
  { source: 'ss-train', target: 'kn-sft', relation: 'depends_on', weight: 0.9 },
  { source: 'ss-train', target: 'kn-rlhf', relation: 'depends_on', weight: 0.8 },
  { source: 'ss-serve', target: 'kn-quant', relation: 'depends_on', weight: 0.7 },
  { source: 'ss-serve', target: 'kn-vllm', relation: 'depends_on', weight: 0.9 },
  { source: 'ss-extract', target: 'kn-ner', relation: 'depends_on', weight: 0.9 },
  { source: 'ss-extract', target: 'kn-re', relation: 'depends_on', weight: 0.8 },
  { source: 'ss-align', target: 'kn-cypher', relation: 'depends_on', weight: 0.6 },
  { source: 'ss-k8s', target: 'kn-helm', relation: 'depends_on', weight: 0.8 },
  { source: 'ss-db', target: 'kn-idx', relation: 'depends_on', weight: 0.8 },
  { source: 'ss-model', target: 'kn-dwd', relation: 'depends_on', weight: 0.9 },
  { source: 'ss-model', target: 'kn-dim', relation: 'depends_on', weight: 0.7 },
]
