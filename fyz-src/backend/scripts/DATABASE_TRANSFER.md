# 团队完整数据迁移：MySQL + ChromaDB + Neo4j

> 文档类型：迁移操作说明
> 状态：**现行 / 已按 0025 以比赛脱敏模式导出并通过离线严格校验**
> 核验日期：2026-08-20
> SQL、manifest 和校验摘要均固定在 `20260820_0025`。导入器会先验证三个文件的
> revision、SQL/manifest checksum、逐表行数及逐表内容摘要，任一不一致即拒绝写库。

本目录是一套可重复执行的数据迁移包。MySQL 是唯一事实源；ChromaDB 是由
MySQL 中已保存的预计算向量物化出的检索索引；Neo4j 是由 MySQL 已验证事实
重建的图查询模型。迁移不复制来源机器的 `.env`、Chroma 二进制目录或 Neo4j
`data/` 目录，因此不依赖来源机器的绝对路径和数据库内部版本。

## 当前快照（2026-08-20）

| 项目 | 当前值 |
| --- | --- |
| Alembic revision | `20260820_0025` |
| MySQL | 47 张表、54474 行 |
| SQL 文件 | `mysql_snapshot.sql` |
| SQL SHA-256 | `ac54bed13bafbb2868167d81576e6fe119018b05ae24db6afaaa473a169db4c8` |
| 完整校验摘要 | `mysql_snapshot_verification.json`（`status=passed`） |
| ChromaDB / Neo4j | 以 manifest 内的来源库物化摘要为准，接收端仍须执行第 3–5 阶段 |

`mysql_snapshot.sql` 保存全部业务表数据，包含
`retrieval_index_entry.embedding` 中的预计算向量；数据库结构由同一 Git 版本的
Alembic migration 创建。两者共同构成“结构 + 数据”的完整 MySQL 迁移来源。

## 接收方准备

1. 拉取包含该 SQL、manifest 和 Alembic revision 的同一 Git 版本。
2. 安装 `fyz-src/backend/requirements-dev.txt`，进入 Python 3.10 环境。
3. 创建空 MySQL 数据库：

   ```sql
   CREATE DATABASE jie_bang
     CHARACTER SET utf8mb4
     COLLATE utf8mb4_0900_ai_ci;
   ```

4. 启动 MySQL 8.0 和 Neo4j 5.x。
5. 从 `.env.example` 创建自己的 `fyz-src/backend/.env`，至少配置：
   `DB_*`、`JWT_SECRET_KEY`、`NEO4J_*`、`CHROMA_MODE=persistent` 和本机
   `CHROMA_PERSIST_PATH`。不要复制来源成员的 `.env`。
6. 确认目标 MySQL 和目标 Chroma JieBang collection 可以被覆盖。

导入现有向量不调用 OpenAI、DeepSeek 或其他外部模型，因此接收方不需要提供
Embedding API Key。后续主动重建新索引时才需要与索引模型匹配的 provider 配置。

## 一键导入（推荐）

先激活项目 Python 环境，再从 `fyz-src/backend` 执行：

```powershell
.\scripts\Import-TeamDatabase.ps1 -Replace
```

如果没有激活 Conda，可显式传入 Python：

```powershell
.\scripts\Import-TeamDatabase.ps1 `
  -Python "E:\Computer_tools\Anaconda\dld\envs\jiebang\python.exe" `
  -Replace
```

跨平台或不使用 PowerShell 时：

```text
python scripts/run_database_import.py --replace
```

`--replace` / `-Replace` 是强制确认参数。脚本不会猜测目标连接，请在执行前检查
`.env` 指向的是成员自己的目标数据库。

## 导入阶段

| 阶段 | 脚本 | 作用 |
| --- | --- | --- |
| 0/5 | `run_database_import.py` 内置预检 | 在任何子进程、数据库连接或 DDL 前离线校验完整迁移包 |
| 1/5 | `01_prepare_mysql_schema.py` | 执行 Alembic upgrade，建立或升级全部表结构 |
| 2/5 | `02_import_mysql_snapshot.py` | 校验 SQL SHA-256 和 revision，事务式替换全部 MySQL 数据并逐表核数 |
| 3/5 | `restore_chroma_from_mysql.py` | 校验向量维度与 checksum，从 MySQL 预计算向量复原 Chroma collection |
| 4/5 | `03_rebuild_neo4j.py` | 通过 `GraphService.sync(mode="full")` 重建 `namespace=jiebang`，不调用 DeepSeek |
| 5/5 | `04_verify_database_import.py` | 核对 MySQL 行数、Chroma collection/向量数和 Neo4j 节点/关系数 |

Chroma 复原只删除名称以 `jiebang-evidence-` 开头的 collection。Neo4j 全量同步
只清理 `namespace=jiebang`；两者都不会删除其他项目的命名空间数据。

PowerShell 入口 `Import-TeamDatabase.ps1` 只调用上述编排器，因此同样必经第 0 步。
若 SQL、manifest 或校验摘要缺失、损坏或 revision 过期，编排器不会启动 Alembic，
也不会连接 MySQL、Chroma 或 Neo4j。

## 来源方刷新快照

当共享事实、审核状态、Agent 审计或向量索引变化后，来源方执行：

```powershell
cd fyz-src\backend
python scripts\export_mysql_snapshot.py --publish --competition --expected-revision 20260820_0025
python scripts\verify_mysql_snapshot_package.py
python scripts\restore_chroma_from_mysql.py --replace
python scripts\04_verify_database_import.py
```

需同步提交：

- `mysql_snapshot.sql`：全部 MySQL 数据，包括预计算向量；
- `mysql_snapshot_manifest.json`：revision、逐表行数、Chroma/Neo4j 摘要与 SQL SHA-256；
- `mysql_snapshot_verification.json`：manifest/SQL 配对摘要和所有离线校验结果；
- 新增或变化的 Alembic migration；
- 本目录导入/校验脚本和本文档。

不要只提交 SQL 而遗漏 manifest 或 migration；导入器会拒绝 checksum 或 revision
不一致的组合。

导出器必须显式传入 `--publish` 才会替换仓库中的正式包。它先在同目录临时区使用
只读、一致性快照事务导出，要求源库 revision 等于仓库 Alembic 唯一 head，并检查
各迁移版本必需表、SQL 语法、逐表行数和逐表摘要；全部通过后才以 manifest 最后发布的
顺序替换正式文件。若需预演，可改用 `--output-dir <空目录>`，不会触碰正式包。

## 数据与安全边界

- 当前正式包标记为 `competition-sanitized-v1`：候选人与员工姓名使用一致化名，
  简历原文、联系方式、查询摘要、收藏备注和来源管理员密码哈希均已脱敏。
- 容器首次导入后必须通过 `INITIAL_ADMIN_PASSWORD` 设置比赛管理员密码；正式包内
  的管理员哈希不可用于登录。
- `.env`、API Key、本机 Chroma/Neo4j 数据目录、上传文件和日志不得放入迁移包。
- MySQL 是事实源。不要直接修改 Chroma 或 Neo4j 后期待结果回写 MySQL。

## 故障处理

- **revision 不一致**：切换到与快照相同的 Git 版本并执行
  `alembic upgrade head`，不要 `alembic stamp head` 跳过 DDL。
- **SQL checksum 不一致**：来源方重新导出 SQL，并让 SQL 与 manifest 成对更新。
- **Chroma collection 缺失/数量不符**：确认 `CHROMA_MODE=persistent` 与
  `CHROMA_PERSIST_PATH`，重新执行 `restore_chroma_from_mysql.py --replace`。
- **向量 checksum 或维度错误**：快照可能损坏或 migration 不匹配，禁止通过
  重新请求 Embedding API 掩盖问题，应重新取得完整 SQL 快照。
- **Neo4j 连接失败**：检查服务、Bolt 端口与 `NEO4J_URI/USER/PASSWORD`。
- **图谱数量不一致**：重新执行 `03_rebuild_neo4j.py`；全量同步是命名空间隔离、
  可重复执行的派生过程。
