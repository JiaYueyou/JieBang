# 智联职引后端开发设计与接口规范

> 面向当前 Vue 3 全量页面的后端实施基线  
> FastAPI · MySQL · Neo4j · Redis/Celery · DeepSeek Provider

---

## 1. 文档目标与实施边界

本文档是后续数据处理、数据库设计、后端 API、知识图谱和 Agent 开发的统一规范。接口与数据类型以当前前端页面为首要依据，同时满足竞赛要求中的多源数据融合、新岗位发现、能力动态更新、图谱可视化、人岗匹配和幻觉防控闭环。

### 1.1 交付优先级

| 级别 | 范围 | 目标 |
| --- | --- | --- |
| P0 | 数据 Pipeline、岗位、图谱、趋势、简历、匹配、转岗、工作台 | 完成可演示、可量化评测的竞赛核心闭环 |
| P1 | 收藏、足迹、人才跟进、完整管理后台、日志和数据质量监控 | 覆盖当前全部前端页面和日常管理流程 |
| P2 | Elasticsearch、向量检索、SSE、告警、对象存储和生产部署增强 | 提升检索、并发、可观测性和生产可用性 |

### 1.2 技术基线

- DeepSeek 是首期默认模型，但业务代码只能依赖 `LLMProvider`，不得直接依赖具体 SDK。
- MySQL 保存业务状态、流程、版本、来源、审计和可统计数据。
- Neo4j 保存岗位五层能力森林及语义关系，不承担用户工作流状态管理。
- Redis + Celery 处理爬虫、文件解析、批量技能抽取、图谱写入、快照和趋势计算。
- Elasticsearch、ChromaDB 或其他向量库不作为 P0/P1 的运行前置条件。
- 正式数据库结构使用 Alembic 管理；应用启动时 `create_all` 仅保留给测试或本地初始化。
- 文件首期存入可配置本地目录，通过存储接口隔离，后续可切换对象存储。

### 1.3 非目标

- P0 不建设复杂微服务体系，后端保持单体分层架构。
- P0 不训练自有大模型，优先使用规则、词典、图谱与可替换 LLM 组合。
- P0 不自动向第三方招聘网站发布岗位，只提供内部发布和可复制的结构化 JD。

---

## 2. 总体架构

```text
Vue 3 页面
   │ REST / multipart / 文件下载
   ▼
FastAPI API 层
   │ 认证、参数校验、响应封装、权限控制
   ▼
Service 领域服务层
   ├── 业务服务：岗位、简历、匹配、转岗、收藏、足迹、管理
   ├── 分析服务：能力变更、新岗位发现、趋势、数据质量
   ├── 图谱服务：Neo4j 查询、增量写入、快照
   └── Agent 服务：Provider、Prompt、结构化校验、事实核验
   │
   ├───────────────┬──────────────────┬─────────────────┐
   ▼               ▼                  ▼                 ▼
MySQL           Neo4j            Redis/Celery       文件存储
业务与审计       五层能力图谱       长任务与调度        简历/报告原件
```

### 2.1 推荐后端目录

```text
fyz-src/backend/app/
├── api/v1/                 # 路由，只负责协议转换
├── core/                   # 配置、数据库、鉴权、异常、日志、Celery
├── models/                 # SQLAlchemy 模型
├── schemas/                # Pydantic 请求/响应 DTO
├── repositories/           # MySQL 数据访问
├── services/               # 领域服务
├── agents/                 # Provider、Prompt、Agent 编排
├── graph/                  # Neo4j 查询与写入
├── tasks/                  # Celery 任务
├── pipelines/              # 数据清洗、抽取、验证、导入
├── storage/                # 本地/对象存储适配
└── utils/
```

依赖方向固定为：

```text
API → Service → Repository / Graph / Agent / Storage
```

API 层不得直接执行 SQL、Cypher 或调用模型。

---

## 3. 四类核心数据流

### 3.1 采集流

```text
数据源
→ 原始记录 raw_job_record
→ Schema 映射
→ 字段清洗与质量评分
→ 复合去重
→ 标准岗位数据 standard_job
→ 待处理版本 job_version
```

每条原始记录必须保留：

- 数据源、原始 URL、外部 ID；
- 抓取时间、原始发布时间；
- 原始字段 JSON 和正文；
- 内容指纹、质量分、处理状态和错误信息。

### 3.2 知识流

```text
标准岗位版本
→ 规则词典技能抽取
→ DeepSeek 补充抽取
→ 实体归一化
→ 多来源事实验证
→ MySQL 技能快照
→ Neo4j 幂等增量写入
→ GraphSnapshot
```

只有 `verified` 的能力声明可写入正式图谱。证据不足的声明保存为 `unverified`，进入人工复核或等待后续数据源补证。

### 3.3 业务流

```text
内部岗位发布
→ 简历上传与解析
→ 岗位匹配
→ 招聘阶段推进
→ 人才跟进
→ 工作台聚合
```

岗位发布、简历、匹配、招聘阶段、收藏、足迹和跟进记录全部以 MySQL 稳定 ID 关联。

### 3.4 Agent 流

```text
用户输入
→ 图谱/来源证据检索
→ Prompt 构建
→ LLMProvider
→ JSON Schema/Pydantic 校验
→ 事实核验
→ 业务结果
→ agent_run 审计记录
```

JD 生成、单次转岗分析等交互任务保持同步，目标响应时间小于 15 秒。文件解析、批量抽取、图谱构建等长任务必须异步化。

---

## 4. 通用 API 规范

### 4.1 基础约定

| 项目 | 约定 |
| --- | --- |
| API 前缀 | `/api/v1` |
| 认证 | JWT Bearer Token |
| 请求与响应编码 | UTF-8 |
| 时间入库 | UTC |
| 时间输出 | ISO 8601，例如 `2026-06-19T06:30:00Z` |
| 前端展示时区 | `Asia/Shanghai` |
| 分页参数 | `page=1&page_size=20`，`page_size ≤ 100` |
| 排序参数 | `sort_by`、`sort_order=asc|desc` |
| 文件上传 | `multipart/form-data` |
| 稳定标识 | 数据库 ID 或 UUID，禁止以名称充当关联主键 |

### 4.2 统一响应

```json
{
  "code": 200,
  "message": "success",
  "data": {},
  "meta": null
}
```

分页响应：

```json
{
  "code": 200,
  "message": "success",
  "data": [],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 128,
    "total_pages": 7
  }
}
```

### 4.3 HTTP 与业务错误码

HTTP 状态码表达协议结果，响应体 `code` 表达业务结果。

| 业务码范围 | 模块 |
| --- | --- |
| 40001-40099 | 认证与权限 |
| 40101-40199 | 岗位与招聘 |
| 40201-40299 | 数据采集与处理 |
| 40301-40399 | 图谱与能力更新 |
| 40401-40499 | 简历与人才 |
| 40501-40599 | 匹配与转岗 |
| 40601-40699 | 收藏与足迹 |
| 40701-40799 | Agent 与模型 |
| 40801-40899 | 系统管理 |

必须覆盖以下通用错误：

- 参数校验失败；
- 资源不存在；
- 无权限或 Token 失效；
- 重复创建或幂等冲突；
- 文件格式、大小或解析失败；
- 异步任务不存在或执行失败；
- 模型超时、限流或结构化输出无效；
- Neo4j/MySQL 等依赖不可用。

### 4.4 异步任务协议

创建任务：

```json
{
  "task_id": "01J10...",
  "task_type": "resume_parse",
  "status": "queued",
  "created_at": "2026-06-19T06:30:00Z"
}
```

任务状态统一使用：

```text
queued | running | succeeded | failed | cancelled
```

通用端点：

```http
GET    /api/v1/tasks/{task_id}
POST   /api/v1/tasks/{task_id}/cancel
```

任务结果仅在 `succeeded` 时存在，错误仅在 `failed` 时存在；进度范围为 `0-100`。

### 4.5 幂等约定

- 文件上传和任务触发支持可选请求头 `Idempotency-Key`。
- 采集记录以 `source_id + external_id` 或内容指纹幂等。
- 图谱节点按 `canonical_key` 合并，关系按起点、终点、关系类型和版本幂等。
- 收藏使用 `(user_id, target_type, target_id)` 唯一约束。
- 浏览足迹允许重复，但相同用户、目标和会话在短时间窗口内可合并。

---

## 5. 核心 DTO 与枚举

所有百分比接口统一返回 `0-100`，图算法和模型内部可以使用 `0-1`，但必须在 Schema 层转换。金额单位统一为人民币元/月，展示文本由前端格式化。

### 5.1 通用枚举

```python
JobLevel = Literal["junior", "middle", "senior", "expert"]
JobStatus = Literal["draft", "open", "paused", "closed"]
EvidenceStatus = Literal["unverified", "verified", "rejected"]
FavoriteTargetType = Literal["job", "resume"]
HistoryType = Literal["job", "resume", "search", "graph", "match"]
RecruitStage = Literal["screening", "interview", "offer", "hired", "rejected"]
Difficulty = Literal["easy", "medium", "hard"]
ChangeType = Literal["added", "modified", "removed", "stable"]
```

### 5.2 岗位 DTO

```python
class JobSummary(BaseModel):
    id: int
    title: str
    standardized_title: str
    department: str | None
    level: JobLevel | None
    location: str | None
    salary_min: int | None
    salary_max: int | None
    salary_months: int | None
    headcount: int
    status: JobStatus
    required_skills: list[str]
    created_at: datetime
    updated_at: datetime

class JobDetail(JobSummary):
    responsibilities: list[str]
    requirements: list[str]
    bonus_skills: list[str]
    jd_text: str
    source_count: int
    current_version: str | None

class JobVersion(BaseModel):
    id: int
    job_id: int
    version: str
    valid_from: datetime
    valid_to: datetime | None
    source_count: int
    snapshot: dict
```

### 5.3 简历与人才 DTO

```python
class ResumeSkill(BaseModel):
    skill_id: int | None
    name: str
    canonical_name: str
    category: str
    years: float | None
    level: str | None
    confidence: float

class ResumeProfile(BaseModel):
    id: int
    name: str | None
    current_title: str | None
    years_experience: float | None
    education: list[dict]
    work_experience: list[dict]
    skills: list[ResumeSkill]
    file_name: str
    file_size: int
    parse_status: str
    parse_confidence: float | None
    uploaded_at: datetime

class TalentSummary(BaseModel):
    resume_id: int
    name: str
    current_title: str | None
    department: str | None
    years_experience: float | None
    highest_education: str | None
    best_match_score: float | None
    matched_skills: list[str]
    missing_skills: list[str]
    target_jobs: list[dict]
    is_new: bool
    urgent: bool
    last_followed_at: datetime | None
```

手机号、邮箱等敏感字段只在有权限的详情接口返回，并在日志中脱敏。

### 5.4 匹配 DTO

```python
class SkillGap(BaseModel):
    skill_id: int | None
    skill_name: str
    importance: float
    current_level: str | None
    target_level: str | None
    graph_distance: int | None
    recommendation: str | None

class RadarDimension(BaseModel):
    name: str
    candidate_score: float
    target_score: float
    max_score: float = 100

class MatchReport(BaseModel):
    id: int
    resume_id: int
    job_id: int
    overall_score: float
    skill_coverage_score: float
    semantic_score: float
    graph_score: float
    experience_score: float
    matched_skills: list[str]
    missing_skills: list[SkillGap]
    radar: list[RadarDimension]
    gap_summary: str
    interview_questions: list[dict]
    evidence: list["EvidenceReference"]
    created_at: datetime
```

首期建议评分权重：

```text
overall =
  skill_coverage × 0.40
  + semantic_similarity × 0.25
  + graph_proximity × 0.20
  + experience_fit × 0.15
```

权重必须配置化，并在匹配记录中保存计算版本。

### 5.5 转岗与学习计划 DTO

```python
class LearningStep(BaseModel):
    skill_id: int | None
    skill: str
    difficulty: Difficulty
    estimated_weeks: float
    prerequisites: list[str]
    resources: list[dict]
    suggested_project: str | None

class CareerRecommendation(BaseModel):
    job_id: int
    job_title: str
    rank: int
    recommendation_score: float
    current_match: float
    expected_match: float
    existing_skills: list[str]
    missing_skills: list[str]
    learning_plan: list[LearningStep]
    estimated_total_weeks: float
    internal_demand: bool
```

### 5.6 图谱 DTO

```python
class GraphNode(BaseModel):
    id: str
    type: Literal[
        "Job", "SkillArea", "TechStack", "TechPoint",
        "KnowledgePoint", "SourceDocument", "GraphSnapshot"
    ]
    name: str
    stack: str | None
    level: str | None
    importance: float | None
    frequency: int | None
    description: str | None
    x: float | None
    y: float | None
    properties: dict = {}

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relation: str
    properties: dict = {}

class GraphSubgraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    node_count: int
    edge_count: int
    snapshot_version: str | None
```

后端可返回持久化或预布局坐标；坐标为空时由前端布局。不得把坐标作为图谱事实的一部分。

### 5.7 趋势 DTO

```python
class TrendPoint(BaseModel):
    period: str
    value: float

class TrendSeries(BaseModel):
    name: str
    unit: str
    points: list[TrendPoint]
    growth_rate: float | None

class HeatmapPoint(BaseModel):
    x: str
    y: str
    value: float
```

### 5.8 任务、Agent 与证据 DTO

```python
class EvidenceReference(BaseModel):
    source_document_id: int
    source_name: str
    source_url: str | None
    published_at: datetime | None
    extracted_at: datetime
    excerpt: str | None
    confidence: float
    verification_status: EvidenceStatus

class TaskStatus(BaseModel):
    task_id: str
    task_type: str
    status: str
    progress: int
    result: dict | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

class AgentRunResult(BaseModel):
    run_id: str
    agent_type: str
    provider: str
    model: str
    prompt_version: str
    output: dict
    evidence: list[EvidenceReference]
    latency_ms: int
    input_tokens: int | None
    output_tokens: int | None
    status: str
```

---

## 6. 页面—接口—数据契约

## 6.1 工作台 `/dashboard`

工作台使用一个聚合接口，避免前端首屏并发请求和统计口径不一致。

```http
GET /api/v1/dashboard/overview?hot_job_months=6&match_limit=6
```

响应：

```json
{
  "metrics": [
    {
      "key": "open_jobs",
      "label": "在招岗位",
      "value": 12,
      "change": 12.5,
      "change_unit": "percent",
      "trend": "up"
    }
  ],
  "recruitment_board": [
    {
      "job_id": 18,
      "title": "Java 高级开发",
      "total": 28,
      "stages": [
        {"stage": "screening", "label": "筛选", "count": 12},
        {"stage": "interview", "label": "面试", "count": 3},
        {"stage": "offer", "label": "发放", "count": 1},
        {"stage": "hired", "label": "入职", "count": 0}
      ]
    }
  ],
  "high_matches": [],
  "hot_jobs": [
    {
      "job_id": 28,
      "title": "AI 大模型工程师",
      "demand": 156,
      "growth_rate": 23,
      "trend": [30, 45, 62, 85, 110, 156]
    }
  ],
  "emerging_skills": [
    {
      "skill_id": 92,
      "name": "AI Agent 开发",
      "combination": ["LangChain", "Function Calling", "多跳推理"],
      "growth_rate": 45,
      "confidence": 92
    }
  ],
  "generated_at": "2026-06-19T06:30:00Z"
}
```

数据来源：

- 指标和招聘看板：MySQL；
- 高匹配人才：MySQL `match_record`；
- 热门岗位和新兴技能：趋势快照表，必要时回查 Neo4j；
- 聚合结果允许 Redis 缓存 1-5 分钟。

---

## 6.2 岗位管理 `/jobs`

### 岗位发布与维护

```http
GET    /api/v1/jobs?page=1&page_size=20&status=open&keyword=
POST   /api/v1/jobs
GET    /api/v1/jobs/{job_id}
PUT    /api/v1/jobs/{job_id}
DELETE /api/v1/jobs/{job_id}
PUT    /api/v1/jobs/{job_id}/status
```

创建/更新字段：

```json
{
  "title": "高级 Java 开发工程师",
  "standardized_title": "Java 开发工程师",
  "level": "senior",
  "department": "后台开发组",
  "location": "合肥",
  "salary_min": 25000,
  "salary_max": 40000,
  "salary_months": 14,
  "headcount": 2,
  "responsibilities": [],
  "requirements": [],
  "required_skill_ids": [],
  "bonus_skill_ids": [],
  "jd_text": "",
  "status": "open"
}
```

删除默认使用软删除；已经关联招聘申请或匹配记录的岗位不得物理删除。

### JD Agent

```http
POST /api/v1/jobs/generate-jd
```

请求：

```json
{
  "mode": "requirements",
  "title": "高级 Java 开发工程师",
  "level": "senior",
  "department": "后台开发组",
  "skill_text": "Java, Spring Boot, MySQL, Redis",
  "talent_profile": null,
  "style_preferences": {
    "tone": "professional",
    "language": "zh-CN"
  }
}
```

`mode` 为 `requirements | talent_profile`。响应必须包含职责、任职要求、加分技能、建议薪资、市场技能和证据列表。模型失败时返回可重试错误，不得悄悄生成无证据内容。

### 岗位版本与能力变更

```http
GET /api/v1/jobs/{job_id}/versions
GET /api/v1/jobs/{job_id}/versions/{version_id}
GET /api/v1/jobs/{job_id}/changes?from_version=&to_version=
GET /api/v1/jobs/{job_id}/trend?months=6
```

能力变更项必须包含技能 ID、变更类型、旧值、新值、首次出现时间、增长率、置信度和来源证据。

### 新兴岗位

```http
GET  /api/v1/emerging-jobs?page=1&status=pending&keyword=
GET  /api/v1/emerging-jobs/{candidate_id}
PUT  /api/v1/emerging-jobs/{candidate_id}
POST /api/v1/emerging-jobs/{candidate_id}/approve
POST /api/v1/emerging-jobs/{candidate_id}/reject
POST /api/v1/emerging-jobs/detect
```

`detect` 创建 Celery 任务。候选数据和审核状态保存在 MySQL；`approve` 后创建正式岗位版本并写入 Neo4j。

### 用户关注偏好

```http
GET /api/v1/users/me/preferences
PUT /api/v1/users/me/preferences
```

字段包括目标行业、目标技能、关注城市、通知频率。岗位洞察搜索条件可临时提交，不必自动覆盖长期偏好。

---

## 6.3 人才匹配 `/matching` 与 `/matching/:id`

### 简历上传与解析

```http
POST /api/v1/resumes
POST /api/v1/resumes/batch
GET  /api/v1/resumes/{resume_id}
GET  /api/v1/resumes/{resume_id}/file
PUT  /api/v1/resumes/{resume_id}
```

上传限制默认：

- 支持 PDF、DOC、DOCX、MD；
- 单文件不超过 20 MB；
- 批量不超过 20 个文件；
- 先校验扩展名、MIME、大小和文件签名；
- 文件名使用 UUID 重命名，原始文件名仅作元数据保存。

上传成功返回 `resume_id + task_id`。解析完成前详情接口返回 `parse_status=queued|running`。

### 人才列表与详情

```http
GET /api/v1/talents?name=&position=&department=&min_score=&sort_by=
GET /api/v1/talents/{resume_id}
GET /api/v1/talents/stats
```

排序支持：

```text
score | urgent | newest | last_followed
```

### 匹配分析

```http
POST /api/v1/matches
POST /api/v1/matches/batch
GET  /api/v1/matches?page=1&page_size=20&resume_id=&job_id=
GET  /api/v1/matches/{match_id}
```

单次请求：

```json
{
  "resume_id": 12,
  "job_id": 18,
  "generate_interview_questions": true
}
```

单份简历与单岗位分析可同步执行；批量比较必须返回任务 ID。详情页通过 `match_id` 获取报告，不能仅以人才 ID 推断唯一报告。

### 招聘阶段

```http
POST /api/v1/recruitment-applications
PUT  /api/v1/recruitment-applications/{application_id}/stage
GET  /api/v1/recruitment-applications?job_id=&resume_id=&stage=
```

每次阶段变化写入不可覆盖的阶段历史，用于工作台招聘看板。

---

## 6.4 转岗指南 `/career`

```http
POST /api/v1/career/analyses
GET  /api/v1/career/analyses/{analysis_id}
POST /api/v1/career/learning-plans
GET  /api/v1/enterprise-tech
PUT  /api/v1/enterprise-tech
POST /api/v1/enterprise-tech/import
```

分析请求支持文本技能、已有简历和企业上下文三种输入：

```json
{
  "skill_text": "Java 3年，Spring Boot，MySQL，Redis，略懂 Python",
  "resume_id": null,
  "current_title": "Java 开发工程师",
  "years_experience": 3,
  "enterprise_tech_ids": [1, 2, 3],
  "internal_job_ids": [18, 22],
  "max_recommendations": 10
}
```

规则：

- `skill_text` 与 `resume_id` 至少存在一个；
- 图谱计算候选岗位和基础差距；
- Agent 只负责解释、排序补充和学习计划生成；
- 企业内部需求岗位优先，但不得掩盖真实匹配度；
- 学习资源必须注明来源类型，模型虚构链接应被过滤。

---

## 6.5 技能图谱 `/graph`

```http
GET /api/v1/graph/panorama?stack=&level=&node_type=&snapshot=&limit=1000
GET /api/v1/graph/nodes/{node_id}
GET /api/v1/graph/expand?node_id=&depth=2&limit=300
GET /api/v1/graph/search?q=&types=&limit=20
GET /api/v1/graph/path?from_id=&to_id=&max_depth=6
GET /api/v1/graph/jobs/{job_id}/tree?depth=5&snapshot=
```

接口直接返回 `GraphSubgraph`。约束：

- `depth` 最大 5；
- `panorama` 默认最大 1000 节点；
- 路径查询最大深度 6；
- 超限时返回截断标记和建议过滤条件；
- 节点详情返回直接关联节点摘要；
- 查询必须参数化，不允许拼接用户输入到 Cypher。

---

## 6.6 趋势分析 `/trends`

```http
GET /api/v1/trends/overview?months=12&job_id=&city=
GET /api/v1/trends/job-demand?months=12&job_ids=
GET /api/v1/trends/salary?months=12&job_id=&city=
GET /api/v1/trends/skill-heatmap?months=6&skill_ids=
GET /api/v1/trends/location-distribution?job_id=&months=12
GET /api/v1/trends/emerging-skills?page=1&page_size=20&months=6
```

`overview` 返回累计岗位数、月度新兴技能数、平均薪资和活跃城市数。图表接口统一返回系列、单位、统计周期和数据生成时间。

趋势数据默认读取 MySQL 预计算快照，不在用户请求中即时扫描全部原始数据或完整图谱。

---

## 6.7 收藏 `/favorites`

前端和后端统一使用：

```text
target_type = job | resume
```

禁止再使用 `talent` 作为收藏类型。

```http
GET    /api/v1/favorites?target_type=&keyword=&sort_by=
POST   /api/v1/favorites
DELETE /api/v1/favorites/{favorite_id}
POST   /api/v1/favorites/batch-delete
PUT    /api/v1/favorites/{favorite_id}/note
```

创建请求：

```json
{
  "target_type": "job",
  "target_id": 18,
  "note": "技术方向与企业 Agent 项目高度吻合"
}
```

列表响应返回前端卡片所需的目标摘要、匹配度、技能、地点、薪资或人才信息，不要求前端再逐条请求详情。

---

## 6.8 浏览足迹 `/history`

```http
GET    /api/v1/history?type=&range=&keyword=&page=1&page_size=50
POST   /api/v1/history
DELETE /api/v1/history/{history_id}
DELETE /api/v1/history
GET    /api/v1/history/insights
```

记录请求：

```json
{
  "type": "graph",
  "target_id": "job-ai",
  "title": "AI 应用开发 · 五层技能树",
  "description": "展开岗位五层技能树",
  "url": "/graph",
  "tags": ["AI 应用", "技能树", "L1-L5"],
  "metadata": {}
}
```

`insights` 返回今日浏览数、独立目标数、关注方向占比和高频记录。足迹创建失败不得阻塞主业务请求。

---

## 6.9 系统管理 `/admin`

管理接口必须校验权限，不能只校验是否登录。

### 运行总览

```http
GET /api/v1/admin/overview
GET /api/v1/admin/health/services
```

返回 API 请求量、采集量、响应时间、异常事件、服务状态、资源利用率和最近任务。

### 数据源与采集

```http
GET    /api/v1/admin/data-sources
POST   /api/v1/admin/data-sources
PUT    /api/v1/admin/data-sources/{source_id}
DELETE /api/v1/admin/data-sources/{source_id}
POST   /api/v1/admin/data-sources/{source_id}/run
GET    /api/v1/admin/crawl-tasks
GET    /api/v1/admin/crawl-tasks/{task_id}
GET    /api/v1/admin/data-quality?source_id=&batch_id=
GET    /api/v1/admin/crawler-policy
PUT    /api/v1/admin/crawler-policy
```

### 日志与性能

```http
GET /api/v1/admin/metrics?range=1h
GET /api/v1/admin/endpoints?range=1h
GET /api/v1/admin/logs?level=&service=&keyword=&cursor=
GET /api/v1/admin/logs/export
GET /api/v1/admin/alert-rules
PUT /api/v1/admin/alert-rules/{rule_id}
```

P1 可从结构化应用日志表和进程指标聚合；P2 再接入专用可观测平台。

### 用户与 RBAC

```http
GET  /api/v1/admin/users
POST /api/v1/admin/users
PUT  /api/v1/admin/users/{user_id}
PUT  /api/v1/admin/users/{user_id}/status
POST /api/v1/admin/users/{user_id}/reset-password
GET  /api/v1/admin/roles
POST /api/v1/admin/roles
PUT  /api/v1/admin/roles/{role_id}
```

首期角色：

- `super_admin`
- `hr_admin`
- `department_manager`
- `hr_specialist`
- `data_maintainer`

### 系统设置与集成

```http
GET  /api/v1/admin/settings
PUT  /api/v1/admin/settings
GET  /api/v1/admin/integrations
POST /api/v1/admin/integrations/{integration}/test
```

敏感配置只显示是否已配置，不回传密钥明文。

---

## 7. 前端页面追踪矩阵

| 页面 | 主要接口 | 核心 DTO | 主数据源 |
| --- | --- | --- | --- |
| Dashboard | `/dashboard/overview` | DashboardOverview、TalentSummary、TrendSeries | MySQL + 趋势快照 |
| JobManagement 发布 | `/jobs`、`/jobs/generate-jd` | JobSummary、JobDetail、AgentRunResult | MySQL + Agent |
| JobManagement 洞察 | `/emerging-jobs`、`/jobs/{id}/changes` | EmergingJob、JobChange | MySQL + Neo4j |
| Matching | `/talents`、`/matches` | TalentSummary、MatchReport | MySQL + Neo4j |
| MatchingDetail | `/talents/{id}`、`/matches/{id}` | ResumeProfile、MatchReport | MySQL + 文件存储 |
| CareerGuide | `/career/analyses` | CareerRecommendation、LearningStep | Neo4j + Agent |
| GraphView | `/graph/*` | GraphNode、GraphEdge、GraphSubgraph | Neo4j |
| Trends | `/trends/*` | TrendSeries、HeatmapPoint | MySQL 趋势快照 |
| Favorites | `/favorites` | FavoriteSummary | MySQL |
| History | `/history`、`/history/insights` | HistoryRecord、HistoryInsights | MySQL |
| Admin | `/admin/*` | AdminOverview、TaskStatus、User、Role | MySQL + 运行指标 |

联调时以本表为入口，每个页面必须验证加载、空数据、错误、权限和刷新场景。

---

## 8. MySQL 领域模型

以下是逻辑表设计。具体字段长度、索引和约束在 Alembic migration 中实现。

### 8.1 账号与权限

#### `user`

- `id`
- `username`，唯一
- `email`，可空、唯一
- `password_hash`
- `display_name`
- `department`
- `status: active|disabled`
- `last_login_at`
- `created_at`、`updated_at`

#### `role`、`permission`

- 角色与权限均使用稳定 code。
- `user_role`、`role_permission` 使用联合唯一约束。
- API 权限通过依赖注入校验，例如 `jobs:write`、`crawler:run`。

### 8.2 数据采集

#### `data_source`

- 名称、类型、入口地址；
- 调度表达式、启停状态；
- 抓取配置 JSON；
- 最后运行、下次运行和连续失败次数。

#### `crawl_task`

- Celery task ID；
- 数据源、任务类型、状态、进度；
- 开始/结束时间、抓取数、成功数、失败数；
- 错误摘要和运行参数。

#### `raw_job_record`

- 数据源 ID、外部 ID、URL；
- 原始标题、公司、正文和原始 JSON；
- 发布时间、抓取时间；
- `content_hash`、`dedup_key`；
- 质量分、处理状态、错误信息。

唯一索引优先使用 `(data_source_id, external_id)`；无外部 ID 时使用内容指纹。

#### `data_quality_report`

- 数据源/批次；
- 完整率、重复率、薪资可用率、技能抽取率；
- 异常数量和明细 JSON；
- 生成时间。

### 8.3 标准岗位与能力版本

#### `standard_job`

- 标准岗位名称、别名；
- 技术方向、级别、描述；
- 当前版本 ID、状态；
- 首次和最后出现时间。

#### `job_version`

- 岗位 ID、版本号；
- 职责、要求、学历、经验、薪资等标准字段；
- 生效区间；
- 来源数、质量分、验证状态；
- 完整快照 JSON。

同一岗位的版本号唯一。

#### `skill`

- 名称、标准名称、分类、别名；
- `canonical_key` 唯一；
- 图谱节点 ID；
- 首次/最后出现时间。

#### `job_version_skill`

- 版本 ID、技能 ID；
- required/preferred；
- 重要度、频次、要求级别；
- 来源数、置信度、验证状态。

用于筛选和统计的技能必须关系化，不能只保存在 JSON 中。

#### `source_document` 与 `evidence_reference`

`source_document` 保存来源元数据和正文摘要；`evidence_reference` 将岗位版本、技能声明或 Agent 结果关联到来源，记录摘录、置信度和验证状态。

#### `job_change`

- 岗位、前后版本；
- 技能、变更类型；
- 旧值、新值、增长率；
- 说明、置信度、证据状态。

#### `emerging_job_candidate`

- 候选名称、核心技能、职责、场景；
- 聚类结果、置信度、来源数量；
- `pending|approved|rejected`；
- 审核人、审核时间、审核意见；
- 批次和生成 Agent 运行 ID。

### 8.4 招聘业务

#### `job_posting`

- 可选关联标准岗位；
- 标题、部门、级别、地点、薪资、人数；
- 职责、要求、JD 正文；
- 状态、创建人、发布时间；
- 软删除字段。

`job_posting_skill` 保存必备/加分技能。

#### `recruitment_application`

- 岗位发布 ID、简历 ID；
- 当前阶段、负责人；
- urgent、来源；
- 创建和更新时间。

#### `recruitment_stage_history`

- 申请 ID；
- from/to 阶段；
- 操作人、备注、时间。

### 8.5 简历、人才与匹配

#### `resume`

- 文件存储 key、原始文件名、MIME、大小、哈希；
- 姓名、当前岗位、年限、最高学历等常用检索字段；
- 解析状态、解析置信度；
- 上传人、创建时间、软删除字段。

#### `resume_parse_result`

- 原始文本；
- 个人信息、工作经历、教育经历 JSON；
- parser 版本、Agent 运行 ID；
- 解析错误。

#### `resume_skill`

- 简历、技能；
- 年限、熟练度、出现次数、置信度；
- 原始文本证据。

#### `talent_tag`、`resume_tag`

标签关系化，支持筛选和复用。

#### `follow_up_record`

- 简历、操作人；
- 动作、备注、下次跟进时间；
- 创建时间。

#### `match_record`

- 简历、岗位发布或标准岗位；
- 综合及各维度分数；
- 已匹配/缺失技能快照 JSON；
- 雷达图、分析说明、面试题 JSON；
- 算法版本、Agent 运行 ID；
- 已读状态、创建时间。

对 `(resume_id, job_id, algorithm_version)` 建查询索引，但允许多次分析保留历史。

### 8.6 Agent 与转岗

#### `agent_run`

- UUID、Agent 类型；
- provider、model、prompt 版本；
- 输入摘要、结构化输出 JSON；
- 状态、耗时、token；
- 重试次数、错误码、错误信息；
- 创建人和时间。

禁止保存不必要的完整敏感简历到外部模型审计字段；输入摘要需脱敏。

#### `user_preference`

- 用户唯一；
- 目标行业、技能、城市；
- 通知频率；
- 更新时间。

#### `enterprise_tech`

- 标准技能 ID；
- 自定义名称、分类、部门；
- 来源、启用状态、创建人。

#### `career_analysis`

- 用户、简历或技能输入摘要；
- 企业上下文；
- 推荐结果 JSON；
- Agent 运行 ID、创建时间。

### 8.7 收藏、足迹与系统

#### `favorite`

- 用户、`target_type`、`target_id`；
- 备注、创建时间；
- 联合唯一约束。

因为目标可能来自不同表，不使用普通外键直接约束 `target_id`，由 Service 层按类型校验资源存在性。

#### `browse_history`

- 用户、类型、目标 ID；
- 标题、描述、URL、标签和元数据；
- 会话 ID、访问时间。

索引：

- `(user_id, visited_at DESC)`
- `(user_id, history_type, visited_at DESC)`

#### `system_setting`

- 设置 key 唯一；
- value JSON；
- 是否敏感；
- 更新人和时间。

#### `audit_log`

- 操作人、动作、资源类型和资源 ID；
- 请求 ID、IP、结果；
- 变更摘要、时间。

管理操作、岗位审核、用户权限和系统设置变更必须写审计日志。

### 8.8 数据库通用规范

- 表名使用单数小写下划线。
- 主键首期统一 `BIGINT UNSIGNED`。
- 金额使用整数元或 `DECIMAL(12,2)`，禁止浮点。
- JSON 只保存低频变化、快照或模型原始结果。
- 所有业务表包含 `created_at`，可修改表包含 `updated_at`。
- 用户可删除资源优先软删除。
- 外键列必须建索引。
- 状态字段用字符串枚举并在应用层集中定义，避免数据库 ENUM 阻碍迁移。

---

## 9. Neo4j 五层森林设计

### 9.1 节点

```text
Job
SkillArea
TechStack
TechPoint
KnowledgePoint
SourceDocument
GraphSnapshot
```

核心公共属性：

```text
id               稳定 UUID
canonicalKey     全局归一化键
name
description
createdAt
updatedAt
firstSeenAt
lastSeenAt
status
```

领域属性：

- `Job`：aliases、stack、level；
- `SkillArea`：category；
- `TechStack`：category；
- `TechPoint`：detail；
- `KnowledgePoint`：difficulty、interviewWeight；
- `SourceDocument`：sourceType、url、publishedAt、contentHash；
- `GraphSnapshot`：version、snapshotType、createdAt。

### 9.2 关系

```text
(Job)-[:REQUIRES_AREA]->(SkillArea)
(SkillArea)-[:CONTAINS]->(TechStack)
(TechStack)-[:REFINES_TO]->(TechPoint)
(TechPoint)-[:HAS_KNOWLEDGE]->(KnowledgePoint)
(TechStack)-[:RELATED_TO]->(TechStack)
(TechPoint)-[:SAME_AS]->(TechPoint)
(KnowledgePoint)-[:PREREQUISITE]->(KnowledgePoint)
(SourceDocument)-[:SUPPORTS]->(Job|SkillArea|TechStack|TechPoint|KnowledgePoint)
(Job)-[:HAS_SNAPSHOT]->(GraphSnapshot)
```

能力关系至少包含：

```text
importance
frequency
firstSeenAt
lastSeenAt
sourceCount
confidence
verificationStatus
version
```

### 9.3 图谱写入规则

1. 使用 `canonicalKey` MERGE 节点。
2. 关系按起终点、类型和版本 MERGE。
3. 只接收已通过 Pydantic 与事实验证的结构。
4. 写入前在 MySQL 创建导入批次。
5. Neo4j 写入成功后更新 MySQL 批次状态。
6. Neo4j 失败时任务可安全重试，不重复增加频次。
7. 审核中的新兴岗位不写正式 `Job` 节点。

MySQL 与 Neo4j 无法使用同一数据库事务，采用任务状态 + 幂等写入 + 补偿重试保证最终一致性。

### 9.4 索引与约束

```cypher
CREATE CONSTRAINT job_key IF NOT EXISTS
FOR (n:Job) REQUIRE n.canonicalKey IS UNIQUE;

CREATE CONSTRAINT skill_area_key IF NOT EXISTS
FOR (n:SkillArea) REQUIRE n.canonicalKey IS UNIQUE;

CREATE CONSTRAINT tech_stack_key IF NOT EXISTS
FOR (n:TechStack) REQUIRE n.canonicalKey IS UNIQUE;

CREATE CONSTRAINT tech_point_key IF NOT EXISTS
FOR (n:TechPoint) REQUIRE n.canonicalKey IS UNIQUE;

CREATE CONSTRAINT knowledge_point_key IF NOT EXISTS
FOR (n:KnowledgePoint) REQUIRE n.canonicalKey IS UNIQUE;

CREATE FULLTEXT INDEX graph_name_search IF NOT EXISTS
FOR (n:Job|SkillArea|TechStack|TechPoint|KnowledgePoint)
ON EACH [n.name, n.description];
```

---

## 10. 数据处理 Pipeline

Pipeline 必须可分步执行、可断点重试、可回放并记录处理版本。

### Step 1：多源导入与统一 Schema

统一字段：

```text
title, company, city, salary, experience, education,
jd_text, responsibilities, requirements, keywords,
posted_at, url, source, crawled_at
```

原始缺失字段保留为空，不在导入阶段编造。

### Step 2：去重

优先级：

1. 数据源外部 ID；
2. 规范化 URL；
3. `title + company + posted_at`；
4. 标题、公司和正文 SimHash/文本相似度。

重复记录不能直接丢弃来源，应关联到同一标准岗位版本，作为交叉验证证据。

### Step 3：字段标准化

- 岗位名称：去除地点、校招、急聘、薪资和广告词；
- 城市：标准化为省/市/区及行政区代码；
- 薪资：换算为月薪最小值、最大值和薪数；
- 经验：转换为最小/最大年限；
- 学历：映射到统一等级；
- 日期：解析相对时间，解析失败时保留原文并标记；
- 正文：去 HTML、重复空白和明显广告段落。

### Step 4：实体归一化

- 词典精确匹配；
- 别名映射；
- RapidFuzz 相似度候选；
- DeepSeek 只处理规则无法确认的歧义项；
- 低置信度项进入人工复核表。

例：

```text
K8s → Kubernetes
SpringBoot → Spring Boot
Java高级开发 → Java 开发工程师 + senior
```

### Step 5：技能抽取

顺序固定：

1. 预置技能词典；
2. 正则与上下文规则；
3. DeepSeek 新技能补充；
4. 去重、归一化和类别校验；
5. 计算出现次数、必要/加分属性、重要度和置信度。

Agent 必须返回结构化 JSON，不允许 Service 层从自由文本猜测字段。

### Step 6：来源交叉验证

能力声明置信度由以下因素构成：

- 独立来源数量；
- 来源类型多样性；
- 数据新鲜度；
- 文本明确程度；
- 抽取模型置信度；
- 是否与现有图谱冲突。

首期正式写图规则：

```text
source_count >= 2
AND confidence >= 0.75
AND verification_status = verified
```

单一企业官网对该企业自身岗位要求可作为高可信事实，但不能直接代表全市场趋势。

### Step 7：版本与图谱写入

- 计算标准岗位当前版本与上一版本的差异；
- 无有效变化时不创建重复版本；
- 创建 MySQL 岗位版本和技能快照；
- 批量写入 Neo4j；
- 保存 `GraphSnapshot`；
- 记录导入批次和证据引用。

### Step 8：分析计算

- 能力新增、修改、淘汰；
- 技能频次和增长率；
- 新兴技能组合；
- 新岗位候选；
- 薪资和地域分布；
- 工作台与趋势页聚合快照。

---

## 11. Agent 架构

### 11.1 Provider 抽象

```python
class LLMProvider(Protocol):
    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        timeout_seconds: int,
        metadata: dict,
    ) -> BaseModel: ...
```

`DeepSeekProvider` 负责：

- API 地址、模型和密钥；
- 超时、指数退避和最多重试次数；
- 并发限制；
- JSON 结构化输出；
- token 与耗时统计；
- 上游错误映射；
- 请求 ID 和日志脱敏。

Provider 不负责业务事实验证。

### 11.2 Agent 类型

| Agent | 输入 | 输出 | 是否可写正式数据 |
| --- | --- | --- | --- |
| JD Agent | 岗位需求、图谱和市场证据 | 结构化 JD | 需用户确认后写岗位发布 |
| Skill Extraction Agent | JD 文本和已知词典候选 | 技能层级结构 | 验证通过后可写图 |
| Match Explanation Agent | 已计算的匹配指标和图谱证据 | 差距解释、面试建议 | 只写匹配报告 |
| Career Planning Agent | 技能差距、前置关系和企业上下文 | 学习路径 | 只写分析结果 |
| Emerging Job Agent | 技能聚类、增长和来源证据 | 候选岗位定义 | 审核通过后写正式岗位 |

匹配分数由可解释算法计算，禁止让模型直接给出最终分数。

### 11.3 Prompt 管理

- Prompt 放入版本化模板文件，不散落在 Service 中。
- 每次运行记录 `prompt_version`。
- Prompt 明确要求只使用提供证据。
- 输出 Schema 变化必须升级版本。
- 测试环境使用固定 Provider Mock，避免测试依赖真实 API。

### 11.4 结构化校验

每次模型输出依次经过：

1. JSON 解析；
2. Pydantic 校验；
3. 枚举与数值范围校验；
4. 技能实体归一化；
5. 来源引用存在性校验；
6. 图谱事实回查；
7. 业务规则校验。

校验失败可触发一次带错误反馈的修复请求，仍失败则任务失败，不得保存半结构化结果。

### 11.5 幻觉防控

- 能力声明必须带来源引用；
- 不存在的来源 ID 直接拒绝；
- 正式图谱能力至少两个独立来源；
- 与图谱冲突的声明标记 `unverified`；
- 学习资源 URL 使用白名单或实际可访问性校验；
- 匹配解释只能解释已有评分和技能差距；
- 保存验证结论和验证方法；
- 建立不少于 20 条故意错误声明测试集。

---

## 12. Celery 任务与调度

### 12.1 任务队列

建议队列：

```text
crawl       数据采集
document    文件与简历解析
agent       模型调用和技能抽取
graph       Neo4j 批量写入与快照
analysis    变更、新岗位和趋势计算
maintenance 清理、备份和健康检查
```

### 12.2 核心任务

```text
crawl_source(source_id)
import_raw_jobs(batch_id)
clean_and_normalize_jobs(batch_id)
extract_job_skills(batch_id)
verify_skill_claims(batch_id)
write_graph_batch(batch_id)
create_graph_snapshot(snapshot_type)
detect_job_changes(snapshot_id)
detect_emerging_jobs(snapshot_id)
calculate_trend_snapshots(snapshot_id)
parse_resume(resume_id)
batch_match(resume_ids, job_id)
import_enterprise_tech(file_id)
```

### 12.3 推荐调度

```text
每日 06:00   增量采集
采集完成后    清洗 → 抽取 → 验证 → 图谱写入
每周一 02:00 全量或重点源回查
每周一 07:00 创建周快照
每周一 08:00 能力变更与新岗位检测
每日 08:30   趋势和工作台聚合快照
每日 03:00   过期任务、临时文件和日志清理
```

### 12.4 失败与重试

- 网络和限流错误可重试；
- 参数、Schema、权限错误不可重试；
- 模型重试最多 2 次；
- 图谱写入按批次幂等重试；
- 连续失败达到阈值后暂停数据源并产生管理事件；
- 任务失败必须保留错误码、摘要和最后进度。

---

## 13. 安全与权限

### 13.1 权限边界

| 能力 | 最低角色 |
| --- | --- |
| 查看岗位、图谱、趋势 | 已登录用户 |
| 发布岗位、上传简历、执行匹配 | HR 专员 |
| 查看部门人才和转岗分析 | 部门经理 |
| 审核新兴岗位 | HR 管理员或数据维护员 |
| 数据源、爬虫、图谱维护 | 数据维护员 |
| 用户、角色、系统设置 | 超级管理员 |

### 13.2 文件与隐私

- 简历文件不可放在 Web 静态目录；
- 下载接口校验所有权和权限；
- 日志不记录原始简历全文、手机号、邮箱和 Token；
- Agent 输入按任务最小化并脱敏；
- 文件删除采用软删除 + 延迟物理清理；
- 文件哈希用于去重和审计。

### 13.3 审计

以下操作必须记录审计日志：

- 登录失败和账号状态变更；
- 用户角色、权限和密码重置；
- 数据源创建、修改、启停和手动运行；
- 新兴岗位审核；
- 图谱批量导入；
- 系统设置和集成测试；
- 岗位删除和简历删除。

---

## 14. 缓存与性能

### 14.1 Redis 缓存建议

| 数据 | TTL |
| --- | --- |
| 工作台聚合 | 1-5 分钟 |
| 趋势图表 | 10-30 分钟 |
| 图谱全景查询 | 5-10 分钟 |
| 节点详情 | 10 分钟 |
| 用户权限 | 5 分钟，权限变更时主动失效 |

缓存 key 必须包含过滤条件、用户权限范围和快照版本。

### 14.2 性能目标

- 图谱三层查询 P95 ≤ 2 秒；
- 单简历单岗位匹配 P95 ≤ 5 秒；
- 普通 MySQL 列表接口 P95 ≤ 500 ms；
- 工作台聚合缓存命中 P95 ≤ 300 ms；
- 同步 Agent 接口超时上限 15 秒；
- 图谱全景 1000 节点内前后端可交互。

### 14.3 预计算

以下结果必须预计算：

- 月度岗位需求；
- 月度薪资；
- 技能热力；
- 地域分布；
- 新兴技能排行；
- 工作台指标；
- 能力变更摘要。

---

## 15. 测试与评测

### 15.1 测试分层

| 层级 | 内容 |
| --- | --- |
| 单元测试 | 清洗、标准化、评分、验证和 Service 规则 |
| API 测试 | 鉴权、参数、响应、分页、错误和权限 |
| Repository 测试 | 事务、唯一约束、查询和软删除 |
| Neo4j 集成测试 | 写入幂等、树查询、路径和快照 |
| Celery 测试 | 任务状态、重试、失败和幂等 |
| Agent 合约测试 | Provider Mock、Schema、超时和无效输出 |
| Pipeline 测试 | 同批次重复执行结果一致 |
| 端到端测试 | 数据采集到前端展示的核心演示链路 |

### 15.2 测试环境

- 保留 `TESTING=true` 的 SQLite 内存 API 测试；
- JSON、关系和 SQL 行为差异较大的测试必须在 MySQL 集成环境执行；
- Neo4j、DeepSeek 和 Celery 在普通单元测试中使用可注入 Mock；
- Neo4j 集成测试在服务不可用时可标记跳过，但 CI 的集成阶段必须执行；
- 不允许测试调用真实收费模型。

### 15.3 必测场景

- 正常、空数据和资源不存在；
- 未登录、Token 失效和角色越权；
- 重复收藏、重复任务和幂等请求；
- 文件过大、类型伪造、损坏 PDF 和扫描件；
- 模型超时、限流、非法 JSON 和证据缺失；
- Neo4j 不可用、部分批次失败和重试；
- 任务取消、失败和状态轮询；
- 删除有关联数据的岗位或简历；
- Pipeline 同批次执行两次不重复写图；
- 跨时区日期和相对发布时间解析。

### 15.4 量化指标

| 指标 | 目标 |
| --- | --- |
| Service 层行覆盖率 | ≥ 60% |
| P0 API 场景覆盖 | 100% |
| JD 技能抽取 F1 | ≥ 0.90 |
| 简历技能抽取 F1 | ≥ 0.90 |
| 匹配判断与专家一致率 | ≥ 0.90 |
| 幻觉声明检测用例 | ≥ 20 条 |
| JD 标注样本 | ≥ 100 条 |
| 简历标注样本 | ≥ 50 份 |
| 匹配标注样本 | ≥ 100 对 |

准确率文档必须记录数据集版本、标注人、指标公式、运行参数和结果，避免只给出最终百分比。

### 15.5 核心验收链路

1. 导入至少三类数据源。
2. 清洗并生成标准岗位和质量报告。
3. 抽取技能并通过来源验证。
4. 写入五层图谱并创建快照。
5. 展示既有岗位能力变化。
6. 发现并人工审核一个新兴岗位。
7. 上传简历并完成解析。
8. 生成匹配报告和技能差距。
9. 生成转岗建议和学习路径。
10. 工作台、趋势和管理页显示真实聚合数据。

---

## 16. 分阶段开发计划

## P0-1：接口与工程基础

### 依赖

- 当前认证和测试骨架；
- MySQL、Neo4j 可连接；
- 确认 API 命名和 DTO。

### 交付

- 路由、Service、Repository、Schema 分层；
- 统一异常和响应；
- Alembic；
- RBAC 基础；
- 任务状态协议；
- 文件存储抽象；
- DeepSeek Provider 接口和 Mock。

### 数据表

`user`、`role`、`permission`、关联表、`agent_run`、`audit_log`、`system_setting`。

### 验收

- 现有认证测试通过；
- 角色权限测试通过；
- migration 可在空库升级和回滚；
- Provider Mock 可产生通过 Schema 校验的结果。

## P0-2：数据基础与五层图谱

### 依赖

- P0-1；
- 现有 `data/jd_crawl_*.json`；
- Redis/Celery。

### 交付

- 数据源、原始记录和质量模型；
- 清洗、去重、标准化；
- 技能词典和 DeepSeek 补充抽取；
- 来源验证；
- 标准岗位版本；
- Neo4j 五层写入和查询；
- 图谱快照。

### 数据表

`data_source`、`crawl_task`、`raw_job_record`、`data_quality_report`、`standard_job`、`job_version`、`skill`、`job_version_skill`、`source_document`、`evidence_reference`。

### Celery

数据导入、清洗、抽取、验证、写图、快照。

### 验收

- 现有三份 JD 数据可重复导入；
- 重复执行不重复创建记录和节点；
- 至少 50 个标准岗位或岗位版本写入；
- 五层树和全景接口可返回真实数据；
- 每个正式能力声明可追踪来源。

## P0-3：岗位、能力更新、新岗位与趋势

### 依赖

- P0-2 图谱和快照。

### 交付

- 岗位 CRUD 和 JD Agent；
- 岗位版本与变更；
- 新兴岗位检测、编辑和审核；
- 趋势预计算与 API；
- 岗位管理、图谱和趋势页面联调。

### 数据表

`job_posting`、`job_posting_skill`、`job_change`、`emerging_job_candidate`、趋势快照表、`user_preference`。

### Celery

能力 diff、新岗位检测、趋势计算、工作台市场指标。

### 验收

- 页面不再使用本地模拟岗位和趋势数据；
- 至少展示一个既有岗位的两个版本；
- 至少生成并审核一个新岗位候选；
- 趋势图包含周期、单位和生成时间；
- 图谱查询达到性能目标。

## P0-4：简历、匹配、转岗与工作台

### 依赖

- P0-3 的岗位和图谱；
- 文件解析依赖；
- DeepSeek Provider。

### 交付

- 简历上传、解析和下载；
- 人才列表和详情；
- 匹配算法、报告和面试建议；
- 招聘阶段；
- 转岗推荐、企业技术栈和学习路径；
- 工作台聚合；
- 当前核心业务页面联调。

### 数据表

`resume`、`resume_parse_result`、`resume_skill`、标签表、`match_record`、`recruitment_application`、阶段历史、`enterprise_tech`、`career_analysis`。

### Celery

简历解析、批量匹配、企业文件导入。

### 验收

- PDF/Word 上传和解析闭环；
- 匹配报告字段完整；
- 分数由算法生成，Agent 只解释；
- 转岗结果包含补课前后匹配度、学习周期和来源；
- 工作台使用真实岗位、人才、阶段和趋势数据；
- 满足三项准确率评测要求。

## P1：辅助业务与管理增强

### 交付

- 收藏、批量取消和备注；
- 足迹、分组和关注洞察；
- 人才标签与跟进；
- 数据源和爬虫管理；
- 数据质量、日志、性能、用户、角色和设置；
- 审计日志。

### 数据表

`favorite`、`browse_history`、标签和跟进表、管理事件与告警规则表。

### 验收

- 收藏类型统一为 `job|resume`；
- 所有管理操作有权限和审计；
- 管理页五个区块均读取真实接口；
- 服务不可用和任务失败有可见状态。

## P2：生产化增强

- Elasticsearch 全文检索与聚合；
- 向量检索和 RAG；
- SSE 流式 Agent 输出；
- 对象存储；
- 专用日志、指标和告警平台；
- 分布式限流、熔断和任务监控；
- 数据备份、恢复和容灾演练；
- Docker Compose 与生产部署优化。

---

## 17. 开发顺序与模块依赖

```text
P0-1 工程基础
  └─ P0-2 数据与图谱
       ├─ P0-3 岗位/变更/发现/趋势
       │    └─ P0-4 匹配/转岗/工作台
       └────────────────────────────┐
                                    ▼
                              P1 管理与辅助功能
                                    ▼
                              P2 生产化增强
```

不得先用临时 JSON 完成全部 API 再补数据库。每个阶段应先确定 Schema 和迁移，再实现 Repository、Service、API 与测试。

---

## 18. 前后端联调规范

### 18.1 必须先统一的现有冲突

- 收藏类型统一为 `job | resume`，前端收藏页的 `talent` 改为 `resume`。
- 匹配资源统一使用 `/matches`，页面路由 `/matching` 不决定 API 名称。
- 趋势统一使用 `/trends`，不再同时维护 `/analysis`。
- 稳定资源 ID 替代岗位名称作为收藏、足迹和关联 ID。
- 匹配详情使用 `match_id`；人才详情使用 `resume_id`，两者不能混用。
- 岗位级别后端统一英文枚举，中文仅作为展示标签。

### 18.2 联调检查

- URL、HTTP Method 和权限；
- Query、Path、Body 和 multipart 参数；
- DTO 字段名、单位、枚举和空值；
- 分页、筛选和排序；
- 空数据、加载、失败和重试状态；
- Token 失效跳转；
- 任务轮询和完成刷新；
- 文件上传、下载和错误；
- 页面刷新后数据状态可恢复；
- 收藏与足迹不再依赖 localStorage 作为唯一数据源。

### 18.3 OpenAPI

- 所有接口声明明确的请求和响应模型；
- 为核心 DTO 添加示例；
- 路由 tag 与领域模块一致；
- 不使用无约束 `dict` 作为正式公共响应；
- CI 可导出 OpenAPI JSON 供前端生成或校验类型。

---

## 19. 配置项

首期环境变量：

```bash
# MySQL
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=jie_bang

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=
NEO4J_DATABASE=neo4j

# Redis / Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# JWT
JWT_SECRET_KEY=
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=120

# LLM
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
LLM_TIMEOUT_SECONDS=15
LLM_MAX_RETRIES=2

# Storage
STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=./storage
MAX_RESUME_SIZE_MB=20

# Application
APP_TIMEZONE=Asia/Shanghai
LOG_LEVEL=INFO
```

启动时检查关键配置，但日志不得打印密码、Token 或 API Key。

---

## 20. 完成定义

模块只有同时满足以下条件才算完成：

- 数据库 migration 已提交；
- API、Service、Repository 和 Schema 分层清晰；
- OpenAPI 可正确展示；
- 正常、空数据、错误和权限测试通过；
- 真实页面已联调，模拟数据已移除；
- 日志和错误信息可定位问题；
- 涉及 Agent 的功能有 Provider Mock、Schema 校验和运行审计；
- 涉及图谱的写入可幂等重试；
- 文档中的页面追踪矩阵已更新；
- 性能或准确率指标有可复现的测试结果。

---

> **文档版本**：v3.0  
> **更新日期**：2026-06-19  
> **状态**：后端开发实施基线
