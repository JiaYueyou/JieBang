# 智联职引（JieBang）

面向数字产业岗位与人才的智能适配平台。项目通过多源岗位数据、技能抽取、
岗位能力图谱和大模型 Agent，支持岗位管理、能力趋势分析、简历解析、
人岗匹配解释与转岗学习规划。

> 新成员建议按本文顺序完成：了解目录 → 克隆代码 → 配置环境 → 初始化数据库
> → 导入数据 → 启动服务 → 创建个人分支开发。

## 1. 当前状态

当前已经具备：

- FastAPI 认证、岗位 CRUD、岗位版本、技能抽取和数据导入接口；
- MySQL Alembic 迁移链与初始管理员 bootstrap；
- MySQL 事实数据到 Neo4j 能力图谱的全量/增量同步；
- 独立 `agent-development` 包：JD 草稿、技能补全、L4/L5 图谱补全与职业规划 Agent；
- 可编辑草稿的 JD 生成 Agent、L4/L5 证据门槛，以及简历文本解析和转岗学习规划接口；
- 团队完整数据迁移包：Alembic 建表、MySQL 全量 SQL、ChromaDB 预计算向量复原、
  Neo4j 命名空间重建和三库一致性校验；
- FYZ 管理与决策端，以及 JTT 求职者端两套 Vue 3 前端；
- DeepSeek 可选增强；模型不可用时 JD 与职业规划仍返回可编辑/可执行模板结果；
- 后端测试、两套前端构建和仓库安全 CI。

截至 2026-08-01，仓库内共享快照状态为：

- MySQL Alembic `20260801_0017`，38 张表、4679 行；
- ChromaDB 4 个有效 collection、646 条 3072 维预计算向量；
- Neo4j 最近已成功图谱快照 474 个节点、817 条关系；
- 快照包含岗位标准化、事实审核、L4/L5 候选/发布、检索索引和 Agent 审计数据。

当前仍需继续开发和验收：

- JTT 简历、匹配、收藏、学习路径等页面需要继续对接真实后端；
- L4/L5 Agent 的外部模型稳定性、失败重试和人工审核质量仍需持续压测；
- 爬虫持续增量数据、岗位/技能标准化评测、图谱高级分析和比赛级评测仍需完善；
- 当前共享快照含内部开发记录，对外发布前必须完成数据授权和脱敏复核。

## 2. 仓库目录

```text
JieBang/
├── fyz-src/
│   ├── backend/             # FastAPI、MySQL、Alembic、Neo4j、Celery、DeepSeek
│   ├── frontend/            # FYZ 管理与决策端 Vue 3
│   ├── FULLSTACK_PLAN.md    # 全栈功能规划
│   └── GRAPH_ARCHITECTURE.md# 五级岗位能力图谱设计
├── jtt-src/
│   ├── frontend/            # JTT 求职者端 Vue 3
│   └── docs/                # JTT 原始需求提取材料
├── data/                    # 允许后端导入的原始岗位 JSON 数据
├── data_analysis/           # 离线词典与可选模型配置，不含独立导入流水线
├── agent-development/       # 独立 Agent 包、接口契约、Prompt、测试与开发计划
├── docs/
│   ├── team/                # 成员 A-F 独立开发指南
│   ├── README.md            # 文档中心
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
| Redis | 7.x | Celery Broker 和结果存储 |

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
python scripts\run_database_import.py --replace
```

该命令会用 Alembic 创建结构、导入仓库中的完整 MySQL SQL 快照，从 SQL 中
保存的预计算向量复原 ChromaDB，再从 MySQL 事实库重建 Neo4j
`namespace=jiebang`，最后校验三类存储。它不会重新调用 Embedding API。
命令会覆盖目标数据库已有业务数据；仅在确认
`fyz-src/backend/.env` 指向目标本地数据库后执行。分步命令和快照刷新方式见
[数据库、数据导入与运行指南](docs/database-and-runtime.md)。

推荐由团队成员直接使用 PowerShell 单入口：

```powershell
cd fyz-src\backend
.\scripts\Import-TeamDatabase.ps1 -Replace
```

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

### 6.3 两套前端

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

# FYZ 前端
cd ..\frontend
npm.cmd run test
npm.cmd run build

# JTT 前端
cd ..\..\jtt-src\frontend
npm.cmd run build
```

根据改动范围至少运行对应检查；涉及共享接口、数据库或配置时运行全部检查。

## 9. 六人开发指南

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
| [需求文档](docs/requirements.md) | 功能范围、优先级与验收指标 |
| [开发规范](docs/dev-spec.md) | API、数据库、代码和协作规范 |
| [数据库与运行指南](docs/database-and-runtime.md) | MySQL、Alembic、Neo4j、Redis、数据导入 |
| [完整数据迁移说明](fyz-src/backend/scripts/DATABASE_TRANSFER.md) | 团队 MySQL、ChromaDB、Neo4j 一键导入与一致性校验 |
| [API 参考](docs/api-reference.md) | 当前真实接口、请求示例和占位状态 |
| [Agent 开发工作区](agent-development/README.md) | 独立 Agent 包、契约、Prompt 与测试入口 |
| [统一文档规范](docs/documentation-standard.md) | 需求、接口、迁移和 Agent 文档格式 |
| [Git 协作指南](docs/git-workflow.md) | 分支、提交、PR、冲突和事故恢复 |
| [仓库安全说明](docs/repository-security.md) | 密钥、缓存和历史安全规则 |
