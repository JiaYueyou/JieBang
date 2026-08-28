# JTT 共享岗位事实表说明

> 文档类型：JTT 数据依赖说明
> 状态：现行
> 核验日期：2026-08-28
> 核验提交：`28a4cc5b`
> 权威来源：`backend/app/repositories/raw_job_repository.py`、FYZ Alembic 与快照 manifest

## 1. 定位

`jie_bang.raw_job_record` 由 FYZ 数据采集、导入和标准化链路维护，是原始岗位事实记录表。
JTT 不创建或迁移该表，只通过 `RawJobRepository` 进行只读查询。JTT 的岗位列表、岗位详情、
自动匹配和部分简历优化流程依赖该数据源。

JTT 查询还会关联：

- `jie_bang.source_document`：来源文档；
- `jie_bang.standard_job_source`：原始记录与标准岗位映射；
- `jie_bang.standard_job`：标准岗位名称和技术栈分类。

任何只导入 JTT 自有 Alembic 表、但没有 FYZ 共享事实表的环境，岗位列表都无法正常工作。

## 2. 当前快照

仓库共享比赛快照生成于 2026-08-20，对应 FYZ Alembic `20260820_0025`：

| 指标 | 数值 |
| --- | ---: |
| 表数量 | 47 |
| 总行数 | 54474 |
| `raw_job_record` | 4683 |
| `source_document` | 4683 |
| `standard_job_source` | 4686 |
| `standard_job` | 4800 |

快照 profile 为 `competition-sanitized-v1`，SQL、manifest、逐表行数、逐表摘要和 SHA-256
离线严格校验均已通过。导入和验证流程见
[数据库、数据导入与运行指南](../docs/database-and-runtime.md)；覆盖式导入只能在已备份、
明确指定的隔离接收环境执行。

## 3. JTT 响应映射

JTT 对外岗位 ID 使用 `raw-{id}`，例如 `raw-123`。列表接口把：

- `standardized_title` 映射为岗位名称；
- `stack=ai` 映射为新兴岗位，其余支持的技术栈映射为既有岗位；
- `keywords` 拆分为最多 8 个必备技能；
- 原始 JD 前 150 个字符作为列表摘要；
- 城市、薪资、经验和学历沿用原始事实字段。

该映射是用户端展示适配，不会修改共享事实表。JTT 自有 `job_position` 种子表只作为部分
服务的降级数据，不能与 `raw_job_record` 混写为同一个事实来源。

## 4. 权限与部署要求

- JTT 数据库账号必须至少拥有上述四张共享表的 `SELECT` 权限，以及 JTT 自有业务表的读写权限。
- 当前仓库查询 SQL 硬编码 schema `jie_bang`；若部署使用其他数据库名，必须同步修改实现，
  仅设置 `DB_NAME` 不足以改变共享岗位表位置。
- JTT 后端健康接口目前不会对共享岗位 JOIN 做完整探测；生产验收必须额外调用
  `GET /api/v1/positions` 和岗位详情接口。
- JTT 没有独立 SQL 快照。前端 mock、后端种子以及 evaluation 下的 `pseudo_gold` 都不能
  作为该共享事实表的备份或恢复来源。
