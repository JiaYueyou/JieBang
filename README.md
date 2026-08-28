# 智联职引（JieBang）

面向数字产业岗位与人才的智能适配平台。项目通过多源岗位数据、技能抽取、
岗位能力图谱和大模型 Agent，支持岗位管理、能力趋势分析、简历解析、
人岗匹配解释与转岗学习规划。

> 新成员建议按本文顺序完成：了解当前状态 → 阅读文档登记表 → 克隆代码 → 配置环境
> → 初始化数据库 → 启动所需服务 → 运行对应检查 → 创建个人分支开发。

> 文档类型：项目现行入口
> 当前阶段：核心系统基本完成，进入联调收尾、质量验收与竞赛材料编制阶段
> 核验日期：2026-08-28；核验基线：`28a4cc5b` + 当前工作区只读验证
> 模块完成度、测试结果和已知风险见 [当前实现状态](docs/implementation-status.md)。

## 1. 当前状态

核心工程已经具备：

- FastAPI 认证、岗位 CRUD、岗位版本、技能抽取和数据导入接口；
- MySQL Alembic 迁移链与初始管理员 bootstrap；
- MySQL 事实数据到 Neo4j 能力图谱的全量/增量同步；
- 手动/定时自动数据闭环、流水线运行持久化、历史基线与 Redis 查询/状态缓存；
- 独立 `agent-development` 包：JD 草稿、技能补全、L4/L5 图谱补全与职业规划 Agent；
- 可编辑草稿的 JD 生成 Agent、L4/L5 证据门槛，以及简历文本解析和转岗学习规划接口；
- 比赛脱敏数据迁移包已按 `20260820_0025` 重新导出，并纳入 Docker 空库引导；
- FYZ 管理与决策端、JTT 求职者端两套 Vue 3 前端，以及独立 JTT FastAPI 后端与 AI 助手服务；
- DeepSeek 可选增强；模型不可用时 JD 与职业规划仍返回可编辑/可执行模板结果；
- 后端测试、两套前端构建和仓库安全 CI。

当前可验证的软件基线（FYZ/Agent 沿用最近已提交结果，2026-08-28 重新验证 JTT）：

- FYZ 后端 OpenAPI：91 个路径、104 个 HTTP 操作；早期无消费者的 `/changes` 占位路由
  已移除，其能力变化需求由 Analysis 趋势与岗位版本接口覆盖；
- FYZ 后端：343 项 pytest 通过；独立 Agent 包：16 项 pytest 通过；
- FYZ 前端：44 项 Vitest 通过，TypeScript 与生产构建通过；
- JTT 前端 TypeScript 与生产构建通过，但未配置前端自动化测试；只读 ESLint 当前为
  217 errors、1 warning；
- JTT 后端收集到 38 项 pytest：绕过缺失的覆盖率插件后为 37 passed、1 failed；默认命令
  因 `pytest-cov` 未纳入依赖而无法启动，不能继续引用旧报告的“38 项全部通过”；
- 上述结果不等同于真实 MySQL、Redis、外部模型、爬虫外站和完整浏览器 E2E 均已验收。

截至 2026-08-28，代码与仓库内共享快照状态为：

- FYZ Alembic 当前 head 与比赛 SQL 快照均为 `20260820_0025`；快照含 47 张表、54474 行，
  SQL、manifest、逐表计数/摘要和独立校验摘要已通过离线严格校验；
- ChromaDB 4 个有效 collection、646 条 3072 维预计算向量；
- Neo4j 最近快照摘要为 5077 个节点、5680 条关系；
- 快照包含岗位标准化、事实审核、L4/L5 候选/发布、检索索引和 Agent 审计数据。

交付前仍需收尾和验收：

- JTT 后端路由已实现首版，当前 Vite 开发代理可将主数据请求发往 8000、AI 请求发往
  8001；但 MSW 仍使用 `/api` 而 Axios 默认使用 `/api/v1`，生产环境也没有 JTT Nginx/容器
  分流，因此不能表述为已完成真实部署联调；
- FYZ `20260820_0025` 团队数据库迁移包已完成重导和离线严格校验，仍需在隔离接收环境
  执行覆盖式导入验收；
- L4/L5 Agent 已补齐分类重试、调用诊断、人工审核质量门槛和离线故障注入压测，真实外部模型仍需持续压测；
- 爬虫增量检查点、岗位/技能标准化金标评测、图谱结构分析和比赛级统一门禁已实现首版，仍需真实外站与基础设施长期验收；
- 当前共享快照含内部开发记录，对外发布前必须完成数据授权和脱敏复核。

### 1.1 下一阶段：策划书与技术文档

后续工作从“继续扩展功能”转向“以当前实现为依据固化项目材料”。策划书和技术文档必须
基于 [当前实现状态](docs/implementation-status.md)、[技术文档状态登记表](docs/document-status-register.md)、
运行时 OpenAPI、Alembic 迁移和已提交评测产物编写，不得直接复制早期计划中的未落地技术栈、
旧接口、旧测试数量或旧数据库版本。

计划形成以下正式材料：

1. **项目策划书**：项目背景、目标用户、核心闭环、竞赛价值、功能边界、实施成果、风险与交付计划。
2. **总体技术说明书**：系统拓扑、两套业务端边界、数据流、存储职责、接口与部署架构。
3. **关键技术专项**：多源数据治理、岗位标准化、五层能力图谱、混合检索、Agent 防幻觉、匹配与趋势算法。
4. **测试与评测说明**：测试范围、质量指标、数据集边界、覆盖率、已知限制及可复现命令。
5. **部署与使用说明**：环境准备、启动拓扑、配置项、演示流程、故障处理和数据安全要求。

材料中的状态统一使用“已实现 / 基本实现 / 部分实现 / 阻塞 / 历史规划”口径；策划目标与
实测结果必须分栏表达。新文档遵循 [统一文档规范](docs/documentation-standard.md)。

## 2. 仓库目录

```text
JieBang/
├── fyz-src/
│   ├── backend/             # FastAPI、MySQL、Alembic、Neo4j、Celery、DeepSeek
│   ├── frontend/            # FYZ 管理与决策端 Vue 3
│   └── docs-plans/          # 历史/专项设计与实施计划
├── jtt-src/
│   ├── README.md            # JTT 当前代码、数据、测试与部署入口
│   ├── frontend/            # JTT 求职者端 Vue 3
│   ├── backend/             # JTT 独立 FastAPI、MySQL、Neo4j
│   ├── ai-assistant/        # JTT 独立 AI 助手 FastAPI（默认 8001）
│   └── docs/                # JTT 原始需求提取材料
├── deploy/                  # FYZ Docker Compose 部署
├── data/                    # 允许后端导入的原始岗位 JSON 数据
├── data_analysis/           # 离线词典与可选模型配置，不含独立导入流水线
├── agent-development/       # 独立 Agent 包、接口契约、Prompt、测试与开发计划
├── docs/
│   ├── team/                # 成员 A-F 独立开发指南
│   ├── README.md            # 文档中心
│   ├── implementation-status.md      # 当前实现、测试与风险基线
│   ├── document-status-register.md   # 全库技术文档有效性登记
│   ├── requirements.md      # 项目需求与验收目标
│   ├── dev-spec.md          # 代码、API、数据库开发规范
│   ├── database-and-runtime.md
│   ├── api-reference.md
│   ├── documentation-standard.md
│   └── git-workflow.md
├── .github/                 # CI、仓库安全检查和 PR 模板
├── AGENTS.md                # 仓库级开发约定
└── README.md                # 当前项目入口
```

不要提交本地的 `.env`、`node_modules`、`dist`、缓存、数据库、上传文件、
IDE 配置或 AI 工具会话。完整规则见
[仓库安全说明](docs/repository-security.md)。

## 3. 环境要求

| 组件 | 推荐版本 | 用途 |
| --- | --- | --- |
| Git | 2.40+ | 分支和 PR 协作 |
| Python | 3.10 | FastAPI 与数据流水线 |
| Conda | 任意近期版本 | 统一 Python 环境 `jiebang` |
| Node.js | 22.12+ | 两套 Vue 前端 |
| MySQL | 8.0 | 业务事实库 |
| Neo4j | 5.x Community | 可重建图查询模型 |
| ChromaDB | 由 `requirements.txt` 固定 | 本地持久化向量检索索引 |
| Redis | 7.x | Celery Broker/结果存储与可选查询、任务状态缓存 |

本项目不依赖任何成员机器上的绝对安装路径。激活 `jiebang` 环境后直接使用
`python`、`pip`、`alembic`、`pytest` 命令。

## 4. 第一次克隆与 Git 初始化

```powershell
git config --global user.name "你的姓名或 GitHub 用户名"
git config --global user.email "你的 GitHub 邮箱"
git config --global init.defaultBranch main
git config --global fetch.prune true

cd E:\Project
git clone https://github.com/JiaYueyou/JieBang.git
cd JieBang
git remote -v
git status --short --branch
```

每天开始开发：

```powershell
git switch main
git fetch origin
git pull --ff-only origin main
git switch -c feat/a-job-management
```

开发中小步提交：

```powershell
git status --short
git diff
git add 指定文件
git diff --cached
git diff --cached --check
git commit -m "feat(fyz-backend): add job filtering"
```

提交 PR 前同步主线：

```powershell
git fetch origin
git rebase origin/main
git push -u origin feat/a-job-management
```

PR 合并后：

```powershell
git switch main
git pull --ff-only origin main
git branch -d feat/a-job-management
git fetch --prune
```

禁止直接推送或强推 `main`。冲突、stash、revert、误提交和密钥事故处理见
[团队 Git 日常协作指南](docs/git-workflow.md)。

## 5. 初始化本地环境

### 5.1 Python

```powershell
conda create -n jiebang python=3.10 -y
conda activate jiebang

cd fyz-src\backend
python -m pip install -r requirements-dev.txt
```

### 5.2 前端

```powershell
cd fyz-src\frontend
npm.cmd ci --cache .npm-cache

cd ..\..\jtt-src\frontend
npm.cmd ci --cache .npm-cache
```

### 5.3 私密配置

```powershell
Copy-Item fyz-src\backend\.env.example fyz-src\backend\.env
```

编辑后端本地 `.env`，至少配置 MySQL、JWT 和 Neo4j。DeepSeek 是可选增强项，
未配置时规则抽取和 L1-L3 图谱仍可工作。真实密钥只能写入 `.env`。

JTT 主后端和 AI 助手使用各自配置文件：

```powershell
Copy-Item jtt-src\backend\.env.example jtt-src\backend\.env
Copy-Item jtt-src\ai-assistant\.env.example jtt-src\ai-assistant\.env
```

JTT 主后端的岗位接口会只读访问共享 `jie_bang.raw_job_record`、`source_document`、
`standard_job_source` 和 `standard_job`，数据库账号必须具备这些表的读取权限。JTT 当前
`requirements.txt` 尚缺测试插件及 PDF/DOCX 解析依赖，不能把单次开发机可运行等同于空环境可复现安装。

## 6. 推荐启动顺序

### 6.1 MySQL 与 Alembic

在 MySQL 中创建空数据库：

```sql
CREATE DATABASE jie_bang
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
```

然后执行：

```powershell
cd fyz-src\backend
alembic current
alembic upgrade head
alembic current
```

当前 `mysql_snapshot.sql`、manifest 和校验摘要均对应 `20260820_0025`。使用完整迁移入口前，
先运行 `python scripts/verify_mysql_snapshot_package.py`；覆盖式导入会替换目标 MySQL、Chroma
和 `namespace=jiebang` 的 Neo4j 数据，只能在已备份且确认目标的接收环境执行。

如果本地数据库已经存在旧表，不要猜测版本，也不要直接执行
`alembic stamp head`。请先阅读
[数据库、数据导入与运行指南](docs/database-and-runtime.md)。

### 6.2 Neo4j、Redis 与后端

启动本机 Neo4j 和 Redis 后：

```powershell
cd fyz-src\backend
python diagnose_neo4j.py
celery -A app.core.celery_app.celery_app worker --loglevel=info --pool=solo
```

另开终端启动后端：

```powershell
conda activate jiebang
cd fyz-src\backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

可访问：

- 健康检查：<http://localhost:8000/api/v1/health>
- Swagger：<http://localhost:8000/docs>
- ReDoc：<http://localhost:8000/redoc>

### 6.3 JTT 主后端与 AI 助手

JTT 主后端与 FYZ 后端源码均默认使用 8000，不能同时绑定同一端口。只运行求职者端时：

```powershell
conda activate jiebang
cd jtt-src\backend
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 另开终端
conda activate jiebang
cd jtt-src\ai-assistant
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

JTT Alembic 当前 head 为 `34d9b68a59ff`，应用启动时仍会同时执行 `create_all()`；这是待收敛的
迁移边界，不应在生产部署说明中省略。AI 助手需要 DeepSeek Key；未配置时只可验证服务健康状态
和部分降级逻辑，不能宣称真实模型联调完成。

### 6.4 两套前端

```powershell
# FYZ 管理与决策端
cd fyz-src\frontend
npm.cmd run dev

# JTT 求职者端（另开终端）
cd jtt-src\frontend
npm.cmd run dev
```

Vite 默认使用 5173；同时启动两套前端时，后启动的实例会自动选择其他端口。
后端当前 CORS 默认允许 `http://localhost:5173`，联调时应明确哪套前端占用该端口。

JTT 开发代理当前会把 `/api/v1/assistant/*`、学习助手和短语优化请求改写到 8001，其余
`/api/*` 请求转发到 8000。MSW handlers 仍停留在 `/api`，不会拦截默认 `/api/v1` 请求；
因此无真实服务时不能依赖默认 mock 启动。Vite proxy 只用于开发，生产部署必须在反向代理中
重新实现同样的主后端/AI 分流。

## 7. 导入岗位数据与构建图谱

后端仅允许导入以下白名单文件：

- `data/jd_crawl_ifly.json`
- `data/jd_crawl_zl.json`
- `data/jd_crawl2.json`

推荐流程：

```text
登录获取 Token
→ POST /api/v1/data-imports/jobs
→ GET /api/v1/tasks/{task_id} 等待 succeeded
→ POST /api/v1/graph/sync
→ GET /api/v1/tasks/{task_id} 等待 succeeded
→ GET /api/v1/graph/panorama
```

导入会按内容指纹幂等去重，并执行规则/DeepSeek 技能抽取和多来源交叉验证。
MySQL 保存事实与审计记录，Neo4j 仅保存可重建的 `namespace=jiebang` 查询模型。
完整 PowerShell 请求示例见 [API 参考](docs/api-reference.md)。

`data_analysis/` 仅保留离线词典和模型配置；仓库不再维护独立的离线导入脚本，
避免其输出与 MySQL 事实库产生分歧。

## 8. 测试与提交前验证

```powershell
# 后端
cd fyz-src\backend
python -m pytest test -q

# 独立 Agent 包
cd ..\..\agent-development
python -m pytest tests -q

# FYZ 前端
cd ..\fyz-src\frontend
npm.cmd run test
npm.cmd run build

# JTT 前端
cd ..\..\jtt-src\frontend
npm.cmd run build
# 当前无 test 脚本；质量审计使用只读命令，避免 npm run lint 的 --fix
npx.cmd eslint . --no-cache

# JTT 后端
cd ..\backend
# 当前 requirements 未包含 pytest-cov，默认命令会被 pytest.ini 的覆盖率参数阻断。
# 临时检查业务测试可使用下式；正式交付前应先补齐依赖并恢复覆盖率门禁。
python -m pytest test -q -o addopts=
```

根据改动范围至少运行对应检查；涉及共享接口、数据库或配置时运行全部检查。

## 9. 历史六人开发指南

以下文件保留早期分工，不代表当前剩余任务；当前完成度以状态基线为准。

| 成员 | 工作流 | 详细指南 |
| --- | --- | --- |
| A | FYZ 管理与决策端全栈 | [成员 A 开发指南](docs/team/member-a-fyz-fullstack.md) |
| B | JTT 求职者端全栈 | [成员 B 开发指南](docs/team/member-b-jtt-fullstack.md) |
| C | Agent 工程 | [成员 C 开发指南](docs/team/member-c-agent.md) |
| D | 爬虫与数据标准化 | [成员 D 开发指南](docs/team/member-d-crawler.md) |
| E | 知识图谱与分级抽取 | [成员 E 开发指南](docs/team/member-e-graph.md) |
| F | 平台集成与质量保障 | [成员 F 开发指南](docs/team/member-f-platform.md) |

统一目标是前 4 周完成可演示 MVP，后 8 周优化准确率、性能、可追溯性、
用户体验、测试覆盖和竞赛交付质量。

## 10. 文档导航

| 文档 | 用途 |
| --- | --- |
| [文档中心](docs/README.md) | 所有项目文档的分类入口 |
| [JTT 求职者端现状](jtt-src/README.md) | 用户端代码、数据、测试、运行与部署边界 |
| [当前实现状态](docs/implementation-status.md) | 代码、测试、完成度和已知缺口 |
| [技术文档状态登记表](docs/document-status-register.md) | 各技术文档是否仍为当前依据 |
| [需求文档](docs/requirements.md) | 功能范围、优先级与验收指标 |
| [开发规范](docs/dev-spec.md) | API、数据库、代码和协作规范 |
| [数据库与运行指南](docs/database-and-runtime.md) | MySQL、Alembic、Neo4j、Redis、数据导入 |
| [完整数据迁移说明](fyz-src/backend/scripts/DATABASE_TRANSFER.md) | 0025 迁移包、离线校验与隔离接收环境覆盖式导入流程 |
| [后端脚本清单](fyz-src/backend/scripts/README.md) | 当前脚本状态、维护入口和工程评测工具 |
| [API 参考](docs/api-reference.md) | FYZ 当前接口、请求示例和已移除兼容入口 |
| [Agent 开发工作区](agent-development/README.md) | 独立 Agent 包、契约、Prompt 与测试入口 |
| [统一文档规范](docs/documentation-standard.md) | 需求、接口、迁移和 Agent 文档格式 |
| [Git 协作指南](docs/git-workflow.md) | 分支、提交、PR、冲突和事故恢复 |
| [仓库安全说明](docs/repository-security.md) | 密钥、缓存和历史安全规则 |
