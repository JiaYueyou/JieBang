# 多源异构数据驱动岗位和能力图谱构建与动态演化分析研究

## 项目核心开发计划书

---

## 一、项目概述

### 1.1 项目背景
- **比赛类型**：企业命题赛
- **交付物**：完整 Web 系统 + 现场演示
- **时间周期**：1-2 个月（8 周）
- **目标行业**：IT/互联网

### 1.2 核心定位
面向企业 HR 和管理者的 **"IT 岗位人才洞察与决策辅助平台"**，解决三大核心问题：
1. **招聘策略缺乏数据支撑** → 多源数据聚合分析，实时掌握市场人才供给画像
2. **岗位能力需求模糊** → 岗位-能力知识图谱精确建模，输出标准化能力需求清单
3. **存量员工培养与转岗困难** → 技能差距分析 + 可转岗路径推荐

### 1.3 目标用户与使用场景
- **主要用户**：企业 HR / 招聘负责人 / 部门管理者
- **使用场景**：
  - 制定招聘策略时了解市场行情
  - 编写 JD 时参考标准能力模型
  - 评估内部员工是否适合转岗
  - 制定员工培训计划

---

## 二、技术选型

| 层级           | 技术                            | 原因                                       |
| ------------ | ----------------------------- | ---------------------------------------- |
| **后端框架**     | FastAPI (Python 3.10+)        | 异步高性能、原生 Swagger 文档、Python 数据/NLP 生态无缝集成 |
| **前端框架**     | Vue 3 + TypeScript + Vite     | 渐进式框架、学习曲线平缓、组合式 API、团队协作友好              |
| **状态管理**     | Pinia                         | Vue 3 官方推荐、TypeScript 支持好                |
| **路由**       | Vue Router 4                  | Vue 3 配套路由方案                             |
| **UI 组件库**   | Element Plus                  | 国产企业级 Vue 3 组件库、中后台场景成熟                  |
| **图表可视化**    | Apache ECharts                | 国内生态最好、大屏展示效果好                           |
| **图谱可视化**    | AntV G6                       | 阿里出品、专为关系图设计、交互能力强                       |
| **关系型数据库**   | MySQL 8.0                     | 存储结构化业务数据、用户数据、分析结果                      |
| **图数据库**     | Neo4j 5.x                     | 存储岗位-能力知识图谱、支持 Cypher 图查询和图算法            |
| **向量数据库**    | Milvus (standalone)           | 岗位描述语义向量相似度检索                            |
| **缓存/队列**    | Redis 7                       | 缓存热点数据 + Celery 消息队列 Broker              |
| **爬虫框架**     | Scrapy + Playwright           | Scrapy 管理爬虫生命周期，Playwright 处理 JS 渲染页面    |
| **NLP/实体抽取** | spaCy + Transformers + DeepKE | 实体识别、关系抽取、文本向量化                          |
| **任务队列**     | Celery                        | 异步处理数据采集、NLP 处理和分析任务                     |
| **部署**       | Docker Compose                | 一键部署全栈服务，统一开发环境                          |

---

## 三、系统架构

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                   前端展示层 (Vue 3 + TS)                     │
│  仪表盘大屏 │ 图谱浏览器 │ 趋势分析 │ 转岗分析 │ 系统管理      │
└──────────────────────────┬──────────────────────────────────┘
                           │ RESTful API (JSON)
┌──────────────────────────▼──────────────────────────────────┐
│                    API 服务层 (FastAPI)                       │
│  岗位服务 │ 图谱服务 │ 分析服务 │ 转岗服务 │ 认证服务 │ 管理服务 │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    异步任务层 (Celery)                         │
│  爬虫调度 │ 数据清洗 │ NLP实体抽取 │ 图谱更新 │ 趋势分析计算    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                      数据存储层                               │
│  MySQL(业务数据)  Neo4j(知识图谱)  Milvus(语义向量)  Redis(缓存) │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 数据流
1. **采集**：Scrapy 爬虫抓取招聘网站数据 → 清洗标准化 → 存入 MySQL (raw_job / job 表)
2. **抽取**：NLP 流水线抽取实体和关系 → 构建三元组 → 写入 Neo4j
3. **向量化**：岗位描述文本 → BERT 向量 (768d) → 存入 Milvus
4. **分析**：Celery Beat 定时触发 → 计算趋势指标 → 结果写入 MySQL (trend_analysis 表)
5. **查询**：API 层查询各存储层 → 数据聚合 → JSON 返回前端

---

## 四、功能模块详解

### 4.1 数据采集与融合引擎
**目标**：从多源异构数据持续获取 IT 岗位数据，覆盖结构化/非结构化、外部/企业内部四个象限

**外部结构化数据采集**：

| 子功能 | 描述 |
|--------|------|
| 多源爬虫管理 | Boss 直聘、拉勾、讯飞招聘官网（≥3 个数据源） |
| 讯飞专有采集 | 采集讯飞岗位分类体系、事业部归属、研发中心城市分布 |
| 公开数据集导入 | 支持导入 Kaggle 等公开研究数据集 |
| 数据清洗流水线 | 去重、格式标准化、缺失值处理、异常值检测 |
| 异构数据融合 | 岗位名称对齐、技能标签归一化、层级分类映射 |
| 定时采集调度 | Celery Beat 定时增量采集，保持数据新鲜度 |

**企业内部数据导入**：

| 子功能 | 描述 |
|--------|------|
| 结构化数据导入 | 支持 CSV/Excel 格式员工表、培训记录、晋升记录上传与解析 |
| 数据隔离 | 企业数据按 enterprise_id 隔离存储，不同企业数据互不可见 |

**非结构化数据处理**：

| 子功能 | 描述 |
|--------|------|
| 文档解析 | PDF（PyMuPDF）、Word（python-docx）文档文本提取 |
| JD/NLP 提取 | 从非结构化 JD 文本中抽取实体和关系（复用 NLP Pipeline） |
| 简历解析 | 从 PDF/Word 简历中提取技能列表和工作经历 |

### 4.2 知识图谱构建
**目标**：构建 IT 岗位-能力知识图谱

**实体类型**：岗位(Job)、技能(Skill)、工具(Tool)、学历(Degree)、行业(Industry)

**关系类型**：REQUIRES(岗位→技能)、REQUIRES_TOOL(岗位→工具)、REQUIRES_DEGREE(岗位→学历)、RELATED_TO(技能→技能)、BELONGS_TO(岗位→行业)、PROMOTES_TO(岗位→岗位)

**子功能**：
- 基于 DeepKE 的实体识别 + 依存句法分析的关系抽取
- Neo4j 图存储与 Cypher 查询服务
- G6 力导向图可视化，支持节点展开/收起/搜索/过滤

### 4.3 动态演化分析
**目标**：分析岗位需求和技能要求的时间变化趋势

| 子功能 | 可视化形式 |
|--------|------------|
| 岗位需求趋势 | 折线图 / 面积图 |
| 技能热度趋势 | 热力图 / 折线图 |
| 新兴岗位检测 | 标签 + 趋势图 |
| 技能生命周期 | 生命周期曲线图 |
| 地域需求分布 | 地图热力图 |
| 薪资水平趋势 | 箱线图 / 折线图 |
| 学历经验分布 | 饼图 / 柱状图 |

### 4.4 企业决策应用
**目标**：为企业 HR 提供可落地的决策辅助工具

| 子功能     | 描述                                  |
| ------- | ----------------------------------- |
| 人才需求仪表盘 | IT 招聘市场全景：岗位总数、热门技能 Top20、需求趋势、薪资分布 |
| 岗位标准画像  | 输入岗位名称 → 输出能力模型（核心技能、工具、学历、薪资范围）    |
| 转岗可行性分析 | 输入员工技能 → 匹配度打分 → 可转岗岗位列表 + 技能差距清单   |
| 培训方案推荐  | 基于技能差距 → 推荐学习路径 + 预计学习时长            |

### 4.5 AI Agent 智能助手（加分亮点）

**目标**：引入 AI Agent 作为用户与数据之间的自然语言交互层。Agent 理解用户意图，自动编排 Function Call 调用底层服务，以自然语言返回结果。

**为何放在应用层**：Agent 是编排者而非生产者——它不产生新数据，而是理解意图→调用工具→整合结果→生成回答，串联现有的 4 层数据资产。

**Agent 架构**：

```
用户自然语言输入
       ↓
┌────────────────────────────────────────┐
│           AI Agent 引擎                 │
│                                        │
│  ① 意图识别 (星火大模型)                  │
│       ↓                                │
│  ② 工具编排 (LangGraph Function Call)    │
│       ↓                                │
│  ③ 并行调用底层服务                       │
│  ┌──────────┬──────────┬──────────┐    │
│  │MySQL查询  │Neo4j检索  │Milvus搜索│    │
│  │Tool      │Tool       │Tool       │    │
│  └──────────┴──────────┴──────────┘    │
│       ↓                                │
│  ④ 结果聚合 + 大模型润色 → 最终回答         │
└────────────────────────────────────────┘
       ↓
  前端 SSE 流式渲染
```

**核心 Agent Tools（Function Call 定义）**：

| Tool 名称 | 功能 | 调用服务 |
|-----------|------|----------|
| `query_job_market` | 查询岗位市场数据（关键词、城市、薪资） | MySQL + 趋势 API |
| `search_skill_graph` | 查询技能关联图谱（技能→相关技能→相关岗位） | Neo4j Cypher |
| `semantic_search_job` | 语义相似岗位搜索 | Milvus |
| `analyze_transfer` | 员工转岗可行性分析 | TransferService |
| `generate_trend_report` | 生成趋势分析报告 | AnalysisService |
| `compare_job_profiles` | 岗位画像对比（内部 vs 行业） | MySQL + Neo4j |
| `generate_jd` | 智能生成 JD | 模板引擎 + 行业数据 |

**可用场景**：

| 场景 | 示例对话 | Agent 调用链 |
|------|----------|-------------|
| 市场洞察 | "合肥 AI 工程师薪资怎么样？" | query_job_market → 聚合薪资/需求/趋势 |
| 图谱探索 | "Go 语言和哪些技能最相关？" | search_skill_graph → 返回关联网络 |
| 岗位对标 | "我们 Java 岗差行业标准哪些技能？" | compare_job_profiles → 差距清单 |
| 转岗评估 | "张工会 Java、MySQL，能转 AI 吗？" | analyze_transfer → 匹配度+差距 |
| JD 生成 | "帮我写份 NLP 工程师的 JD" | generate_jd → 标准技能+薪资建议 |

**技术选型**：

| 组件 | 选择 | 理由 |
|------|------|------|
| 大模型 | 讯飞星火大模型 (Spark 4.0) | 比赛方核心产品，体现命题契合度 |
| Agent 框架 | LangChain + LangGraph | Function Call 编排成熟，支持条件分支和多轮对话 |
| RAG 知识库 | Milvus + BERT 768d | 复用已有向量库，增强岗位知识检索 |
| 前端交互 | 全局对话浮窗 + SSE 流式渲染 | 不干扰主界面，打字机效果提升体验 |

**降级策略**：若星火 API 不稳定，核心问答预置缓存回复，确保演示场景不受影响。

---

## 五、数据库设计概要

### 5.1 MySQL 核心表

```sql
datasource         (id, name, type, status, last_crawl_time, config)
raw_job            (id, source_id, title, company, description, raw_json, crawl_time)
job                (id, title, standardized_title, level, min_salary, max_salary,
                    experience_required, degree_required, location, industry, post_date,
                    data_source)                                          -- 'crawl'/'import'/'manual'
skill              (id, name, category, alias, description)
job_skill          (job_id, skill_id, importance, mention_count)
trend_analysis     (id, analysis_type, entity_id, time_period, metrics_json)
enterprise_user    (id, company, username, password_hash, role)
employee_profile   (id, enterprise_id, name, current_position, skills_json)
training_record    (id, enterprise_id, employee_id, course_name, score, date)
promotion_record   (id, enterprise_id, employee_id, from_position, to_position, date)
internal_job       (id, enterprise_id, title, department, requirements, status)
iflytek_job        (id, job_id, iflytek_category, research_center, business_unit)
unstructured_doc   (id, enterprise_id, doc_type, file_path, parsed_text, entities_json)
agent_conversation (id, user_id, session_id, query, response, tool_calls_json)
```

### 5.2 Neo4j 图谱模型

```
(:Job {title, level, salary_range})-[:REQUIRES {importance}]->(:Skill {name, category})
(:Job)-[:BELONGS_TO]->(:Industry {name})
(:Job)-[:REQUIRES_TOOL]->(:Tool {name, category})
(:Skill)-[:RELATED_TO {strength}]->(:Skill)
(:Job)-[:PROMOTES_TO]->(:Job)
```

### 5.3 Milvus Collection
- `job_description`：岗位描述文本的 BERT 768 维向量
- 用途：语义相似度搜索、岗位聚类、相似岗位推荐

---

## 六、前端页面设计

| 页面    | 路由            | 核心内容                  | 涉及图表组件                 |
| ----- | ------------- | --------------------- | ---------------------- |
| 首页仪表盘 | `/`           | IT 招聘市场全景大屏           | ECharts: 指标卡、趋势图、地图、词云 |
| 岗位搜索  | `/jobs`       | 岗位列表 + 筛选搜索 + 详情弹窗    | G6: 岗位-技能关联子图          |
| 技能图谱  | `/graph`      | 岗位-技能关联网络交互探索         | G6: 力导向图               |
| 趋势分析  | `/trends`     | 岗位/技能时间趋势、新兴岗位、技能生命周期 | ECharts: 折线图、热力图、箱线图   |
| 企业工作台 | `/enterprise` | 企业专属仪表盘 + 定制报告        | ECharts: 指标卡、对比图       |
| 转岗分析  | `/transfer`   | 员工技能输入 → 可转岗岗位 + 差距对比 | ECharts: 雷达图、柱状对比图     |
| 培训推荐  | `/training`   | 技能学习路径推荐              | ECharts: 路径图、进度图       |
| 系统管理  | `/admin`      | 数据源管理、爬虫调度、系统配置       | 表格 + 状态标签              |

---

## 七、项目目录结构

```
JieBang/
├── backend/                       # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/               # API 路由
│   │   │   ├── jobs.py           # 岗位相关接口
│   │   │   ├── graph.py          # 图谱查询接口
│   │   │   ├── analysis.py       # 分析结果接口
│   │   │   ├── transfer.py       # 转岗分析接口
│   │   │   ├── auth.py           # 认证接口
│   │   │   └── admin.py          # 管理接口
│   │   ├── core/                 # 核心配置
│   │   │   ├── config.py         # 配置管理（环境变量）
│   │   │   ├── security.py       # JWT 认证与授权
│   │   │   └── database.py       # MySQL/Neo4j/Milvus/Redis 连接管理
│   │   ├── models/               # SQLAlchemy ORM 模型
│   │   ├── schemas/              # Pydantic 请求/响应 Schema
│   │   ├── services/             # 业务逻辑层
│   │   │   ├── crawler_service.py
│   │   │   ├── document_service.py   # 非结构化文档解析
│   │   │   ├── nlp_service.py
│   │   │   ├── graph_service.py
│   │   │   ├── analysis_service.py
│   │   │   ├── iflytek_analysis.py   # 讯飞专有分析
│   │   │   ├── transfer_service.py
│   │   │   ├── agent_service.py      # AI Agent 引擎
│   │   │   └── agent_tools.py        # Agent Function Call 工具定义
│   │   ├── tasks/                # Celery 异步任务
│   │   │   ├── crawl_tasks.py
│   │   │   ├── nlp_tasks.py
│   │   │   ├── document_tasks.py
│   │   │   └── analysis_tasks.py
│   │   └── utils/                # 工具函数
│   ├── crawlers/                 # Scrapy 爬虫项目
│   │   ├── spiders/
│   │   │   ├── boss_spider.py
│   │   │   ├── lagou_spider.py
│   │   │   └── iflytek_spider.py     # 讯飞专有爬虫
│   │   ├── pipelines.py
│   │   ├── middlewares.py
│   │   └── items.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                      # Vue 3 前端
│   ├── src/
│   │   ├── views/                # 页面视图
│   │   ├── components/           # 通用组件
│   │   │   ├── charts/           # ECharts 图表组件
│   │   │   ├── graph/            # G6 图谱组件
│   │   │   ├── agent/            # AI Agent 对话组件
│   │   │   └── common/           # 通用业务组件
│   │   ├── router/               # Vue Router 路由配置
│   │   ├── stores/               # Pinia 状态管理
│   │   ├── api/                  # 后端 API 请求封装（axios）
│   │   ├── utils/                # 工具函数
│   │   └── assets/               # 静态资源
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
│
├── docker-compose.yml             # 一键部署编排
│   # services: backend, frontend, mysql, neo4j, milvus, redis, celery-worker, celery-beat
├── docs/
│   ├── requirements.md           # 项目需求与目标文档
│   ├── dev-plan.md               # 本文档：项目核心开发计划书
│   └── dev-spec.md               # 开发规范文档
└── README.md
```

---

## 八、团队分工

### 成员 A：数据采集与处理引擎
**负责模块**：外部数据采集（含讯飞专有）、企业数据导入、非结构化文档处理、NLP 实体关系抽取

| 任务 | 产出 |
|------|------|
| Scrapy 爬虫系统开发（Boss直聘、拉勾、讯飞官网 ≥3 个数据源） | `crawlers/spiders/` |
| 讯飞招聘专有化采集（岗位分类、事业部、研发中心） | `crawlers/spiders/iflytek_spider.py` |
| 反爬中间件（IP 代理池、UA 轮换、频率控制） | `crawlers/middlewares.py` |
| 数据清洗流水线（含讯飞数据标准化） | `crawlers/pipelines.py` |
| 企业内部数据导入（CSV/Excel 上传解析） | `services/crawler_service.py` |
| 非结构化文档解析（PDF/Word 简历和报告） | `services/document_service.py` |
| NLP 实体识别与关系抽取 Pipeline | `services/nlp_service.py` |
| Celery 爬虫、文档处理与 NLP 异步任务 | `tasks/crawl_tasks.py`、`tasks/document_tasks.py`、`tasks/nlp_tasks.py` |

**对外接口**：
- `CrawlerService`：爬虫触发、状态查询、企业数据导入
- `DocumentService`：文档解析、文本提取
- `NLPService`：实体抽取、关系抽取、批量处理

### 成员 B：数据库与知识图谱
**负责模块**：MySQL 设计、Neo4j 图谱（含讯飞子图+企业子图）、Milvus 向量库、Redis 缓存

| 任务 | 产出 |
|------|------|
| MySQL 数据库设计与 SQLAlchemy 模型（含企业表、讯飞表、Agent 表） | `models/` 全部模型 |
| 数据库连接管理（MySQL/Neo4j/Milvus/Redis） | `core/database.py` |
| Neo4j 图谱写入（行业图谱 + 讯飞子图 + 企业子图隔离） | `services/graph_service.py` |
| Neo4j 企业数据隔离方案（不同企业图谱不可互访） | 集成到 `graph_service.py` |
| Milvus 向量存储与语义检索服务 | 集成到 `graph_service.py` |
| 图谱查询 API（按岗位查技能、按技能查岗位、企业内查询等） | `api/v1/graph.py` |
| Redis 缓存策略设计与实现 | 集成到 `core/database.py` |
| Neo4j 约束、索引、初始数据预置脚本 | 初始化脚本 |

**对外接口**：
- `GraphService`：图谱 CRUD、Cypher 查询、语义搜索、子图获取
- 所有数据库连接实例

### 成员 C：后端服务、分析引擎与 AI Agent
**负责模块**：FastAPI 框架、业务逻辑、分析算法（含讯飞对标）、认证系统、AI Agent 引擎

| 任务 | 产出 |
|------|------|
| FastAPI 项目框架搭建与配置管理 | `core/config.py`、`main.py` |
| JWT 用户认证与授权系统 | `core/security.py`、`api/v1/auth.py` |
| 岗位服务（搜索、筛选、详情、标准画像、讯飞 vs 行业对比） | `api/v1/jobs.py`、`services/` |
| 动态演化分析算法与 API | `services/analysis_service.py`、`api/v1/analysis.py` |
| 讯飞对标分析（讯飞 vs 竞品 vs 行业平均） | `services/iflytek_analysis.py` |
| 转岗分析算法与培训推荐 | `services/transfer_service.py`、`api/v1/transfer.py` |
| **AI Agent 引擎**（LangChain + 星火大模型） | **`services/agent_service.py`** |
| **Agent 工具定义与 Function Call 编排** | **`services/agent_tools.py`** |
| **Agent API（对话接口 + SSE 流式响应）** | **`api/v1/agent.py`** |
| 系统管理 API（数据源、调度） | `api/v1/admin.py` |
| Pydantic Schema 定义（请求/响应模型） | `schemas/` 全部 |
| 定时分析任务（Celery Beat） | `tasks/analysis_tasks.py` |

**对外接口**：
- 全部 RESTful API 端点（Swagger 自动生成）
- `AnalysisService`、`TransferService`、`AgentService`、`IFlytekAnalysis` 类
- Agent SSE 流式接口（供前端对话组件调用）

### 成员 D：前端与可视化
**负责模块**：Vue 3 项目、页面开发、图表/图谱集成、AI 助手前端

| 任务 | 产出 |
|------|------|
| Vue 3 + TS + Vite 项目搭建 | 项目脚手架、`vite.config.ts` |
| 路由配置与布局组件（含 AI 助手浮窗入口） | `router/`、`components/common/` |
| 首页仪表盘页面（含讯飞专有数据视图） | `views/Dashboard.vue` |
| 岗位搜索与详情页面（讯飞 vs 行业对比） | `views/JobList.vue`、`views/JobDetail.vue` |
| 技能图谱可视化页面（G6） | `views/GraphExplorer.vue`、`components/graph/` |
| 趋势分析页面（ECharts 图表组） | `views/TrendAnalysis.vue`、`components/charts/` |
| 企业工作台页面（数据导入 + 员工管理） | `views/Enterprise.vue` |
| 转岗分析与培训推荐页面 | `views/TransferAnalysis.vue`、`views/Training.vue` |
| 系统管理页面 | `views/Admin.vue` |
| **AI 助手对话组件（浮窗 + SSE 流式渲染 + 数据卡片）** | **`components/agent/ChatWidget.vue`** |
| API 请求层封装（axios + SSE + 拦截器） | `api/` |
| Pinia 状态管理 | `stores/` |

**依赖接口**：全部后端 API + Agent SSE 流式接口（由成员 C 提供 Swagger 文档）

---

## 九、开发阶段规划（8 周）

### 第一阶段：基础建设（第 1-2 周）
| 周次 | 成员 A | 成员 B | 成员 C | 成员 D |
|------|--------|--------|--------|--------|
| W1 | 调研反爬策略 + 讯飞官网结构分析 | MySQL/Neo4j/Milvus/Redis 环境搭建 | FastAPI 脚手架 + 星火大模型 API 调研 | Vue 3 项目搭建 + 路由 + 布局 |
| W2 | Scrapy + 数据模型定义（含讯飞/企业表） | SQLAlchemy 全量模型 + 建表 | JWT 认证 + LangChain 框架引入 | Element Plus + AI 对话组件原型 |

**W2 里程碑**：环境可启动，前后端通信，星火 API 调通

### 第二阶段：数据与图谱（第 3-4 周）
| 周次 | 成员 A | 成员 B | 成员 C | 成员 D |
|------|--------|--------|--------|--------|
| W3 | Boss 直聘 + 讯飞官网爬虫 | Neo4j 写入（行业+讯飞子图） | 岗位 API + 讯飞对标查询 | 岗位列表与详情页（含对比视图） |
| W4 | 清洗流水线 + NLP 抽取 + 企业数据导入 | Milvus 嵌入 + 图谱查询 API | 岗位画像 API + Agent 工具链定义 | 仪表盘（含讯飞专有视图） |

**W4 里程碑**：数据采集 → 入库 → 图谱构建 → 前端展示全链路跑通

### 第三阶段：分析引擎 + AI Agent（第 5-6 周）
| 周次 | 成员 A | 成员 B | 成员 C | 成员 D |
|------|--------|--------|--------|--------|
| W5 | 拉勾爬虫 + 非结构化文档解析 | 图算法（技能关联、企业子图隔离） | 趋势分析 + Celery + Agent Function Call 工具 | 图谱可视化（G6） |
| W6 | NLP 微调 + 数据融合 | 语义检索优化 | 转岗分析 + Agent 意图识别 + 多轮对话 | Agent 对话组件（SSE）+ 趋势分析页 |

**W6 里程碑**：核心分析可用，Agent 可完成基本问答

### 第四阶段：集成与交付（第 7-8 周）
| 周次 | 成员 A | 成员 B | 成员 C | 成员 D |
|------|--------|--------|--------|--------|
| W7 | 演示数据预置（讯飞+模拟企业） | 性能优化 + 全量数据预置 | Agent 调试 + 报告导出 + 集成测试 | 转岗分析 + 培训推荐页 |
| W8 | 联调 Bug 修复 | 联调 Bug 修复 | API 文档完善 + 联调 | UI 打磨 + Agent 体验优化 |

**W8 里程碑**：Docker Compose 一键启动全栈，5 个演示场景全部通过

---

## 十、关键挑战与应对策略

| 挑战 | 应对策略 |
|------|----------|
| 异构数据融合 | 建立"标准岗位词典"和"技能标签词典"，规则映射 + 相似度匹配兜底 |
| 讯飞官网数据复杂 | 提前分析页面结构，必要时人工采集补充 |
| 实体抽取质量 | 先用少量标注数据微调 NER 模型，再用规则模板补充覆盖 |
| 数据量不足 | 爬虫增量采集 + Kaggle 公开数据集 + 可用星火大模型生成模拟数据演示 |
| 星火 API 波动 | 关键问答预置缓存回复，确保演示不受影响 |
| Agent Function Call 复杂 | 优先实现 2-3 个核心工具，其余简化或预设回复 |
| 图谱动态更新 | Neo4j 增量写入 + 时间戳版本标记，按周执行全量演化分析 |
| 反爬对抗 | IP 代理池 + UA 轮换 + 请求频率控制，必要时手动采集补充 |
| 4 人协作冲突 | 提前约定接口格式（见开发规范文档），前后端通过 Swagger 文档对齐 |

---

## 十一、验证方案

### 端到端演示场景
1. **场景 A**：HR 登录 → 首页仪表盘查看 IT 招聘全景 → 点击 "Python 后端开发" 查看岗位标准画像和市场趋势
2. **场景 B**：打开技能图谱 → 搜索 "Go语言" → 看到关联的岗位和技能网络 → 发现 "Go语言" 与 "云原生" 关联紧密
3. **场景 C**：进入转岗分析 → 输入某 Java 工程师技能列表 → 看到可转岗到 "AI 工程师" 的匹配度评分和技能差距
4. **场景 D**：查看趋势分析 → 选择近 6 个月 → 观察 AI 相关岗位需求增长曲线
5. **场景 E（Agent）**：唤起 AI 助手 → 自然语言问答"合肥 NLP 工程师薪资？"→ Agent 调用工具链回答 → 追问"帮我写份 JD"→ Agent 生成完整 JD

### 性能指标
- 爬虫单次采集 ≥ 200 条，完成 ≤ 10 分钟
- 图谱查询（3 层关系）响应 ≤ 2 秒
- 前端页面首屏加载 ≤ 3 秒
- 转岗分析（10 个目标岗位）≤ 5 秒

### 各阶段检查点
- W2 末：前后端通信验证
- W4 末：数据采集 → 入库 → 图谱构建 → 前端展示全链路跑通
- W6 末：核心分析功能可用
- W8 末：Docker Compose 一键启动，4 个演示场景全部通过

---

> **文档类型**：项目核心开发计划书
> **版本**：v1.1
> **创建日期**：2026-05-19
> **状态**：待确认
