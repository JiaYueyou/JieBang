# 自动数据闭环

> 文档类型：现行架构与运行说明
> 状态：首版已实现
> 核验日期：2026-08-20
> 流水线已持久化到 `pipeline_run`，但服务覆盖率与生产长期运行验收仍不足；见
> [当前实现状态](implementation-status.md)。

## 目标与边界

后台流水线负责把独立招聘门户的公开技术岗位，按以下顺序持续更新：

```text
定时领取 → 门户采集 → job-v1 校验 → MySQL 入库/去重/每日观测
         → 技能抽取与跨门户核验 → 检索索引刷新 → 图谱 L1-L5 生成/发布
         → 总体历史基线滚动 → 6 个月趋势验收
```

- 每个招聘门户是独立来源，来源失败互不阻断。
- 只采集互联网、AI、软件和硬件技术岗位。
- 岗位与技能成熟度按总体市场判断，不按城市或行业切分。
- 源站没有历史发布日期时，不伪造发布日期；以每日在线观测逐步形成真实历史。

## 调度与恢复

FastAPI 启动时会将爬虫注册表同步到 `data_source`，并恢复中断的
`pipeline_run`。定时槽使用数据库唯一幂等键，多 Uvicorn worker 不会重复执行同一批次。

主要环境变量：

| 变量 | 默认值 | 含义 |
|---|---:|---|
| `AUTO_PIPELINE_ENABLED` | 非测试环境 `true` | 开启自动调度 |
| `AUTO_PIPELINE_INTERVAL_MINUTES` | `1440` | 来源刷新周期 |
| `AUTO_PIPELINE_STARTUP_DELAY_SECONDS` | `60` | 启动后首次扫描延迟 |
| `AUTO_PIPELINE_SOURCE_TIMEOUT_SECONDS` | `1800` | 单门户最长运行时间 |
| `AUTO_PIPELINE_SOURCE_IDS` | `4,5,6` | 默认自动来源；PDD验证稳定后再启用 |
| `AUTO_PIPELINE_ENRICH_GRAPH` | `true` | 新事实触发 L4/L5 补全 |
| `AUTO_PIPELINE_AUTO_PUBLISH_CONFIDENCE` | `0.90` | 自动发布最低置信度 |
| `AUTO_PIPELINE_MAX_REJECTED_RATIO` | `0.25` | 批次最大质量拒绝率；超过后禁止向检索/图谱发布 |
| `AUTO_PIPELINE_MAX_TIME_ANOMALY_RATIO` | `0.50` | 批次最大时间异常率；超过后禁止向检索/图谱发布 |
| `AUTO_PIPELINE_MAX_QUARANTINE_RATIO` | `0.05` | 批次最大逐条隔离率；超过后禁止向检索/图谱发布 |
| `AUTO_PIPELINE_GRAPH_FULL_RECONCILE_HOURS` | `24` | 增量图谱两次全量校准的最长间隔 |
| `AUTO_PIPELINE_BASELINE_LOOKBACK_MONTHS` | `24` | 滚动基线回看长度 |
| `AUTO_PIPELINE_BASELINE_LAG_MONTHS` | `2` | 避免未完整月份进入基线 |

同一岗位正文不变时，同日复用快照、跨日生成新快照。数据库再通过
`(source_document_id, observed_on)` 保证每天最多一条在线观测。

每个爬虫快照同时发布 `<snapshot>.manifest`，声明完整/增量类型、观测时间、
采集范围 `scope_hash`、记录数和文件 SHA-256。完整遍历即使得到 0 条岗位也会发布
空数组快照；只有相同来源且相同采集范围内连续缺失达到阈值的岗位才会转为 closed，
截断、失败或不同筛选范围的结果不会推进下线计数。

## 质量门禁

1. job-v1 无效记录写入 `job_import_quarantine`；同文件有效记录继续入库。含隔离记录的
   full snapshot 自动降级为 delta，不参与岗位缺失/下线判断。
2. manifest 的来源、scope、记录数与文件 SHA-256 必须匹配；同一快照键重放时，
   内容和 manifest 均不可改变。
3. 单来源失败只标记该来源失败；已成功来源继续处理。
4. 拒绝率或时间异常率超过配置阈值时，批次保留审计数据但停止检索与图谱发布。
5. 没有新增岗位、技能事实或生命周期变化时跳过无意义的检索/图谱重写。
6. L4/L5 自动发布要求：机器校验通过、置信度不低于配置值、至少两条证据、
   同时存在技术点和知识点、grounding 无拒绝项。其余候选保留人工审核。
7. 滚动基线必须满足去重岗位簇、独立来源、覆盖月份和可审核技能事实门槛。
8. 新基线激活后必须通过趋势接口验收；失败会恢复上一个活动基线。
9. 图谱清理和计数只作用于正式图谱标签，不删除 Neo4j 中的检索证据节点。

## 管理 API

- `POST /api/v1/admin/pipeline/runs`：手动启动全部或指定来源。
- `GET /api/v1/admin/pipeline/runs`：查看最近运行。
- `GET /api/v1/admin/pipeline/runs/{id}`：查看来源、阶段、质量和错误明细。
- `GET /api/v1/admin/data-sources/{spider_id}/health`：查看 freshness lag、SLO、连续失败，
  以及 `healthy/stale/failing/never_run/overdue/manual/disabled` 告警状态。
- `PUT /api/v1/admin/data-sources/{spider_id}`：持久启停来源。

管理端“采集中心”展示当前阶段、进度、运行 ID、最近状态与错误；页面关闭不会中断
后台采集和入库。

## 当前已知边界

- PDD 的公开接口需要页面动态生成完整性令牌；完整性校验失败时按来源失败处理，绝不绕过。
- DeepSeek 官方页面没有岗位发布日期；其历史只使用页面快照观测时间。
- 自动流水线按受影响标准岗位增量清理/合并，并每 24 小时全量校准；Neo4j 仍是原地
  MERGE 模型。若需要严格的跨库原子发布与一键回滚，下一阶段应增加 staging namespace
  和 active-version 指针。
