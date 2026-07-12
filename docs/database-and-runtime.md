# 数据库、数据导入与运行指南

## 1. 数据边界

- MySQL 是用户、岗位、技能事实、来源证据、任务和图谱审计的事实库。
- Neo4j 是由 MySQL 已验证事实重建的查询模型，不是事实来源。
- Neo4j 业务节点和关系使用 `namespace=jiebang` 隔离。
- Redis 只负责 Celery 消息和任务结果，不保存最终业务事实。
- DeepSeek 是可选增强项；未配置时系统必须保留规则抽取和基础图谱能力。

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
→ 20260710_0005  岗位洞察决策审计（head）
→ 20260712_0006  私有简历、匹配快照与解释证据（当前 head）
```

### ⚠ `20260712_0006_matching` 数据库版本更新

该迁移创建 `resume`、`resume_parse_result`、`resume_skill`、`match_record` 和 `match_evidence`，供 FYZ 人才匹配与 Match Explanation 使用。拉取包含该 revision 的代码后，先执行：

```powershell
cd fyz-src\backend
alembic upgrade head
alembic current
```

确认当前版本为 `20260712_0006 (head)` 后再重启 FastAPI。不要使用 `alembic stamp head` 跳过 DDL；否则会造成 `/api/v1/talents` 已存在、但登录后查询因业务表缺失而失败。

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

团队本地环境统一使用 `fyz-src/backend/scripts/` 的四步迁移包。它先创建或升级
MySQL 表，再导入全部表数据，最后从 MySQL 事实库重建 Neo4j；不要再使用多个
离线脚本分别导入同一批 JD、技能或图谱数据。

```powershell
cd fyz-src\backend
python scripts\01_prepare_mysql_schema.py
python scripts\02_import_mysql_snapshot.py --replace
python scripts\03_rebuild_neo4j.py
python scripts\04_verify_database_import.py
```

也可以一键运行：

```powershell
python scripts\run_database_import.py --replace
```

第二步会覆盖目标 MySQL 的现有业务数据。来源方更新数据库内容后，运行
`python scripts\export_mysql_snapshot.py` 来刷新 `mysql_snapshot.sql` 与其
SHA-256 manifest。完整安全边界、校验项和故障处理见
[数据库迁移脚本说明](../fyz-src/backend/scripts/DATABASE_TRANSFER.md)。

## 4. 初始管理员

默认关闭自动管理员创建。首次本地初始化可临时配置：

```dotenv
INITIAL_ADMIN_ENABLED=true
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=本地强密码
```

执行迁移后启动后端，管理员不存在时会被创建。之后建议关闭
`INITIAL_ADMIN_ENABLED`。生产环境不得使用文档示例密码。

## 5. Neo4j

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
