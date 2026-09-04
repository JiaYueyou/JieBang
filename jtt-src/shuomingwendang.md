# 智联职引（JieBang）— 人才分析与决策系统 使用说明文档

> 文档类型：JTT 早期使用与架构说明
> 状态：历史参考 / 待重写
> 核验日期：2026-08-12（`c995a09e`）
> 当前主后端源码默认 8000，AI 助手默认 8001；前端代理与 API 前缀尚未完成分流。
> 本文的端口、目录、接口数量和“配置 Key 后自动生效”等描述不可作为当前运行依据，
> 请先阅读 [当前实现状态](../docs/implementation-status.md) 与 [前端 README](frontend/README.md)。

---

## 一、项目概述

**智联职引**是一套基于多源异构数据驱动的岗位-能力图谱构建与动态演化分析系统。面向求职者提供：岗位探索、知识图谱可视化、简历管理与诊断、AI 智能匹配、AI 简历优化、职业发展规划、个性化学习路径生成等功能。

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | Vue 3 + TypeScript (Composition API / `<script setup>`) |
| 前端 UI 库 | Element Plus |
| 状态管理 | Pinia |
| 路由 | Vue Router 4 |
| 构建工具 | Vite |
| 后端框架 | Python FastAPI + Pydantic v2 |
| 数据库 ORM | SQLAlchemy 2.0 (异步) |
| 关系数据库 | MySQL (通过 aiomysql 驱动) |
| 图数据库 | Neo4j (知识图谱) |
| 认证 | JWT (python-jose) |
| LLM 接入 | DeepSeek API (OpenAI 兼容接口) |

### 智能体（Agent）说明

系统预设了三个 AI 智能体的接入位置，当前 LLM_API_KEY 为占位符，AI 功能走**规则降级**。替换为真实 DeepSeek API Key 后所有 AI 功能自动生效。

| Agent | 功能 | 核心文件 |
|-------|------|----------|
| **Agent 1 — 简历优化智能体** | 分析简历与岗位的匹配差异，逐段生成修改建议 | `tailor_service.py` |
| **Agent 2 — 学习助手智能体** | 对话式学习咨询、自动生成学习路径和测试题 | `learning_service.py` |
| **Agent 3 — 智能匹配诊断** | 简历与全站岗位逐一匹配，生成诊断报告排名 | `match_service.py` |

---

## 二、系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Vue 3 + TS)                      │
│  ┌─────────┐ ┌──────────┐ ┌───────────┐ ┌───────────┐  │
│  │  Views  │ │Components│ │  Stores   │ │   API     │  │
│  │  页面    │ │  组件    │ │ (Pinia)   │ │  接口层    │  │
│  └─────────┘ └──────────┘ └───────────┘ └─────┬─────┘  │
│                   Vite Proxy /api → 127.0.0.1:8000      │
└─────────────────────────────────────────────────────────┘
                        │ HTTP (JSON + JWT)
┌─────────────────────────────────────────────────────────┐
│                后端 (FastAPI, port 8000)                  │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────┐  │
│  │  Routes  │ │ Services │ │Repositories│ │  Models  │  │
│  │ (API层)  │ │ (业务层)  │ │  (数据层)   │ │ (ORM)    │  │
│  └──────────┘ └──────────┘ └───────────┘ └──────────┘  │
│         ┌────────────────────┬──────────────────┐       │
│         ▼                    ▼                  ▼       │
│     MySQL (关系数据)    Neo4j (图谱)    DeepSeek (LLM)  │
└─────────────────────────────────────────────────────────┘
```

---

## 三、后端文件说明 (`backend/`)

### 3.1 入口与配置

| 文件 | 作用 |
|------|------|
| `run.py` | 启动入口，等价于 `uvicorn app.main:app` |
| `app/main.py` | **FastAPI 应用主入口**。注册所有路由、CORS 中间件、全局异常处理、数据库初始化、种子数据填充、Neo4j 连接管理 |
| `app/core/config.py` | **全局配置**。从 `.env` 文件加载 MySQL/Neo4j/JWT/LLM/Redis/ChromaDB 等配置项。包含 `_required()` 辅助函数用于必需的环墧变量校验 |
| `app/core/database.py` | **数据库连接管理**。创建 SQLAlchemy 异步引擎和 session 工厂，提供 `get_db()` FastAPI 依赖注入函数。测试模式使用 SQLite 内存数据库 |
| `app/core/security.py` | **JWT 认证**。提供 `create_access_token()`（生成 token）、`decode_token()`（解析 token）、`get_current_user()`（FastAPI 依赖，从 Bearer Token 提取用户信息） |
| `app/core/exceptions.py` | **统一异常类**。定义 `BusinessException` 基类及 `AuthenticationError`、`ResourceNotFoundError`、`InvalidParameterError` 等子类。`register_exception_handlers()` 注册全局异常处理器，统一返回 `ApiResponse` 格式 |
| `app/core/neo4j.py` | **Neo4j 知识图谱连接**。单例驱动管理，提供 `run_read()`（只读查询）和 `run_write()`（写入查询）辅助函数 |
| `.env` | 环境变量配置文件（数据库密码、JWT密钥、LLM Key 等） |

### 3.2 数据模型 (`app/models/`)

每个文件定义一个 SQLAlchemy ORM 模型，对应 MySQL 中的一张表。

| 文件 | 表名 | 主要字段 | 说明 |
|------|------|---------|------|
| `user.py` | `user` | id, username, email, password_hash, nickname, phone, city, education, created_at | 用户表 |
| `resume.py` | `resume` | id, user_id, name, target_position, personal_info(JSON), job_intent(JSON), education(JSON), work_experience(JSON), projects(JSON), skills(JSON), self_evaluation, source_file | 简历表，核心数据以 JSON 字段灵活存储 |
| `position.py` | `job_position` + `position_skill` | 岗位：id, name, category, summary, responsibilities(JSON), industry_scenarios(JSON), tech_stack(JSON), career_level, salary_range / 技能：id, position_id, name, level, category | 岗位和技能分表存储，一对多关联 |
| `match.py` | `match_record` | id, user_id, resume_id, position_id, total_score, dimensions(JSON), gap_analysis(JSON), suggestions(JSON) | 匹配记录表 |
| `learning.py` | `learning_path` | id, user_id, name, position_id, position_name, steps(JSON), total_duration | 学习路径表，步骤以 JSON 存储 |
| `favorite.py` | `favorite` | id, user_id, item_type, item_id, title, summary, metadata(JSON), tags(JSON), created_at | **多态收藏表**。通过 `item_type` + `item_id` 统一支持岗位/学习资料/错题/AI知识点四种收藏 |

### 3.3 请求/响应 Schema (`app/schemas/`)

Pydantic v2 模型，定义 API 的请求体和响应体格式，同时提供自动数据校验。

| 文件 | 包含的 Schema 类 |
|------|-----------------|
| `common.py` | `ApiResponse[T]`（统一响应 `{code, message, data}`）、`PaginatedData[T]`（分页 `{list, total, page, pageSize}`） |
| `auth.py` | `LoginRequest`, `RegisterRequest`, `TokenResponse`, `UserProfileResponse`, `UpdateProfileRequest`, `ChangePasswordRequest` |
| `position.py` | `JobPositionResponse`, `GraphResponse`（知识图谱 nodes + edges） |
| `resume.py` | `ResumeCreate`, `ResumeUpdate`, `ResumeResponse`, `ResumeUploadResponse` |
| `match.py` | `MatchResultResponse`（含 dimensions / gap_analysis / suggestions 嵌套结构） |
| `tailor.py` | `SuggestionResponse`, `AcceptSuggestionRequest`, `ApplyAllRequest`, `OptimizePhraseRequest`, `OptimizePhraseResponse`, `SaveAsNewRequest`, `SaveAsNewResponse` |
| `learning.py` | `LearningPathCreate`, `LearningPathUpdate`, `LearningPathResponse`, `ChatRequest`, `ChatResponse`, `GeneratePathRequest`, `QuizRequest`, `QuizResponse` |
| `favorite.py` | `FavoriteCreate`, `FavoriteResponse` |

### 3.4 数据仓库层 (`app/repositories/`)

封装数据库操作，每个 Repository 对应一个模型。Service 层通过 Repository 访问数据库，不与 ORM 直接耦合。

| 文件 | 主要方法 | 说明 |
|------|---------|------|
| `user_repository.py` | `get_by_username()`, `get_by_id()`, `create()`, `update()` | 用户增删改查 |
| `resume_repository.py` | `list_by_user()`, `get_by_id()`, `create()`, `update()`, `delete()`, `duplicate()` | 简历 CRUD + 复制 |
| `position_repository.py` | `list_all()`, `get_by_id()`, `search()`, `get_all_ids()`, `get_skills_for_positions()` | 岗位查询 + 技能关联加载 |
| `match_repository.py` | `create()`, `list_by_user()`, `get_by_resume_position()` | 匹配记录存取 |
| `learning_repository.py` | `list_by_user()`, `get_by_id()`, `create()`, `update()`, `delete()` | 学习路径 CRUD |
| `favorite_repository.py` | `list_by_user()`, `get_by_item()`, `add()`, `remove()`, `is_favorited()` | 收藏增删查 |

### 3.5 业务服务层 (`app/services/`)

核心业务逻辑所在，协调多个 Repository 和外部服务完成业务流程。

| 文件 | 主要方法 | 对应 Agent | 说明 |
|------|---------|-----------|------|
| `auth_service.py` | `login()`, `register()`, `get_profile()`, `update_profile()`, `change_password()` | — | 认证 + 用户管理 |
| `position_service.py` | `list_positions()`, `get_detail()`, `get_graph_data()` | — | 岗位查询 + 图谱数据组装 |
| `resume_service.py` | `list_resumes()`, `get_detail()`, `create()`, `update()`, `delete()`, `duplicate()`, `parse_upload()` | — | 简历全生命周期管理 |
| **`match_service.py`** | `do_match()`, `batch_match()`, `auto_match()` | **Agent 3** | 人岗匹配核心。技能模糊匹配、四维度评分（技能/经验/学历/综合）、差距分析、改进建议生成。`auto_match()` 自动逐一匹配全站岗位 |
| **`tailor_service.py`** | `get_suggestions()`, `accept_suggestion()`, `apply_all()`, `optimize_phrase()`, `save_as_new()` | **Agent 1** | 简历优化。LLM 生成逐段修改建议 → 图谱回查校验（防幻觉）→ 用户接受/拒绝 → 一键生成优化版简历 |
| **`learning_service.py`** | `chat()`, `generate_path()`, `recommend_resources()`, `generate_quiz()` | **Agent 2** | 学习助手。对话式问答（结合图谱上下文）、自动生成学习路径、推荐学习资源、生成测试题 |

### 3.6 API 路由层 (`app/api/v1/`)

每个文件定义一组 RESTful API 端点，负责参数校验和 Service 调用。

#### 认证 (`auth.py`) — 前缀 `/api/v1/auth`

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/login` | 用户登录，返回 JWT token |
| `POST` | `/register` | 用户注册 |
| `POST` | `/logout` | 用户登出 |
| `GET` | `/profile` | 获取当前用户个人信息 |
| `PUT` | `/profile` | 更新个人信息 |
| `PUT` | `/password` | 修改密码 |

#### 岗位 (`positions.py`) — 前缀 `/api/v1/positions`

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `` | 分页查询岗位列表（支持 category/keyword/tech_stack 筛选） |
| `GET` | `/graph` | 获取知识图谱数据（五级节点 + 边，支持 root_tech 筛选） |
| `GET` | `/{position_id}` | 获取岗位详情（含技能要求和变化历史） |

#### 简历 (`resume.py`) — 前缀 `/api/v1/resume`

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/upload` | 上传并解析简历文件（PDF/Word） |
| `GET` | `/resumes` | 获取当前用户的所有简历 |
| `GET` | `/{resume_id}` | 获取简历详情 |
| `POST` | `/` | 手动创建空简历 |
| `PUT` | `/{resume_id}` | 更新简历 |
| `DELETE` | `/{resume_id}` | 删除简历 |
| `POST` | `/{resume_id}/duplicate` | 复制简历 |

#### 匹配 (`match.py`) — 前缀 `/api/v1/match`

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/` | 单次匹配：简历 vs 岗位 |
| `GET` | `/result/{resume_id}/{position_id}` | 获取历史匹配结果 |
| `GET` | `/history` | 获取匹配历史 |
| `POST` | `/batch` | 批量匹配：简历 vs 多个岗位 |
| `POST` | `/auto/{resume_id}` | **[Agent 3]** 自动匹配：简历 vs 全站岗位，按分数降序返回 |

#### 简历优化 (`tailor.py`) — 前缀 `/api/v1/tailor`

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/suggestions/{resume_id}/{position_id}` | **[Agent 1]** 获取 AI 优化建议（含图谱校验） |
| `POST` | `/accept` | 接受单条优化建议 |
| `POST` | `/apply-all` | 批量应用已接受建议，生成新简历 |
| `POST` | `/optimize-phrase` | 短语润色 |
| `POST` | `/save-as-new` | 保存优化版简历 |

#### 学习路径 (`learning.py`) — 前缀 `/api/v1/learning`

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/paths` | 获取用户所有学习路径 |
| `GET` | `/paths/{path_id}` | 获取学习路径详情 |
| `POST` | `/paths` | 创建学习路径 |
| `PUT` | `/paths/{path_id}` | 更新学习路径（名称/步骤/完成状态） |
| `DELETE` | `/paths/{path_id}` | 删除学习路径 |
| `POST` | `/assistant/chat` | **[Agent 2]** AI 学习助手对话 |
| `POST` | `/assistant/generate-path` | **[Agent 2]** 自动生成学习路径 |
| `POST` | `/assistant/recommend-resources` | AI 推荐学习资源 |
| `POST` | `/assistant/quiz` | AI 生成测试题 |

#### 收藏 (`favorites.py`) — 前缀 `/api/v1/favorites`

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `` | 获取收藏列表（可按 type 筛选） |
| `POST` | `` | 添加收藏 |
| `DELETE` | `/{fav_id}` | 取消收藏 |
| `GET` | `/check` | 检查是否已收藏某项 |

### 3.7 LLM Provider (`app/providers/llm.py`)

| 类 | 说明 |
|---|------|
| `LLMProvider` | 抽象基类，定义 `chat()` 接口 |
| `MockLLMProvider` | 测试用，返回固定 Mock 响应 |
| `DeepSeekProvider` | **生产用**。调用 DeepSeek Chat API（兼容 OpenAI 格式），支持结构化 JSON 输出和指数退避重试（最多 3 次） |
| `get_llm_provider()` | 工厂函数，测试模式返回 Mock，否则返回 DeepSeek |

### 3.8 其他后端文件

| 文件 | 作用 |
|------|------|
| `app/seed.py` | **种子数据填充**。在应用启动时检查各表是否为空，为空则自动插入示例数据（岗位、技能、简历、学习路径、收藏） |
| `tailor_sg.json` | Agent 1 的示例输出数据（AI 优化建议的样本 JSON） |
| `requirements.txt` | Python 依赖清单 |

---

## 四、前端文件说明 (`frontend/`)

### 4.1 目录结构总览

```
frontend/
├── index.html              # HTML 入口
├── package.json            # 依赖和脚本
├── vite.config.ts          # Vite 构建配置（含 API 代理到 8000）
├── tsconfig.json           # TypeScript 配置
├── src/
│   ├── main.ts             # 应用入口（创建 Vue app、注册插件）
│   ├── App.vue             # 根组件（布局框架：侧边栏 + 顶栏 + 内容区）
│   ├── assets/
│   │   └── styles/
│   │       └── global.scss # 全局样式变量（CSS 自定义属性）
│   ├── api/                # API 接口层
│   ├── stores/             # Pinia 状态管理
│   ├── router/             # 路由配置
│   ├── types/              # TypeScript 类型定义
│   ├── utils/              # 工具函数
│   ├── mock/               # Mock 数据
│   ├── components/         # 可复用组件
│   └── views/              # 页面视图
```

### 4.2 入口文件

| 文件 | 作用 |
|------|------|
| `src/main.ts` | **Vue 应用入口**。创建 Pinia、Vue Router、Element Plus 实例，全局注册所有 Element Plus 图标组件 |
| `src/App.vue` | **根布局组件**。`<AppSidebar>` + `<AppHeader>` + `<router-view>` |
| `vite.config.ts` | Vite 构建配置，配置了 `/api` → `http://127.0.0.1:8000` 的代理转发 |

### 4.3 API 接口层 (`src/api/`)

每个文件封装一组后端 API 调用，使用 axios 实例（`src/api/index.ts`）。

| 文件 | 说明 |
|------|------|
| `index.ts` | **Axios 实例**。配置 baseURL、请求拦截器（自动附加 JWT token）、响应拦截器（401 自动跳转登录页） |
| `auth.ts` | 认证 API：`login()`, `register()`, `getProfile()`, `updateProfile()`, `changePassword()` |
| `positions.ts` | 岗位 API：`getList()`, `getDetail()`, `getGraph()` |
| `resume.ts` | 简历 API：`upload()`, `getList()`, `getDetail()`, `create()`, `update()`, `deleteResume()`, `duplicate()` |
| `match.ts` | 匹配 API：`match()`, `getResult()`, `getHistory()`, `matchBatch()`, `autoMatch()` |
| `tailor.ts` | 优化 API：`getSuggestions()`, `accept()`, `applyAll()`, `optimizePhrase()`, `saveAsNew()` |
| `learning.ts` | 学习 API：路径 CRUD + `chat()`, `generatePath()`, `recommendResources()`, `quiz()` |
| `favorites.ts` | 收藏 API：`getList()`, `add()`, `remove()`, `check()` |
| `career.ts` | 职业发展 API：`assess()`, `getPlan()`, `savePlan()` |

### 4.4 类型定义 (`src/types/index.ts`)

前后端共享的完整数据模型定义，包括：

- **岗位**: `JobPosition`, `Skill`, `SkillChange`
- **图谱**: `GraphNode`（五级类型）, `GraphEdge`, `KnowledgeGraph`
- **简历**: `ResumeData`, `Education`, `WorkExperience`, `Project`
- **匹配**: `MatchResult`, `MatchDimension`, `ImprovementSuggestion`, `GapAnalysis`
- **学习**: `LearningPath`, `LearningStep`, `LearningResource`
- **职业发展**: `CareerPlan`, `CareerTransitionAssessment`, `CareerPreferences`, `LearningBudget`
- **用户**: `UserProfile`
- **通用**: `ApiResponse<T>`, `PaginatedData<T>`

### 4.5 状态管理 Store (`src/stores/`)

Pinia 组合式 API 风格的状态管理。

| 文件 | Store ID | 核心 State | 说明 |
|------|----------|-----------|------|
| `user.ts` | `user` | `user`, `token`, `isLoggedIn` | 用户认证状态、登录/注册/获取个人信息/更新资料/修改密码 |
| `resume.ts` | `resume` | `resumes`, `currentResume`, `loading` | 简历列表和详情，增删改查复制上传 |
| `positions.ts` | `positions` | `positions`, `currentPosition`, `graphNodes`, `graphEdges`, `loading` | 岗位列表/详情，知识图谱数据 |
| **`match.ts`** | `match` | `currentResult`, `history`, `aiSuggestions`, `batchResults`, `selectedBatchResult` | **核心匹配 Store**。单次匹配、AI 建议获取、一键优化、自动匹配全站岗位、批次结果管理 |
| `learning.ts` | `learning` | `paths`, `currentPath`, `chatHistory` | 学习路径 CRUD、步骤切换、AI 对话框 |
| `favorites.ts` | `favorites` | `allFavorites`, `positionFavs`, `resourceFavs`, `errorFavs`, `knowledgeFavs` | 四种类型收藏的增删查、分组计算 |

### 4.6 数据转换 (`src/utils/transform.ts`)

**前后端字段名转换**：后端使用 snake_case（`total_score`），前端使用 camelCase（`totalScore`）。本文件提供所有数据模型的转换函数。

| 函数 | 方向 | 说明 |
|------|------|------|
| `resumeFromApi()` | 后端→前端 | 简历数据转换 |
| `resumeToApi()` | 前端→后端 | 简历数据转换（更新请求用） |
| `positionFromApi()` | 后端→前端 | 岗位数据转换（含嵌套技能） |
| `pathFromApi()` | 后端→前端 | 学习路径转换 |
| `matchResultFromApi()` | 后端→前端 | 匹配结果转换（含维度、差距、建议嵌套） |
| `suggestionFromApi()` | 后端→前端 | 单条优化建议转换 |

### 4.7 路由配置 (`src/router/index.ts`)

| 路由 | 名称 | 页面组件 | 说明 |
|------|------|---------|------|
| `/` | — | — | 重定向到 `/login` |
| `/login` | `Login` | `views/Login.vue` | 登录页 |
| `/register` | `Register` | `views/Register.vue` | 注册页 |
| `/home` | `Home` | `views/Home.vue` | **首页**：快捷入口 + 推荐岗位 + 学习路径 |
| `/positions` | `Positions` | `views/positions/Index.vue` | **岗位探索**：岗位列表搜索 |
| `/positions/:id` | `PositionDetail` | `views/positions/Detail.vue` | **岗位详情**：概述/技能/图谱/诊断入口 |
| `/graph` | `Graph` | `views/graph/Index.vue` | **知识图谱**：五级技能关系可视化 |
| `/favorites` | `Favorites` | `views/favorites/Index.vue` | **我的收藏**：岗位/资料/错题/知识点四Tab |
| `/diagnosis` | `DiagnosisIndex` | `views/diagnosis/Index.vue` | **简历诊断列表**：简历管理 |
| `/diagnosis/:id` | `DiagnosisDetail` | `views/diagnosis/Detail.vue` | **简历诊断详情**：编辑 + 智能匹配 |
| `/career` | `Career` | `views/career/Index.vue` | **职业发展**：双路径（智能推荐/定向搜索）→ 差距分析 → 学习路径 |
| `/learning` | `Learning` | `views/learning/Index.vue` | **学习路径**：学习计划管理 + AI 助手 |
| `/profile` | `Profile` | `views/profile/Index.vue` | **个人中心**：资料编辑 + 改密 + 匹配历史 |

### 4.8 页面视图 (`src/views/`)

| 文件 | 功能描述 | 关键交互 |
|------|---------|---------|
| `Login.vue` | 登录/注册切换表单 | 用户名密码登录，注册含邮箱 |
| `Home.vue` | **首页** | 快捷入口卡片（简历诊断/探索岗位/知识图谱/职业发展）、推荐岗位网格、学习路径折叠面板（含流程图时间线） |
| `positions/Index.vue` | **岗位探索列表** | 搜索筛选（关键词/分类/职级）、岗位卡片列表、"开始匹配"快速浮窗 |
| **`positions/Detail.vue`** | **岗位详情** | 岗位概述/职责/技能（必备+加分）/行业场景、关联技能图谱小部件、能力变化时间线（既有岗位）、**"开始匹配诊断"按钮 → 简历选择对话框**、收藏切换 |
| `graph/Index.vue` | **知识图谱** | 五级技能图谱可视化、节点展开/折叠 |
| `favorites/Index.vue` | **我的收藏** | 四Tab（岗位/学习资料/错题/AI知识点）、卡片网格、取消收藏 |
| `diagnosis/Index.vue` | **简历诊断列表** | 简历卡片列表、创建/上传/删除/复制简历 |
| **`diagnosis/Detail.vue`** | **简历诊断详情**（核心页面） | 双Tab：**编辑简历**（表单+预览）→ **简历匹配**（自动匹配全站岗位 → 左侧排名列表 + 右侧诊断报告详情 → 技能差距分析 → AI 优化建议接受/拒绝 → 一键生成优化版简历） |
| **`career/Index.vue`** | **职业发展**（双路径） | Step 1 双卡片：**Path A** "不知道转什么方向"（选简历 → 智能推荐岗位）；**Path B** "已有目标方向"（关键词搜索）→ Step 2 岗位推荐列表（含匹配分数和缺失技能）→ Step 3 确认目标（差距分析/维度评分）→ Step 4 生成学习路径流程图 |
| `learning/Index.vue` | **学习路径** | 学习路径列表、AI 学习助手对话框、测验功能 |
| `profile/Index.vue` | **个人中心** | 个人信息表单、修改密码、快捷入口、匹配历史列表 |

### 4.9 可复用组件 (`src/components/`)

| 文件 | 说明 |
|------|------|
| `layout/AppSidebar.vue` | **左侧导航栏**。六项菜单（首页/岗位探索/知识图谱/我的收藏/简历诊断/学习路径/职业发展）、路由高亮 |
| `layout/AppHeader.vue` | **顶部导航栏**。面包屑、搜索框、城市/学历快速设置、通知、用户头像下拉菜单 |
| `common/QuickMatchFab.vue` | **快速匹配悬浮按钮**。右下角 FAB，两种模式：`list`（批量匹配后弹窗显示结果）、`detail`（选简历跳转诊断详情页并传递岗位上下文） |
| `common/FloatingAIButton.vue` | AI 助手悬浮入口按钮 |
| `positions/PositionCard.vue` | **岗位卡片组件**。展示岗位名称/分类/薪资/技能标签 |
| `diagnosis/MatchPanel.vue` | 匹配面板组件（独立于详情页的匹配 UI） |

### 4.10 Mock 数据 (`src/mock/`)

| 文件 | 说明 |
|------|------|
| `data/positions.ts` | 示例岗位数据 |
| `data/resume.ts` | 示例简历数据 |
| `data/match.ts` | 示例匹配结果 |
| `data/tailor.ts` | 示例优化建议 |
| `data/learning.ts` | 示例学习路径 |
| `data/career.ts` | 示例职业发展计划 |
| `data/notes.ts` | 示例笔记 |

---

## 五、核心业务流程

### 5.1 简历诊断流程（Agent 1 + Agent 3）

```
1. 用户进入 /diagnosis → 简历列表
2. 点击某份简历 → /diagnosis/:id → 编辑 Tab
3. 切换到"简历匹配" Tab → 自动触发 autoMatch()
4. 后端逐一匹配全站岗位 → 按 totalScore 降序返回
5. 左侧：排名列表（分数 + 匹配/缺失技能数）
6. 点击某岗位 → 右侧展开：
   - 四维度评分（技能/经验/学历/综合素质）
   - 技能差距分析（绿色=已具备，黄色=薄弱，红色=缺失）
   - 规则生成的改进建议
   - AI 优化建议卡片（含 diff 对比 + 图谱校验标签）
7. 用户 接受/拒绝 每条建议
8. 点击"一键优化简历" → 生成新简历保存到数据库
```

### 5.2 岗位探索 → 匹配诊断流程

```
1. /positions → 浏览/搜索岗位
2. 点击岗位 → /positions/:id → 岗位详情
3. 点击"开始匹配诊断" → 弹出简历选择对话框
4. 选择简历 → 跳转 /diagnosis/:resumeId?positionId=X&focusPos=true
5. 诊断详情页自动匹配并展开对应岗位的报告
```

### 5.3 职业发展双路径流程（Agent 2）

```
Path A（不知道转什么方向）：
  选简历 → 自动匹配全站岗位 → 按分数排名 → 选目标 → 差距分析 → 生成学习路径

Path B（已有目标方向）：
  输入关键词 → 搜索岗位 → 可选简历匹配 → 选目标 → 差距分析 → 生成学习路径
```

### 5.4 AI 学习助手流程（Agent 2）

```
1. 用户在 /learning 页面打开 AI 助手对话框
2. 输入问题（如"转行 AI 需要学什么？"）
3. 后端从 Neo4j 图谱查询相关技能依赖关系作为上下文
4. 拼接 system prompt → 调用 LLM → 返回 Markdown 回复
5. 同时从图谱提取关联概念和推荐资源
6. 可自动生成学习路径和测试题
```

---

## 六、数据库表结构

### MySQL（关系数据）

```
user
├── id (PK)
├── username (唯一)
├── email
├── password_hash
├── nickname, phone, city, education
└── created_at

resume
├── id (PK)
├── user_id (FK → user.id)
├── name
├── personal_info (JSON: name, email, phone, location)
├── job_intent (JSON: desired_position, desired_city, salary_expectation, work_mode)
├── education (JSON)
├── work_experience (JSON)
├── projects (JSON)
├── skills (JSON: [{name, level, category}])
├── self_evaluation
├── source_file
├── created_at, updated_at
└── is_deleted

job_position
├── id (PK)
├── name
├── category ('new' | 'existing')
├── aliases (JSON)
├── summary
├── responsibilities (JSON)
├── industry_scenarios (JSON)
├── tech_stack (JSON)
├── career_level ('junior' | 'mid' | 'senior')
├── salary_range
├── created_at, updated_at
└── is_deleted

position_skill
├── id (PK)
├── position_id (FK → job_position.id)
├── name
├── level ('required' | 'preferred' | 'advanced')
├── category
└── kind ('required' | 'preferred')

match_record
├── id (PK)
├── user_id (FK → user.id)
├── resume_id (FK)
├── position_id (FK)
├── total_score (INT, 0-100)
├── dimensions (JSON)
├── gap_analysis (JSON)
├── suggestions (JSON)
└── created_at

learning_path
├── id (PK)
├── user_id (FK → user.id)
├── name
├── position_id (FK → job_position.id)
├── position_name
├── steps (JSON)
├── total_duration
├── created_at, updated_at
└── is_deleted

favorite
├── id (PK)
├── user_id (FK → user.id)
├── item_type (VARCHAR 30: 'position' | 'learning_resource' | 'quiz_error' | 'knowledge_point')
├── item_id (VARCHAR 100)
├── title
├── summary
├── metadata (JSON)  -- 映射为 item_data
├── tags (JSON)
└── created_at
```

### Neo4j（知识图谱）

五级节点结构：`Position → SkillsetBranch → Module → Knowledge`

- **Position** (`:Position`) — 岗位节点
- **SkillsetBranch** (`:SkillsetBranch`) — 技能集分支
- **Module** (`:Module`) — 模块
- **Knowledge** (`:Knowledge`) — 知识点

关系类型：`:COMPOSES`, `:CONTAINS`, `:INCLUDES`

---

## 七、如何运行

### 7.1 前置条件

- Node.js 18+
- Python 3.11+
- MySQL 8.0+
- Neo4j 4.x+（可选，图谱功能）
- Redis（可选，Celery 用）

### 7.2 后端启动

```bash
cd jtt-src/backend

# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填入数据库密码、JWT密钥等

# 4. 启动（端口 8000）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 7.3 前端启动

```bash
cd jtt-src/frontend

# 1. 安装依赖
npm install

# 2. 启动开发服务器
npm run dev

# 3. TypeScript 类型检查
npx vue-tsc --noEmit

# 4. 生产构建
npm run build
```

### 7.4 默认管理员账号

在 `.env` 中配置 `INITIAL_ADMIN_ENABLED=true` 后，启动时会自动创建：

- 用户名: `admin`
- 密码: `admin123`

### 7.5 启用 AI 功能

在 `.env` 中设置真实 LLM Key：

```env
LLM_API_KEY=sk-your-deepseek-api-key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

当前 `LLM_API_KEY` 为空时，所有 AI 功能自动走规则降级。

---

## 八、AI/智能体扩展点速查

| 文件 | 行内注释标记 | 说明 |
|------|------------|------|
| `backend/app/services/match_service.py` | `# [AI] 此处可接入 LLM...` | 技能语义匹配、维度解读、建议生成 |
| `backend/app/services/tailor_service.py` | `# [AI] 核心 Prompt...` / `# [AI] LLM 调用入口...` | Prompt 组装、LLM 调用入口、规则降级路径 |
| `backend/app/services/learning_service.py` | `# [AI] 学习路径 LLM 生成入口...` | 路径生成 LLM 调用、规则降级 |
| `frontend/src/stores/match.ts` | `// [Agent 3]` | 前端自动匹配入口 |
| `frontend/src/api/match.ts` | `// [Agent 3] 自动匹配` | autoMatch API 封装 |
| `frontend/src/views/diagnosis/Detail.vue` | `<!-- [Agent 3] 自动匹配所有岗位 -->` | 匹配 Tab UI |

---

## 九、常用调试命令

```bash
# 后端健康检查
curl http://127.0.0.1:8000/api/v1/health

# 测试登录获取 token
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 测试自动匹配（替换 TOKEN）
curl -X POST http://127.0.0.1:8000/api/v1/match/auto/2 \
  -H "Authorization: Bearer <TOKEN>"

# 前端类型检查
cd jtt-src/frontend && npx vue-tsc --noEmit

# 检查 git 暂存区是否有问题
git diff --cached --check
```

---

## 十、新环境准备清单（本地从零跑通 JTT 求职端）

> 本清单适用于新成员拉取代码后，在本机完整跑通 JTT 求职者端（除知识图谱外全部功能）。
> 共涉及 3 个服务进程 + MySQL，即 4 个终端。以下内容为当前实际可用的启动方式。

### 10.1 服务与端口总览

| 服务 | 目录 | 端口 | 说明 |
|---|---|---|---|
| MySQL | 本机服务（本机名为 `mysql97`） | 3306 | 业务库 + 爬虫库 |
| JTT 后端 | `jtt-src/backend` | **8000** | FastAPI，业务接口 |
| AI 助手服务 | `jtt-src/ai-assistant` | **8001** | 独立 LLM 代理（DeepSeek） |
| JTT 前端 | `jtt-src/frontend` | 5173 | Vite dev，代理数据→8000、AI→8001 |

### 10.2 配置文件准备（git 未跟踪，必须手动创建）

**1）JTT 后端 `.env`**

```powershell
Copy-Item jtt-src\backend\.env.example jtt-src\backend\.env
```

编辑 `jtt-src/backend/.env`，至少配置：

| 变量 | 必填 | 说明 |
|---|---|---|
| `DB_PASSWORD` | ✅ | 本机 MySQL 密码 |
| `JWT_SECRET_KEY` | ✅ | 任意随机字符串 |
| `LLM_API_KEY` | 可选 | DeepSeek Key，为空时 AI 功能走规则降级 |
| `INITIAL_ADMIN_ENABLED` | ✅ | 设为 `true`，自动创建 `admin / admin123` |
| `NEO4J_*` | 可选 | 无 Neo4j 不影响除图谱外功能 |

**2）AI 助手服务 `.env`**

```powershell
Copy-Item jtt-src\ai-assistant\.env.example jtt-src\ai-assistant\.env
```

编辑 `jtt-src/ai-assistant/.env`，必填：

```
DEEPSEEK_API_KEY=sk-你的Key
```

### 10.3 数据库准备（MySQL）

需要两个库：

```sql
CREATE DATABASE jiebang_user CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE jie_bang CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
```

- **`jiebang_user`**（应用数据：用户/简历/学习路径/匹配）：建库即可，后端启动时自动建表并创建 admin 账号。
- **`jie_bang`**（爬虫岗位数据：`raw_job_record` 等 190 条）：**仓库不包含该库数据，不会自动创建**，需从已有环境导出导入：

```bash
# 已有环境导出
mysqldump -h localhost -P 3306 -u root -p jie_bang > jie_bang_full.sql

# 新环境导入（先执行上面的 CREATE DATABASE）
mysql -h localhost -u root -p < jie_bang_full.sql
```

未导入 `jie_bang` 时：岗位探索页为空，自动匹配降级为 MySQL `job_position` 的少量种子数据。

### 10.4 启动顺序（4 个终端）

```powershell
# 1) MySQL（本机服务）
net start mysql97

# 2) JTT 后端（8000）
cd "D:\contest\little challenge\JieBang\jtt-src\backend"
D:\Anaconda\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 3) AI 助手服务（8001）
cd "D:\contest\little challenge\JieBang\jtt-src\ai-assistant"
D:\Anaconda\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# 4) JTT 前端（5173）
cd "D:\contest\little challenge\JieBang\jtt-src\frontend"
npm.cmd run dev
```

> `D:\Anaconda\python.exe` 为示例路径，按本机 Python 环境替换；`--reload` 可选（开发时开启）。

### 10.5 验证

```powershell
# 后端健康检查（neo4j: unavailable 属正常，不影响使用）
curl http://localhost:8000/api/v1/health

# 打开浏览器 http://localhost:5173
# 用 admin / admin123 登录 → 岗位探索应显示 190 条岗位
```

### 10.6 没有 Neo4j 时的功能边界

| 功能 | 无 Neo4j 是否可用 |
|---|---|
| 岗位探索 / 简历 CRUD / 简历诊断 / 一键优化 / 悬浮窗匹配诊断 / 学习路径 / AI 聊天 | ✅ 可用（走 MySQL + AI 服务） |
| 知识图谱页面 / 图谱富化 | ❌ 空（0 节点） |

> 后端对 Neo4j 连接失败会自动降级（健康检查显示 `unavailable`，启动不受影响）。

### 10.7 常见问题

| 现象 | 原因与解决 |
|---|---|
| 后端启动报缺库 | 未执行 10.3 建库 |
| 岗位探索空白 | `jie_bang` 未导入（见 10.3） |
| AI 功能 503 / 报错 | `ai-assistant/.env` 的 `DEEPSEEK_API_KEY` 未配置或失效 |
| 登录失败 | 确认 `INITIAL_ADMIN_ENABLED=true` 且后端已自动建表 |
```
