# MySQL 与 Neo4j 数据迁移

这套脚本用于把一台开发机上的完整 MySQL 数据迁移到另一台开发机，并根据 MySQL 事实库重新构建 Neo4j。MySQL 是事实源；不会复制 Neo4j 的本地 `data/` 目录。

## 接收方准备

1. 安装 `requirements.txt`，并进入项目的 `jiebang` Python 环境。
2. 在 MySQL 中创建一个空数据库，例如：

   ```sql
   CREATE DATABASE jie_bang CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

3. 启动 Neo4j，并在 `fyz-src/backend/.env` 中配置目标机器自己的 `DB_*` 和 `NEO4J_*`。不要复制来源机器的 `.env`。
4. 确认目标数据库允许被覆盖。第二步会删除目标库所有业务表中的现有行。

## 按顺序执行

从 `fyz-src/backend` 运行：

```powershell
conda activate jiebang
python scripts/01_prepare_mysql_schema.py
python scripts/02_import_mysql_snapshot.py --replace
python scripts/03_rebuild_neo4j.py
python scripts/04_verify_database_import.py
```

也可以用一个命令执行完整流程：

```powershell
python scripts/run_database_import.py --replace
```

各步骤含义：

1. 使用 Alembic 创建或升级全部 MySQL 表。
2. 校验快照 SHA-256 和 Alembic 版本，然后在关闭外键检查的事务中导入所有表的数据，并逐表核对行数。
3. 调用项目现有 `GraphService.sync(mode="full")`，仅重建 Neo4j 中 `namespace=jiebang` 的节点和关系；不会调用 DeepSeek。
4. 校验 MySQL 表、快照版本、最新图谱快照以及 Neo4j 节点/关系数量。

## 来源方刷新数据快照

只有负责发布数据的来源方需要执行：

```powershell
python scripts/export_mysql_snapshot.py
```

该命令会重新生成：

- `mysql_snapshot.sql`：全部 MySQL 基础表的数据，不包含数据库密码或连接串。
- `mysql_snapshot_manifest.json`：表行数、Alembic 版本、生成时间和 SHA-256。

刷新后必须重新执行测试，并检查快照中是否含有不应共享的真实用户信息、招聘内容或 Agent 输入。快照包含 `user` 表中的密码哈希，但不包含明文密码；不要把 `.env` 一并提交。

## 失败处理

- Alembic 版本不一致：确保双方使用相同 Git 提交，然后重新执行步骤 1。
- 快照校验失败：来源方重新运行导出命令，并同时提交 SQL 和 manifest。
- Neo4j 连接失败：检查服务状态、`NEO4J_URI`、用户名和密码。
- 图谱数量不一致：重新执行步骤 3；`full` 同步具有命名空间隔离和幂等清理行为。
