# 数据库、数据导入与运行指南

> 文档类型：FYZ 运行说明
> 状态：现行
> 核验日期：2026-08-28（`28a4cc5b`）
> JTT 使用独立业务后端和迁移链，但岗位接口只读依赖 FYZ 共享事实库，见
> [当前实现状态](implementation-status.md)。

## 1. 数据边界

- MySQL 是用户、岗位、技能事实、来源证据、任务和图谱审计的事实库。
- ChromaDB 是由 MySQL `retrieval_index_entry` 中的预计算向量物化的检索索引，
  可以删除后重建，不是事实来源。
- Neo4j 是由 MySQL 已验证事实重建的查询模型，不是事实来源。
- Neo4j 业务节点和关系使用 `namespace=jiebang` 隔离。
- Redis 不保存最终业务事实：一套实例用于 Celery Broker/结果，另一套可选实例用于查询、
  任务状态与预热缓存；缓存连接失败时 FYZ 后端降级为直接查询。
- DeepSeek 是可选增强项；未配置时系统必须保留规则抽取和基础图谱能力。

### JTT 数据边界

- JTT 自有 ORM/Alembic 管理 `user`、`job_position`、`position_skill`、`skill_change`、
  `user_resume`、`match_result`、`learning_path` 和 `favorite` 等用户端业务表；JTT Alembic
  当前 head 为 `34d9b68a59ff`，版本表为 `alembic_version_jtt`。
- JTT 岗位列表、详情与自动匹配会只读查询 `jie_bang.raw_job_record`、`source_document`、
  `standard_job_source` 和 `standard_job`，因此必须先导入 FYZ 共享快照并授予读取权限。
- JTT 没有独立 SQL 快照；前端 mock、后端种子和 evaluation 下的 `pseudo_gold` 均不是
  生产事实库备份。
- JTT 应用启动时仍执行 `Base.metadata.create_all()`，与 Alembic 并存；生产运行应以 Alembic
  为结构权威，并在后续实现中移除启动时隐式建表。

## 2. 环境配置

```powershell
Copy-Item fyz-src\backend\.env.example fyz-src\backend\.env
```

必须配置：

```dotenv
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=本地密码
DB_NAME=jie_bang
JWT_SECRET_KEY=足够长的随机值
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=本地密码
CHROMA_MODE=persistent
CHROMA_PERSIST_PATH=./storage/chroma
```

生成 JWT 密钥：

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

可选配置：

```dotenv
DEEPSEEK_API_KEY=仅写入本地env
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT_SECONDS=12
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
DATA_DIR=../../data
```

职业规划文件解析依赖已经写入 `fyz-src/backend/requirements.txt`：`pypdf` 用于 PDF，`python-docx` 用于 DOCX。安装后使用 `python -m pip install -r requirements.txt`；扫描件 PDF 仍需要外部 OCR，当前服务只提取其中已有的文本层。

## 3. MySQL 初始化

```sql
CREATE DATABASE jie_bang
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
```

应用不会自动建表，正式结构只能由 Alembic 管理：

```powershell
conda activate jiebang
cd fyz-src\backend
alembic heads
alembic history
alembic upgrade head
alembic current
```

当前迁移链：

```text
base
→ 20260619_0001  user 基线
→ 20260620_0002  岗位、技能和版本
→ 20260620_0003  标准技能与抽取流水线
→ 20260620_0004  标准岗位与图谱同步审计
→ 20260710_0005  岗位洞察决策审计
→ 20260712_0006  私有简历、匹配快照与解释证据
→ 20260715_0007～20260731_0015  转岗、员工、来源、审核、审计、质量与 RAG
→ 20260801_0016  岗位标准化 v2
→ 20260801_0017  L4/L5 图谱补全工作流
→ 20260808_0018  分析参考基线快照
→ 20260809_0019  岗位来源观测
→ 20260809_0020  自动流水线持久化
→ 20260820_0021～0025  企业部门、外部岗位生命周期、快照范围、导入隔离与 Java 标准岗位合并（当前 head）
```

### ⚠ 当前 `20260820_0025` 数据库版本

当前 head 已包含私有简历与匹配、L4/L5 审核、分析基线、岗位来源观测、持久化自动流水线、
企业部门、外部岗位生命周期、快照范围、导入隔离和 Java 标准岗位合并。
拉取代码后先执行：

```powershell
cd fyz-src\backend
alembic upgrade head
alembic current
```

确认当前版本为 `20260820_0025 (head)` 后再重启 FastAPI。不要使用
`alembic stamp head` 跳过 DDL；否则会造成路由已存在、但查询因岗位标准化或
图谱审核表缺失而失败。

### 已存在旧 `user` 表

只有在人工确认表结构与 `20260619_0001_user_baseline.py` 一致后：

```powershell
alembic stamp 20260619_0001
alembic upgrade head
```

不要执行 `alembic stamp head`。它只写版本号，不执行后续建表操作，
会造成“版本显示最新但业务表缺失”。

### 常用命令

| 命令 | 用途 |
| --- | --- |
| `alembic current` | 查看数据库当前版本 |
| `alembic heads` | 查看代码迁移头 |
| `alembic history` | 查看完整迁移链 |
| `alembic upgrade head` | 升级到最新版本 |
| `alembic downgrade -1` | 回退一个版本，仅限确认数据风险后 |
| `alembic revision --autogenerate -m "message"` | 根据 ORM 差异生成迁移草稿 |
| `alembic stamp <revision>` | 仅标记版本，不执行 DDL |

### 新增数据库变更

1. 修改 SQLAlchemy ORM。
2. 在 `app/models/__init__.py` 导入新模型。
3. 执行 `alembic revision --autogenerate -m "..."`。
4. 人工检查表名、索引、外键、默认值、升级和回滚逻辑。
5. 在临时数据库执行：

```powershell
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

6. 运行后端测试并在 PR 中说明数据兼容性。

禁止删除已进入共享主线的 migration 后重新生成；应增加新的修正 migration。

### 导入团队完整数据库快照

`fyz-src/backend/scripts/` 提供完整迁移包的导出、离线校验和接收端导入流程。当前共享快照
已于 2026-08-20 按 `20260820_0025` 重导，包含 47 张表、54474 行，并配套 manifest、
逐表内容摘要和 `mysql_snapshot_verification.json`；离线严格校验状态为 `passed`。

导入前必须先执行 `python scripts/verify_mysql_snapshot_package.py`。覆盖式接收流程会替换
目标 MySQL、Chroma 和 `namespace=jiebang` 的 Neo4j 数据，因此只能在已备份、明确指定的
隔离目标环境执行；当前源库未执行自覆盖式验收。

## 4. 初始管理员

默认关闭自动管理员创建。首次本地初始化可临时配置：

```dotenv
INITIAL_ADMIN_ENABLED=true
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=本地强密码
```

执行迁移后启动后端，管理员不存在时会被创建。之后建议关闭
`INITIAL_ADMIN_ENABLED`。生产环境不得使用文档示例密码。

## 5. ChromaDB 与 Neo4j

ChromaDB 使用持久化目录，但该目录属于本机运行数据，不提交 Git。团队迁移时
由 `restore_chroma_from_mysql.py` 读取 MySQL 中的 index version、evidence、
lexical text、embedding 和 checksum 后重新建立 collection。只有主动创建新的
索引版本时才调用配置的 Embedding provider。

可单独复原并校验：

```powershell
python scripts\restore_chroma_from_mysql.py --replace
python scripts\04_verify_database_import.py
```

### Neo4j

启动 Neo4j 5.x，设置与 `.env` 一致的密码后：

```powershell
cd fyz-src\backend
python diagnose_neo4j.py
```

图谱由同步 API 创建，不需要手工导入 Cypher。全量同步只清理
`namespace=jiebang`，不得删除其他命名空间。

同步模式：

- `incremental`：日常增量更新；
- `full`：从 MySQL 事实重新构建整个 JieBang 图谱；
- `enrich_top_skills=true`：允许 DeepSeek 对高价值技能生成 L4/L5 候选。

未配置 DeepSeek 时 L1-L3 仍正常同步。L4/L5 必须保留来源证据和置信度；
不满足至少两个独立来源且置信度低于 `0.75` 的内容只能作为候选。

## 5.1 简历文本与职业规划

`POST /api/v1/career/resume-extractions` 将上传文件转换为文本，`POST /api/v1/career/analyses` 使用技能文本、可选简历文本、企业技术栈和内部岗位生成转岗建议。简历原文不会写入 `AgentRun.input_summary` 或日志；分析结果、模型版本和降级状态保留在 `AgentRun` 中。岗位匹配分数由后端规则计算，模型只能补充学习路径与解释。

## 6. Redis 与 Celery

启动 Redis 后运行 Worker：

```powershell
cd fyz-src\backend
celery -A app.core.celery_app.celery_app worker --loglevel=info --pool=solo
```

Windows 本地使用 `--pool=solo`。测试通过
`CELERY_TASK_ALWAYS_EAGER=true` 在当前进程运行，不依赖 Redis。

任务状态：

```text
queued → running → succeeded
                 ↘ failed
```

排查顺序：

1. Redis 是否监听配置端口；
2. Worker 是否加载项目 Conda 环境；
3. 后端和 Worker 是否使用同一 `.env`；
4. MySQL migration 是否为 head；
5. `error_code` 和 `error_message` 是否记录文件、网络或模型错误。

## 7. 导入岗位数据

仅允许以下文件名，且必须位于 `DATA_DIR`：

```text
jd_crawl_ifly.json
jd_crawl_zl.json
jd_crawl2.json
```

导入处理：

1. 校验文件白名单和 JSON 数组格式；
2. 按内容指纹幂等去重；
3. 保存来源文档和原始岗位事实；
4. 标准化岗位标题；
5. 规则抽取技能，配置密钥时执行 DeepSeek 补全；
6. 多来源交叉验证，`source_count >= 2` 且 `confidence >= 0.75` 标记为 verified；
7. 写入异步任务结果。

先导入 MySQL，再同步 Neo4j。不要把离线分析输出直接写入 Neo4j。

## 8. 离线分析配置

`data_analysis/` 保留技能词典、分类和可选 DeepSeek 配置，不含可执行的数据
导入脚本。所有可共享的岗位与技能数据必须通过上述 MySQL 快照流程进入系统，
避免离线输出绕过来源记录、验证状态和图谱审计。

## 9. 完整启动顺序

```text
MySQL
→ alembic upgrade head
→ Neo4j
→ Redis
→ Celery Worker
→ FastAPI
→ FYZ/JTT 前端
→ 导入岗位数据
→ 同步图谱
```
