# FYZ 优化 Phase 0 契约与基线实施记录

> 实施日期：2026-07-30
>
> 对应计划：[FYZ 数据链路、图谱、Agent 防幻觉与 RAG 优化计划](./FYZ数据链路图谱Agent防幻觉与RAG优化计划.md)
>
> 当前结论：工程实现、用户授权的透明工程审核和 Phase 1 前数据库备份均已完成；评测集仍不等同于业务专家人工金标。

## 1. 本阶段交付

Phase 0 未修改业务表结构，完成了以下可复用基础设施：

1. 增加任务、Agent、事实信任、机器校验、人工审核和发布状态枚举。
2. 增加统一 UTC 时间工具；现有无时区 `DateTime` 列统一写入 UTC-naive 兼容值，API/感知时区字段使用 RFC 3339 UTC。
3. 将技能抽取、JD 生成、职业规划、匹配解释、图谱补全、图谱同步和 Celery 任务链切换到统一状态常量。
4. 修复技能抽取 Agent 将成功状态写为 `success` 的缺陷，统一为 `succeeded`。
5. 增加可重复运行的 MySQL、Neo4j、Agent 耗时和 Git 基线采集脚本。
6. 增加 100 条确定性评测种子数据与结构校验器。
7. 完成 Neo4j 服务版本与向量检索能力探测，并冻结 Phase 1 RAG 索引决策。

## 2. 冻结契约

### 2.1 运行状态

- 异步任务：`queued -> running -> succeeded | failed | cancelled`
- Agent：`queued -> running -> succeeded | degraded | failed | cancelled`
- `degraded` 表示模型增强不可用或校验未完全通过，但系统返回了可继续人工编辑的确定性降级结果。
- 禁止再写入历史非标准状态 `success`。

### 2.2 事实与发布状态

- 信任阶段：`raw / extracted / machine_validated / human_approved / published / rejected / insufficient_evidence / expired`
- 机器校验：`pending / passed / failed / insufficient_evidence`
- 人工审核：`pending / approved / rejected`
- 发布状态：`draft / ready / published / failed / superseded`

这些枚举先作为 Phase 0 代码契约存在。现有 `verified / unverified / rejected` 数据列在 Phase 1 迁移前保持兼容，避免本阶段提前改变数据库语义。

### 2.3 时间

- API、评测集和报告：UTC RFC 3339，使用 `Z` 后缀。
- 已有 timezone-aware 列：写入 aware UTC。
- 已有无时区 `DateTime` 列：写入 UTC 后移除 `tzinfo` 的兼容值。
- Phase 1 再通过迁移明确列级时区策略，并修复历史时间数据。

## 3. 运行基线

基线脚本：

```powershell
cd E:\Project\JieBang\fyz-src\backend
$env:TESTING='false'
& 'E:\Computer_tools\Anaconda\dld\envs\jiebang\python.exe' scripts\capture_phase0_baseline.py
```

Phase 0 冻结时的机器可读报告：

- [phase0-baseline-20260730T142617441984Z.json](./phase0-runtime/phase0-baseline-20260730T142617441984Z.json)
- [phase0-baseline-20260730T142617441984Z.md](./phase0-runtime/phase0-baseline-20260730T142617441984Z.md)

`latest.json/latest.md` 会由基线脚本覆盖，当前已指向 Phase 1 完成后的最终对账；Phase 0 历史结论以以上固定文件为准。

本次采集基于 Git HEAD `28379574a251b46dcce9a82136e15f0bb8ca388b`、分支 `feat/fyz-job-agent`，采集时工作区含尚未提交变更。

### 3.1 MySQL

| 指标 | 数量 |
|---|---:|
| 岗位 `job_posting` | 7 |
| 来源文档 `source_document` | 190 |
| 原始岗位 `raw_job_record` | 190 |
| 技能 `skill` | 107 |
| 岗位技能事实 `job_skill_fact` | 1,143 |
| 标准岗位 `standard_job` | 130 |
| Agent 运行 `agent_run` | 86 |
| 异步任务 `async_task` | 85 |
| 图谱快照 `graph_snapshot` | 11 |
| 图谱补全候选 `graph_enrichment_candidate` | 100 |

状态分布：

- 技能事实：`verified=1000`，`unverified=143`。
- Agent：`succeeded=55`，`degraded=31`；降级占比约 36.0%。
- 异步任务：`succeeded=83`，`queued=2`。
- 图谱快照与同步批次：11 个均为 `succeeded`。
- 图谱补全候选：100 个均为 `unverified`。
- Alembic revision：`20260730_0012`。

### 3.2 Neo4j

| 项目 | 结果 |
|---|---|
| 连通性 | 成功 |
| 版本 | Neo4j `2026.05.0` Community |
| `namespace=jiebang` 节点 | 360 |
| `namespace=jiebang` 关系 | 1,650 |
| 节点向量查询 | `db.index.vector.queryNodes` |
| 关系向量查询 | `db.index.vector.queryRelationships` |
| 相似度函数 | cosine、euclidean |

MySQL 最新图谱快照记录的 `node_count=360`、`edge_count=1650` 与 Neo4j 当前计数一致。

### 3.3 基线暴露的问题

1. 历史最新图谱快照的 `created_at=2026-07-29T22:22:20Z`、`completed_at=2026-07-29T14:22:24Z`，完成时间早于创建时间，确认了旧代码混用本地时间和 UTC 的问题。Phase 0 已统一新写入路径，历史数据修复进入 Phase 1。
2. 31/86 次 Agent 运行处于降级状态，职业规划和 JD 生成的平均耗时较高；后续需要把检索命中、模型失败和后校验失败拆分统计。
3. 100 条图谱补全候选尚无人工批准结果，不能直接作为正式发布图谱或 RAG 权威证据。
4. 仍有 2 条异步任务停留在 `queued`，Phase 1 应增加超时、租约或恢复策略。

## 4. RAG 索引决策

Phase 1 采用以下架构决策：

- MySQL 继续保存原始来源、证据片段、审核、发布和索引版本，是唯一权威来源。
- Neo4j 向量索引作为首选试点实现，用于图谱邻域与文本向量的联合检索。
- 向量索引始终是可重建读模型，不承载业务事实；必须能按 MySQL 索引版本全量重建。
- 保留本地可重建向量索引作为开发、测试和 Neo4j 能力不可用时的降级实现。
- Phase 1 在离线检索评测完成前不锁定具体 Embedding 模型。

选择 Neo4j 试点的依据是当前服务已实际暴露节点/关系向量查询过程及 cosine/euclidean 相似度函数，而不是仅根据文档或版本号推断。

## 5. 评测种子集

生成命令：

```powershell
cd E:\Project\JieBang\fyz-src\backend
& 'E:\Computer_tools\Anaconda\dld\envs\jiebang\python.exe' scripts\build_phase0_golden_set.py
```

评测文件：[phase0_golden_set.json](../../fyz-src/backend/evaluation/phase0_golden_set.json)

固定分布：

| 分类 | 样本数 |
|---|---:|
| 完全重复/近重复 JD | 20 |
| 时效与日期异常 | 15 |
| 岗位—技能一致性 | 20 |
| 图谱证据落地 | 15 |
| 匹配解释引用 | 15 |
| JD/职业规划边界 | 15 |
| 合计 | 100 |

2026-07-30 已按用户授权完成逐条工程语义审核：`approved=100`、`rejected=0`、`release_gate=true`。每条样本均记录审核状态、审核人、时间和意见；集合元数据明确标记 `human_domain_gold=false`。它可作为 Phase 1 工程回归门禁，但在业务专家再次复核前，不应被描述为“人工领域金标集”。

## 6. 验证记录

- 后端完整回归：`153 passed`。
- 独立 Agent 包：`11 passed`。
- FYZ 前端 Vitest：`28 passed`，使用 `--cache=false` 避免仓库 `node_modules/.vite` 的机器权限影响。
- FYZ 前端类型检查与 Vite 生产构建：通过；构建产物输出到独立临时目录。
- 状态、UTC、Phase 0 基线与评测集测试均已纳入后端完整回归。
- 基线脚本：已在真实 MySQL 与 Neo4j 环境重复运行并输出 JSON/Markdown。
- Resume API 测试已切换到独立临时存储根目录，原先受 `storage/resumes` ACL 影响的 2 项回归已通过。
- 仓库现有 `dist` 目录在标准 `npm run build` 清理旧产物时仍会触发 Windows `EPERM`；改用新的临时输出目录后构建成功，说明类型检查与源码构建链正常，剩余问题是本机旧产物 ACL。

## 7. Phase 1 门禁执行结果

1. 100 条样本已完成用户授权的工程审核；业务专家人工金标复核仍是后续增强项，不再冒充为已完成。
2. `jie_bang` 已备份至 `E:\Backups\JieBang\mysql\jie_bang-20260730-225931.sql`，大小 1,839,134 字节，SHA-256 为 `1AB003268E8E6853A2F8AADC4B5DBBCB5C022936E69A301F93E5195AE04662EC`。
3. Phase 1 已获用户授权并完成迁移、回填；历史图谱快照/批次中 24 个本地时间与 UTC 混写记录已按严格异常窗口修复。
4. 具体实施与验证见 [FYZ 优化 Phase 1 数据质量与事实认证实施记录](./FYZ优化Phase1数据质量与事实认证实施记录.md)。
