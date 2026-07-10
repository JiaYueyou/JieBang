# 离线数据分析配置

此目录保留岗位分析的词典、分类和可选 DeepSeek 配置，不再提供独立、重复的
数据导入脚本。当前仓库中不存在 `01_merge_clean.py`、`02_normalize_titles.py`
等旧流水线文件；相关说明已移除，避免把离线输出误当作 MySQL 事实数据。

## 当前数据入口

所有可执行的数据导入、数据库迁移和图谱重建统一放在
`fyz-src/backend/scripts/`：

| 目标 | 命令 | 说明 |
| --- | --- | --- |
| 导入团队完整数据库快照 | `python scripts/run_database_import.py --replace` | 覆盖目标 MySQL 数据后，从 MySQL 重建 Neo4j。 |
| 刷新完整 MySQL 快照 | `python scripts/export_mysql_snapshot.py` | 仅由快照发布者执行。 |
| 评测现有技能抽取 | `python scripts/evaluate_skill_extraction.py --limit 100` | 不写入岗位事实。 |

完整步骤见 [数据库迁移说明](../fyz-src/backend/scripts/DATABASE_TRANSFER.md)
和 [数据库、数据导入与运行指南](../docs/database-and-runtime.md)。

## 配置

`.env` 仅用于本地可选模型配置，不能提交到 Git：

```dotenv
DEEPSEEK_API_KEY=replace-with-local-key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
```

`config.py` 中的技能词典可作为离线分析或后续工具开发的共享参考；进入系统的
岗位、技能事实和图谱数据仍必须走后端服务与 MySQL 事实库。
