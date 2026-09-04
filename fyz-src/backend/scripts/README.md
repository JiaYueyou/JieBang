# 后端运维与评测脚本

> 文档类型：脚本索引
> 状态：现行
> 核验日期：2026-08-12
> 注意：`DATABASE_TRANSFER.md` 所述完整迁移包已按 0020 重导出并通过严格校验。
> 脚本执行前先查看 [当前实现状态](../../../docs/implementation-status.md)。

本目录只保留当前代码和数据库版本仍可执行的脚本。业务操作优先通过 FastAPI
和管理端完成；脚本用于团队数据迁移、一次性结构回填以及可重复工程评测。

## 团队数据迁移

推荐从 `fyz-src/backend` 使用项目指定 Python 执行：

```powershell
.\scripts\Import-TeamDatabase.ps1 -Replace
```

| 文件 | 用途 |
| --- | --- |
| `Import-TeamDatabase.ps1` | Windows 单命令迁移入口 |
| `run_database_import.py` | 跨平台迁移编排入口；任何目标连接/DDL 前先离线预检完整包 |
| `01_prepare_mysql_schema.py` | 执行 Alembic migration |
| `02_import_mysql_snapshot.py` | 校验并导入 MySQL 数据快照 |
| `restore_chroma_from_mysql.py` | 从 MySQL 预计算向量复原 ChromaDB |
| `03_rebuild_neo4j.py` | 从 MySQL 重建 Neo4j `namespace=jiebang` |
| `04_verify_database_import.py` | 校验 MySQL、ChromaDB、Neo4j 一致性 |
| `export_mysql_snapshot.py` | 来源方刷新团队 SQL 快照与 manifest |
| `verify_mysql_snapshot_package.py` | 不连接数据库，严格校验 SQL/manifest/校验摘要 |
| `db_transfer_common.py` | 上述迁移脚本的内部公共函数，不单独执行 |
| `mysql_snapshot.sql` | 当前共享数据快照 |
| `mysql_snapshot_manifest.json` | 快照版本、行数和 SHA-256 |
| `mysql_snapshot_verification.json` | 当前包的独立校验摘要 |

完整说明见 [DATABASE_TRANSFER.md](DATABASE_TRANSFER.md)。

## 当前数据维护

| 文件 | 用途 |
| --- | --- |
| `backfill_job_standardization_v2.py` | 预览或执行岗位标准化 v2 回填，默认只读 |
| `rebuild_retrieval_index.py` | 从 MySQL 权威证据创建新的检索索引版本 |

回填脚本必须先以默认只读模式检查结果，再显式使用 `--apply`。索引重建会使用
当前配置的 Embedding provider；团队迁移已有索引时应使用
`restore_chroma_from_mysql.py`，避免重复调用外部 API。

## 工程评测

| 文件 | 用途 |
| --- | --- |
| `evaluate_skill_extraction.py` | 评估技能抽取结果 |
| `evaluate_fyz_quality.py` | 运行 100 条真实 JD、简历抽取和匹配准确率量化评测 |
| `run_fyz_coverage.py` | 运行 FYZ 全量测试并统计 Service 可执行行覆盖率 |
| `generate_fyz_test_report.py` | 汇总质量、覆盖率、JUnit 和 Docker 状态为简洁 HTML 报告 |
| `build_phase0_golden_set.py` | 重建确定性数据质量种子集 |
| `finalize_phase0_review.py` | 固化 Phase 0 工程审核结果 |
| `capture_phase0_baseline.py` | 采集 MySQL、Neo4j 和 Git 只读基线 |
| `evaluate_phase1_data_quality.py` | 评估重复识别和时效规则 |
| `build_phase2_golden_set.py` | 从已认证 Evidence 构建检索评测集 |
| `evaluate_phase2_retrieval.py` | 运行检索质量、拒答和过滤评测 |
| `verify_embedding_provider.py` | 验证 Embedding provider，不输出密钥 |

FYZ 竞赛量化报告可按以下顺序复现：

```powershell
python scripts/evaluate_fyz_quality.py --jd-limit 100 --case-count 60
python scripts/run_fyz_coverage.py
python scripts/generate_fyz_test_report.py
```

最终报告位于 `evaluation/fyz_test_report.html`。JD 指标使用爬取数据中的正例关键词锚点，
因此报告为锚点召回率，并明确保留其不能估算完整误报率的限制。

这些脚本只生成或检查 `fyz-src/backend/evaluation/` 下的工程评测材料，不承担
线上业务写入。

## 已移除的旧入口

- `05_enrich_l45.py`、`run_all_l45.py` 和 `scripts/tests/`：旧版脚本会绕过
  当前候选审核/发布状态机并直接写图，已由异步 Graph API、管理端图谱审核和
  `agent-development/tests/` 替代。
- `approve_phase2_coverage_facts.py`：硬编码 Phase 2 岗位范围，已由事实审核
  API 的批量审批和一键同意替代。
- `backfill_phase1_data_quality.py`：一次性 Phase 1 回填，当前导入服务和团队
  快照已包含对应质量字段。
- `check_mvp_baseline.py`：依赖已淘汰的 `iflytek_N.json`、`zhaopin_N.json`
  命名规则，已由当前导入校验与工程评测替代。
- `CRAWLER_STATUS.md`：过期阶段状态记录，不再作为运行说明。

L4/L5 当前入口：

```text
POST  /api/v1/graph/enrichment/generate
GET   /api/v1/graph/enrichment/candidates
PATCH /api/v1/graph/enrichment/candidates/{candidate_id}/review
POST  /api/v1/graph/enrichment/publish
GET   /api/v1/tasks/{task_id}
```

禁止重新增加会绕过 MySQL 审核状态、证据引用或异步任务审计而直接写 Neo4j 的
脚本。
