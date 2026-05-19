# 开发规范文档

## 多源异构数据驱动岗位和能力图谱构建项目

---

## 一、API 接口规范

### 1.1 基础约定

| 项目 | 规范 |
|------|------|
| 协议 | HTTPS（生产）/ HTTP（本地开发） |
| 域名 | 开发：`http://localhost:8000` |
| 版本 | URL 路径版本：`/api/v1/` |
| 格式 | 请求/响应均为 `application/json` |
| 编码 | UTF-8 |
| 文档 | FastAPI 自动生成 Swagger UI（`/docs`） |

### 1.2 URL 命名规范

```
# === 岗位 ===
GET    /api/v1/jobs              # 岗位列表（分页+筛选）
GET    /api/v1/jobs/{id}         # 岗位详情
GET    /api/v1/jobs/{id}/skills  # 岗位关联技能
GET    /api/v1/jobs/search       # 岗位搜索

# === 图谱 ===
GET    /api/v1/graph/query       # 图谱查询（POST 传复杂查询参数）
GET    /api/v1/graph/node/{type}/{id}  # 图谱节点详情
GET    /api/v1/graph/expand      # 图谱节点展开

# === 分析 ===
GET    /api/v1/analysis/trends   # 趋势分析数据
GET    /api/v1/analysis/hot-skills   # 热门技能
GET    /api/v1/analysis/emerging-jobs # 新兴岗位
GET    /api/v1/analysis/iflytek/benchmark  # 讯飞 vs 行业对标

# === 转岗 ===
POST   /api/v1/transfer/analyze  # 转岗可行性分析
POST   /api/v1/transfer/gap      # 技能差距分析
GET    /api/v1/transfer/recommend # 培训推荐

# === 企业数据 ===
POST   /api/v1/enterprise/import/employees   # 导入员工数据（CSV/Excel）
POST   /api/v1/enterprise/import/training    # 导入培训记录
POST   /api/v1/enterprise/import/documents   # 上传非结构化文档（PDF/Word）
GET    /api/v1/enterprise/employees          # 员工列表
GET    /api/v1/enterprise/employees/{id}     # 员工详情（含技能+转岗记录）
GET    /api/v1/enterprise/internal-jobs      # 企业内部岗位列表

# === AI Agent ===
POST   /api/v1/agent/chat        # Agent 对话（标准 JSON 响应）
POST   /api/v1/agent/chat/stream # Agent 流式对话（SSE，text/event-stream）
GET    /api/v1/agent/sessions    # 用户历史会话列表
GET    /api/v1/agent/sessions/{id}  # 会话历史消息

# === 认证 ===
POST   /api/v1/auth/login        # 登录
POST   /api/v1/auth/register     # 注册

# === 管理 ===
GET    /api/v1/admin/datasources # 数据源管理
POST   /api/v1/admin/crawl/trigger # 触发爬虫任务
```

**命名规则**：
- 资源名用复数名词（`/jobs` 而非 `/job`）
- 动作用 HTTP 方法表达，不在 URL 中用动词
- 复杂查询（多条件、嵌套参数）使用 `POST` + body
- 层级资源：`/jobs/{id}/skills`

### 1.3 统一响应格式

所有 API 返回以下标准 JSON 结构：

```json
{
  "code": 200,
  "message": "success",
  "data": { ... },
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 156,
    "total_pages": 8
  }
}
```

**字段说明**：

| 字段        | 类型     | 说明                 |
| --------- | ------ | ------------------ |
| `code`    | int    | 业务状态码，200 成功       |
| `message` | string | 提示信息，成功为 "success" |
| `data`    | any    | 响应数据体，列表/对象/null   |
| `meta`    | object | 分页信息，仅列表接口返回       |

**错误响应**：

```json
{
  "code": 40001,
  "message": "岗位不存在",
  "data": null
}
```

### 1.4 状态码规范

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证（Token 缺失或无效） |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 422 | 请求参数校验失败（Pydantic 自动） |
| 500 | 服务器内部错误 |

**业务错误码范围**：

| 范围 | 模块 |
|------|------|
| 40001-40099 | 岗位模块 |
| 40101-40199 | 图谱模块 |
| 40201-40299 | 分析模块 |
| 40301-40399 | 转岗模块 |
| 40401-40499 | 认证模块 |
| 40501-40599 | 管理模块 |
| 40601-40699 | AI Agent 模块 |
| 40701-40799 | 企业数据模块 |

### 1.5 分页规范

列表接口统一使用分页参数：

```
GET /api/v1/jobs?page=1&page_size=20
```

| 参数 | 类型 | 默认值 | 最大值 |
|------|------|--------|--------|
| `page` | int | 1 | - |
| `page_size` | int | 20 | 100 |

### 1.6 认证方式

使用 JWT Bearer Token：

```
Authorization: Bearer <access_token>
```

- Token 有效期：access_token 2 小时
- 登录接口返回 `access_token` 和 `token_type: "bearer"`

---

## 二、数据库设计规范

### 2.1 命名规范

| 对象 | 规范 | 示例 |
|------|------|------|
| 数据库名 | 小写 + 下划线 | `jie_bang` |
| 表名 | 小写 + 下划线，单数 | `job`、`enterprise_user` |
| 字段名 | 小写 + 下划线 | `created_at`、`min_salary` |
| 主键 | `id`，INT/BIGINT 自增 | `id` |
| 外键 | `关联表_id` | `job_id`、`skill_id` |
| 索引 | `idx_表名_字段` | `idx_job_title` |
| 唯一索引 | `uk_表名_字段` | `uk_user_username` |
| 创建时间 | `created_at` (DATETIME) | - |
| 更新时间 | `updated_at` (DATETIME) | - |

### 2.2 字段类型规范

| 数据 | MySQL 类型 |
|------|-----------|
| 主键 | `INT UNSIGNED AUTO_INCREMENT` 或 `BIGINT UNSIGNED` |
| 短文本（≤255） | `VARCHAR(N)` |
| 长文本 | `TEXT` |
| JSON 数据 | `JSON` |
| 金额 | `DECIMAL(12,2)` |
| 时间 | `DATETIME`（UTC 存储） |
| 布尔 | `TINYINT(1)` |

### 2.3 Neo4j 规范

- 节点标签：大驼峰（`Job`、`Skill`、`Tool`）
- 关系类型：全大写 + 下划线（`REQUIRES`、`RELATED_TO`）
- 属性键：小驼峰（`salaryRange`、`mentionCount`）
- 索引：对高频查询属性建索引（`CREATE INDEX job_title FOR (j:Job) ON (j.title)`）

---

## 三、代码规范

### 3.1 Python 后端规范

| 项目 | 规范 |
|------|------|
| 风格 | PEP 8 |
| 格式化 | Black（行宽 100） |
| 类型注解 | 所有函数参数和返回值必须标注类型 |
| 导入顺序 | 标准库 → 第三方库 → 项目内部模块 |
| 文档字符串 | Google 风格（Args/Returns/Raises） |

**示例**：

```python
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.job import JobResponse, JobListResponse
from app.services.job_service import JobService


router = APIRouter(prefix="/jobs", tags=["岗位管理"])


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    db: AsyncSession = ...,
) -> JobListResponse:
    """获取岗位列表，支持分页和关键词搜索。"""
    ...
```

### 3.2 Vue 前端规范

| 项目 | 规范 |
|------|------|
| 组件命名 | PascalCase（`JobList.vue`） |
| 组合式 API | 统一使用 `<script setup lang="ts">` |
| CSS | Scoped + BEM 命名（`.job-list__item--active`） |
| 目录 | 页面放 `views/`，复用组件放 `components/` |
| API 调用 | 统一在 `api/` 目录封装，不在组件中直接调用 axios |

**示例**：

```typescript
// api/job.ts
import request from './request'
import type { Job, JobListParams, PageResponse } from '@/types'

export const getJobList = (params: JobListParams): Promise<PageResponse<Job>> => {
  return request.get('/jobs', { params })
}
```

```vue
<!-- views/JobList.vue -->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getJobList } from '@/api/job'
import type { Job } from '@/types'

const jobs = ref<Job[]>([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  const res = await getJobList({ page: 1, page_size: 20 })
  jobs.value = res.data
  loading.value = false
})
</script>
```

### 3.3 通用约定

- **错误处理**：后端 Service 层抛出自定义异常，API 层统一捕获并转换为标准响应
- **日志**：使用 Python `logging` 模块，生产环境 INFO 级别
- **环境变量**：所有敏感配置（数据库密码、密钥等）通过 `.env` 文件读取
- **注释**：仅对非显而易见的逻辑写注释，不写"做什么"（代码本身说明），只写"为什么这样做"

---

## 四、Git 协作规范

### 4.1 分支策略

```
main                    # 主分支，只接受经过测试的合并
├── develop             # 开发主分支，所有 feature 合并到此
│   ├── feature/a-crawler    # 成员 A：数据采集
│   ├── feature/b-graph      # 成员 B：数据库与图谱
│   ├── feature/c-api        # 成员 C：后端服务
│   └── feature/d-frontend   # 成员 D：前端
```

### 4.2 提交规范

```
<type>(<scope>): <subject>

类型：feat / fix / docs / style / refactor / test / chore
范围：crawler / graph / api / frontend / docs
主题：简短描述（中文，≤50 字）
```

**示例**：
```
feat(crawler): 完成Boss直聘爬虫开发
feat(graph): 新增岗位-技能关系写入接口
fix(api): 修复转岗分析匹配度计算除零异常
chore(docker): 添加docker-compose部署配置
```

### 4.3 协作流程

1. 从 `develop` 拉取最新代码
2. 创建个人 `feature/xxx` 分支开发
3. 完成后提 PR 到 `develop`
4. 至少 1 人 Code Review 后合并
5. 每周五 `develop` → `main` 打版本 Tag

---

## 五、模块间接口约定

### 5.1 数据交换格式

**成员 A（数据采集）→ 成员 B（数据库）**：

成员 A 将清洗后的数据写入 MySQL `job` 表和 `skill` 表。表结构由成员 B 定义，成员 A 按表结构写入。

**成员 A（NLP）→ 成员 B（图谱）**：

成员 A 调用成员 B 提供的 `GraphService` 写入图谱：

```python
# 成员 B 提供的接口
class GraphService:
    def create_job_node(self, job_data: dict) -> str: ...
    def create_skill_node(self, skill_data: dict) -> str: ...
    def create_relation(self, from_node: str, to_node: str, 
                        relation_type: str, properties: dict = None) -> None: ...
    def batch_import_triples(self, triples: list[dict]) -> int: ...
```

**成员 C（后端 API）→ 成员 D（前端）**：

通过 RESTful API 交互。成员 C 先提供 Swagger 文档，成员 D 据此开发。

### 5.2 Service 层接口定义

各成员暴露的 Service 类方法签名（在开发前对齐）：

```python
# === 成员 A 暴露 ===
class CrawlerService:
    async def trigger_crawl(datasource_id: int) -> str: ...
    async def get_crawl_status(task_id: str) -> dict: ...
    async def import_dataset(file_path: str) -> int: ...
    async def import_enterprise_employees(enterprise_id: int, file_path: str) -> int: ...
    async def import_training_records(enterprise_id: int, file_path: str) -> int: ...

class DocumentService:
    async def parse_pdf(file_path: str) -> str: ...
    async def parse_docx(file_path: str) -> str: ...
    async def extract_resume_skills(text: str) -> list[str]: ...

class NLPService:
    async def extract_entities(text: str) -> list[Entity]: ...
    async def extract_relations(text: str) -> list[Relation]: ...
    async def process_job_batch(job_ids: list[int]) -> int: ...
    async def process_unstructured_doc(doc_id: int) -> dict: ...

# === 成员 B 暴露 ===
class GraphService:
    # 行业通用查询
    async def query_job_skills(job_title: str, depth: int = 1) -> dict: ...
    async def query_skill_jobs(skill_name: str) -> list[dict]: ...
    async def query_related_skills(skill_name: str, top_k: int = 10) -> list[dict]: ...
    async def semantic_search(query: str, top_k: int = 10) -> list[dict]: ...
    async def get_subgraph(node_id: str, depth: int = 2) -> dict: ...
    # 讯飞专有
    async def query_iflytek_jobs(category: str = None) -> list[dict]: ...
    async def iflytek_vs_industry(job_title: str) -> dict: ...
    # 企业子图（隔离查询）
    async def get_enterprise_subgraph(enterprise_id: int, depth: int = 2) -> dict: ...
    async def query_enterprise_employee_skills(enterprise_id: int, employee_id: int) -> dict: ...
    # 数据写入
    async def batch_import_triples(triples: list[dict]) -> int: ...
    async def create_enterprise_graph(enterprise_id: int, employee_data: list[dict]) -> int: ...

# === 成员 C 暴露 ===
class AnalysisService:
    async def get_job_trend(job_title: str, months: int = 6) -> TrendResult: ...
    async def get_hot_skills(limit: int = 20) -> list[SkillRank]: ...
    async def detect_emerging_jobs(threshold: float = 0.3) -> list[EmergingJob]: ...
    async def get_skill_lifecycle(skill_name: str) -> LifecycleData: ...
    async def get_salary_trend(job_title: str, months: int = 12) -> SalaryTrend: ...

class IFlytekAnalysis:
    async def benchmark_vs_competitors(job_title: str) -> BenchmarkResult: ...
    async def talent_distribution() -> TalentMap: ...
    async def skill_gap_iflytek_vs_industry(job_title: str) -> GapReport: ...

class TransferService:
    async def analyze_transfer(employee_skills: list[str], 
                               current_job: str) -> TransferResult: ...
    async def calc_skill_gap(employee_skills: list[str],
                             target_job: str) -> SkillGapResult: ...
    async def recommend_training(skill_gaps: list[str]) -> TrainingPlan: ...

class AgentService:
    async def process_message(session_id: str, message: str, user_id: int) -> AgentResponse: ...
    async def process_message_stream(session_id: str, message: str, user_id: int) -> AsyncGenerator: ...
    async def get_or_create_session(user_id: int) -> str: ...
    async def get_session_history(session_id: str) -> list[AgentMessage]: ...

class AgentTools:
    """Agent 可调用的 Function Call 工具集"""
    async def query_job_market(keyword: str, city: str = None) -> dict: ...
    async def search_skill_graph(skill_name: str, depth: int = 2) -> dict: ...
    async def semantic_search_job(query: str, top_k: int = 5) -> list[dict]: ...
    async def analyze_transfer_tool(employee_skills: list[str], current_job: str) -> dict: ...
    async def generate_trend_report(period: str = "weekly") -> dict: ...
    async def compare_job_profiles(job_a: str, job_b: str) -> dict: ...
    async def generate_jd(job_title: str, company: str = "科大讯飞") -> str: ...
```

### 5.3 核心数据结构

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# === 岗位 ===
class JobResponse(BaseModel):
    id: int
    title: str
    standardized_title: str
    level: Optional[str]      # 初级/中级/高级
    min_salary: Optional[float]
    max_salary: Optional[float]
    experience_required: Optional[str]
    degree_required: Optional[str]
    location: Optional[str]
    industry: Optional[str]
    post_date: Optional[datetime]
    skills: list["SkillBrief"] = []

class SkillBrief(BaseModel):
    id: int
    name: str
    category: str
    importance: float        # 0.0 ~ 1.0

# === 图谱节点 ===
class GraphNode(BaseModel):
    id: str
    label: str               # Job / Skill / Tool / Industry
    name: str
    properties: dict = {}

class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str            # REQUIRES / RELATED_TO / ...
    properties: dict = {}

class SubGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]

# === 趋势分析 ===
class TrendPoint(BaseModel):
    date: str                # "2026-01"
    value: float

class TrendResult(BaseModel):
    entity_name: str
    entity_type: str         # job / skill
    data: list[TrendPoint]
    growth_rate: float       # 环比增长率

# === 转岗分析 ===
class TransferOption(BaseModel):
    target_job: str
    match_score: float       # 0.0 ~ 1.0
    matched_skills: list[str]
    missing_skills: list[str]
    difficulty: str          # easy / medium / hard

class TransferResult(BaseModel):
    employee_skills: list[str]
    current_job: str
    options: list[TransferOption]

# === 技能差距 ===
class SkillGapItem(BaseModel):
    skill_name: str
    importance: float        # 目标岗位对该技能的重视度
    current_level: str       # 未知 / 入门 / 熟练 / 精通

class SkillGapResult(BaseModel):
    target_job: str
    overall_match: float
    gaps: list[SkillGapItem]

# === 分页 ===
class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int

# === 统一响应 ===
class ApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Optional[object] = None
    meta: Optional[PageMeta] = None

# === AI Agent ===
class AgentRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class AgentMessage(BaseModel):
    role: str                # "user" / "assistant" / "tool"
    content: str
    tool_calls: Optional[list[dict]] = None
    timestamp: datetime

class AgentResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[dict] = []    # [{type: "mysql"/"neo4j"/"milvus", query: "...", result_summary: "..."}]
    tool_calls_made: list[str] = []

# === 企业数据 ===
class EnterpriseEmployeeImport(BaseModel):
    enterprise_id: int
    file: bytes                # CSV/Excel 文件内容

class EnterpriseEmployeeResponse(BaseModel):
    id: int
    enterprise_id: int
    name: str
    current_position: str
    department: Optional[str]
    skills: list["SkillBrief"]
    training_history: list[dict] = []
    promotion_history: list[dict] = []

# === 非结构化文档 ===
class UnstructuredDocUpload(BaseModel):
    enterprise_id: int
    doc_type: str              # "resume" / "jd" / "report" / "review"
    file: bytes

class UnstructuredDocResponse(BaseModel):
    id: int
    doc_type: str
    parsed_text: str
    extracted_entities: list[dict]
    created_at: datetime

# === 讯飞对标 ===
class BenchmarkResult(BaseModel):
    iflytek_stats: dict        # 讯飞岗位数量/薪资/技能分布
    industry_stats: dict       # 行业平均数据
    competitors: dict          # 竞品企业对比数据
    gap_analysis: str          # 差距分析文本
```

---

## 六、环境与部署规范

### 6.1 开发环境

| 工具 | 版本 |
|------|------|
| Python | 3.10+ |
| Node.js | 18 LTS |
| MySQL | 8.0 |
| Neo4j | 5.x (Community) |
| Milvus | 2.3+ (standalone) |
| Redis | 7.x |
| Docker | 24+ |
| Poetry (Python 依赖管理) | 1.5+ |
| pnpm (前端包管理) | 8+ |

### 6.2 环境变量（`.env` 文件，不入库）

```bash
# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=jie_bang

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256

# 星火大模型
SPARK_APP_ID=your_app_id
SPARK_API_KEY=your_api_key
SPARK_API_SECRET=your_api_secret
SPARK_API_MODEL=spark-4.0

# API
API_HOST=0.0.0.0
API_PORT=8000
```

### 6.3 Docker Compose 服务编排

`docker-compose.yml` 包含以下服务：
- `mysql`（端口 3306）
- `neo4j`（端口 7474/7687）
- `milvus-standalone`（端口 19530/9091）
- `redis`（端口 6379）
- `backend`（FastAPI，端口 8000）
- `frontend`（Vue 3 dev server，端口 5173）
- `celery-worker`（后台任务处理）
- `celery-beat`（定时任务调度）

---

## 七、前后端联调流程

1. **成员 C** 完成 API 开发后，在 Swagger UI（`/docs`）上自测通过
2. **成员 C** 将接口变更同步到接口文档（Swagger 即为文档，无需额外维护）
3. **成员 D** 在 `api/` 目录创建对应的请求函数，类型引用 `@/types` 定义
4. **成员 D** 本地联调，发现问题在微信群同步（截图 + 请求参数 + 错误信息）
5. **双方确认** 修复后关闭问题

### 联调检查清单

- [ ] 请求 URL、Method 是否正确
- [ ] 请求参数格式（Query/Body/Path）是否正确
- [ ] 响应 JSON 字段名是否与前端类型定义一致
- [ ] 分页参数是否生效
- [ ] 空数据/错误情况前端是否正确展示
- [ ] Token 过期时前端是否自动跳转登录

---

## 八、测试规范

| 层级 | 工具 | 覆盖率要求 |
|------|------|-----------|
| 后端单元测试 | pytest + pytest-asyncio | Service 层 ≥ 60% |
| 后端 API 测试 | pytest + httpx (TestClient) | 核心 API 100% 覆盖 |
| 前端组件测试 | Vitest + Vue Test Utils | 核心组件（可选） |
| 端到端测试 | 手动验证（4 个演示场景） | 100% 通过 |

---

> **文档类型**：开发规范文档
> **版本**：v1.0
> **创建日期**：2026-05-19
> **状态**：待确认
