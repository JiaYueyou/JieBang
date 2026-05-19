# 多源异构数据驱动岗位和能力图谱构建与动态演化分析研究

## 项目需求与目标文档

---

## 一、项目概述

### 1.1 基本信息

| 项目       | 详情                         |
| -------- | -------------------------- |
| **项目名称** | 多源异构数据驱动岗位和能力图谱构建与动态演化分析研究 |
| **简称**   | IT 岗位人才洞察与决策辅助平台           |
| **比赛类型** | 企业命题赛（科大讯飞发榜）              |
| **交付物**  | 完整 Web 系统 + 现场演示           |
| **时间周期** | 8 周（1-2 个月）                |
| **目标行业** | IT / 互联网                   |
| **目标企业** | 以科大讯飞为核心案例，做专有化深度分析        |

### 1.2 项目背景

当前企业在 IT 人才招聘和管理中面临三大困境：

1. **招聘策略凭经验，缺乏数据支撑** — HR 不清楚市场上各岗位的真实供需情况，薪资定价和招聘节奏全凭感觉
2. **岗位能力需求模糊** — JD 编写依赖模板复制，缺乏对岗位所需技能的精确理解，导致招进来的人与真实需求不匹配
3. **存量员工的培养和转岗缺乏依据** — 企业不知道现有员工距离目标岗位有多大差距，应该培训哪些技能，投入多少资源

本项目的目标是通过**多源异构数据**（外部招聘数据 + 企业内部数据 + 结构化数据 + 非结构化数据）的采集与融合，构建 IT 行业的岗位-能力知识图谱，并引入 **AI Agent 智能助手**，提供动态演化分析和企业决策辅助，解决上述三大痛点。项目以**科大讯飞**为核心案例，进行专有化深度定制。

### 1.2.1 数据源分类

本项目处理的"多源异构"数据涵盖四个象限：

| | 结构化 | 非结构化 |
|------|----------|----------|
| **外部数据** | 招聘网站岗位信息（Boss直聘、拉勾、讯飞官网） | JD 描述文本、行业报告 PDF、政策文件 |
| **企业内部数据** | 员工信息表、培训记录、晋升/转岗记录 | 绩效评语、面试记录、简历文本 |

### 1.3 目标用户

- **主要用户**：企业 HR、招聘负责人、部门管理者
- **次要用户**：企业员工（查看自身转岗可能性）、企业培训部门

### 1.4 核心价值

| 痛点 | 解决方案 | 预期效果 |
|------|----------|----------|
| 招聘策略缺乏数据 | 多源数据聚合，实时市场供给画像 | HR 可基于数据制定招聘策略 |
| 岗位能力需求模糊 | 岗位-能力知识图谱精确建模 | 输出标准化的岗位能力模型 |
| 员工培养转岗困难 | 技能差距分析 + 转岗路径推荐 | 精准识别培训方向，降低转岗风险 |

---

## 二、功能需求

### 2.1 数据采集与融合引擎（成员 A）

**需求描述**：从多个异构数据源（外部招聘网站 + 企业内部数据 + 结构化 + 非结构化）持续获取 IT 岗位数据，清洗、标准化并融合为统一数据模型。

**外部招聘网站采集**：

| 需求编号   | 需求描述                        | 优先级 |
| ------ | --------------------------- | --- |
| REQ-A1 | 从 Boss 直聘、拉勾等主流招聘网站采集岗位数据   | P0  |
| REQ-A2 | 从科大讯飞招聘官网采集岗位数据，做专有化设计      | P0  |
| REQ-A3 | 支持导入公开研究数据集（如 Kaggle 招聘数据集） | P1  |
| REQ-A4 | 数据去重、格式标准化、异常值检测与清洗         | P0  |
| REQ-A5 | 不同来源的岗位名称对齐和技能标签归一化         | P0  |
| REQ-A6 | 定时增量采集，保持数据新鲜度              | P1  |
| REQ-A7 | 反爬对抗：IP 代理池、UA 轮换、请求频率控制    | P1  |

**企业内部数据导入**：

| 需求编号 | 需求描述 | 优先级 |
|----------|----------|--------|
| REQ-A8 | 支持企业上传员工信息表（Excel/CSV），解析并入库 | P0 |
| REQ-A9 | 支持企业上传历史培训记录、晋升/转岗记录 | P1 |
| REQ-A10 | 企业内部员工数据与外部市场数据隔离存储，按企业维度管理 | P0 |

**非结构化数据处理**：

| 需求编号 | 需求描述 | 优先级 |
|----------|----------|--------|
| REQ-A11 | JD 描述文本的 NLP 实体抽取（技能、工具、学历等） | P0 |
| REQ-A12 | 简历文本解析：从 PDF/Word 简历中提取技能和工作经历 | P1 |
| REQ-A13 | 行业报告 PDF 解析与关键信息提取 | P2 |
| REQ-A14 | 绩效评语、面试记录等非结构化文本的情感分析与能力标签提取 | P2 |

**讯飞招聘专有化数据设计**：

| 需求编号 | 需求描述 | 优先级 |
|----------|----------|--------|
| REQ-A15 | 采集科大讯飞招聘官网的完整岗位信息（含岗位类别、城市、技能要求） | P0 |
| REQ-A16 | 建立讯飞特有的岗位分类体系（AI 研究员、语音算法、NLP 工程师、教育产品经理等） | P0 |
| REQ-A17 | 构建讯飞专属岗位-技能知识图谱，与行业通用图谱形成对比 | P0 |
| REQ-A18 | 采集讯飞竞品企业（百度、阿里、腾讯等）的 AI 岗位数据，用于对标分析 | P1 |

**验收标准**：
- 单次爬虫采集 ≥ 200 条有效岗位数据，含讯飞官网 ≥ 30 条，完成时间 ≤ 10 分钟
- 数据融合后，同一岗位在不同来源的数据能正确合并（去重准确率 ≥ 90%）
- 清洗后的数据字段完整率 ≥ 85%（关键字段：岗位名、公司、技能、薪资、地点）
- 企业数据导入支持 CSV/Excel 格式，字段映射自动识别

### 2.2 知识图谱构建（成员 B）

**需求描述**：从清洗后的岗位数据中抽取实体和关系，构建 IT 岗位-能力知识图谱。

| 需求编号 | 需求描述 | 优先级 |
|----------|----------|--------|
| REQ-B1 | 从岗位描述文本中抽取实体：岗位、技能、工具、学历、行业 | P0 |
| REQ-B2 | 抽取实体间关系：岗位→技能、技能→技能、岗位→行业等 | P0 |
| REQ-B3 | Neo4j 图数据库存储，支持 Cypher 查询 | P0 |
| REQ-B4 | 岗位描述文本向量化（BERT），存入 Milvus，支持语义相似度搜索 | P1 |
| REQ-B5 | 图谱查询接口：按岗位查技能、按技能查岗位、技能关联网络 | P0 |
| REQ-B6 | 图谱可视化：G6 力导向图，支持节点展开/收起/搜索/过滤 | P0 |

**实体与关系模型**：

```
实体：Job（岗位）、Skill（技能）、Tool（工具）、Degree（学历）、Industry（行业）

关系：
  (Job)-[:REQUIRES]->(Skill)          岗位要求某技能
  (Job)-[:REQUIRES_TOOL]->(Tool)      岗位要求某工具
  (Job)-[:REQUIRES_DEGREE]->(Degree)  岗位学历要求
  (Job)-[:BELONGS_TO]->(Industry)     岗位所属行业
  (Skill)-[:RELATED_TO]->(Skill)      技能间关联关系
  (Job)-[:PROMOTES_TO]->(Job)         岗位晋升路径
```

**验收标准**：
- 实体抽取准确率 ≥ 80%（基于人工抽检 100 条数据）
- 图谱查询（3 层关系）响应时间 ≤ 2 秒
- 图谱可视化页面能正常加载并交互（1000 节点内不卡顿）

### 2.3 动态演化分析（成员 C）

**需求描述**：基于历史岗位数据，分析岗位需求和技能要求随时间的变化趋势。

| 需求编号 | 需求描述 | 优先级 |
|----------|----------|--------|
| REQ-C1 | 岗位需求趋势：各岗位招聘量随时间变化（折线图/面积图） | P0 |
| REQ-C2 | 技能热度趋势：各技能被提及频率变化（热力图/折线图） | P0 |
| REQ-C3 | 新兴岗位检测：识别近期快速增长的新兴岗位 | P1 |
| REQ-C4 | 技能生命周期：技能从出现→增长→饱和→衰退的周期分析 | P1 |
| REQ-C5 | 地域需求分布：不同城市对岗位的需求差异（地图热力图） | P1 |
| REQ-C6 | 薪资水平趋势：各岗位薪资随时间变化（箱线图/折线图） | P0 |
| REQ-C7 | 学历经验分布：不同岗位的学历/经验要求分布（饼图/柱状图） | P1 |

**核心指标**：
- 需求增长速率 = 本期需求数 / 上期需求数 - 1
- 技能关联度 = Jaccard 相似度（基于技能在岗位中的共现频率）
- 岗位迁移难度 = 1 - (两岗位共有技能数 / 目标岗位总技能数)
- 技能新颖度 = 首次出现时间 + 近期增长斜率

**验收标准**：
- 趋势分析结果与原始数据验证一致（抽样 10 个岗位/技能，手动核对趋势方向）
- 分析计算完成后 10 秒内返回结果

### 2.4 企业决策应用（成员 C + 成员 D）

**需求描述**：为企业 HR 提供可落地的决策辅助工具。

| 需求编号 | 需求描述 | 优先级 |
|----------|----------|--------|
| REQ-D1 | 人才需求仪表盘：IT 招聘市场全景大屏 | P0 |
| REQ-D2 | 岗位标准画像：输入岗位名 → 输出能力模型 | P0 |
| REQ-D3 | 转岗可行性分析：输入员工技能 → 匹配度打分 → 可转岗列表 | P0 |
| REQ-D4 | 技能差距清单：目标岗位要求 vs 员工现有技能的对比 | P0 |
| REQ-D5 | 培训方案推荐：基于技能差距推荐学习路径 | P1 |
| REQ-D6 | 报告导出（PDF/Excel） | P2 |

**转岗匹配算法**：

```
匹配度 = |员工已有技能 ∩ 目标岗位要求技能| / |目标岗位要求技能|

难度评级：
  ≥ 70%  → 容易（easy）
  40-70% → 中等（medium）
  < 40%  → 困难（hard）
```

**验收标准**：
- 转岗分析（10 个目标岗位）计算时间 ≤ 5 秒
- 岗位标准画像至少包含：核心技能 Top 10、薪资范围、学历要求、经验要求
- 4 个核心演示场景全部可走通

### 2.5 AI Agent 智能助手（成员 C × 成员 D 协作）

**需求描述**：引入 AI Agent 作为用户与数据之间的自然语言交互层。Agent 理解用户意图，自动调用底层数据服务（MySQL 查询、图谱检索、语义搜索、趋势分析），整合多源结果，以自然语言和可视化组合的形式返回答案。

**Agent 核心能力**：

| 需求编号 | 需求描述 | 优先级 |
|----------|----------|--------|
| REQ-E1 | **市场洞察问答**：用户自然语言提问（如"合肥 AI 工程师薪资怎么样？"），Agent 自动查询数据库并回答 | P0 |
| REQ-E2 | **岗位对标分析**：输入岗位名，Agent 自动对比企业内部岗位与行业标准的能力差异 | P1 |
| REQ-E3 | **JD 智能生成**：输入岗位名和目标企业，Agent 生成包含标准技能要求和薪资建议的 JD | P1 |
| REQ-E4 | **转岗评估对话**：自然语言描述员工情况，Agent 自动提取技能、匹配岗位、输出差距分析 | P0 |
| REQ-E5 | **趋势预警问答**：如"最近三个月增长最快的技能是什么？"Agent 调用趋势分析 API 回答 | P1 |
| REQ-E6 | **自动报告生成**：如"生成本周 IT 人才市场周报"，Agent 聚合多个分析指标，填充模板导出 | P2 |

**Agent 技术方案**：

| 组件 | 选择 | 理由 |
|------|------|------|
| **大模型** | 讯飞星火大模型 (Spark 4.0) | 比赛方科大讯飞核心产品，天然契合命题 |
| **Agent 框架** | LangChain / LangGraph | Function Call 工具编排成熟，支持多轮对话 |
| **RAG 知识增强** | Milvus + BERT Embedding | 复用已有向量库，增强岗位知识检索 |
| **前端交互** | 对话浮窗 + 侧边栏助手 | 不干扰主界面，随时可唤出 |

**Agent 工具链**（Agent 可调用的底层能力）：

```
Agent 意图识别 → Function Call 调度
├── query_job_market(keyword, city)    → MySQL + 趋势分析
├── search_skill_graph(skill_name)     → Neo4j Cypher 查询
├── semantic_search_job(query)         → Milvus 向量检索
├── analyze_transfer(employee_skills)  → 转岗分析引擎
├── generate_trend_report(period)      → 趋势分析 API
├── compare_job_profiles(job_a, job_b) → 图谱对比
└── generate_jd(job_title, company)    → 模板 + 行业数据
```

**验收标准**：
- Agent 能正确理解 5 类核心意图（市场洞察、岗位对标、转岗评估、趋势问答、JD 生成）
- 单轮问答响应时间 ≤ 8 秒
- Function Call 工具调用成功率 ≥ 90%
- Agent 回答包含数据来源引用

---

## 三、技术架构

### 3.1 技术栈

| 层级 | 技术选型 | 选型理由 |
|------|----------|----------|
| **后端框架** | FastAPI (Python 3.10+) | 异步高性能、原生 Swagger 文档、Python 数据/NLP 生态无缝集成 |
| **前端框架** | Vue 3 + TypeScript + Vite | 渐进式框架、组合式 API、学习曲线平缓、团队协作友好 |
| **状态管理** | Pinia | Vue 3 官方推荐、TypeScript 支持好 |
| **路由** | Vue Router 4 | Vue 3 配套路由方案 |
| **UI 组件库** | Element Plus | 国产企业级 Vue 3 组件库、中后台场景成熟 |
| **图表可视化** | Apache ECharts 5 | 国内生态最好、大屏展示效果好、文档完善 |
| **图谱可视化** | AntV G6 5 | 阿里出品、专为关系图设计、交互能力强 |
| **关系型数据库** | MySQL 8.0 | 存储结构化业务数据、用户数据、分析结果 |
| **图数据库** | Neo4j 5.x | 存储岗位-能力知识图谱、支持 Cypher 图查询和图算法 |
| **向量数据库** | Milvus 2.3+ (standalone) | 岗位描述语义向量相似度检索 |
| **缓存/消息队列** | Redis 7 | 缓存热点数据 + Celery 消息队列 Broker |
| **爬虫框架** | Scrapy + Playwright | Scrapy 管理爬虫生命周期，Playwright 处理 JS 渲染 |
| **NLP** | spaCy + Transformers + DeepKE | 实体识别、关系抽取、文本向量化 |
| **文档解析** | PyMuPDF + python-docx | PDF/Word 简历和报告的文本提取 |
| **大模型** | 讯飞星火大模型 (Spark 4.0) | 比赛方核心产品，Agent 推理与生成 |
| **Agent 框架** | LangChain + LangGraph | Function Call 工具编排、多轮对话管理 |
| **异步任务** | Celery | 异步处理数据采集、NLP 处理和分析任务 |
| **部署** | Docker Compose | 一键部署全栈服务、统一开发环境 |

### 3.2 系统架构图

```
┌──────────────────────────────────────────────────────────────┐
│                   前端展示层 (Vue 3 + TS)                      │
│  仪表盘 │ 图谱 │ 趋势 │ 转岗 │ 企业 │ 管理 │ AI助手(对话浮窗)  │
└──────────────────────────┬───────────────────────────────────┘
                           │ RESTful API (JSON)
┌──────────────────────────▼───────────────────────────────────┐
│                   AI Agent 层 (LangChain + 星火大模型)          │
│  意图识别 │ 工具编排(Function Call) │ RAG检索 │ 多轮对话管理     │
└──────────────────────────┬───────────────────────────────────┘
                           │ 调用底层服务
┌──────────────────────────▼───────────────────────────────────┐
│                    API 服务层 (FastAPI)                        │
│  岗位服务 │ 图谱服务 │ 分析服务 │ 转岗服务 │ 认证服务 │ 管理服务 │
│  数据导入服务(企业数据/非结构化) │ Agent工具接口                │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                    异步任务层 (Celery)                          │
│  爬虫调度 │ 数据清洗 │ NLP抽取 │ 文档解析 │ 图谱更新 │ 趋势计算  │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                      数据存储层                                │
│  MySQL(业务数据)  Neo4j(知识图谱)  Milvus(语义向量)  Redis(缓存) │
└──────────────────────────────────────────────────────────────┘
```

### 3.3 数据流

**外部招聘数据流**：
```
招聘网站(Boss/拉勾/讯飞官网) → Scrapy爬虫 → 数据清洗 → MySQL(job表)
                                                        ↓
                                                  NLP实体抽取 → 三元组
                                                        ↓
                                                   Neo4j 图谱
```

**企业内部数据流**：
```
企业上传(员工表/培训记录/简历) → 格式解析(CSV/Excel/PDF/Word)
                                    ↓
                              结构化数据 → MySQL(employee_profile/training_record)
                              非结构化文本 → NLP抽取 → Neo4j 图谱 / Milvus 向量
```

**Agent 交互流**：
```
用户自然语言问题 → Agent意图识别 → Function Call调度
                                      ↓
                    ┌─────────────────┼─────────────────┐
                    ↓                 ↓                   ↓
              MySQL查询         Neo4j图检索        Milvus语义搜索
                    ↓                 ↓                   ↓
                    └─────────────────┼─────────────────┘
                                      ↓
                              结果聚合 + 星火大模型润色 → 自然语言回答 + 可视化
```

**分析计算流**：
```
Celery Beat 定时触发 → 计算趋势指标 → MySQL(trend_analysis)
    ├── 行业通用分析（全市场数据）
    └── 讯飞专有分析（讯飞 vs 行业对标）
                    ↓
              API → 前端图表 / Agent 调用
```

### 3.4 数据库设计

**MySQL 核心表**：

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| `datasource` | 数据源管理 | name, type, status, last_crawl_time |
| `raw_job` | 原始岗位数据 | title, company, description, raw_json, crawl_time |
| `job` | 清洗后岗位数据 | standardized_title, level, salary_range, skills |
| `skill` | 技能词典 | name, category, alias |
| `job_skill` | 岗位-技能关联 | job_id, skill_id, importance |
| `trend_analysis` | 趋势分析结果 | analysis_type, entity_id, time_period, metrics_json |
| `enterprise_user` | 企业用户 | company, username, password_hash |
| `employee_profile` | 员工档案 | enterprise_id, name, current_position, skills_json |
| `training_record` | 培训记录 | enterprise_id, employee_id, course_name, score, date |
| `promotion_record` | 晋升/转岗记录 | enterprise_id, employee_id, from_position, to_position, date |
| `internal_job` | 企业内部岗位 | enterprise_id, title, department, requirements, status |
| `iflytek_job` | 科大讯飞专有岗位 | job_id, iflytek_category, research_center, business_unit |
| `unstructured_doc` | 非结构化文档 | enterprise_id, doc_type, file_path, parsed_text, entities_json |
| `agent_conversation` | Agent 对话记录 | user_id, session_id, query, response, tool_calls_json |

**Neo4j 图谱模型**：
```
# 行业通用图谱
(:Job)-[:REQUIRES]->(:Skill)
(:Job)-[:REQUIRES_TOOL]->(:Tool)
(:Job)-[:BELONGS_TO]->(:Industry)
(:Skill)-[:RELATED_TO]->(:Skill)
(:Job)-[:PROMOTES_TO]->(:Job)

# 讯飞专有图谱（叠加层）
(:IFlytekJob)-[:REQUIRES]->(:Skill)
(:IFlytekJob)-[:BELONGS_TO]->(:IFlytekBU)        # 讯飞事业部
(:IFlytekJob)-[:LOCATED_AT]->(:ResearchCenter)    # 研发中心

# 企业内部图谱（企业独立子图）
(:InternalPosition)-[:REQUIRES]->(:Skill)
(:Employee)-[:HAS_SKILL {level}]->(:Skill)
(:Employee)-[:HOLDS]->(:InternalPosition)
(:Employee)-[:TRANSFERRED_TO {date}]->(:InternalPosition)
```

---

## 四、前端页面规划

| 页面 | 路由 | 核心内容 | 图表类型 |
|------|------|----------|----------|
| 首页仪表盘 | `/` | 岗位总数、热门技能 Top20、需求趋势、薪资分布 | ECharts 指标卡 + 趋势图 + 地图 |
| 岗位搜索 | `/jobs` | 岗位列表 + 筛选 + 搜索 + 详情弹窗 + 能力雷达图 | 表格 + G6 子图 + ECharts 雷达图 |
| 技能图谱 | `/graph` | 岗位-技能关联网络交互探索 | G6 力导向图 |
| 趋势分析 | `/trends` | 岗位/技能时间趋势、新兴岗位、技能生命周期 | ECharts 折线/热力/箱线图 |
| 企业工作台 | `/enterprise` | 企业专属仪表盘 + 定制报告 | ECharts 指标卡 + 对比图 |
| 转岗分析 | `/transfer` | 员工技能输入 → 可转岗岗位列表 + 技能差距对比 | ECharts 雷达图 + 柱状对比图 |
| 培训推荐 | `/training` | 技能学习路径推荐 | 路径图 + 进度图 |
| 系统管理 | `/admin` | 数据源管理、爬虫调度 | 表格 + 状态标签 |
| AI 助手 | 全局浮窗 | 自然语言问答、JD 生成、市场洞察 | 对话界面 + 数据卡片 |

---

## 五、团队分工

### 5.1 成员 A：数据采集与处理引擎

**核心职责**：外部数据采集、企业数据导入、非结构化数据处理、NLP 实体抽取

| 任务项 | 技术/工具 | 产出 |
|--------|-----------|------|
| 招聘网站爬虫（Boss直聘、拉勾、讯飞官网 ≥3 个数据源） | Scrapy + Playwright | `crawlers/spiders/` |
| 讯飞招聘专有化采集（岗位分类、事业部、研发中心） | Scrapy | `crawlers/spiders/iflytek_spider.py` |
| 反爬中间件 | IP 代理池、UA 轮换 | `crawlers/middlewares.py` |
| 数据清洗流水线（含讯飞数据标准化） | Python + Pandas | `crawlers/pipelines.py` |
| 企业内部数据导入（CSV/Excel 员工表、培训记录） | Python + pandas | `services/crawler_service.py` |
| 非结构化文档解析（PDF/Word 简历、JD 文本） | PyMuPDF + python-docx | `services/document_service.py` |
| NLP 实体识别 + 关系抽取 | DeepKE + spaCy + Transformers | `services/nlp_service.py` |
| 爬虫与 NLP 异步任务 | Celery | `tasks/crawl_tasks.py`、`tasks/nlp_tasks.py` |

**对外接口**：
- `CrawlerService`：爬虫触发、状态查询、数据集导入
- `DocumentService`：文档解析、文本提取
- `NLPService`：实体抽取、关系抽取、批量处理

### 5.2 成员 B：数据库与知识图谱

**核心职责**：数据存储、图谱构建、向量检索、缓存

| 任务项 | 技术/工具 | 产出 |
|--------|-----------|------|
| MySQL 数据库设计 | SQLAlchemy ORM | `models/` 全部模型 |
| Neo4j 图谱存储与查询 | Neo4j Python Driver + Cypher | `services/graph_service.py` |
| Milvus 向量存储与语义检索 | pymilvus + BERT 768d | 集成到 `graph_service.py` |
| Redis 缓存策略 | redis-py | 集成到 `core/database.py` |
| 数据库连接管理 | 多数据库统一管理 | `core/database.py` |
| 图谱查询 API | FastAPI | `api/v1/graph.py` |
| 初始化脚本 | Cypher + Python | Neo4j 约束、索引、预置数据 |

**对外接口**：
- `GraphService`：图谱 CRUD、Cypher 查询、语义搜索、子图获取
- 所有数据库连接实例

### 5.3 成员 C：后端服务、分析引擎与 AI Agent

**核心职责**：API 框架、业务逻辑、分析算法、认证系统、AI Agent 引擎

| 任务项 | 技术/工具 | 产出 |
|--------|-----------|------|
| FastAPI 项目框架搭建 | FastAPI + Pydantic | `main.py`、`core/config.py` |
| JWT 认证与授权 | python-jose + passlib | `core/security.py`、`api/v1/auth.py` |
| 岗位服务（搜索/筛选/详情/画像） | FastAPI + SQLAlchemy | `api/v1/jobs.py` + Service |
| 动态演化分析 | 趋势计算、新兴检测、生命周期 | `services/analysis_service.py` |
| 讯飞对标分析（讯飞 vs 竞品 vs 行业） | 统计分析 | `services/iflytek_analysis.py` |
| 转岗分析与培训推荐 | 匹配度计算、差距分析 | `services/transfer_service.py` |
| **AI Agent 引擎** | **LangChain + 星火大模型** | **`services/agent_service.py`** |
| Agent 工具定义与 Function Call 编排 | LangGraph | `services/agent_tools.py` |
| Agent API 接口（对话、流式响应） | FastAPI + SSE | `api/v1/agent.py` |
| 系统管理 API | 数据源管理、爬虫调度 | `api/v1/admin.py` |
| Pydantic Schema | 请求/响应模型 | `schemas/` 全部 |
| 定时分析任务 | Celery Beat | `tasks/analysis_tasks.py` |
| 报告导出 | PDF/Excel | 工具模块 |

**对外接口**：
- 全部 RESTful API 端点（Swagger 文档自动生成）
- `AnalysisService`、`TransferService`、`AgentService` 类

### 5.4 成员 D：前端与可视化

**核心职责**：Vue 3 项目、页面开发、图表/图谱集成、AI 助手前端

| 任务项 | 技术/工具 | 产出 |
|--------|-----------|------|
| Vue 3 项目搭建 | Vue 3 + TS + Vite + Pinia + Vue Router | 项目脚手架 |
| 首页仪表盘（含讯飞专有数据视图） | Element Plus + ECharts | `views/Dashboard.vue` |
| 岗位搜索与详情页（讯飞 vs 行业对比） | 表格 + 筛选 + 雷达图 | `views/JobList.vue`、`views/JobDetail.vue` |
| 技能图谱可视化 | AntV G6 | `views/GraphExplorer.vue` |
| 趋势分析页面 | ECharts（折线/热力/箱线/地图） | `views/TrendAnalysis.vue` |
| 企业工作台（数据导入 + 员工管理） | Element Plus 表单 + ECharts | `views/Enterprise.vue` |
| 转岗分析页面 | 雷达图 + 柱状对比 | `views/TransferAnalysis.vue` |
| 培训推荐页面 | 路径图 | `views/Training.vue` |
| 系统管理页面 | 表格 + 表单 | `views/Admin.vue` |
| **AI 助手对话组件** | **对话浮窗 + SSE 流式渲染 + 数据卡片** | **`components/agent/ChatWidget.vue`** |
| API 请求层 | axios + 拦截器 + 错误处理 + SSE | `api/` |
| 状态管理 | Pinia stores | `stores/` |

**依赖接口**：全部后端 API + Agent SSE 流式接口（由成员 C 提供）

---

## 六、项目目录结构

```
JieBang/
├── backend/                       # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/               # API 路由层
│   │   │   ├── jobs.py           # 岗位接口
│   │   │   ├── graph.py          # 图谱接口
│   │   │   ├── analysis.py       # 分析接口
│   │   │   ├── transfer.py       # 转岗接口
│   │   │   ├── auth.py           # 认证接口
│   │   │   └── admin.py          # 管理接口
│   │   ├── core/                 # 核心配置
│   │   │   ├── config.py         # 环境变量管理
│   │   │   ├── security.py       # JWT 认证
│   │   │   └── database.py       # 多数据库连接
│   │   ├── models/               # SQLAlchemy 模型
│   │   ├── schemas/              # Pydantic Schema
│   │   ├── services/             # 业务逻辑
│   │   │   ├── crawler_service.py
│   │   │   ├── nlp_service.py
│   │   │   ├── graph_service.py
│   │   │   ├── analysis_service.py
│   │   │   └── transfer_service.py
│   │   ├── tasks/                # Celery 任务
│   │   │   ├── crawl_tasks.py
│   │   │   ├── nlp_tasks.py
│   │   │   └── analysis_tasks.py
│   │   └── utils/
│   ├── crawlers/                 # Scrapy 爬虫
│   │   ├── spiders/
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
│   │   │   ├── charts/           # ECharts 组件
│   │   │   ├── graph/            # G6 组件
│   │   │   └── common/           # 业务组件
│   │   ├── router/               # 路由配置
│   │   ├── stores/               # Pinia 状态
│   │   ├── api/                  # API 封装
│   │   ├── utils/
│   │   └── assets/
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
│
├── docker-compose.yml             # 服务编排
│   # services: backend, frontend, mysql, neo4j, milvus,
│   #           redis, celery-worker, celery-beat
│
├── docs/
│   ├── requirements.md           # 本文档：项目需求与目标
│   └── dev-spec.md               # 开发规范文档
└── README.md
```

---

## 七、开发阶段规划

### 第一阶段：基础建设（第 1-2 周）
| 成员 | 第 1 周 | 第 2 周 |
|------|---------|---------|
| A | 调研招聘网站反爬策略 + 讯飞官网结构分析 | Scrapy 项目搭建 + 数据模型定义 |
| B | MySQL、Neo4j、Milvus、Redis 环境搭建 | SQLAlchemy 模型编写（含企业表、讯飞表）+ 建表 |
| C | FastAPI 脚手架 + 配置管理 + 星火大模型 API 调研 | JWT 认证 + 用户 API + LangChain 框架引入 |
| D | Vue 3 项目搭建 + 路由 + 布局 | Element Plus 集成 + AI 助手对话组件原型 |

**里程碑**：前后端可通信（`GET /api/v1/health` → 前端可调用），星火 API 调通

### 第二阶段：数据与图谱（第 3-4 周）
| 成员 | 第 3 周 | 第 4 周 |
|------|---------|---------|
| A | 完成 Boss 直聘 + 讯飞官网爬虫 | 数据清洗流水线 + NLP 实体抽取 + 企业数据导入 |
| B | Neo4j 图谱写入服务（含讯飞子图） | Milvus 嵌入 + 图谱查询 API |
| C | 岗位 API（搜索/筛选/详情）+ 讯飞对标查询 | 岗位标准画像 API + Agent 基础工具链定义 |
| D | 岗位列表与详情页面 | 仪表盘页面（含讯飞专有数据视图） |

**里程碑**：数据采集 → 入库 → NLP 抽取 → 图谱可查 → 前端展示全链路跑通

### 第三阶段：分析引擎 + AI Agent（第 5-6 周）
| 成员 | 第 5 周 | 第 6 周 |
|------|---------|---------|
| A | 拉勾爬虫 + 非结构化文档解析 | NLP 模型微调 + 数据融合优化 |
| B | 图算法（技能关联、岗位相似度）+ 企业子图隔离 | 语义检索优化 |
| C | 趋势分析 API + Celery 定时任务 + Agent Function Call 工具实现 | 转岗分析 API + Agent 意图识别 + 多轮对话 |
| D | 图谱可视化页面（G6） | Agent 对话组件（SSE 流式）+ 趋势分析页面 |

**里程碑**：核心分析功能可用，Agent 可完成基本问答

### 第四阶段：集成与交付（第 7-8 周）
| 成员 | 第 7 周 | 第 8 周 |
|------|---------|---------|
| A | 演示用数据预置（含讯飞数据 + 模拟企业数据） | 联调 Bug 修复 |
| B | 性能优化 + 全量数据预置 | 联调 Bug 修复 |
| C | Agent 完整调试 + 报告导出 + 集成测试 | API 文档完善 + 联调 |
| D | 转岗分析 + 培训推荐页面 + UI 打磨 | 系统管理页 + Agent 对话体验优化 |

**里程碑**：Docker Compose 一键启动全栈，5 个演示场景全部通过

---

## 八、演示场景设计

### 场景 A：企业 HR 查看岗位画像与市场趋势
1. HR 登录系统，首页仪表盘展示 IT 招聘市场全景
2. 点击/搜索 "Python 后端开发"，进入岗位详情
3. 查看该岗位的标准化能力模型（核心技能、工具、学历要求、薪资范围）
4. 切换"趋势"标签，查看该岗位近 6 个月的需求变化曲线

### 场景 B：探索技能图谱关联网络
1. 进入"技能图谱"页面
2. 搜索 "Go 语言"，中心节点展开关联岗位和技能
3. 发现 "Go 语言" 与 "云原生"、"Kubernetes"、"微服务" 紧密关联
4. 点击 "云原生" 节点，进一步展开查看更多关联

### 场景 C：员工转岗可行性分析
1. 进入"转岗分析"页面
2. 输入某 Java 工程师的技能列表：[Java, Spring Boot, MySQL, Redis, Git]
3. 系统计算出多个可转岗方向及匹配度：
   - Python 后端开发：匹配度 60%（中等）— 缺少 Python、Django
   - 大数据工程师：匹配度 40%（中等）— 缺少 Hadoop、Spark、Scala
   - AI 工程师：匹配度 20%（困难）— 缺少 Python、ML、深度学习
4. 查看每个方向的详细技能差距清单

### 场景 D：行业趋势动态观察
1. 进入"趋势分析"页面
2. 选择时间范围：近 6 个月
3. 观察 AI 相关岗位（AI 工程师、数据科学家、算法工程师）需求增长曲线明显上升
4. 发现 "提示词工程" 作为新兴技能出现，3 个月内需求增长 300%
5. 观察传统 Java 开发岗位需求趋于平稳

### 场景 E：AI Agent 智能助手（加分亮点）
1. 用户点击右下角 AI 助手图标，展开对话浮窗
2. 用户输入："合肥的 NLP 算法工程师现在平均薪资是多少？需要哪些核心技能？"
3. Agent 识别"市场洞察"意图 → 调用 MySQL 查询薪资数据 + Neo4j 查询技能图谱
4. Agent 返回：薪资范围 + Top 10 核心技能列表 + 来源引用
5. 用户追问："帮我写一份这个岗位的 JD"
6. Agent 识别"JD 生成"意图 → 结合行业标准 + 讯飞特色 → 生成完整 JD
7. 用户继续问："我们公司有位 Java 工程师，他会 Java、Spring、MySQL、Redis，能转这个方向吗？"
8. Agent 识别"转岗评估"意图 → 调用转岗分析引擎 → 输出匹配度 + 技能差距清单

---

## 九、非功能性需求

| 类别 | 要求 |
|------|------|
| **性能** | 图谱查询 ≤ 2s，转岗分析 ≤ 5s，前端首屏 ≤ 3s |
| **可用性** | 核心页面在 Chrome/Edge 最新版正常展示 |
| **可维护性** | 代码遵循统一规范（见 `dev-spec.md`），Docker 一键部署 |
| **安全性** | JWT 认证、密码哈希存储、SQL 注入防护（ORM 参数化查询） |
| **可扩展性** | 爬虫模块化设计，新增数据源只需添加新 Spider |

---

## 十、风险与应对

| 风险 | 等级 | 应对措施 |
|------|------|----------|
| 爬虫被反爬封锁 | 高 | IP 代理池 + UA 轮换 + 频率控制，准备公开数据集兜底 |
| 讯飞官网数据结构复杂 | 中 | 提前分析页面结构，必要时人工采集补充 |
| 实体抽取质量不达标 | 中 | 先用规则模板保底，再用少量标注数据微调，必要时人工补充 |
| 演示数据量不足 | 中 | 提前预置数据（含模拟企业数据），必要时用星火大模型生成 |
| 星火大模型 API 调用不稳定 | 中 | 关键问答预置缓存回复，确保演示不受 API 波动影响 |
| Agent Function Call 编排复杂 | 中 | 优先实现 2-3 个核心工具，其余简化或预设回复 |
| 团队协作冲突 | 低 | 接口预先定义好（见 `dev-spec.md`），Swagger 文档驱动开发 |

---

> **文档类型**：项目需求与目标文档
> **版本**：v1.0
> **创建日期**：2026-05-19
> **状态**：待确认
