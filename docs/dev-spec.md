# 开发规范文档

## 多源异构数据驱动岗位和能力图谱构建项目

---

## 一、API 接口规范

### 1.1 基础约定

| 项目 | 规范 |
| --- | --- |
| 协议 | HTTPS（生产）/ HTTP（本地开发） |
| 域名 | 开发：`http://localhost:8000` |
| 版本 | URL 路径版本：`/api/v1/` |
| 格式 | 请求/响应均为 `application/json` |
| 编码 | UTF-8 |
| 文档 | FastAPI 自动生成 Swagger UI（`/docs`） |

### 1.2 URL 命名规范

```
# === 新岗位发现（模块一）===
GET    /api/v1/jobs/discover           # 新兴岗位检测结果列表
GET    /api/v1/jobs/discover/{id}      # 岗位定义详情
PUT    /api/v1/jobs/discover/{id}      # 人工优化岗位定义
POST   /api/v1/jobs/discover/trigger   # 触发新岗位检测

# === 能力动态更新（模块二）===
GET    /api/v1/jobs/{id}/changes       # 岗位能力变更列表
GET    /api/v1/jobs/{id}/versions      # 版本历史
GET    /api/v1/jobs/{id}/versions/{v}  # 特定版本快照
GET    /api/v1/changes/{id}            # 单条变更详情（含新增/删除/修改标注）

# === 全景图谱（模块三）===
GET    /api/v1/graph/panorama          # 全景图谱数据（支持 ?stack=ai&level=senior 过滤）
GET    /api/v1/graph/node/{type}/{id}  # 图谱节点详情
GET    /api/v1/graph/expand            # 图谱节点展开（?node_id=X&depth=2）
GET    /api/v1/graph/search            # 图谱模糊搜索
GET    /api/v1/graph/timeline          # 技能需求时序数据（?skill=X&months=6）

# === 人岗匹配（模块四）===
POST   /api/v1/resume/parse            # 上传并解析简历（PDF/Word）
GET    /api/v1/resume/result/{id}      # 获取简历解析结果
POST   /api/v1/matching/analyze        # 人岗匹配分析（传技能列表 + 目标岗位）
GET    /api/v1/matching/gap            # 技能差距详情（?employee_id=X&job_id=Y）
GET    /api/v1/matching/learning-path  # 学习路径推荐

# === 分析 ===
GET    /api/v1/analysis/trends         # 趋势分析数据
GET    /api/v1/analysis/hot-skills     # 热门技能排行
GET    /api/v1/analysis/emerging-skills # 新兴技能检测

# === 岗位基础 ===
GET    /api/v1/jobs                    # 岗位列表（分页+筛选）
GET    /api/v1/jobs/{id}               # 岗位详情
GET    /api/v1/jobs/{id}/skills        # 岗位关联技能

# === 认证 ===
POST   /api/v1/auth/login              # 登录
POST   /api/v1/auth/register           # 注册（简化，演示用单用户）

# === 管理 ===
GET    /api/v1/admin/datasources       # 数据源管理
POST   /api/v1/admin/crawl/trigger     # 触发爬虫
GET    /api/v1/admin/test-cases        # 测试用例管理
```

**命名规则**：
- 资源名用复数名词（`/jobs` 而非 `/job`）
- 动作用 HTTP 方法表达，不在 URL 中用动词（特殊操作如 `discover`、`trigger` 除外）
- 复杂查询使用 query parameters
- 层级资源：`/jobs/{id}/skills`

### 1.3 统一响应格式

所有 API 返回以下标准 JSON 结构：

```json
{
  "code": 200,
  "message": "success",
  "data": { },
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 156,
    "total_pages": 8
  }
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | int | 业务状态码，200 成功 |
| `message` | string | 提示信息，成功为 "success" |
| `data` | any | 响应数据体，列表/对象/null |
| `meta` | object | 分页信息，仅列表接口返回 |

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
| --- | --- |
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 422 | 请求参数校验失败（Pydantic 自动） |
| 500 | 服务器内部错误 |

**业务错误码范围**：

| 范围 | 模块 |
| --- | --- |
| 40001-40099 | 岗位模块 |
| 40101-40199 | 图谱模块 |
| 40201-40299 | 分析模块 |
| 40301-40399 | 匹配模块 |
| 40401-40499 | 简历解析模块 |
| 40501-40599 | 认证模块 |
| 40601-40699 | 管理模块 |

### 1.5 分页规范

```
GET /api/v1/jobs?page=1&page_size=20
```

| 参数 | 类型 | 默认值 | 最大值 |
| --- | --- | --- | --- |
| `page` | int | 1 | - |
| `page_size` | int | 20 | 100 |

### 1.6 认证方式

JWT Bearer Token（演示模式简化为单用户）：

```
Authorization: Bearer <access_token>
```

---

## 二、数据库设计规范

### 2.1 命名规范

| 对象 | 规范 | 示例 |
| --- | --- | --- |
| 数据库名 | 小写 + 下划线 | `jie_bang` |
| 表名 | 小写 + 下划线，单数 | `job`、`test_case` |
| 字段名 | 小写 + 下划线 | `created_at`、`min_salary` |
| 主键 | `id`，INT/BIGINT 自增 | `id` |
| 外键 | `关联表_id` | `job_id`、`skill_id` |
| 索引 | `idx_表名_字段` | `idx_job_title` |
| 唯一索引 | `uk_表名_字段` | `uk_skill_name` |
| 创建时间 | `created_at` (DATETIME) | - |
| 更新时间 | `updated_at` (DATETIME) | - |

### 2.2 字段类型规范

| 数据 | MySQL 类型 |
| --- | --- |
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
| --- | --- |
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
| --- | --- |
| 组件命名 | PascalCase（`JobList.vue`） |
| 组合式 API | 统一使用 `<script setup lang="ts">` |
| CSS | Scoped + BEM 命名（`.job-list__item--active`） |
| 目录 | 页面放 `views/`，复用组件放 `components/` |
| API 调用 | 统一在 `api/` 目录封装，不在组件中直接调用 axios |

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

- **错误处理**：Service 层抛出自定义异常，API 层统一捕获并转换为标准响应
- **日志**：使用 Python `logging` 模块，生产环境 INFO 级别
- **环境变量**：所有敏感配置通过 `.env` 文件读取
- **注释**：仅对非显而易见的逻辑写注释，只写"为什么这样做"
- **AI 生成代码标注**：由 AI 辅助生成的复杂代码块需添加 `# AI-assisted` 注释

---

## 四、Git 协作规范

### 4.1 分支策略

```
main                    # 主分支，只接受经过测试的合并
├── develop             # 开发主分支，所有 feature 合并到此
│   ├── feature/a-data      # 成员 A：数据采集与清洗
│   ├── feature/b-graph     # 成员 B：知识图谱构建
│   ├── feature/c-nlp       # 成员 C：NLP与智能分析
│   ├── feature/d-backend   # 成员 D：后端与平台
│   └── feature/e-frontend  # 成员 E：前端与可视化
```

### 4.2 提交规范

```
<type>(<scope>): <subject>

类型：feat / fix / docs / style / refactor / test / chore
范围：data / graph / nlp / backend / frontend / docs
主题：简短描述（中文，≤50 字）
```

**示例**：
```
feat(data): 完成Boss直聘爬虫开发
feat(graph): 新增岗位-技能关系写入接口
feat(nlp): 完成NER实体抽取Pipeline
fix(backend): 修复匹配度计算除零异常
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
A 将清洗后数据写入 MySQL `job` 表和 `skill` 表。表结构由 B 定义，A 按表结构写入。

**成员 C（NLP）→ 成员 B（图谱）**：
C 调用 B 提供的 `GraphService` 写入图谱三元组：

```python
# 成员 B 提供
class GraphService:
    def create_job_node(self, job_data: dict) -> str: ...
    def create_skill_node(self, skill_data: dict) -> str: ...
    def create_relation(self, from_node: str, to_node: str,
                        relation_type: str, properties: dict = None) -> None: ...
    def batch_import_triples(self, triples: list[dict]) -> int: ...
    def create_version_snapshot(self, job_title: str) -> str: ...
    def get_version_diff(self, job_title: str, v1: str, v2: str) -> dict: ...
```

**成员 D（后端 API）→ 成员 E（前端）**：
通过 RESTful API 交互，D 提供 Swagger 文档，E 据此开发。

### 5.2 Service 层接口定义

各成员暴露的 Service 类方法签名（开发前对齐）：

```python
# === 成员 A 暴露 ===
class CrawlerService:
    async def trigger_crawl(datasource_id: int) -> str: ...
    async def get_crawl_status(task_id: str) -> dict: ...
    async def import_dataset(file_path: str) -> int: ...
    async def get_data_quality_report(datasource_id: int) -> dict: ...

# === 成员 B 暴露 ===
class GraphService:
    async def query_job_skills(job_title: str, depth: int = 1) -> dict: ...
    async def query_skill_jobs(skill_name: str) -> list[dict]: ...
    async def query_related_skills(skill_name: str, top_k: int = 10) -> list[dict]: ...
    async def semantic_search(query: str, top_k: int = 10) -> list[dict]: ...
    async def get_subgraph(node_id: str, depth: int = 2) -> dict: ...
    async def get_panorama(filters: dict = None) -> dict: ...
    async def batch_import_triples(triples: list[dict]) -> int: ...
    async def create_version_snapshot(job_title: str) -> str: ...
    async def get_version_diff(job_title: str, v1: str, v2: str) -> dict: ...
    async def resolve_entity_alias(entity_name: str) -> str: ...

# === 成员 C 暴露 ===
class NLPService:
    async def extract_entities(text: str) -> list[Entity]: ...
    async def extract_relations(text: str) -> list[Relation]: ...
    async def process_job_batch(job_ids: list[int]) -> int: ...
    async def verify_claim_against_graph(claim: str) -> VerificationResult: ...

class ResumeService:
    async def parse_resume(file_path: str) -> ResumeParsingResult: ...
    async def extract_skills_from_text(text: str) -> list[SkillExtraction]: ...

class MatchingService:
    async def analyze_match(employee_skills: list[str], target_job: str) -> MatchResult: ...
    async def calc_skill_gap(employee_skills: list[str], target_job: str) -> SkillGapResult: ...
    async def recommend_learning_path(skill_gaps: list[str]) -> LearningPath: ...

class AnalysisService:
    async def detect_new_jobs() -> list[NewJobCandidate]: ...
    async def detect_capability_changes(job_title: str, months: int = 6) -> ChangeResult: ...
    async def get_job_trend(job_title: str, months: int = 6) -> TrendResult: ...
    async def get_hot_skills(limit: int = 20) -> list[SkillRank]: ...
    async def get_skill_lifecycle(skill_name: str) -> LifecycleData: ...

# === 成员 D 提供所有 API 端点，各成员提供底层 Service ===
# 成员 D 编写 API 路由层，调用 A/B/C 的 Service
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
    level: Optional[str]
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

# === 新岗位发现 ===
class NewJobCandidate(BaseModel):
    id: Optional[int]
    job_name: str
    core_skills: list[str]
    bonus_skills: list[str]
    core_responsibilities: list[str]
    typical_scenarios: list[str]
    confidence: float        # 新岗位置信度
    source_jobs: list[str]   # 来源岗位名称
    status: str = "pending"  # pending / approved / rejected

# === 图谱 ===
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

# === 趋势 ===
class TrendPoint(BaseModel):
    date: str                # "2026-01"
    value: float

class TrendResult(BaseModel):
    entity_name: str
    entity_type: str         # job / skill
    data: list[TrendPoint]
    growth_rate: float

# === 能力变更 ===
class ChangeItem(BaseModel):
    skill_name: str
    change_type: str         # added / removed / modified
    old_value: Optional[str]
    new_value: Optional[str]
    data_source: str
    confidence: float

class ChangeResult(BaseModel):
    job_title: str
    previous_version: str
    current_version: str
    changes: list[ChangeItem]

# === 匹配分析 ===
class MatchResult(BaseModel):
    target_job: str
    overall_match: float     # 0.0 ~ 1.0
    matched_skills: list[str]
    missing_skills: list[str]
    difficulty: str          # easy / medium / hard
    skill_coverage: float

class SkillGapItem(BaseModel):
    skill_name: str
    importance: float
    current_level: str       # 未知 / 入门 / 熟练 / 精通

class SkillGapResult(BaseModel):
    target_job: str
    overall_match: float
    gaps: list[SkillGapItem]

class LearningPath(BaseModel):
    target_job: str
    steps: list[dict]        # [{skill: "Python", time_estimate: "2周", resources: [...]}]
    total_time_estimate: str

# === 简历解析 ===
class ResumeParsingResult(BaseModel):
    raw_text: str
    personal_info: Optional[dict]
    skills: list["SkillExtraction"]
    work_experience: list[dict]
    education: list[dict]
    confidence: float

class SkillExtraction(BaseModel):
    skill_name: str
    skill_category: str      # programming_language / framework / tool / domain_knowledge
    mentions: int
    confidence: float

# === 幻觉验证 ===
class VerificationResult(BaseModel):
    claim_text: str
    verified: bool
    graph_evidence: list[dict]   # 图谱中匹配的节点和关系
    source_count: int             # 支持该声明的独立数据源数量
    confidence: float
    verification_method: str

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
```

---

## 六、数据格式标准

### 6.1 JD 解析标准输出

每次 JD 解析必须返回以下标准格式：

```json
{
  "raw_text": "原始JD文本",
  "job_title": "Java开发工程师",
  "company": "某科技有限公司",
  "required_skills": [
    {"skill_name": "Java", "category": "programming_language", "mentions": 5, "confidence": 0.95},
    {"skill_name": "Spring Boot", "category": "framework", "mentions": 3, "confidence": 0.92}
  ],
  "preferred_skills": [
    {"skill_name": "Docker", "category": "tool", "mentions": 1, "confidence": 0.88}
  ],
  "degree_requirement": "本科及以上",
  "experience_requirement": "3-5年",
  "salary_range": [15000, 25000],
  "responsibilities": ["负责后端服务开发", "参与系统架构设计"],
  "confidence": 0.93
}
```

### 6.2 简历解析标准输出

```json
{
  "raw_text": "简历原始文本",
  "name": "张三",
  "years_experience": 5,
  "current_title": "Java开发工程师",
  "skills": [
    {"skill_name": "Java", "category": "programming_language", "years": 5, "confidence": 0.98},
    {"skill_name": "Spring Boot", "category": "framework", "years": 4, "confidence": 0.96}
  ],
  "work_experience": [
    {"company": "XX公司", "title": "Java开发", "duration_months": 36, "description": "..."}
  ],
  "education": [
    {"school": "XX大学", "degree": "本科", "major": "计算机科学"}
  ],
  "confidence": 0.95
}
```

---

## 七、准确率评测框架

### 7.1 JD 解析准确率（≥90%）

- **评测指标**：提取的技能/要求与人工标注的一致性比例
- **方法**：随机抽样 100 条 JD，2 人独立标注，取并集作为 ground truth
- **公式**：`accuracy = |正确提取项| / |ground truth 项|`
- **最低要求**：≥ 90%

### 7.2 简历提取准确率（≥90%）

- **评测指标**：技能实体提取的 F1 分数
- **方法**：50+ 样本简历，已知技能清单为 ground truth
- **公式**：`F1 = 2 * (precision * recall) / (precision + recall)`
- **最低要求**：F1 ≥ 0.90

### 7.3 匹配准确率（≥90%）

- **评测指标**：系统匹配评分与人工专家判断的一致性
- **方法**：100+ (简历, 岗位) 配对，3 人专家独立评判匹配程度（匹配/不匹配）
- **公式**：`accuracy = |一致判断数| / |总配对数|`
- **最低要求**：≥ 90%

### 7.4 单元测试覆盖率（≥60%）

- **工具**：pytest + pytest-cov
- **目标**：后端 Service 层 ≥ 60% 行覆盖率
- **输出**：HTML 报告，附在提交物中

### 7.5 幻觉防控验证

- **验证机制**：每条 AI 生成的能力声明必须可回查图谱节点验证
- **跨源验证**：每个能力声明至少需 2 个独立数据源支持
- **审计追踪**：每次能力更新记录 `{来源URL, 抽取时间, 置信度, 验证状态}`
- **测试**：准备 20+ 故意错误的声明，验证系统检测率

---

## 八、环境与部署规范

### 8.1 开发环境

| 工具 | 版本 |
| --- | --- |
| Python | 3.10+ |
| Node.js | 18 LTS |
| MySQL | 8.0 |
| Elasticsearch | 8.x |
| Neo4j | 5.x (Community) |
| ChromaDB | latest |
| Redis | 7.x |
| Scrapy | latest | 
| Playwright | latest |
| Docker | 24+ |
| Poetry (Python 依赖管理) | 1.5+ |
| pnpm (前端包管理) | 8+ |

### 8.2 环境变量（`.env` 文件，不入库）

```bash
# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=jie_bang

# Elasticsearch
ES_HOST=localhost
ES_PORT=9200

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# ChromaDB
CHROMA_HOST=localhost
CHROMA_PORT=8001

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256

# 讯飞星火大模型
SPARK_APP_ID=your_app_id
SPARK_API_KEY=your_api_key
SPARK_API_SECRET=your_api_secret
SPARK_API_MODEL=spark-4.0

# API
API_HOST=0.0.0.0
API_PORT=8000
```

### 8.3 Docker Compose 服务编排

`docker-compose.yml` 包含以下服务：
- `mysql`（端口 3306）
- `elasticsearch`（端口 9200）
- `neo4j`（端口 7474/7687）
- `chromadb`（端口 8001）
- `redis`（端口 6379）
- `backend`（FastAPI，端口 8000）
- `frontend`（Vue 3 dev server，端口 5173）
- `celery-worker`（后台任务处理）
- `celery-beat`（定时任务调度）

---

## 九、前后端联调流程

1. **成员 D** 完成 API 开发后，在 Swagger UI（`/docs`）上自测通过
2. **成员 D** 将接口变更同步到 Swagger 文档（自动生成）
3. **成员 E** 在 `api/` 目录创建对应的请求函数，类型引用 `@/types`
4. **成员 E** 本地联调，发现问题在群同步（截图 + 请求参数 + 错误信息）
5. **双方确认** 修复后关闭问题

### 联调检查清单

- [ ] 请求 URL、Method 是否正确
- [ ] 请求参数格式（Query/Body/Path）是否正确
- [ ] 响应 JSON 字段名是否与前端类型定义一致
- [ ] 分页参数是否生效
- [ ] 空数据/错误情况前端是否正确展示
- [ ] Token 过期时前端是否自动跳转登录

---

## 十、测试规范

| 层级 | 工具 | 覆盖率要求 |
| --- | --- | --- |
| 后端单元测试 | pytest + pytest-asyncio | Service 层 ≥ 60% |
| 后端 API 测试 | pytest + httpx (TestClient) | 核心 API 100% 覆盖 |
| 准确率评测 | 自定义评测脚本 | JD 解析/简历提取/匹配 ≥ 90% |
| 幻觉检测测试 | 自定义验证脚本 | 20+ 错误声明检测 |
| 前端组件测试 | Vitest + Vue Test Utils | 核心组件（可选） |
| 端到端测试 | 手动验证（4 个演示场景） | 100% 通过 |

### 测试数据要求

- JD 测试集：≥ 100 条，包含人工标注的 ground truth
- 简历测试集：≥ 50 份，包含已知技能清单
- 匹配测试集：≥ 100 对 (简历, 岗位)，含专家评判结果
- 幻觉测试集：≥ 20 条故意错误的能力声明

---

> **文档类型**：开发规范文档
> **版本**：v2.0
> **创建日期**：2026-05-19
> **更新日期**：2026-06-09
> **状态**：比赛备赛用
