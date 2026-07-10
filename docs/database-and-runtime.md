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
→ 20260620_0004  标准岗位与图谱同步审计（head）
```

### 已存在旧 `user` 表

只有在人工确认表结构与 `20260619_0001_user_baseline.py` 一致后：

```powershell
alembic stamp 20260619_0001
alembic upgrade head
```

不要执行 `alembic stamp head`。它只写版本号，不执行 0002–0004 的建表操作，
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

### 导入统一的本地初始化数据

每位成员先将本地数据库升级到当前 migration head，再运行初始化脚本：

```powershell
cd fyz-src\backend
alembic upgrade head
python scripts\init_data.py
```

脚本会按固定顺序完成以下操作：

1. 校验数据库 `alembic_version` 与当前代码的 Alembic head 完全一致；
2. 按 `canonical_key` 幂等写入公共技能字典和别名；
3. 按内容指纹幂等导入 `data/` 下三份白名单 JD，并使用固定规则抽取保证结果可复现；
4. 从现有岗位数据聚合标准岗位。

重复执行不会重复创建技能、原始 JD 或标准岗位来源。它不会删除成员自己的业务数据，
也不会默认连接 Neo4j。可用选项：

```powershell
# 只导入指定公共数据文件
python scripts\init_data.py --files jd_crawl_ifly.json jd_crawl_zl.json

# 只补齐公共技能字典并聚合数据库中已有岗位
python scripts\init_data.py --skip-jobs

# 显式允许 DeepSeek 辅助导入；该结果可能随模型版本变化，不作为团队基线
python scripts\init_data.py --use-deepseek

# 初始化 MySQL 后全量重建 JieBang 图谱命名空间
python scripts\init_data.py --sync-neo4j

# 有有效 DeepSeek 配置时，同时生成带证据约束的 L4/L5 候选
python scripts\init_data.py --sync-neo4j --enrich-top-skills
```

若 `.env` 中启用 `INITIAL_ADMIN_ENABLED=true`，脚本也会创建不存在的初始管理员；
已有同名账号时不会覆盖密码。团队不得在脚本、文档或 Git 中保存统一明文密码。

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

## 8. 独立数据分析流水线

```powershell
cd data_analysis
Copy-Item .env.example .env
python -m pip install -r requirements.txt
python scripts\01_merge_clean.py
python scripts\02_normalize_titles.py
python scripts\03_extract_skills.py
python scripts\04_build_reference.py
```

输出位于 `data_analysis/outputs/`，包括合并数据、岗位映射、技能词典、
岗位技能矩阵和参考数据集。输出是分析产物，不自动成为数据库事实；
进入主系统前必须经过字段校验、来源记录和导入流程。

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
