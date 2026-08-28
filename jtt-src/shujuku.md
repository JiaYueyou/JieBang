# 数据库设计文档

> 文档类型：JTT 数据库时间点设计
> 状态：历史快照（2026-07-20），非当前迁移清单
> 核验日期：2026-08-28（`28a4cc5b`）
> JTT 后端现已包含独立 Alembic 迁移链，本文“无 Alembic”已过时；当前表结构以
> `jtt-src/backend/app/models`、`alembic/versions` 和实际数据库为准。
> JTT Alembic head 为 `34d9b68a59ff`，版本表为 `alembic_version_jtt`；岗位接口另外只读
> 依赖共享 `jie_bang.raw_job_record` 等 FYZ 表。JTT 本身未提交独立 SQL 快照。

> 智联职引 —— 人才分析与决策系统
> 数据库: **jiebang** | MySQL 8.0 | 引擎: InnoDB
> 版本: 0.1.0 | 更新: 2026-07-20

---

## 1. 概述

### 1.1 数据库配置

| 配置项 | 值 |
|--------|-----|
| 数据库名 | `jiebang` |
| 数据库引擎 | MySQL 8.0 (InnoDB) |
| 主机 | `localhost:3306` |
| 用户 | `root` |
| ORM | SQLAlchemy 2.0 (async, `aiomysql` 驱动) |
| 迁移方式 | `Base.metadata.create_all()` 自动建表（无 Alembic） |
| 测试库 | SQLite `:memory:`（`TESTING=true` 时自动切换） |
| 配置文件 | `backend/app/core/database.py` + `backend/app/core/config.py` |
| 环境变量 | `backend/.env` |

### 1.2 表总览

| 序号 | 表名 | 模型类 | 说明 | 种子数据量 |
|------|------|--------|------|-----------|
| 1 | `user` | `User` | 用户账号 | 1 条（admin） |
| 2 | `job_position` | `JobPosition` | 岗位信息 | 6 条 |
| 3 | `skill` | `Skill` | 岗位技能要求（子表） | 32 条 |
| 4 | `skill_change` | `SkillChange` | 岗位技能变化历史（子表） | 7 条 |
| 5 | `resume` | `Resume` | 用户简历 | 2 条 |
| 6 | `match_result` | `MatchResult` | 人岗匹配结果 | 0 条（按需生成） |
| 7 | `learning_path` | `LearningPath` | 学习路径 | 2 条 |
| 8 | `favorite` | `Favorite` | 用户收藏 | 4 条 |

### 1.3 实体关系图（ERD）

```
user ──< resume           (user_id FK, 1对多)
user ──< match_result     (user_id FK, 1对多)
user ──< learning_path    (user_id FK, 1对多)
user ──< favorite         (user_id FK, 1对多)

job_position ──< skill          (position_id FK, 1对多)
job_position ──< skill_change   (position_id FK, 1对多)
job_position ──< match_result   (position_id FK, 1对多)
job_position ──< learning_path  (position_id FK, 1对多)

resume ──< match_result   (resume_id FK, 1对多)
```

**设计特点**:
- 不使用 SQLAlchemy ORM `relationship()`，所有关联通过 repository 层手动查询，避免异步懒加载问题
- 简历的工作经历、教育经历、技能等子结构使用 **JSON 列** 存储，不拆分为独立关系表
- 匹配结果的维度评分、差距分析、优化建议也以 **JSON 列** 存储
- 学习路径的步骤和资源同样使用 **JSON 列**

---

## 2. 表详细定义

### 2.1 user — 用户表

用户账号信息，所有业务数据通过 `user_id` 外键关联到此表。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | `INT` | PK, AUTO_INCREMENT | 用户唯一标识 |
| `username` | `VARCHAR(50)` | UNIQUE, NOT NULL | 用户名（登录用） |
| `email` | `VARCHAR(100)` | UNIQUE, NOT NULL | 邮箱 |
| `password_hash` | `VARCHAR(255)` | NOT NULL | 密码哈希（bcrypt 加密） |
| `nickname` | `VARCHAR(50)` | NULL | 昵称 |
| `phone` | `VARCHAR(20)` | NULL | 手机号 |
| `city` | `VARCHAR(50)` | NULL | 所在城市 |
| `education` | `VARCHAR(50)` | NULL | 最高学历 |
| `avatar` | `VARCHAR(500)` | NULL | 头像 URL |
| `resume_count` | `INT` | DEFAULT 0 | 简历数量（冗余，便于展示） |
| `match_history_count` | `INT` | DEFAULT 0 | 匹配历史次数 |
| `created_at` | `DATETIME` | DEFAULT NOW() | 注册时间 |
| `updated_at` | `DATETIME` | DEFAULT NOW() ON UPDATE NOW() | 更新时间 |

**种子数据**: 初始管理员账号由 `INITIAL_ADMIN_ENABLED` 配置控制，在应用启动时自动创建。默认用户名 `admin`，密码 `admin123`。

**索引**: `username` (UNIQUE), `email` (UNIQUE)

---

### 2.2 job_position — 岗位信息表

存储系统中所有岗位的详细信息，分"新兴岗位"和"既有岗位"两类。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | `INT` | PK, AUTO_INCREMENT | 岗位唯一标识 |
| `name` | `VARCHAR(100)` | NOT NULL | 岗位名称 |
| `category` | `VARCHAR(20)` | NOT NULL | 类别: `new`=新兴岗位, `existing`=既有岗位 |
| `aliases` | `JSON` | DEFAULT [] | 岗位别名列表，如 `["Java工程师", "Java后端"]` |
| `summary` | `TEXT` | NOT NULL | 岗位概述（1-2 句描述） |
| `responsibilities` | `JSON` | DEFAULT [] | 核心职责列表（字符串数组） |
| `industry_scenarios` | `JSON` | DEFAULT [] | 典型行业应用场景（字符串数组） |
| `tech_stack` | `JSON` | DEFAULT [] | 技术栈分类（字符串数组） |
| `career_level` | `VARCHAR(20)` | DEFAULT 'mid' | 级别: `junior` / `mid` / `senior` |
| `salary_range` | `VARCHAR(50)` | NULL | 薪资范围，如 `25K-50K` |
| `created_at` | `DATETIME` | DEFAULT NOW() | 创建时间 |
| `updated_at` | `DATETIME` | DEFAULT NOW() ON UPDATE NOW() | 更新时间 |

**关联子表**:
- `skill` — 岗位的技能要求（通过 `position_id` 关联）
- `skill_change` — 岗位技能的历史变化记录（通过 `position_id` 关联）

**索引**: `category`（用于筛选新兴/既有岗位）

---

### 2.3 skill — 技能要求表

每个岗位的技能要求，分为"必备技能"和"加分技能"两类。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | `INT` | PK, AUTO_INCREMENT | 技能记录 ID |
| `position_id` | `INT` | FK → `job_position.id`, NOT NULL | 所属岗位 ID |
| `name` | `VARCHAR(100)` | NOT NULL | 技能名称 |
| `level` | `VARCHAR(20)` | DEFAULT 'required' | 级别: `required` / `preferred` / `advanced` |
| `kind` | `VARCHAR(20)` | DEFAULT 'required' | 技能性质: `required`=必备, `preferred`=加分 |
| `category` | `VARCHAR(50)` | DEFAULT '' | 技术栈分类，如 "编程语言" / "AI框架" / "数据存储" |

**查询方式**: 通过 `PositionRepository.get_skills_for_positions(position_ids)` 批量查询，返回以 `position_id` 为 key 的字典。

**索引**: `position_id`（用于按岗位查询技能）

---

### 2.4 skill_change — 技能变化历史表

记录既有岗位的技能要求随时间的变化（新增/移除/修改），用于展示岗位趋势。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | `INT` | PK, AUTO_INCREMENT | 变化记录 ID |
| `position_id` | `INT` | FK → `job_position.id`, NOT NULL | 所属岗位 ID |
| `skill_name` | `VARCHAR(100)` | NOT NULL | 变化的技能名 |
| `change_type` | `VARCHAR(20)` | NOT NULL | 变化类型: `added`=新增, `removed`=淘汰, `modified`=升级 |
| `description` | `TEXT` | DEFAULT '' | 变化说明文字 |
| `source` | `VARCHAR(200)` | DEFAULT '' | 数据来源，如 "招聘平台+行业报告" |
| `change_date` | `VARCHAR(20)` | DEFAULT '' | 变化日期，如 `2026-02` |

**查询方式**: 通过 `PositionRepository.get_skill_changes_for_positions(position_ids)` 批量查询。

**索引**: `position_id`

---

### 2.5 resume — 简历表

用户简历的完整数据。基本信息为独立字段，教育/工作/项目/技能等子结构存储为 JSON 列。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | `INT` | PK, AUTO_INCREMENT | 简历唯一标识 |
| `user_id` | `INT` | FK → `user.id`, NOT NULL | 所属用户 ID |
| `name` | `VARCHAR(100)` | NOT NULL | 简历别名（用户自定义标题） |
| `target_position` | `VARCHAR(100)` | NULL | 目标岗位方向 |
| `personal_name` | `VARCHAR(50)` | DEFAULT '' | 姓名 |
| `personal_email` | `VARCHAR(100)` | DEFAULT '' | 邮箱 |
| `personal_phone` | `VARCHAR(20)` | DEFAULT '' | 手机号 |
| `personal_location` | `VARCHAR(50)` | DEFAULT '' | 所在地 |
| `desired_position` | `VARCHAR(100)` | NULL | 期望职位 |
| `desired_city` | `VARCHAR(50)` | NULL | 期望城市 |
| `salary_expectation` | `VARCHAR(50)` | NULL | 期望薪资，如 `15K-25K` |
| `work_mode` | `VARCHAR(20)` | NULL | 工作模式: `fulltime` / `intern` / `remote` |
| `self_evaluation` | `TEXT` | DEFAULT '' | 自我评价 |
| `source_file` | `VARCHAR(200)` | NULL | 上传的原始文件名 |
| `education_list` | `JSON` | DEFAULT [] | 教育经历列表 |
| `work_experience_list` | `JSON` | DEFAULT [] | 工作经历列表 |
| `project_list` | `JSON` | DEFAULT [] | 项目经历列表 |
| `skill_list` | `JSON` | DEFAULT [] | 技能列表 |
| `created_at` | `DATETIME` | DEFAULT NOW() | 创建时间 |
| `updated_at` | `DATETIME` | DEFAULT NOW() ON UPDATE NOW() | 更新时间 |

**索引**: `user_id`（用于按用户查询简历列表）

#### JSON 子结构定义

**education_list** — 教育经历

```json
[
  {
    "school": "某科技大学",
    "degree": "本科",
    "major": "计算机科学与技术",
    "startDate": "2019-09",
    "endDate": "2023-06"
  }
]
```

**work_experience_list** — 工作经历

```json
[
  {
    "company": "某互联网公司",
    "position": "Java 后端开发",
    "startDate": "2023-07",
    "endDate": "2026-06",
    "description": "负责电商平台订单系统后端开发...",
    "skills": ["Java", "Spring Boot", "MySQL", "Redis", "Docker"]
  }
]
```

**project_list** — 项目经历

```json
[
  {
    "name": "电商订单系统",
    "role": "核心开发",
    "description": "负责订单模块的设计与开发...",
    "technologies": ["Java", "Spring Cloud", "RocketMQ", "MySQL"],
    "highlights": ["系统QPS从500优化至2000", "引入消息队列解耦订单流程"]
  }
]
```

**skill_list** — 技能列表

```json
[
  { "id": "rs1", "name": "Java", "level": "advanced", "category": "编程语言" },
  { "id": "rs2", "name": "Spring Boot", "level": "advanced", "category": "框架" }
]
```

---

### 2.6 match_result — 匹配结果表

存储每次人岗匹配的完整结果，包括四维度评分、差距分析和优化建议。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | `INT` | PK, AUTO_INCREMENT | 匹配结果 ID |
| `user_id` | `INT` | FK → `user.id`, NOT NULL | 发起匹配的用户 ID |
| `resume_id` | `INT` | FK → `resume.id`, NOT NULL | 匹配的简历 ID |
| `position_id` | `INT` | FK → `job_position.id`, NOT NULL | 匹配的岗位 ID |
| `position_name` | `VARCHAR(100)` | DEFAULT '' | 岗位名称（冗余，便于展示） |
| `resume_name` | `VARCHAR(100)` | DEFAULT '' | 简历名称（冗余，便于展示） |
| `total_score` | `INT` | DEFAULT 0 | 综合匹配分数 (0–100) |
| `dimensions` | `JSON` | DEFAULT [] | 四维度评分详情 |
| `gap_analysis` | `JSON` | DEFAULT {} | 差距分析结果 |
| `suggestions` | `JSON` | DEFAULT [] | 优化建议列表 |
| `match_date` | `DATETIME` | DEFAULT NOW() | 匹配时间 |
| `created_at` | `DATETIME` | DEFAULT NOW() | 记录创建时间 |

**索引**: `(resume_id, position_id)` 联合查询（取最新匹配结果），`user_id`（按用户查历史）

#### JSON 子结构定义

**dimensions** — 维度评分（数组，4 个固定维度）

```json
[
  {
    "name": "技能匹配",
    "score": 72,
    "weight": 0.4,
    "details": "匹配 3/7 项技能，缺失 4 项"
  },
  {
    "name": "经验匹配",
    "score": 65,
    "weight": 0.3,
    "details": "2 段工作经历"
  },
  {
    "name": "学历匹配",
    "score": 80,
    "weight": 0.15,
    "details": "1 段教育经历"
  },
  {
    "name": "综合素质",
    "score": 55,
    "weight": 0.15,
    "details": "1 个项目，有自我评价"
  }
]
```

**gap_analysis** — 差距分析

```json
{
  "missing_skills": [
    { "name": "智能体开发", "level": "required", "category": "AI集成" }
  ],
  "weak_skills": [
    { "name": "LLM API 集成", "level": "preferred", "category": "AI集成" }
  ],
  "match_skills": [
    { "name": "Java", "level": "required", "category": "编程语言" }
  ]
}
```

**suggestions** — 优化建议

```json
[
  {
    "id": "sg-1",
    "section": "skills",
    "field": "skills",
    "original": "",
    "suggested": "建议学习并添加技能: 智能体开发",
    "reason": "该岗位要求掌握 智能体开发",
    "change_type": "large",
    "accepted": false,
    "verified": true,
    "warning": null
  }
]
```

---

### 2.7 learning_path — 学习路径表

存储用户的学习计划，包含分步骤的学习内容和资源。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | `INT` | PK, AUTO_INCREMENT | 学习路径 ID |
| `user_id` | `INT` | FK → `user.id`, NOT NULL | 所属用户 ID |
| `name` | `VARCHAR(100)` | NOT NULL | 路径名称 |
| `position_id` | `INT` | FK → `job_position.id`, NOT NULL | 目标岗位 ID |
| `position_name` | `VARCHAR(100)` | DEFAULT '' | 目标岗位名称（冗余） |
| `steps` | `JSON` | DEFAULT [] | 学习步骤列表 |
| `total_duration` | `VARCHAR(50)` | DEFAULT '' | 总时长，如 `12周` |
| `created_at` | `DATETIME` | DEFAULT NOW() | 创建时间 |
| `updated_at` | `DATETIME` | DEFAULT NOW() ON UPDATE NOW() | 更新时间 |

**索引**: `user_id`（用于按用户查询学习路径列表）

#### JSON 子结构定义

**steps** — 学习步骤（数组）

```json
[
  {
    "id": "s-1",
    "order": 1,
    "title": "Java 核心基础强化",
    "description": "深入理解 Java 集合框架、JVM 内存模型、并发编程",
    "duration": "1-2周",
    "completed": true,
    "resources": [
      {
        "id": "res-1",
        "title": "《深入理解Java虚拟机》",
        "type": "book",
        "url": "",
        "platform": "京东读书"
      }
    ]
  }
]
```

**resources** — 学习资源（每个步骤可包含多个）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `string` | 资源 ID |
| `title` | `string` | 资源名称 |
| `type` | `string` | 类型: `course`(课程) / `book`(书籍) / `article`(文章) / `project`(项目) / `video`(视频) |
| `url` | `string` | 资源链接 |
| `platform` | `string` | 平台，如 "慕课网" / "B站" / "GitHub" |

---

### 2.8 favorite — 收藏表

统一的多态收藏表，支持收藏岗位、学习资源、错题、知识点四种类型。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | `INT` | PK, AUTO_INCREMENT | 收藏记录 ID |
| `user_id` | `INT` | FK → `user.id`, NOT NULL | 所属用户 ID |
| `item_type` | `VARCHAR(30)` | NOT NULL, INDEX | 收藏类型 |
| `item_id` | `VARCHAR(100)` | NOT NULL | 收藏项的原始 ID |
| `title` | `VARCHAR(200)` | NOT NULL | 收藏项标题 |
| `summary` | `VARCHAR(500)` | NULL | 简要描述 |
| `metadata` | `JSON` | DEFAULT {} | 完整数据快照（列名 `metadata`，属性名 `item_data`） |
| `tags` | `JSON` | NULL | 用户自定义标签 |
| `created_at` | `DATETIME` | DEFAULT NOW() | 收藏时间 |

**收藏类型枚举**:

| item_type | 说明 | item_id 示例 | metadata 内容 |
|-----------|------|-------------|---------------|
| `position` | 岗位 | 岗位 ID | 岗位名称、类别、薪资、技能列表 |
| `learning_resource` | 学习资源 | 资源 ID | 资源标题、类型、URL、平台、关联技能 |
| `quiz_error` | 错题 | 题目 ID | 题目、用户答案、正确答案、解析、知识点 |
| `knowledge_point` | AI 知识点 | 知识点 ID | 概念名称、说明、关联技能（预留） |

**索引**: `user_id`（按用户查收藏），`item_type`（按类型筛选），`(user_id, item_type, item_id)` 联合唯一（防止重复收藏）

**查询**: 通过 `FavoriteRepository` 提供 `list_by_user()`（支持按类型筛选）、`is_favorited()`（判断是否已收藏）、`get_by_item()`（查找特定收藏）。

---

## 3. 种子数据

所有种子数据在应用启动时通过 `seed.py` 自动填充。**幂等操作**: 仅在对应表为空时才插入。

### 3.1 岗位 (6 条)

#### 新兴岗位 (3 条)

**1. AI 智能体开发工程师** (career_level=mid, 25K-50K)
- 必备技能: Python, LangChain/LangGraph, LLM API 调用与调优, Prompt Engineering, RAG 检索增强生成
- 加分技能: Multi-Agent 系统设计, 向量数据库(Milvus/ChromaDB), FastAPI/Flask
- 职责: LLM Agent 架构设计、工具链构建、Multi-Agent 协作、Agent 框架跟踪
- 场景: 智能客服、自动化运维 Agent、个人 AI 助理、企业知识管理

**2. 上下文工程专家** (career_level=senior, 30K-60K)
- 必备技能: Prompt Engineering, LLM 推理与 Token 优化, Python
- 加分技能: Agent 框架, NLP 基础
- 职责: 上下文管理架构设计、Token 利用率优化、动态上下文注入策略

**3. 具身智能算法工程师** (career_level=senior, 35K-70K)
- 必备技能: Python/C++, ROS/ROS2, 计算机视觉, 深度强化学习
- 加分技能: NVIDIA Isaac Sim, VLM 模型微调
- 职责: 机器人视觉感知、VLM 自主决策、仿真训练流程
- 场景: 工业机器人、服务机器人、自动驾驶、仓储物流

#### 既有岗位 (3 条)

**4. Java 开发工程师** (career_level=mid, 15K-35K)
- 必备技能: Java/Spring Boot, MySQL/Redis, 微服务架构, Docker/K8s, LLM API 集成
- 加分技能: 智能体开发, 全栈能力(Vue/React), RAG 框架
- 技能变化: 新增智能体开发(2026-02)、新增 LLM API 集成(2025-09)、淘汰 SSH/SSM(2025-06)、新增 RAG 框架(2026-04)
- 场景: 金融科技、电商平台、企业 SaaS、互联网

**5. 前端开发工程师** (career_level=mid, 15K-30K)
- 必备技能: TypeScript, Vue 3/React, Vite/Webpack, AI 辅助开发工具
- 加分技能: Node.js/SSR, 可视化(G6/ECharts)
- 技能变化: 新增 AI 辅助开发工具(2025-12)、TypeScript 从加分升级为必备(2025-06)
- 场景: 互联网产品、企业后台、数据可视化、移动端 H5

**6. 数据工程师** (career_level=mid, 20K-40K)
- 必备技能: Python/SQL, Spark/Flink, 数据仓库建模
- 加分技能: ML Pipeline, 实时计算
- 技能变化: 新增 ML Pipeline(2026-01)
- 场景: 互联网数据平台、金融风控、AI 数据中台

### 3.2 简历 (2 条)

**1. Java后端开发简历** (用户: admin, user_id=1)
- 姓名: 张三 | 地点: 北京 | 期望: Java 开发工程师, 北京, 15K-25K
- 教育: 某科技大学 本科 计算机科学 (2019-2023)
- 工作: 某互联网公司 Java后端开发 (2023-2026), 电商订单系统
- 技能: Java(advanced), Spring Boot(advanced), MySQL, Redis, Docker, 微服务
- 项目: 电商订单系统 — 核心开发, QPS 从 500 优化至 2000

**2. AI方向简历** (用户: admin, user_id=1)
- 姓名: 李四 | 地点: 上海 | 期望: AI 工程师, 上海, 25K-40K
- 教育: 某理工大学 硕士 人工智能 (2021-2024)
- 工作: 某AI公司 AI算法工程师 (2024-2026), LLM 对话系统
- 技能: Python(advanced), LangChain, LLM API, RAG, Prompt Engineering, FastAPI
- 项目: 企业智能知识库 — 项目负责人, 检索召回率 95%+, 日均问答 5000+

### 3.3 学习路径 (2 条)

**1. Java工程师进阶路径** (12周, 5 步骤)
| 步骤 | 标题 | 周期 | 状态 |
|------|------|------|------|
| 1 | Java 核心基础强化 (JVM/并发/集合) | 1-2周 | 已完成 |
| 2 | Spring Boot 微服务实战 (Spring Cloud/网关) | 3-5周 | 未完成 |
| 3 | Docker & Kubernetes (容器化/Helm) | 6-7周 | 未完成 |
| 4 | LLM API 集成与 Agent 开发 (RAG/LangChain) | 8-10周 | 未完成 |
| 5 | 综合实战项目 (Java + Spring Boot + LLM) | 11-12周 | 未完成 |

**2. AI智能体开发学习路径** (10周, 5 步骤)
| 步骤 | 标题 | 周期 | 状态 |
|------|------|------|------|
| 1 | Python 高级编程 (异步/装饰器/类型注解) | 1-2周 | 未完成 |
| 2 | LLM 基础与 Prompt Engineering | 3-4周 | 未完成 |
| 3 | LangChain & Agent 框架 (ReAct/Tool Calling) | 5-7周 | 未完成 |
| 4 | RAG 与向量数据库 (ChromaDB/Milvus) | 8-9周 | 未完成 |
| 5 | Multi-Agent 系统实战 (AutoGen/端到端) | 10周 | 未完成 |

### 3.4 收藏 (4 条)

| 类型 | 标题 | 数据快照 |
|------|------|---------|
| `position` | Java 开发工程师 | 类别: existing, 级别: mid, 薪资: 15K-35K, 5 项核心技能 |
| `position` | AI 智能体开发工程师 | 类别: new, 级别: mid, 薪资: 25K-50K, 5 项核心技能 |
| `learning_resource` | 《深入理解Java虚拟机》 | 类型: book, 平台: 京东读书, 标签: Java/JVM |
| `quiz_error` | Java GC 算法选择 (错题) | 问: JDK 9+ 默认 GC? 答错: CMS, 正确: G1 |

---

## 4. 技术要点

### 4.1 JSON 列策略

以下数据存储为 JSON 而非独立的关联表:

| 表 | JSON 列 | 内容 | 原因 |
|----|---------|------|------|
| `resume` | `education_list` | 教育经历 | 数量少 (1-3 条)，与简历始终同查 |
| `resume` | `work_experience_list` | 工作经历 | 同上 |
| `resume` | `project_list` | 项目经历 | 同上 |
| `resume` | `skill_list` | 用户技能 | 同上 |
| `match_result` | `dimensions` | 维度评分 | 固定 4 个维度，始终整体读写 |
| `match_result` | `gap_analysis` | 差距分析 | 动态列表，作为整体展示 |
| `match_result` | `suggestions` | 优化建议 | AI 生成 + 用户接受/拒绝状态 |
| `learning_path` | `steps` | 学习步骤 + 资源 | 嵌套结构，始终整体读写 |

**优点**: 减少 JOIN 查询、灵活扩展字段、数据读写原子性。
**注意**: JSON 列不支持 MySQL 索引，因此不建议作为 WHERE 条件。

### 4.2 无 ORM relationship

项目**不使用** SQLAlchemy 的 `relationship()` 和 `back_populates`。原因：

- 项目使用异步引擎 (`aiomysql`)，`relationship()` 的懒加载在异步环境下容易触发 `MissingGreenlet` 错误
- 改为在 Repository 层通过显式查询手动关联，查询路径明确可控
- 示例: 获取岗位的技能列表 → `PositionRepository.get_skills_for_positions([pid])` 批量查询

### 4.3 数据库迁移

项目当前**没有使用 Alembic** 管理数据库迁移。建表方式为应用启动时 `Base.metadata.create_all()` 自动创建。这意味着：

- **开发环境**: 修改模型后需重启应用，新列会自动添加
- **生产环境**: 建议在必要时引入 Alembic 做版本化迁移
- **测试环境**: 每个测试函数通过 `Base.metadata.drop_all` + `create_all` 重建全新 SQLite 内存库

### 4.4 关键索引策略

| 表 | 索引列 | 用途 |
|----|--------|------|
| `user` | `username`, `email` | 登录查找 |
| `job_position` | `category` | 前端按新兴/既有岗位筛选 |
| `skill` | `position_id` | 按岗位查技能 |
| `skill_change` | `position_id` | 按岗位查技能变化 |
| `resume` | `user_id` | 按用户查简历列表 |
| `match_result` | `user_id`, `(resume_id, position_id)` | 历史查询 + 去重查询 |
| `learning_path` | `user_id` | 按用户查学习路径 |
| `favorite` | `user_id`, `item_type`, `(user_id, item_type, item_id)` | 按用户/类型查收藏 + 去重 |

### 4.5 前后端字段映射

后端 API 使用 **snake_case**（如 `target_position`），前端使用 **camelCase**（如 `targetPosition`）。转换在 `frontend/src/utils/transform.ts` 中处理。

| 后端字段 (DB/API) | 前端字段 (TypeScript) | 所在表 |
|-------------------|----------------------|--------|
| `personal_name` / `personal_email` / `personal_phone` / `personal_location` | `personalInfo: { name, email, phone, location }` | resume |
| `desired_position` / `desired_city` / `salary_expectation` / `work_mode` | `jobIntent: { desiredPosition, desiredCity, salaryExpectation, workMode }` | resume |
| `education_list` | `education: Education[]` | resume |
| `work_experience_list` | `workExperience: WorkExperience[]` | resume |
| `project_list` | `projects: Project[]` | resume |
| `skill_list` | `skills: Skill[]` | resume |
| `self_evaluation` | `selfEvaluation` | resume |
| `total_score` | `totalScore` | match_result |
| `gap_analysis` → `missing_skills` / `weak_skills` / `match_skills` | `gapAnalysis: { missingSkills, weakSkills, matchSkills }` | match_result |
| `change_type` | `changeType` | match_result.suggestions |
| `total_duration` | `totalDuration` | learning_path |
| `item_type` | `itemType` | favorite |

---

## 5. 文件索引

| 层级 | 文件 | 说明 |
|------|------|------|
| 数据库配置 | `backend/app/core/database.py` | engine / session / Base |
| 应用配置 | `backend/app/core/config.py` | DATABASE_URL 拼装 + 环境变量 |
| 环境变量 | `backend/.env` | 实际数据库连接信息 |
| User 模型 | `backend/app/models/user.py` | |
| Resume 模型 | `backend/app/models/resume.py` | |
| Position/Skill 模型 | `backend/app/models/position.py` | |
| MatchResult 模型 | `backend/app/models/match.py` | |
| LearningPath 模型 | `backend/app/models/learning.py` | |
| Favorite 模型 | `backend/app/models/favorite.py` | |
| 种子数据 | `backend/app/seed.py` | |
| 用户 Repository | `backend/app/repositories/user_repository.py` | |
| 简历 Repository | `backend/app/repositories/resume_repository.py` | |
| 岗位 Repository | `backend/app/repositories/position_repository.py` | |
| 匹配 Repository | `backend/app/repositories/match_repository.py` | |
| 收藏 Repository | `backend/app/repositories/favorite_repository.py` | |
| 学习 Repository | `backend/app/repositories/learning_repository.py` | |
| 前端字段转换 | `frontend/src/utils/transform.ts` | snake_case ↔ camelCase |
