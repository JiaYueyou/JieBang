# 用户端后端技术与功能说明

> 文档类型：早期设计与接口草案
> 状态：历史参考，部分内容已与代码漂移
> 核验日期：2026-08-28（`28a4cc5b`）
> 当前代码已注册 auth、positions、resume、match、tailor、learning、favorites、graph 八组
> 路由；实际 Schema、端点和依赖以 `app/` 与运行时 OpenAPI 为准。本文所列 Elasticsearch、
> 讯飞、BERT、完整 RAG、Docker 拓扑等多项仍是目标设计，不应表述为已实现。
> 当前岗位 API 只读依赖 FYZ 共享 `jie_bang` 事实表；JTT 没有独立 SQL 快照或生产 Compose。
> 当前测试为 37 passed、1 failed，覆盖率因缺少 `pytest-cov` 不可复现。

> **项目名称**：多源异构数据驱动岗位和能力图谱构建与动态演化分析研究项目
> **项目定位**：人才分析与决策系统 —— 利用知识图谱与大模型技术，实现从简历解析到人岗匹配的精准决策。

---

## 一、项目背景与定位

### 核心闭环流程

```
新岗位发现 → 能力图谱动态更新 → 全景可视化 → 人岗匹配诊断 → 改进建议与学习路径推荐
```

### 四大功能模块

| 模块 | 说明 |
|---|---|
| 新岗位发现与定义 | 识别新兴岗位，生成岗位名称、核心职责、必备/加分技能、典型应用场景 |
| 既有岗位能力动态更新 | 识别能力要求变化，标注新增/删除/修改的能力项，提供数据源和更新说明 |
| 全景图谱可视化 | 五级知识图谱，支持按技术栈和级别切换视图，颗粒度到技能点 |
| 人岗匹配度诊断 | 简历解析（准确率 ≥ 90%），多维度匹配分析，提供改进建议与学习路径 |

### 硬性指标

- JD 解析准确率 ≥ 90%
- 简历提取准确率 ≥ 90%
- 人岗匹配准确率 ≥ 90%
- 测试数据集 ≥ 100 条 JD
- 单元测试覆盖率 ≥ 60%
- 防幻觉机制必须具备

### 评分权重

| 维度 | 分值 | 关键点 |
|---|---|---|
| 作品完整性 | 30 | 全流程闭环，系统可部署运行 |
| 技术创新性 | 25 | 幻觉防控，多源数据融合机制 |
| 用户体验 | 15 | 界面友好，图谱交互流畅 |
| 实用价值 | 30 | 测试方案完整，三项准确率 ≥ 90% |

---

## 二、推荐技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| Web 框架 | **FastAPI** | 异步高性能，自带 OpenAPI/Swagger 文档 |
| 关系数据库 | **MySQL** | 岗位、简历、用户等结构化数据存储 |
| 搜索引擎 | **Elasticsearch** | 岗位全文检索、技能聚合分析 |
| 知识图谱 | **Neo4j + py2neo** | 图数据库存储岗位-技能关系，Cypher 查询 |
| 大模型推理 | **讯飞星火 X2 / 4.0 Turbo** | 实体抽取、关系推理、人岗匹配、趋势预测 |
| 复杂推理 | **讯飞星火 X1.5** | 多跳推理、能力差距分析、学习路径规划 |
| 文本向量化 | **BGE-M3 / bge-large-zh** | 语义编码，RAG embedding |
| NER 基础 | **HanLP / LAC** | 基础分词、命名实体识别 |
| RAG 框架 | **LangChain + ChromaDB** | 检索增强生成，图谱引导的 RAG |
| 异步任务 | **Celery + Redis** | 简历解析、批量匹配等长任务 |
| 简历解析 | **讯飞文档解析 API + 自定义 NER** | PDF/Word OCR + 字段提取 |
| 数据分析 | **Pandas + NetworkX** | 数据清洗 + 图算法（中心性、社区发现） |
| 容器化 | **Docker + docker-compose** | 一键部署 |

### 大模型策略："大模型 + 小模型" 协同

- **讯飞星火**做 few-shot 标注 → 生成训练数据
- 微调 **BERT-CRF / GlobalPointer** 等轻量 NER 模型
- 兼顾标注质量与推理效率

---

## 三、系统架构（五层）

```
┌──────────────────────────────────────────────────┐
│  应用层：RESTful API (FastAPI) → Vue 3 前端       │
├──────────────────────────────────────────────────┤
│  分析层：时序图谱对比 / 图算法 / 人岗匹配评分      │
│         (NetworkX + 语义相似度 + 图谱路径距离)     │
├──────────────────────────────────────────────────┤
│  智能层：RAG (LangChain + ChromaDB)               │
│         讯飞星火 API / 幻觉检测（图谱回查校验）    │
├──────────────────────────────────────────────────┤
│  知识层：NER 实体抽取 / 关系抽取 / 实体对齐        │
│         Neo4j 图谱存储（带时间戳 + 版本管理）      │
├──────────────────────────────────────────────────┤
│  数据层：爬虫集群 → 数据清洗管道 → MySQL + ES     │
│         多源异构数据 ETL（≥3类数据源）             │
└──────────────────────────────────────────────────┘
```

### 数据流转

1. **数据采集**：Scrapy + Playwright 多源爬取（招聘平台、企业官网、行业报告）
2. **数据清洗**：去重 → 格式统一 → 质量评分 → 时效性标注
3. **知识构建**：NER 抽取 → 大模型关系抽取 → 实体对齐消歧 → Neo4j 图谱
4. **智能分析**：RAG 检索增强 → 大模型推理 → 图谱回查校验 → 结构化输出
5. **应用服务**：RESTful API → 前端消费

---

## 四、API 完整清单

### 基础约定

- Base URL: `/api`
- 认证方式: Bearer Token（`Authorization: Bearer <token>`）
- 通用响应格式:
  ```json
  { "code": 200, "message": "ok", "data": {} }
  ```
- 分页响应格式:
  ```json
  { "code": 200, "message": "ok", "data": { "list": [], "total": 100, "page": 1, "pageSize": 20 } }
  ```

---

### 4.1 认证模块 `/api/auth`

| 方法 | 端点 | 说明 | 请求体 | 响应 data |
|---|---|---|---|---|
| POST | `/auth/login` | 登录 | `{ username, password }` | `{ token, user }` |
| POST | `/auth/register` | 注册 | `{ username, email, password }` | `{ token, user }` |
| POST | `/auth/logout` | 登出 | — | `null` |
| GET | `/auth/profile` | 获取个人信息 | — | `UserProfile` |
| PUT | `/auth/profile` | 更新个人信息 | `Partial<UserProfile>` | `UserProfile` |
| PUT | `/auth/password` | 修改密码 | `{ oldPassword, newPassword }` | `null` |

---

### 4.2 岗位模块 `/api/positions`

| 方法 | 端点 | 说明 | 参数 |
|---|---|---|---|
| GET | `/positions` | 岗位列表 | Query: `category`(new/existing), `keyword`, `techStack`, `page`, `pageSize` |
| GET | `/positions/:id` | 岗位详情 | Path: `id` |
| GET | `/positions/graph` | 知识图谱数据 | Query: `rootTech`（根技术过滤） |

**GET `/positions` 响应 data:**
```json
{
  "list": [
    {
      "id": "ep-1",
      "name": "Java开发工程师",
      "category": "existing",
      "aliases": ["Java工程师", "Java后端开发"],
      "summary": "负责企业级Java应用的设计、开发和维护...",
      "responsibilities": ["参与系统架构设计", "编写高质量Java代码", "..."],
      "requiredSkills": [
        { "id": "sk-1", "name": "Java", "level": "required", "category": "后端" }
      ],
      "preferredSkills": [
        { "id": "sk-2", "name": "Docker", "level": "preferred", "category": "运维" }
      ],
      "industryScenarios": ["电商", "金融", "企业应用"],
      "techStack": ["Java", "Spring Boot", "MySQL", "Redis"],
      "careerLevel": "mid",
      "salaryRange": "15K-30K",
      "skillChanges": [
        {
          "id": "sc-1",
          "skillName": "RAG应用开发",
          "type": "added",
          "date": "2026-06",
          "description": "大模型技术普及，Java工程师需掌握RAG集成能力",
          "source": "招聘平台数据交叉分析"
        }
      ],
      "createdAt": "2026-01-01T00:00:00Z",
      "updatedAt": "2026-06-15T00:00:00Z"
    }
  ],
  "total": 50,
  "page": 1,
  "pageSize": 20
}
```

**GET `/positions/graph` 响应 data（五级图谱数据）:**
```json
{
  "nodes": [
    { "id": "root-java", "label": "Java", "type": "root", "layer": 1 },
    { "id": "pos-java-dev", "label": "Java开发工程师", "type": "position", "layer": 2 },
    { "id": "domain-finance", "label": "金融", "type": "domain_branch", "layer": 3 },
    { "id": "skillset-backend", "label": "后端开发技能", "type": "skillset_branch", "layer": 3 },
    { "id": "mod-microservice", "label": "微服务架构", "type": "module", "layer": 4 },
    { "id": "kp-springboot", "label": "Spring Boot", "type": "knowledge", "layer": 5 }
  ],
  "edges": [
    { "source": "root-java", "target": "pos-java-dev", "relation": "derives", "weight": 5 },
    { "source": "pos-java-dev", "target": "domain-finance", "relation": "applies_to", "weight": 4 },
    { "source": "pos-java-dev", "target": "skillset-backend", "relation": "composes", "weight": 5 },
    { "source": "skillset-backend", "target": "mod-microservice", "relation": "contains", "weight": 5 },
    { "source": "mod-microservice", "target": "kp-springboot", "relation": "includes", "weight": 5 },
    { "source": "kp-springboot", "target": "mod-distributed", "relation": "cross_ref", "weight": 3 }
  ]
}
```

---

### 4.3 简历模块 `/api`

| 方法 | 端点 | 说明 | 请求体 |
|---|---|---|---|
| POST | `/resume/upload` | 上传并解析简历文件 | FormData (multipart, .pdf/.doc/.docx) |
| GET | `/resumes` | 简历列表 | — |
| GET | `/resume/:id` | 简历详情 | — |
| POST | `/resume` | 手动创建简历 | `Partial<ResumeData>` |
| PUT | `/resume/:id` | 更新简历 | `Partial<ResumeData>` |
| DELETE | `/resume/:id` | 删除简历 | — |
| POST | `/resume/:id/duplicate` | 复制简历 | — |

**POST `/resume/upload` 响应 data（解析结果）:**
```json
{
  "id": "r-3",
  "name": "张三的简历",
  "personalInfo": {
    "name": "张三",
    "email": "zhangsan@example.com",
    "phone": "13800138000",
    "location": "北京"
  },
  "jobIntent": {
    "desiredPosition": "Java开发工程师",
    "desiredCity": "北京",
    "salaryExpectation": "15K-25K",
    "workMode": "fulltime"
  },
  "education": [
    { "school": "某某大学", "degree": "本科", "major": "计算机科学", "startDate": "2020-09", "endDate": "2024-06" }
  ],
  "workExperience": [
    { "company": "某科技公司", "position": "Java实习生", "startDate": "2023-07", "endDate": "2024-06", "description": "...", "skills": ["Java", "Spring Boot"] }
  ],
  "projects": [
    { "name": "电商后台系统", "role": "后端开发", "description": "...", "technologies": ["Java", "MySQL", "Redis"], "highlights": ["QPS提升30%"] }
  ],
  "skills": [
    { "id": "sk-1", "name": "Java", "level": "required", "category": "后端" }
  ],
  "selfEvaluation": "热爱技术，喜欢钻研...",
  "sourceFile": "张三_简历.pdf",
  "createdAt": "2026-07-11T10:00:00Z",
  "updatedAt": "2026-07-11T10:00:00Z"
}
```

**简历解析流程（后端需实现）:**
```
PDF/Word 文件 → 讯飞文档解析 API (OCR) → 自定义 NER 模型提取字段
→ 实体识别（姓名、手机、邮箱、学校、公司...）
→ 技能标准化（将提取的技能映射到图谱中的标准技能节点）
→ 返回结构化 ResumeData
```

---

### 4.4 匹配模块 `/api/match`

| 方法 | 端点 | 说明 | 请求体 |
|---|---|---|---|
| POST | `/match` | 单次人岗匹配 | `{ resumeId, positionId }` |
| GET | `/match/result/:resumeId/:positionId` | 获取已有匹配结果 | — |
| GET | `/match/history` | 匹配历史列表 | — |
| POST | `/match/batch` | 批量匹配（一份简历 vs 多个岗位） | `{ resumeId, positionIds[] }` |

**POST `/match` 响应 data:**
```json
{
  "id": "m-1",
  "resumeId": "r-1",
  "positionId": "ep-1",
  "positionName": "Java开发工程师",
  "resumeName": "张三的简历",
  "totalScore": 68,
  "dimensions": [
    { "name": "技能匹配", "score": 72, "weight": 0.4, "details": "核心技能Java、Spring Boot匹配，缺少Docker和微服务经验" },
    { "name": "经验匹配", "score": 65, "weight": 0.3, "details": "1年实习经验，目标岗位要求2-3年" },
    { "name": "学历匹配", "score": 80, "weight": 0.15, "details": "本科学历满足要求" },
    { "name": "综合素质", "score": 55, "weight": 0.15, "details": "缺少团队管理经验" }
  ],
  "gapAnalysis": {
    "missingSkills": [
      { "id": "sk-2", "name": "Docker", "level": "required", "category": "运维" },
      { "id": "sk-3", "name": "微服务架构", "level": "required", "category": "架构" }
    ],
    "weakSkills": [
      { "id": "sk-4", "name": "Redis", "level": "preferred", "category": "后端" }
    ],
    "matchSkills": [
      { "id": "sk-1", "name": "Java", "level": "required", "category": "后端" },
      { "id": "sk-5", "name": "Spring Boot", "level": "required", "category": "后端" }
    ]
  },
  "suggestions": [
    {
      "id": "sg-1",
      "section": "skills",
      "field": "skills",
      "original": "Java",
      "suggested": "Java, Spring Boot, Spring Cloud微服务",
      "reason": "目标岗位明确要求微服务架构经验，建议补充相关技能关键词",
      "changeType": "large",
      "accepted": false
    }
  ],
  "matchDate": "2026-07-11T10:30:00Z"
}
```

**匹配评分算法要点:**
- 不能仅依赖关键词匹配
- 需结合语义理解（BGE-M3 向量相似度）与图谱推理（Neo4j 路径距离）
- 权重可配（技能 40%、经验 30%、学历 15%、综合素质 15%）
- 跨维度关联：例如技能缺失也会影响"综合素质"评分

---

### 4.5 简历优化模块 `/api/tailor`

| 方法 | 端点 | 说明 | 请求体 |
|---|---|---|---|
| GET | `/tailor/suggestions/:resumeId/:positionId` | 获取 AI 优化建议列表 | — |
| POST | `/tailor/accept` | 接受单条建议 | `{ resumeId, suggestionId }` |
| POST | `/tailor/apply-all` | 批量应用建议，生成新简历 | `{ resumeId, suggestionIds[] }` |
| POST | `/tailor/optimize-phrase` | AI 短语润色 | `{ text, style }` |
| POST | `/tailor/save-as-new` | 保存为新的简历版本 | `{ resumeId, suggestionIds[] }` |

**POST `/tailor/optimize-phrase` 请求与响应:**
```json
// Request
{ "text": "负责系统开发工作", "style": "professional" }

// Response data
{
  "suggestions": [
    "主导企业级分布式系统架构设计与核心模块开发",
    "负责高并发场景下的系统研发与性能优化",
    "参与大型业务系统的全生命周期开发与交付"
  ]
}
```

**`style` 可选值:** `professional`（专业）、`concise`（简洁）、`match`（匹配岗位）、`impact`（突出影响力）

**防幻觉机制（见第九节详述）**

---

### 4.6 学习模块 `/api/learning`（待建）

| 方法 | 端点 | 说明 |
|---|---|---|
| GET | `/learning/paths` | 学习路径列表 |
| POST | `/learning/paths` | 创建学习路径 |
| PUT | `/learning/paths/:id` | 更新学习路径 |
| DELETE | `/learning/paths/:id` | 删除学习路径 |
| POST | `/learning/assistant/chat` | AI 学习助手对话 |
| POST | `/learning/assistant/generate-path` | AI 自动生成学习路径 |
| POST | `/learning/assistant/recommend-resources` | AI 推荐学习资源 |
| POST | `/learning/assistant/quiz` | AI 生成学习测试题 |

**POST `/learning/assistant/chat` 请求与响应:**
```json
// Request
{
  "message": "Agent是什么？我想转行做AI开发",
  "context": {
    "resumeId": "r-1",
    "targetPositionId": "np-1"
  },
  "history": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}

// Response data
{
  "reply": "Agent（智能体）是一种能够自主感知环境、做出决策并执行行动的AI系统...",
  "relatedConcepts": [
    { "name": "LangChain", "nodeId": "tech-langchain", "relation": "核心框架" },
    { "name": "Prompt工程", "nodeId": "sk-prompt-eng", "relation": "前置技能" }
  ],
  "suggestedResources": [
    { "title": "LangChain实战课程", "type": "course", "url": "...", "platform": "Coursera" }
  ],
  "followUpQuestions": [
    "Agent和传统程序有什么区别？",
    "学习Agent开发需要什么基础？"
  ]
}
```

**POST `/learning/assistant/generate-path` 请求与响应:**
```json
// Request
{ "positionId": "ep-1", "resumeId": "r-1" }

// Response data
{
  "id": "lp-3",
  "name": "Java工程师学习路径（个性化）",
  "positionId": "ep-1",
  "positionName": "Java开发工程师",
  "steps": [
    {
      "id": "step-1",
      "order": 1,
      "title": "Java核心基础强化",
      "description": "深入理解JVM、并发编程、集合框架",
      "duration": "2-3周",
      "resources": [
        { "id": "res-1", "title": "深入理解Java虚拟机", "type": "book", "url": "...", "platform": "京东" },
        { "id": "res-2", "title": "Java并发编程实战", "type": "course", "url": "...", "platform": "慕课网" }
      ],
      "completed": false
    }
  ],
  "totalDuration": "12周",
  "createdAt": "2026-07-11T11:00:00Z",
  "updatedAt": "2026-07-11T11:00:00Z"
}
```

**POST `/learning/assistant/quiz` 请求与响应:**
```json
// Request
{ "pathId": "lp-3", "stepIds": ["step-1", "step-2"], "questionCount": 5 }

// Response data
{
  "questions": [
    {
      "id": "q-1",
      "type": "choice",
      "question": "以下哪个不是Java垃圾回收器？",
      "options": ["G1", "CMS", "ZGC", "Nginx"],
      "correctAnswer": 3,
      "explanation": "Nginx是Web服务器，不是JVM垃圾回收器"
    }
  ]
}
```

---

### 4.7 收藏模块 `/api/favorites`（待建）

| 方法 | 端点 | 说明 |
|---|---|---|
| GET | `/favorites` | 获取用户收藏的岗位列表 |
| POST | `/favorites/:positionId` | 添加收藏 |
| DELETE | `/favorites/:positionId` | 取消收藏 |
| GET | `/favorites/check/:positionId` | 检查是否已收藏 |

---

## 五、核心数据模型

### JobPosition（岗位）

```python
class JobPosition:
    id: str
    name: str                       # 岗位名称
    category: "new" | "existing"    # 新岗位 / 既有岗位
    aliases: list[str]              # 别名（如"Java开发" = "Java工程师"）
    summary: str                    # 岗位概述
    responsibilities: list[str]     # 核心职责
    requiredSkills: list[Skill]     # 必备技能
    preferredSkills: list[Skill]    # 加分技能
    industryScenarios: list[str]    # 典型行业应用场景
    techStack: list[str]            # 技术栈
    careerLevel: "junior" | "mid" | "senior"
    salaryRange: str                # 薪资范围
    skillChanges: list[SkillChange] | None  # 技能变化历史（仅既有岗位）
    created_at: datetime
    updated_at: datetime

class Skill:
    id: str
    name: str
    level: "required" | "preferred" | "advanced"
    category: str                   # 技术栈分类：前端/后端/AI/大数据等

class SkillChange:
    id: str
    skill_name: str
    type: "added" | "removed" | "modified"
    date: str
    description: str
    source: str                     # 数据来源
```

### ResumeData（简历）

```python
class ResumeData:
    id: str
    name: str                       # 简历别名（用户自定义）
    targetPosition: str | None      # 目标岗位方向
    personalInfo: PersonalInfo
    jobIntent: JobIntent
    education: list[Education]
    workExperience: list[WorkExperience]
    projects: list[Project]
    skills: list[Skill]
    selfEvaluation: str
    sourceFile: str | None          # 上传文件原始名
    created_at: datetime
    updated_at: datetime

class PersonalInfo:
    name: str; email: str; phone: str; location: str; avatar: str | None

class JobIntent:
    desiredPosition: str; desiredCity: str
    salaryExpectation: str; workMode: "fulltime" | "intern" | "remote"

class Education:
    school: str; degree: str; major: str; startDate: str; endDate: str

class WorkExperience:
    company: str; position: str; startDate: str; endDate: str
    description: str; skills: list[str]

class Project:
    name: str; role: str; description: str
    technologies: list[str]; highlights: list[str]
```

### MatchResult（匹配结果）

```python
class MatchResult:
    id: str
    resumeId: str; positionId: str
    positionName: str; resumeName: str
    totalScore: int                         # 0-100
    dimensions: list[MatchDimension]
    gapAnalysis: GapAnalysis
    suggestions: list[ImprovementSuggestion]
    matchDate: str

class MatchDimension:
    name: str       # 技能匹配 / 经验匹配 / 学历匹配 / 综合素质
    score: int      # 0-100
    weight: float
    details: str

class GapAnalysis:
    missingSkills: list[Skill]    # 完全缺失的技能
    weakSkills: list[Skill]       # 薄弱需加强的技能
    matchSkills: list[Skill]      # 已匹配的技能

class ImprovementSuggestion:
    id: str
    section: str    # skills / workExperience / education / selfEvaluation
    field: str
    original: str
    suggested: str
    reason: str
    changeType: "small" | "large"
    accepted: bool
```

### 图谱数据模型（五级）

```python
class GraphNode:
    id: str
    label: str
    type: "root" | "position" | "domain_branch" | "skillset_branch" | "module" | "knowledge"
    layer: 1 | 2 | 3 | 4 | 5
    rootId: str | None     # 所属根技术 ID，用于快速过滤

class GraphEdge:
    source: str
    target: str
    relation: "derives" | "applies_to" | "composes" | "contains" | "includes" | "cross_ref"
    weight: int
```

### 学习路径

```python
class LearningPath:
    id: str
    name: str
    positionId: str; positionName: str
    steps: list[LearningStep]
    totalDuration: str
    created_at: datetime; updated_at: datetime

class LearningStep:
    id: str; order: int
    title: str; description: str; duration: str
    resources: list[LearningResource]
    completed: bool

class LearningResource:
    id: str; title: str
    type: "course" | "book" | "article" | "project" | "video"
    url: str; platform: str
```

---

## 六、知识图谱设计

### 五级节点层级

```
Level 1 (root)        核心技术/编程语言        Java, Python, JavaScript
       │                derives
Level 2 (position)    对应行业岗位              Java开发工程师, 大数据工程师
       │               ┌─ applies_to (应用领域)
       │               │                       电商, 金融, 企业应用
Level 3 (branch)      ─┤
       │               └─ composes (技能集合)
       │                                       后端开发技能, 系统架构技能
       │                  contains
Level 4 (module)      专项能力模块              微服务架构, 数据库设计, 分布式系统
       │                  includes
Level 5 (knowledge)   细分知识点                 Spring Boot, SQL优化, Kafka

       ═══════════════ cross_ref (跨分支多对多连接) ═══════════════
```

### 边关系类型

| 关系 | 方向 | 含义 |
|---|---|---|
| `derives` | Root → Position | 核心技术衍生出岗位 |
| `applies_to` | Position → Domain Branch | 岗位应用于某业务领域 |
| `composes` | Position → Skillset Branch | 岗位需要的技能集合 |
| `contains` | Branch → Module | 技能集合拆分为模块 |
| `includes` | Module → Knowledge | 模块包含的知识点 |
| `cross_ref` | 任意跨层 | 多对多交叉关联 |

### Neo4j 存储方案

```cypher
// 节点标签: Root, Position, DomainBranch, SkillsetBranch, Module, Knowledge
// 节点属性: id, label, layer, category, rootId, description, created_at, version

// 创建索引
CREATE INDEX node_id FOR (n:GraphNode) ON (n.id);
CREATE INDEX node_layer FOR (n:GraphNode) ON (n.layer);
CREATE INDEX node_root FOR (n:GraphNode) ON (n.rootId);

// 示例：Java 根节点 → Java开发工程师
CREATE (r:Root {id: 'root-java', label: 'Java', layer: 1})
CREATE (p:Position {id: 'pos-java-dev', label: 'Java开发工程师', layer: 2, rootId: 'root-java'})
CREATE (r)-[:DERIVES {weight: 5}]->(p)
```

### 版本化管理

- 每个图谱节点携带 `version` 和 `valid_from` / `valid_to` 时间戳
- 查询时指定 `AS OF TIMESTAMP` 获取历史快照
- 支持"某技能在过去 N 个月的需求变化"查询

---

## 七、两大智能体

### Agent 1: 简历优化智能体

**对应前端页面**: `ResumeTailor.vue` (`/resume/tailor/:resumeId/:positionId`)
**对应 API**: `/api/tailor/*`

#### 功能概述

| 能力 | 说明 |
|---|---|
| 优化建议生成 | 输入简历 + 目标岗位 → 逐条生成 diff 建议（原文 vs 优化后 + 理由） |
| 短语润色 | 输入一段文本 + 风格 → 返回 3 个优化版本 |
| 批量应用 | 将已接受的建议合并，生成新版本简历 |
| 幻觉防控 | 每条建议经过 Neo4j 图谱回查验证 |

#### 核心流程

```
1. 接收请求（resumeId + positionId）
2. 从 MySQL 加载简历和岗位数据
3. 从 Neo4j 查询岗位要求的完整技能树（含隐含技能、前置技能）
4. 组装 Prompt：
   - System: "你是简历优化专家。根据岗位要求为求职者提供简历修改建议。"
   - Context: 岗位要求（技能、职责、行业场景）+ 简历内容
   - Instruction: 逐段对比，生成 diff 建议（格式：section, original, suggested, reason, changeType）
5. 调用讯飞星火 API 生成建议
6. 图谱回查校验（防幻觉）：
   - 遍历每条建议
   - 对于"技能建议"，查询 Neo4j 确认建议的技能确实属于目标岗位的技能树
   - 对于"经验建议"，验证涉及的技术栈与岗位匹配
   - 校验失败的建议标记 verified: false 并附带警告
7. 返回结构化建议列表
```

#### 防幻觉策略详解

```python
def verify_suggestion(suggestion, position_id, graph_db):
    """图谱回查校验单条建议"""

    # 1. 技能类建议：提取建议中新增的技能名
    if suggestion.section == "skills":
        new_skills = extract_skill_names(suggestion.suggested)
        for skill in new_skills:
            # 在 Neo4j 中查询该技能是否属于目标岗位的技能树
            exists = graph_db.query("""
                MATCH (p:Position {id: $position_id})
                -[:COMPOSES*1..3]->(k:Knowledge {label: $skill})
                RETURN count(k) > 0
            """, position_id=position_id, skill=skill)

            if not exists:
                suggestion.verified = False
                suggestion.warning = f"技能 '{skill}' 未在目标岗位知识图谱中找到，请人工确认"
                continue

        suggestion.verified = True

    # 2. 经验类建议：验证技术栈匹配
    if suggestion.section == "workExperience":
        technologies = extract_tech_names(suggestion.suggested)
        for tech in technologies:
            related = graph_db.query("""
                MATCH (p:Position {id: $position_id})
                -[:COMPOSES|CONTAINS|INCLUDES*1..3]->(n {label: $tech})
                RETURN count(n) > 0
            """, position_id=position_id, tech=tech)

            if not related:
                suggestion.verified = False
                suggestion.warning = f"技术 '{tech}' 与目标岗位关联度低"

    return suggestion
```

#### 短语润色流程

```
1. 接收 text + style (professional/concise/match/impact)
2. 组装 Prompt（不涉及图谱回查，仅做文本优化）
3. 调用讯飞星火 API
4. 返回 3 个优化版本
```

---

### Agent 2: 学习助手智能体

**对应前端页面**: `LearningIndex.vue` (`/learning`) + `FloatingAIButton.vue`
**对应 API**: `/api/learning/assistant/*`

#### 功能概述

| 能力 | 说明 |
|---|---|
| 对话问答 | 用户问职业/技术问题，AI 结合知识图谱给出带上下文的回答 |
| 学习路径生成 | 指定目标岗位 + 当前简历 → 生成个性化分步学习路径 |
| 资源推荐 | 按知识点推荐视频/课程/书籍/文章，标注平台和难度 |
| 学习测试 | 根据已学内容生成选择题/简答题，检验掌握程度 |
| 上下文感知 | 结合用户简历和目标岗位进行个性化输出 |

#### 对话问答流程

```
1. 接收用户消息 + 对话历史 + 上下文（resumeId, targetPositionId）
2. 意图识别（规则 or 小模型）:
   - "什么是X" / "解释X"      → 概念解释
   - "如何学习X" / "转行到X"  → 学习建议
   - "推荐资源"               → 资源推荐
3. 从 Neo4j 知识图谱检索相关概念:
   - 查询目标岗位的技能树
   - 查询用户缺失技能的前置依赖
   - 查询相关技术的上下游关系
4. 从 ChromaDB 检索相关学习资源文档（RAG）
5. 组装 Prompt（System角色: 学习导师 + 图谱上下文 + RAG检索结果 + 用户简历）
6. 调用讯飞星火 API 生成回答
7. 解析结构化输出:
   - reply: Markdown 格式回答
   - relatedConcepts: 关联概念列表（含图谱节点ID）
   - suggestedResources: 推荐资源列表
   - followUpQuestions: 建议追问
8. 返回
```

#### 学习路径生成流程

```
1. 接收 positionId + resumeId
2. 加载岗位完整技能树（Neo4j）
3. 计算用户技能差距（比较简历技能 vs 岗位要求）
4. 按依赖关系排序学习顺序（拓扑排序）:
   - 先学基础/前置技能
   - 再学核心/必备技能
   - 最后学进阶/加分技能
5. 为每个学习步骤:
   - 从 ChromaDB RAG 检索匹配的学习资源
   - 估算学习时长
   - 生成步骤描述
6. 组装完整 LearningPath 对象返回
```

#### 学习测试生成

```
1. 接收 pathId + stepIds + questionCount
2. 加载用户已完成的步骤涉及的知识点（从 Neo4j 查询模块→知识点的关系）
3. 组装 Prompt: "根据以下知识点生成 N 道测试题..."
4. 调用讯飞星火 API
5. 解析并格式化为题目列表（选择题/简答题）
6. 附带正确答案和解析
```

---

## 八、核心算法

### 8.1 人岗匹配评分

```
综合评分 = Σ(维度分 × 权重)

维度:
- 技能匹配 (40%): 基于语义向量相似度 + 图谱最短路径距离
  - 语义部分: BGE-M3 将简历技能和岗位技能向量化，计算余弦相似度
  - 图谱部分: 在 Neo4j 中计算简历技能节点到岗位技能节点的加权最短路径
  - 缺一不可: 关键词匹配作为基线，语义和图谱互补

- 经验匹配 (30%): 工作年限、行业领域、项目规模
  - 年限: 分段函数映射到 0-100 分
  - 行业: 基于行业分类的 Jaccard 相似度

- 学历匹配 (15%): 学历层次、专业相关度
  - 学历层次: 博士100/硕士85/本科70/大专50/...
  - 专业: 基于专业分类树的距离

- 综合素质 (15%): 沟通能力、项目影响力、技术深度
  - 基于简历中的项目描述和自评进行语义分析
```

### 8.2 新岗位发现

```
1. 多源数据采集（招聘网站 + 行业报告 + 技术博客）
2. 技能共现分析:
   - 提取近期招聘数据中新出现的技能组合
   - 计算技能共现频率的时序变化
3. 聚类:
   - 使用 NetworkX 社区发现算法
   - 将高频共现的新技能聚类为候选岗位
4. 岗位定义生成:
   - 组装 Prompt（聚类技能 + 行业上下文）
   - 调用讯飞星火生成: 岗位名称、职责、必备/加分技能、应用场景
5. 图谱写入:
   - 在 Neo4j 中创建新 Position 节点
   - 关联技能节点
   - 标记置信度和数据来源
```

### 8.3 既有岗位动态更新

```
1. 定期抓取目标岗位的最新 JD
2. NER 提取最新技能要求
3. 与历史快照对比:
   - 新增技能: 历史上不存在，当前出现
   - 删除技能: 历史上存在，当前消失
   - 修改技能: 描述/重要度/层级变化
4. 生成 SkillChange 记录:
   - 标注数据来源（多条来源交叉验证）
   - 标注更新时间
   - 标注置信度
5. 更新 Neo4j 图谱节点（带版本时间戳）
```

### 8.4 简历解析（NER 提取）

```
1. 文件上传 → 讯飞文档解析 API
   - PDF/Word → 纯文本 + 版面分析
2. 基础 NER（HanLP）:
   - 人名、手机号、邮箱、地名、学校名、公司名
3. 结构化字段提取（微调 BERT-CRF）:
   - 教育经历: 学校 + 学历 + 专业 + 时间
   - 工作经历: 公司 + 职位 + 时间 + 描述
   - 项目经历: 项目名 + 角色 + 技术栈
   - 技能: 技能名 → 映射到标准技能词表（从图谱中获取）
4. 技能标准化:
   - "SpringBoot" / "spring boot" / "Spring Boot框架" → "Spring Boot"
   - 别名映射表从 Neo4j 图谱动态获取
```

---

## 九、幻觉防控策略

### 核心原则

> 所有 AI 生成的内容在返回用户之前，必须经过可验证的事实核对。

### 四层防控体系

```
┌─────────────────────────────────────────────┐
│ Layer 1: Prompt 约束                         │
│ → System Prompt 明确要求不编造不存在的内容     │
│ → 要求标注信息来源和置信度                     │
├─────────────────────────────────────────────┤
│ Layer 2: RAG 检索增强                        │
│ → 先从 ChromaDB 检索真实数据再生成回答         │
│ → 图谱结构化知识注入 RAG 上下文               │
├─────────────────────────────────────────────┤
│ Layer 3: 图谱回查校验（核心）                  │
│ → 每条 AI 输出中的实体与 Neo4j 图谱交叉比对    │
│ → 技能是否存在于岗位技能树? 技术栈是否匹配?    │
│ → 校验失败 → 标记 verified: false + 警告      │
├─────────────────────────────────────────────┤
│ Layer 4: 多源交叉验证                         │
│ → 关键结论需要 ≥2 个独立数据源支持            │
│ → 标注每个结论的数据来源和采集时间             │
└─────────────────────────────────────────────┘
```

### 具体实现

```python
# 每条 AI 输出的标准包装
class VerifiedOutput:
    content: str                # AI 生成内容
    confidence: float           # 置信度 0.0-1.0
    verified: bool              # 是否通过图谱校验
    data_sources: list[str]     # 数据来源（招聘平台/行业报告/企业官网）
    warnings: list[str] | None  # 校验警告
    graph_nodes: list[str]      # 引用的图谱节点 ID
```

### 校验失败处理

- **技能不存在于图谱**: 标记警告 "该技能为 AI 推断，尚未在现有数据中充分验证"
- **结论无数据源支撑**: 降级为 "建议" 而非 "结论"
- **多源验证矛盾**: 标注 "存在争议，待进一步确认"

---

## 十、部署运维

### Docker Compose 编排

```yaml
services:
  api:
    build: .
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=mysql://user:pass@mysql:3306/jiebang
      - NEO4J_URI=bolt://neo4j:7687
      - ES_HOST=http://elasticsearch:9200
      - REDIS_URL=redis://redis:6379
      - XUNFEI_APP_ID=${XUNFEI_APP_ID}
      - XUNFEI_API_KEY=${XUNFEI_API_KEY}
    depends_on: [mysql, neo4j, elasticsearch, redis]

  mysql:
    image: mysql:8.0
    volumes: ["./data/mysql:/var/lib/mysql"]

  neo4j:
    image: neo4j:5
    volumes: ["./data/neo4j:/data"]

  elasticsearch:
    image: elasticsearch:8.12

  redis:
    image: redis:7-alpine

  celery-worker:
    build: .
    command: celery -A app.core.celery_app worker -l info
    depends_on: [redis, mysql]

  chromadb:
    image: chromadb/chroma
```

### 环境变量

| 变量 | 说明 |
|---|---|
| `DATABASE_URL` | MySQL 连接字符串 |
| `NEO4J_URI` | Neo4j Bolt 连接 |
| `ES_HOST` | Elasticsearch 地址 |
| `REDIS_URL` | Redis 连接 |
| `XUNFEI_APP_ID` | 讯飞星火 App ID |
| `XUNFEI_API_KEY` | 讯飞星火 API Key |
| `XUNFEI_API_SECRET` | 讯飞星火 API Secret |
| `SECRET_KEY` | JWT 签名密钥 |
| `CHROMADB_PATH` | ChromaDB 持久化路径 |

### 测试要求

- 单元测试覆盖率 ≥ 60%
- 测试数据集 ≥ 100 条 JD
- 需覆盖: 所有 API 端点、匹配算法、图谱查询、防幻觉校验逻辑
- 推荐工具: pytest + pytest-asyncio + pytest-cov

---

## 附录：前端 API 调用对照表

便于后端开发时快速对照前端期望的 API 格式：

| 前端文件 | 调用的 API |
|---|---|
| `api/auth.ts` | `/auth/login`, `/auth/register`, `/auth/logout`, `/auth/profile` |
| `api/positions.ts` | `/positions` (GET), `/positions/:id`, `/positions/graph` |
| `api/resume.ts` | `/resume/upload`, `/resumes`, `/resume/:id`, `/resume` (POST/PUT/DELETE), `/resume/:id/duplicate` |
| `api/match.ts` | `/match` (POST), `/match/result/:rid/:pid`, `/match/history`, `/match/batch` |
| `api/tailor.ts` | `/tailor/suggestions/:rid/:pid`, `/tailor/accept`, `/tailor/apply-all`, `/tailor/optimize-phrase`, `/tailor/save-as-new` |
| 待建 | `/learning/*`, `/favorites/*` |
