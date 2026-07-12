# 智联职引后端

## 环境

所有 Python 命令使用项目 Conda 环境：

```powershell
conda activate jiebang
pip install -r requirements-dev.txt
```

环境路径：`E:\Computer_tools\Anaconda\dld\envs\jiebang`。

## 数据库迁移

正式环境的数据库结构只由 Alembic 管理，应用启动不会自动建表。

### 空数据库

先在 MySQL 创建 `.env` 中 `DB_NAME` 指定的数据库，然后执行：

```powershell
alembic upgrade head
```

### 已存在旧 `user` 表的开发数据库

先人工确认表结构与
`alembic/versions/20260619_0001_user_baseline.py` 一致，再标记版本：

```powershell
alembic stamp 20260619_0001
alembic upgrade head
```

`stamp` 只写入 Alembic 版本号，不创建、删除或修改业务表。禁止直接执行
`alembic stamp head`，否则会跳过岗位、技能流水线和图谱审计表的迁移。

### 常用命令

```powershell
alembic current
alembic history
alembic upgrade head
alembic downgrade -1
alembic revision --autogenerate -m "describe change"
```

### ⚠ 数据库版本更新：`20260712_0006_matching`

本版本新增私有简历、解析结果、简历技能、确定性人岗匹配和匹配证据表：`resume`、`resume_parse_result`、`resume_skill`、`match_record`、`match_evidence`。更新代码后必须执行：

```powershell
alembic upgrade head
alembic current  # 应显示 20260712_0006 (head)
```

迁移完成后重启 Uvicorn，确认 `/api/v1/talents` 已注册。不要以 `alembic stamp head` 代替升级，否则会出现 API 已部署但匹配数据表缺失的问题。

新增 ORM 模型后，必须在 `app/models/__init__.py` 导入，确保 Alembic
自动生成迁移时可以读取完整 metadata。自动生成的 migration 必须经过人工检查。

也可以通过 `DATABASE_URL` 临时覆盖分项数据库配置：

```powershell
$env:DATABASE_URL="mysql+aiomysql://user:password@localhost:3306/jie_bang"
alembic upgrade head
```

## 完整数据库迁移包

需要把一台开发机的全部 MySQL 数据迁移到另一台机器，并从事实库重建
Neo4j 时，使用 [scripts/DATABASE_TRANSFER.md](scripts/DATABASE_TRANSFER.md)
中的编号脚本。接收方既可以依次执行 `01` 到 `04`，也可以运行：

```powershell
python scripts/run_database_import.py --replace
```

该流程会覆盖目标 MySQL 的现有业务数据；执行前必须确认目标 `.env`。
Neo4j 只重建 `namespace=jiebang`，不会复制或删除其他命名空间。

## 初始管理员

迁移完成后，应用启动会执行显式管理员 bootstrap，但不会创建表。

```text
INITIAL_ADMIN_ENABLED=true
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=admin123
```

部署环境必须修改默认密码，也可以设置 `INITIAL_ADMIN_ENABLED=false`
关闭自动初始化。如果数据库尚未迁移，应用会明确提示先运行
`alembic upgrade head`。

## 启动与测试

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pytest test/ -v
```

测试仍使用 SQLite 内存数据库，每条测试前通过 SQLAlchemy metadata
重建表，不依赖 Alembic 或本地 MySQL。

测试按 `api`、`core`、`services`、`repositories`、`schemas` 和
`integrations` 分层组织，详细约定见 [test/README.md](test/README.md)。

## 技能抽取 Pipeline

先执行最新迁移：

```powershell
alembic upgrade head
```

默认支持导入项目 `data/` 下三份 JD 文件：

- `jd_crawl_ifly.json`
- `jd_crawl_zl.json`
- `jd_crawl2.json`

批量导入由 Celery Worker 执行，Redis 默认地址为
`redis://localhost:6379/0`：

```powershell
celery -A app.core.celery_app.celery_app worker --loglevel=info --pool=solo
```

自动化测试通过 `CELERY_TASK_ALWAYS_EAGER=true` 在进程内执行任务，不需要
启动 Redis。未配置 `DEEPSEEK_API_KEY` 时，Pipeline 只运行规则抽取并返回
`llm_enrichment=false`；DeepSeek 超时不会回滚已经确认的规则结果。

主要接口：

```text
GET  /api/v1/skills
GET  /api/v1/skills/{skill_id}
POST /api/v1/jobs/{job_id}/extract-skills
GET  /api/v1/jobs/{job_id}/skill-facts
POST /api/v1/data-imports/jobs
GET  /api/v1/tasks/{task_id}
```

运行不少于 100 条现有 JD 的关键词锚点代理评测：

```powershell
python scripts/evaluate_skill_extraction.py --limit 100
```

该指标使用爬取数据中的 `keywords` 正例作为显式锚点，主要检查锚点召回，
无法评估未标注技能的误报；正式抽取 F1 应在后续人工标注评测集上再次确认。

## Neo4j 能力图谱

图谱数据由 MySQL 中的标准岗位和 `verified` 技能事实重建，所有业务节点和
关系都带有 `namespace=jiebang`。全量同步只清理该命名空间，不会删除 Neo4j
中的其他业务数据。

```http
POST /api/v1/graph/sync
GET  /api/v1/graph/snapshots
GET  /api/v1/graph/panorama
GET  /api/v1/graph/nodes/{node_id}
GET  /api/v1/graph/expand
GET  /api/v1/graph/search
GET  /api/v1/graph/path
GET  /api/v1/graph/jobs/{standard_job_id}/tree
```

同步请求：

```json
{"mode": "full", "enrich_top_skills": true}
```

未配置 DeepSeek 时，L1-L3 正常同步；Top 20 技能保存为带来源证据的
`unverified` 补全候选。配置模型后，只有至少两个独立来源且置信度不低于
`0.75` 的 L4/L5 声明会进入正式图谱。

## 独立 Agent 与职业规划

可执行 Agent 位于仓库根目录 `agent-development/src/jiebang_agents/`，后端通过 `app.core.agent_runtime` 加载；可用 `JIEBANG_AGENT_PATH` 指向独立部署目录。该包包含 JD Generation、技能补全、L4/L5 图谱补全和职业规划 Agent，后端仅负责 API、持久化、任务编排和审计。

职业规划接口：

```text
POST /api/v1/career/resume-extractions
POST /api/v1/career/analyses
```

文件解析支持 TXT、Markdown、PDF 与 DOCX，大小上限 20MB。岗位匹配与排序由后端确定性规则计算；Agent 不会覆盖分数或岗位 ID。未配置 DeepSeek 时仍会返回模板化学习路径，并记录 `AgentRun.status=degraded`。
