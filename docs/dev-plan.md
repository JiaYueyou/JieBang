# 多源异构数据驱动岗位和能力图谱构建与动态演化分析研究

> 文档类型：早期开发计划
> 状态：历史归档
> 核验日期：2026-08-12；技术选型、人数、接口和完成度均以当前代码及
> [当前实现状态](implementation-status.md) 为准。

## 项目核心开发计划书（5人团队 · AI辅助开发）

---

## 一、项目概述

### 1.1 基本信息

| 项目 | 详情 |
| --- | --- |
| **项目名称** | 多源异构数据驱动岗位和能力图谱构建与动态演化分析研究 |
| **比赛类型** | 企业命题赛（科大讯飞发榜，自主命题） |
| **交付物** | 完整 Web 系统 + 现场演示 |
| **时间周期** | 12 周（约 3 个月） |
| **提交时间** | 暂定 9 月上旬 |
| **目标行业** | IT / 互联网（新一代信息技术领域） |

### 1.2 核心定位

面向竞赛评委的**数据驱动智能决策系统**，核心逻辑：

> 新岗位发现 → 能力图谱动态更新 → 全景可视化 → 人岗匹配诊断 → 改进建议与学习路径

### 1.3 策略重点

普通院校应注重**工程实现、功能完整性、应用场景落地**，而非追求理论创新和论文发表。关键策略：

- 选择一个具体行业深入（IT/互联网），比泛泛覆盖多行业效果好
- 准备真实数据集（1000+ 岗位、500+ 简历样本）
- 设计可量化评估指标，用数据证明系统效果
- 提供 Docker 一键部署方案
- 优先使用科大讯飞相关工具

---

## 二、技术选型

| 层级 | 技术 | 选择理由 |
| --- | --- | --- |
| **后端框架** | FastAPI (Python 3.10+) | 异步高性能、原生 Swagger 文档、Python 数据/NLP 生态无缝集成 |
| **前端框架** | Vue 3 + TypeScript + Vite | 渐进式框架、组合式 API、学习曲线平缓 |
| **状态管理** | Pinia | Vue 3 官方推荐 |
| **路由** | Vue Router 4 | Vue 3 配套 |
| **UI 组件库** | Element Plus | 企业级 Vue 3 组件库 |
| **图表可视化** | Apache ECharts 5 | 国内生态最好、大屏展示效果好 |
| **图谱可视化** | AntV G6 | 阿里出品、专为关系图设计 |
| **关系型数据库** | MySQL 8.0 | 结构化业务数据存储 |
| **搜索引擎** | Elasticsearch 8.x | 全文检索、聚合分析 |
| **图数据库** | Neo4j 5.x | 岗位-能力知识图谱存储 |
| **向量存储** | ChromaDB（可选 Milvus） | RAG 语义检索、轻量部署 |
| **缓存/队列** | Redis 7 | 缓存热点数据 + Celery Broker |
| **爬虫框架** | Scrapy + Playwright | 静态+动态页面覆盖 |
| **NLP 基础** | HanLP | 中文分词/NER 基础能力 |
| **NLP 进阶** | 讯飞星火 API (X2/4.0 Turbo) | 实体抽取、关系推理、匹配分析 |
| **知识图谱** | Neo4j + py2neo | Cypher 查询、图算法 |
| **RAG 框架** | LangChain + ChromaDB | 检索增强生成 |
| **数据分析** | Pandas + NetworkX | 数据处理 + 图算法 |
| **简历解析** | 讯飞文档解析 + 自定义 NER | OCR + 字段提取 |
| **任务队列** | Celery + Redis | 异步任务处理 |
| **部署** | Docker Compose | 一键部署全栈服务 |

---

## 三、系统架构

### 3.1 五层架构

```
┌─────────────────────────────────────────────────────────────┐
│              应用层 (Vue 3 + AntV G6 + ECharts)               │
│  岗位发现 │ 能力更新 │ 图谱可视化 │ 匹配诊断 │ 趋势分析         │
└──────────────────────────┬──────────────────────────────────┘
                           │ RESTful API (JSON)
┌──────────────────────────▼──────────────────────────────────┐
│              分析层 (Pandas + NetworkX)                       │
│  时序图谱快照对比 │ 趋势预测 │ 人岗匹配评分 │ 图算法分析          │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              智能层 (讯飞星火API + LangChain + ChromaDB)       │
│  RAG检索增强 │ 实体抽取 │ 关系推理 │ 幻觉检测与事实校验          │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              知识层 (Neo4j + py2neo + BERT)                   │
│  NER实体抽取 │ 关系抽取 │ 实体对齐与消歧 │ 图谱版本管理           │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              数据层 (Scrapy + Playwright + Pandas)            │
│  多源爬虫集群 │ 数据清洗管道 │ MySQL + ES + 原始文件存储         │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 数据流

1. **采集**：多源爬虫 → 数据清洗 → MySQL (raw_job / job 表) + ES 全文索引
2. **抽取**：NLP 流水线 → 实体+关系三元组 → Neo4j 图谱（带时间戳）
3. **向量化**：岗位描述文本 → BGE-M3 向量化 → ChromaDB
4. **分析**：Celery Beat 定时触发 → 趋势计算 → 结果写入 MySQL
5. **查询**：API 层查询各存储层 → 数据聚合 → JSON 返回前端

---

## 四、功能模块详解

### 4.1 新岗位发现与定义

从多源数据中识别新兴技能组合，自动生成岗位定义（名称、职责、必备技能、加分技能、典型场景），支持人工优化。

### 4.2 既有岗位能力动态更新

对比历史数据，识别岗位能力要求变化，标注新增/删除/修改的能力项，提供版本化管理。

### 4.3 全景图谱可视化

G6 力导向图展示岗位-技能关联网络，支持按技术栈和级别切换视图，技能点级别颗粒度。

### 4.4 人岗匹配度诊断

PDF/Word 简历解析（≥90% 准确率），多维度匹配分析，技能差距清单 + 学习路径推荐。

---

## 五、数据库设计概要

### 5.1 MySQL 核心表

```sql
datasource        (id, name, type, status, last_crawl_time)
raw_job           (id, source_id, title, company, description, raw_json, crawl_time)
job               (id, title, standardized_title, level, min_salary, max_salary,
                   experience_required, degree_required, location, industry, post_date)
skill             (id, name, category, alias, description)
job_skill         (job_id, skill_id, importance, mention_count)
trend_analysis    (id, analysis_type, entity_id, time_period, metrics_json)
graph_snapshot    (id, snapshot_time, change_type, entity_type, entity_id, diff_json)
test_case         (id, jd_text, expected_skills, expected_entities, labeled_by)
hallucination_log (id, claim_text, verified, source_count, confidence, created_at)
```

### 5.2 Neo4j 图谱模型

```
(:Job {title, level, salary_range})
  -[:REQUIRES {importance, version, first_seen, last_seen}]->(:Skill {name, category})
  -[:REQUIRES_TOOL]->(:Tool {name, category})
  -[:BELONGS_TO]->(:Industry {name})
  -[:PROMOTES_TO]->(:Job)

(:Skill)-[:RELATED_TO {strength, co_occurrence}]->(:Skill)
(:Skill)-[:BELONGS_TO]->(:SkillGroup {name})    -- Python、Java 属于"编程语言"组
```

### 5.3 ChromaDB Collection

- `job_description`：岗位描述文本 BGE-M3 向量（1024d）
- 用途：语义相似度搜索、岗位聚类、相似岗位推荐

---

## 六、前端页面设计

| 页面 | 路由 | 核心内容 |
| --- | --- | --- |
| 首页仪表盘 | `/` | IT 招聘市场全景：岗位总数、热门技能 Top20、需求趋势、地域分布 |
| 新岗位发现 | `/discover` | 新兴岗位列表 + 定义生成 + 人工优化界面 |
| 能力动态更新 | `/changes` | 岗位能力变更对比、版本历史、标注视图 |
| 技能图谱 | `/graph` | G6 力导向图，按技术栈/级别切换 |
| 趋势分析 | `/trends` | ECharts 折线/热力/箱线图，岗位/技能趋势 |
| 匹配诊断 | `/matching` | 简历上传 → 提取 → 匹配 → 差距分析雷达图 |
| 学习路径 | `/learning` | 技能差距 → 推荐学习路径图 |
| 系统管理 | `/admin` | 数据源管理、爬虫调度、测试数据管理 |

---

## 七、项目目录结构

```
JieBang/
├── backend/                       # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/               # API 路由
│   │   │   ├── jobs.py           # 岗位发现接口
│   │   │   ├── changes.py        # 能力更新接口
│   │   │   ├── graph.py          # 图谱接口
│   │   │   ├── matching.py       # 匹配诊断接口
│   │   │   ├── analysis.py       # 趋势分析接口
│   │   │   ├── resume.py         # 简历解析接口
│   │   │   ├── auth.py           # 认证接口
│   │   │   └── admin.py          # 管理接口
│   │   ├── core/                 # 核心配置
│   │   ├── models/               # SQLAlchemy ORM
│   │   ├── schemas/              # Pydantic Schema
│   │   ├── services/             # 业务逻辑层
│   │   │   ├── crawler_service.py
│   │   │   ├── nlp_service.py
│   │   │   ├── graph_service.py
│   │   │   ├── analysis_service.py
│   │   │   ├── matching_service.py
│   │   │   └── resume_service.py
│   │   └── tasks/                # Celery 异步任务
│   ├── crawlers/                 # Scrapy 爬虫
│   │   └── spiders/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                      # Vue 3 前端
│   ├── src/
│   │   ├── views/                # 页面视图
│   │   ├── components/           # 通用组件
│   │   │   ├── charts/           # ECharts 组件
│   │   │   ├── graph/            # G6 组件
│   │   │   └── common/           # 业务组件
│   │   ├── router/
│   │   ├── stores/               # Pinia
│   │   ├── api/                  # API 封装
│   │   └── assets/
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml
├── docs/
│   ├── requirements.md
│   ├── dev-plan.md               # 本文档
│   └── dev-spec.md
└── README.md
```

---

## 八、团队分工（5人）

### 总体原则

- 每位成员推荐使用 **Cursor IDE 或 GitHub Copilot** 辅助编码
- 涉及 NLP/推理任务优先调用 **讯飞星火大模型 API**
- 接口先行：各角色先定义接口，再并行开发
- 每周末同步进度，Swagger 文档驱动前后端联调

### 成员 A：数据采集与清洗

**负责**：多源数据爬虫、ETL 清洗管道、数据质量评分、测试数据集构建

| 任务 | 产出 | AI 工具 |
| --- | --- | --- |
| 至少 3 个数据源爬虫开发（Boss直聘、智联招聘、讯飞官网） | `crawlers/spiders/` | Cursor/Copilot 辅助编写爬虫代码 |
| 反爬中间件（IP 代理池、UA 轮换、频率控制） | `crawlers/middlewares.py` | Copilot 生成反爬策略模板 |
| 数据清洗流水线（去重/标准化/异常检测） | `crawlers/pipelines.py` | Cursor 辅助 Pandas 数据处理 |
| 数据质量评分体系 | `services/crawler_service.py` | 星火 API 辅助数据质量判断 |
| 100+ JD 测试数据集标注 | `data/test_jobs.json` | 星火 API 辅助标注 |
| 数据源管理 API | 集成到管理接口 | Copilot 生成 CRUD 模板 |

**对外接口**：
- `CrawlerService`：触发爬虫、状态查询、数据导入
- 写入 MySQL `raw_job`/`job`/`skill` 表（表结构由 B 定义）

### 成员 B：知识图谱构建

**负责**：MySQL 表设计、Neo4j 图谱存储与服务、图谱版本管理、实体消歧

| 任务 | 产出 | AI 工具 |
| --- | --- | --- |
| MySQL 数据库设计与 SQLAlchemy 模型 | `models/` 全部模型 | Cursor 辅助 ORM 模型生成 |
| 多数据库连接管理（MySQL/Neo4j/ES/ChromaDB/Redis） | `core/database.py` | Copilot 辅助连接池配置 |
| Neo4j 图谱写入服务（含时间戳版本标记） | `services/graph_service.py` | Copilot 辅助 Cypher 生成 |
| 图谱查询 API（按岗位查技能、按技能查岗位、多级展开） | `api/v1/graph.py` | Cursor 辅助 API 实现 |
| 实体消歧服务（"Java开发"="Java工程师"） | `services/graph_service.py` | 星火 API 辅助实体对齐 |
| 图谱版本管理与快照 | 集成到 `graph_service.py` | Copilot 辅助快照逻辑 |
| Neo4j 约束、索引、初始数据预置脚本 | 初始化脚本 | Cursor 辅助脚本生成 |

**对外接口**：
- `GraphService`：图谱 CRUD、Cypher 查询、子图获取、版本管理、实体消歧
- 所有数据库连接实例

### 成员 C：NLP 与智能分析

**负责**：NER/关系抽取 Pipeline、新岗位发现算法、能力变更检测、人岗匹配算法、幻觉防控、学习路径推荐

| 任务 | 产出 | AI 工具 |
| --- | --- | --- |
| NER 实体抽取 Pipeline（HanLP + 讯飞星火协同） | `services/nlp_service.py` | 星火 API 做核心 NER |
| "大模型+小模型"协同：星火标注 → BERT-CRF 微调 | `models/ner_model/` | Cursor 辅助训练脚本 |
| 新岗位发现算法（技能聚类 + 增长趋势检测） | `services/analysis_service.py` | 星火 API 辅助模式识别 |
| 既有岗位能力变更检测（时序 diff） | `services/analysis_service.py` | Copilot 辅助算法实现 |
| 简历解析 Pipeline（讯飞文档解析 + NER 字段提取） | `services/resume_service.py` | 讯飞 API 做文档解析 |
| 人岗匹配算法（语义相似度 + 图谱路径距离） | `services/matching_service.py` | 星火 API 辅助语义匹配 |
| 能力差距分析 + 学习路径推荐 | `services/matching_service.py` | 星火 X1.5 做推理 |
| 幻觉防控验证模块（图谱回查 + 多源交叉验证） | `services/nlp_service.py` | Copilot 辅助验证逻辑 |
| 准确率评测框架 | `tests/accuracy/` | Cursor 辅助测试脚本 |

**对外接口**：
- `NLPService`：实体抽取、关系抽取、批量处理
- `ResumeService`：PDF/Word 解析、技能提取
- `MatchingService`：匹配分析、差距计算、路径推荐
- `AnalysisService`：新岗位检测、能力变更检测、趋势计算

### 成员 D：后端与平台

**负责**：FastAPI 框架、全部 API 端点、认证系统、集成测试、Docker 部署、Celery 任务编排

| 任务 | 产出 | AI 工具 |
| --- | --- | --- |
| FastAPI 项目框架搭建与配置管理 | `core/config.py`、`main.py` | Copilot 脚手架生成 |
| JWT 认证与授权（简化单用户模式） | `core/security.py`、`api/v1/auth.py` | Cursor 辅助认证实现 |
| 岗位发现与定义 API | `api/v1/jobs.py` | Copilot 辅助 CRUD 模板 |
| 能力更新 API | `api/v1/changes.py` | Cursor 编写接口 |
| 图谱查询 API（调用 B 的 GraphService） | `api/v1/graph.py` | Cursor 编写接口 |
| 匹配诊断 API（调用 C 的 MatchingService） | `api/v1/matching.py` | Cursor 编写接口 |
| 趋势分析 API | `api/v1/analysis.py` | Copilot 辅助实现 |
| 简历解析 API | `api/v1/resume.py` | Cursor 编写接口 |
| 系统管理 API | `api/v1/admin.py` | Copilot 生成管理接口 |
| Pydantic Schema 定义 | `schemas/` 全部 | Cursor 辅助 Schema 生成 |
| Celery 异步任务编排 | `tasks/` | Copilot 辅助任务定义 |
| 集成测试（API 测试覆盖率 ≥ 60%） | `tests/` | Cursor 辅助测试生成 |
| Docker Compose 编排（全部服务） | `docker-compose.yml` | Copilot 辅助 Docker 配置 |
| Swagger 文档维护 | FastAPI 自动生成 | — |

**对外接口**：
- 全部 RESTful API 端点（Swagger 自动生成文档）
- Docker Compose 一键启动脚本

### 成员 E：前端与可视化

**负责**：Vue 3 项目、全部页面开发、G6/ECharts 图表集成、UI/UX

| 任务 | 产出 | AI 工具 |
| --- | --- | --- |
| Vue 3 + TS + Vite 项目搭建 | 项目脚手架 | Copilot 脚手架生成 |
| 路由配置与布局组件 | `router/`、`components/common/` | Cursor 辅助布局设计 |
| 首页仪表盘页面 | `views/Dashboard.vue` | Copilot 辅助 ECharts 集成 |
| 新岗位发现页面 | `views/Discover.vue` | Cursor 编写页面 |
| 能力动态更新页面 | `views/Changes.vue` | Cursor 编写页面 |
| 技能图谱可视化页面（G6） | `views/GraphExplorer.vue`、`components/graph/` | Copilot 辅助 G6 配置 |
| 趋势分析页面 | `views/TrendAnalysis.vue` | Cursor 辅助 ECharts |
| 匹配诊断页面（简历上传 + 结果展示） | `views/Matching.vue` | Cursor 编写页面 |
| 学习路径页面 | `views/Learning.vue` | Copilot 辅助路径图 |
| 系统管理页面 | `views/Admin.vue` | Copilot 生成表单/表格 |
| API 请求层封装（axios + 拦截器） | `api/` | Cursor 辅助封装 |
| Pinia 状态管理 | `stores/` | Copilot 辅助 Store 定义 |
| UI/UX 打磨 | 全局样式、动画、响应式 | Cursor 辅助 CSS |

**依赖接口**：全部后端 API（由 D 提供 Swagger 文档）

---

## 九、开发阶段规划（12 周）

### 第一阶段：基础建设（第 1-4 周）

| 周次 | A（数据） | B（图谱） | C（NLP） | D（后端） | E（前端） |
| --- | --- | --- | --- | --- | --- |
| W1 | 多源数据源调研、反爬策略分析 | MySQL/Neo4j/ES/Redis 环境搭建 | HanLP + 星火 API 调研、NER 原型测试 | FastAPI 脚手架 + config | Vue 3 项目搭建 + 路由 + 布局 |
| W2 | Scrapy 搭建 + 数据模型定义 | SQLAlchemy 全量模型 + 建表 | NER Pipeline 原型（规则+模型） | JWT 认证 + health API | Element Plus + 页面骨架 |
| W3 | 爬虫开发（Boss 直聘） | Neo4j 图谱写入服务 | 简历解析原型（PDF/Word） | 岗位 CRUD API | 岗位列表与详情页 |
| W4 | 清洗流水线 + 数据质量评分 | 图谱查询 API + 实体消歧服务 | 实体对齐与消歧模块 | 图谱查询 API + 管理 API | 仪表盘页面 |

**里程碑 W4**：多源数据 → 清洗 → 图谱存储 → API 可查 → 前端展示（单条岗位全链路跑通）

### 第二阶段：核心功能（第 5-8 周）

| 周次 | A（数据） | B（图谱） | C（NLP） | D（后端） | E（前端） |
| --- | --- | --- | --- | --- | --- |
| W5 | 爬虫开发（智联招聘） | 图谱时间戳版本管理 | 新岗位发现算法 | 新岗位发现 API | 图谱可视化页面（G6） |
| W6 | 爬虫开发（行业报告解析） | 图谱版本对比查询 | 能力变更检测算法 | 能力更新 API | 能力变更对比页面 |
| W7 | 数据融合（跨源实体对齐） | 多级子图查询优化 | 人岗匹配算法开发 | 匹配诊断 API | 匹配诊断页面 |
| W8 | 100+ JD 测试数据采集 | 测试数据图谱预置 | 学习路径推荐 + 幻觉防控 | 简历解析 API + 分析 API + Celery | 趋势分析 + 学习路径页面 |

**里程碑 W8**：四大核心模块全部可用，可进行完整演示

### 第三阶段：集成与提交（第 9-12 周）

| 周次 | A（数据） | B（图谱） | C（NLP） | D（后端） | E（前端） |
| --- | --- | --- | --- | --- | --- |
| W9 | 数据补充 + 质量验证 | 图谱性能优化 | 准确率评测（三项≥90%） | 单元测试（覆盖率≥60%） | UX 打磨、交互动效 |
| W10 | 演示数据预置（含1新+1旧岗位示例） | 测试数据图谱构建 | 准确率调优 + 幻觉检测验证 | Docker Compose 编排 | 测试报告页面 |
| W11 | Bug 修复 | Bug 修复 | 准确率验证报告 | 集成测试 + 联调 | 演示视频录制准备 |
| W12 | 最终数据包 | 最终图谱导出 | 提交文档支持 | Docker 最终化 + API 文档 | PPT + 演示视频 |

**里程碑 W12**：Docker 一键启动全栈，三项准确率 ≥90%，测试覆盖率 ≥60%，全部提交物就绪

---

## 十、AI 辅助开发指南

### 10.1 推荐工具

| 工具 | 适用场景 | 使用建议 |
| --- | --- | --- |
| **Cursor IDE** | 所有代码开发 | 用 AI 辅助生成样板代码、单元测试、重构 |
| **GitHub Copilot** | 所有代码开发 | 作为 Cursor 的补充，实时代码补全 |
| **讯飞星火 X2/4.0** | NLP 任务核心引擎 | NER 标注生成、关系抽取、语义匹配、JD 生成 |
| **讯飞星火 X1.5** | 复杂推理任务 | 多跳推理、能力差距分析、学习路径规划 |
| **ChatGPT / Claude** | 架构设计、调试 | 方案讨论、代码审查、Bug 分析 |

### 10.2 AI 辅助开发原则

1. **AI 生成代码必须 Review**：所有 AI 生成的代码需经过人工审查，确保逻辑正确和安全性
2. **核心算法需理解原理**：AI 可辅助实现，但团队成员必须能解释算法原理（答辩需要）
3. **测试用 AI 批量生成**：利用 AI 生成大量测试用例，人工筛选和标注
4. **文档用 AI 辅助撰写**：接口文档、注释、README 可借助 AI 生成初稿，人工润色
5. **幻觉防控是关键加分项**：展示 AI 辅助开发的同时，必须展示对 AI 生成内容的管控能力

---

## 十一、关键挑战与应对

| 挑战 | 应对策略 |
| --- | --- |
| 异构数据融合 | 建立"标准岗位词典"和"技能标签词典"，规则映射 + 相似度匹配兜底 |
| 实体消歧困难 | 大模型辅助消歧 + 人工校验；建立实体别名映射词典 |
| 实体抽取质量 | 大模型+小模型协同策略：星火 few-shot 标注 → BERT-CRF 微调 → 规则模板兜底 |
| 数据量不足 | 爬虫增量采集 + Kaggle 公开数据集 + 必要时星火生成模拟数据 |
| 星火 API 波动 | 关键问答预置缓存回复；设计本地模型兜底方案 |
| 三项准确率达标 | 提前设计评测方案；构建高质量人工标注测试集；预留充分调优时间 |
| 图谱动态更新 | Neo4j 增量写入 + 时间戳版本标记；按周执行全量演化分析 |
| 反爬对抗 | IP 代理池 + UA 轮换 + 频率控制；准备公开数据集兜底 |
| 5 人协作冲突 | 接口预先定义好（见 `dev-spec.md`）；Swagger 文档驱动开发 |

---

## 十二、验证方案

### 12.1 端到端演示场景

1. **场景 A（新岗位发现）**：系统自动检测到新兴技能组合 → 生成新岗位定义（含名称、职责、技能、场景）→ 人工审核优化 → 入库
2. **场景 B（能力动态更新）**：选择"Java 开发工程师"→ 对比 6 个月前 vs 现在的技能要求 → 标注新增（RAG/AI）、删除、修改的技能项
3. **场景 C（图谱可视化）**：打开技能图谱 → 搜索"Python" → 展开关联岗位和技能 → 切换到"AI 技术栈"视图 → 切换"高级"级别过滤
4. **场景 D（人岗匹配）**：上传 Java 工程师简历 → 系统提取技能清单 → 匹配 AI 工程师岗位 → 展示匹配度 + 技能差距雷达图 → 推荐学习路径

### 12.2 性能指标

| 指标 | 目标 |
| --- | --- |
| 爬虫单次采集 | ≥ 200 条有效数据，≤ 10 分钟 |
| 图谱查询（3 层关系） | ≤ 2 秒 |
| 前端首屏加载 | ≤ 3 秒 |
| 匹配分析（10 个岗位） | ≤ 5 秒 |
| 简历解析 | ≤ 10 秒/份 |

### 12.3 各阶段检查点

- W4 末：数据采集 → 入库 → 图谱 → API → 前端单条链路跑通
- W8 末：四大核心模块全部可用，可完整演示
- W12 末：Docker 一键启动，三项准确率 ≥90%，测试覆盖率 ≥60%

---

> **文档类型**：项目核心开发计划书（5人团队 · AI辅助开发）
> **版本**：v2.0
> **创建日期**：2026-05-19
> **更新日期**：2026-06-09
> **状态**：比赛备赛用
