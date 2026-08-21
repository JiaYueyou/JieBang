# FYZ 端接口功能效果与测试计算逻辑说明

> 文档用途：用于项目策划书、测试方案和答辩材料中的“接口验证、算法效果、量化指标”章节。
> 统计范围：仅 FYZ 后端，不包含 JTT。
> 对应版本：`fyz-quality-v1`。
> 对应报告：`fyz_test_report.html`、`fyz_quality_metrics.json`、`fyz_coverage.json`、`fyz_pytest_results.xml`。
> 本次实测：311 项测试全部通过；其中 96 项为直接 API 测试。当前 OpenAPI 包含 93 个路径、106 个 HTTP 操作。

## 1. 测试目标与判定原则

FYZ 测试不只检查接口是否返回 HTTP 200，还验证以下四类效果：

1. **契约正确性**：请求鉴权、参数校验、分页信息、统一响应结构、错误码和资源隔离是否符合约定。
2. **业务计算正确性**：技能抽取、人岗匹配、数据质量、趋势、检索、工作台和内部转岗等计算是否符合确定性公式。
3. **状态与数据一致性**：异步任务、Pipeline、缓存、数据库审计记录及用户所有权是否一致。
4. **可量化门禁**：JD 锚点召回、简历抽取 F1、匹配准确率、Service 可执行行覆盖率是否达到门槛。

所有准确率均由实际 FYZ 代码执行后统计。单元测试使用隔离测试数据库保证可重复性；Docker 复测使用已部署的 FYZ API 镜像。外部 LLM 的随机输出不纳入确定性准确率，Agent 测试使用 Mock、失败降级及证据约束验证。

## 2. 总体量化结果与公式

| 指标 | 计算公式 | 样本量 | 实测结果 | 门槛 |
| --- | --- | ---: | ---: | ---: |
| JD 正例锚点召回率 | `TP / (TP + FN)` | 100 条真实爬取 JD；103 个可识别锚点 | `102 / 103 = 99.03%` | ≥ 90% |
| 简历抽取 micro-Precision | `TP / (TP + FP)` | 60 条标注边界样本 | `180 / 183 = 98.36%` | 辅助指标 |
| 简历抽取 micro-Recall | `TP / (TP + FN)` | 60 条标注边界样本 | `180 / 180 = 100%` | 辅助指标 |
| 简历抽取 micro-F1 | `2PR / (P + R)` | 60 条标注边界样本 | `99.17%` | ≥ 90% |
| 简历逐条完全一致率 | `预测技能集合与标注集合完全一致的样本数 / 总样本数` | 60 条 | `57 / 60 = 95%` | 观察指标 |
| 匹配分数精确准确率 | `预测分数与标注分数完全相同的样本数 / 总样本数` | 60 条端到端样本 | `60 / 60 = 100%` | ≥ 90% |
| 匹配分数 MAE | `Σ|预测分数 - 标注分数| / N` | 60 条 | `0` | 越低越好 |
| Service 行覆盖率 | `被执行的 Service 可执行行 / Service 全部可执行行` | 8644 行 | `7233 / 8644 = 83.68%` | ≥ 60% |

### 2.1 JD 指标的解释边界

JD 数据来自：

- `data/jd_crawl_ifly.json`：50 条；
- `data/jd_crawl_zl.json`：50 条。

原始 `keywords` 仅提供不完整的正例标签。计算时先通过技能词典完成别名归一化，再比较系统抽取集合与关键词锚点集合：

```text
TP = |预测技能 ∩ 正例锚点|
FN = |正例锚点 - 预测技能|
锚点召回率 = TP / (TP + FN)
```

由于数据没有完整标注“哪些技能不应被抽取”，无法诚实计算 JD 的完整 FP 和完整 Precision。因此策划书中应写“**JD 正例关键词锚点召回率 99.03%**”，不能直接写成“完整人工金标准 JD F1 99.03%”。

### 2.2 简历抽取指标

60 条简历样本为确定性技能边界样本，每条包含 3 个已标注技能，并覆盖 `K8s → Kubernetes`、`Postgres → PostgreSQL`、`TS → TypeScript` 等别名。调用的是生产 `RuleSkillExtractor`，不是测试桩。

本次统计：

```text
TP = 180
FP = 3
FN = 0
Precision = 180 / (180 + 3) = 98.36%
Recall = 180 / (180 + 0) = 100%
F1 = 2 × 98.36% × 100% / (98.36% + 100%) = 99.17%
```

3 个 FP 均来自 `React.js` 同时触发 `React` 与 `JavaScript` 别名识别。该误差已保留在报告中，没有删除失败样本来提高结果。

### 2.3 人岗匹配指标

匹配算法版本为 `skill-coverage-v1`。技能先经过标准名和别名归一化，再去重：

```text
matched = 简历标准技能集合 ∩ 岗位标准技能集合
missing = 岗位标准技能集合 - 简历标准技能集合
score = round(|matched| / |岗位标准技能集合| × 100)
```

如果岗位没有可识别技能，该岗位不会生成正常匹配记录。60 条端到端样本同时运行生产技能抽取器和生产 `calculate_skill_coverage` 函数，再与人工构造的期望技能集合、期望分数比较。

## 3. 接口分组与功能效果计算逻辑

## 3.1 健康检查与统一响应

### 接口

- `GET /api/v1/health`

### 功能效果

- 返回统一结构：`code`、`message`、`data`、`meta`；
- `data.status = ok`；
- 用于 Docker API 健康检查和 Nginx 上游存活判断。

### 测试判定

- HTTP 状态码为 200；
- JSON 结构完整；
- Nginx 转发访问与容器内访问结果一致。

## 3.2 认证接口

### 接口

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`

### 功能效果

- 注册执行用户名唯一性检查和 bcrypt 密码哈希；
- 登录使用 bcrypt 校验并签发 JWT；
- JWT 包含用户 ID、用户名、角色和有效期；
- 受保护接口必须携带有效 Bearer Token。

### 测试判定

- 正常注册、登录成功；
- 重复用户名、错误密码、不存在用户、短密码、缺字段被拒绝；
- 无 Token、伪造 Token、过期 Token 返回统一认证错误；
- 不直接比较哈希文本，而是验证 `bcrypt.checkpw` 和 JWT 解码结果。

对应测试：`test/api/test_auth.py`、`test/core/test_security.py`。

## 3.3 岗位管理、JD 解析与技能事实

### 接口

- `GET/POST /api/v1/jobs`
- `GET/PUT/DELETE /api/v1/jobs/{job_id}`
- `PUT /api/v1/jobs/{job_id}/status`
- `GET /api/v1/jobs/{job_id}/versions`
- `GET /api/v1/jobs/{job_id}/versions/{version_id}`
- `POST /api/v1/jobs/{job_id}/extract-skills`
- `GET /api/v1/jobs/{job_id}/skill-facts`
- `GET /api/v1/jobs/observed`
- `GET /api/v1/jobs/observed/{raw_job_id}`

### 功能效果

1. 岗位创建和修改验证薪资上下界、职责、要求和状态；删除采用软删除。
2. 薪资展示逻辑：

```text
salary_range = salary_min / 1000 + "K" + "-" + salary_max / 1000 + "K"
如配置 salary_months，再追加“· N薪”
```

3. JD 技能抽取合并 `jd_text`、`responsibilities`、`requirements` 三部分文本；
4. 技能词典完成大小写与别名归一化；
5. 通过词边界避免 `Java` 错误命中 `JavaScript`；
6. 否定词附近的技能不抽取；“优先、加分、preferred”等上下文标记为 preferred；
7. 基础置信度：标准名约 `0.96`，别名约 `0.92`，再乘熟练度系数；
8. 抽取结果保存为可审核技能事实，修改成功后使 Dashboard、Analysis 缓存失效。

### 测试判定

- CRUD、版本记录、状态修改、软删除和鉴权正确；
- 技能别名、上下文、证据文本、置信度和指纹稳定；
- 100 条真实 JD 的正例锚点召回率达到 90%。

对应测试：`test/api/test_jobs.py`、`test/api/test_skills.py`、`test/services/test_skill_extractor.py`、`test/evaluation/test_fyz_quality_metrics.py`。

## 3.4 数据导入、数据质量与近重复

### 接口

- `POST /api/v1/data-imports/jobs`
- `GET /api/v1/tasks/{task_id}`
- `GET /api/v1/admin/data-quality/records`
- `PATCH /api/v1/admin/data-quality/records/{record_id}`

### 数据质量计算

核心字段完整率：

```text
completeness = 非空字段数 / 5
字段 = title、company、source、url、jd_text
```

文本有效分：

```text
text_score = min(JD 规范化文本长度 / (minimum_jd_length × 3), 1)
默认 minimum_jd_length = 30
```

时效分：

```text
freshness_score = max(0, 1 - age_days / freshness_window_days)
默认 freshness_window_days = 90
缺少发布时间时使用保守值 0.35
未来时间直接记 0 并添加 future_posted_at 标记
```

最终质量分：

```text
quality_score =
    0.30 × completeness
  + 0.25 × text_score
  + 0.30 × freshness_score
  + 0.15 × source_trust_score
```

默认状态门槛：

- `quality_score ≥ 0.75` 且没有未来/无效发布时间：accepted；
- `quality_score ≥ 0.55`：warning；
- 其他：rejected。

近重复使用 64 位 SimHash：

```text
similarity = 1 - HammingDistance(hash1, hash2) / 64
```

近重复不会直接删除，而是降低质量权重：

```text
penalty = 0.15 × clamp((similarity - 0.85) / 0.15, 0, 1)
adjusted_score = quality_score × (1 - penalty)
```

### 功能效果与测试判定

- 文件只能从允许的数据目录读取并且必须为 JSON；
- 相同来源快照幂等，内容变化生成版本；
- 同一标准岗位的独立来源用于交叉验证；
- accepted/warning 且未排除的数据才进入后续分析；
- 管理员可排除、恢复质量记录，普通用户不可操作。

对应测试：`test/services/test_import_service.py`、`test/domain/test_data_quality.py`、`test/api/test_data_quality.py`、`test/api/test_skills.py`。

## 3.5 异步任务状态与 Redis 轮询

### 接口

- `GET /api/v1/tasks/{task_id}`
- 任务来源包括导入、图谱同步、JD 生成、职业规划、匹配解释等。

### 状态逻辑

```text
queued → running → succeeded / failed / cancelled
progress ∈ [0, 100]
```

- MySQL 是任务事实源；每次数据库提交后才将状态投影到 Redis；
- 查询先读 Redis，未命中、坏数据或 Redis 故障时回源 MySQL；
- 缓存载荷包含 `created_by`，命中后仍检查用户所有权；
- 不缓存 `request_data` 等敏感输入；
- 活跃任务 TTL 15 秒，终态任务 TTL 24 小时；
- Lua 原子脚本拒绝 `80% → 40%` 的进度倒退，也拒绝 `succeeded → running` 的终态回退。

### 测试判定

- 命中、未命中、坏 JSON、Redis 连接失败均不影响接口可用性；
- 不同用户不能通过 task ID 读取他人任务；
- 终态不能被延迟 Worker 写回运行态。

对应测试：`test/core/test_cache.py`、`test/services/test_task_status_cache.py`、`test/api/test_skills.py`。

## 3.6 简历上传、解析和人岗匹配

### 接口

- `POST /api/v1/resumes`
- `GET /api/v1/resumes/{resume_id}/file`
- `GET /api/v1/talents`
- `GET /api/v1/talents/{resume_id}`
- `GET /api/v1/talents/{resume_id}/details`
- `POST /api/v1/resumes/{resume_id}/matches`
- `POST /api/v1/matches/recalculate`
- `POST /api/v1/matches/{match_id}/explanation`

### 功能效果

1. 支持 TXT、Markdown、PDF、DOCX，最大 20MB；
2. TXT/Markdown 按 UTF-8-SIG、UTF-8、GB18030 顺序尝试解码；
3. PDF 提取文本过短时提示可能为扫描件；
4. 文件 SHA-256 用于同一用户下的重复上传检测；
5. 解析文本经过生产技能抽取器得到标准技能；
6. 与开放岗位逐一执行 skill-coverage 匹配；
7. 匹配证据同时保存简历技能证据和岗位要求证据；
8. 文件下载必须校验简历所有者；
9. 匹配解释中的 LLM 只生成解释，不修改确定性匹配分数；证据不足时过滤陈述或降级为模板。

### 匹配计算

```text
matched = normalized_resume_skills ∩ normalized_job_skills
missing = normalized_job_skills - normalized_resume_skills
score = round(|matched| / |normalized_job_skills| × 100)
```

### 测试判定

- 上传后技能、解析结果、匹配记录及证据同时落库；
- 后创建的岗位可通过 recalculate 补算；
- 文件不能跨用户下载；
- 60 条端到端样本分数准确率 100%，MAE 为 0；
- LLM 失败、未知引用和部分无效引用均不会篡改分数。

对应测试：`test/api/test_matching.py`、`test/services/test_matching_grounding.py`、`test/evaluation/test_fyz_quality_metrics.py`。

## 3.7 职业规划与 Agent

### 接口

- `POST /api/v1/career/resume-extractions`
- `POST /api/v1/career/analyses`
- `POST /api/v1/agents/career-plannings`
- `POST /api/v1/agents/jd-generations`
- `POST /api/v1/agents/jd-input-suggestions`
- `POST /api/v1/agents/match-explanations`
- `GET /api/v1/agents/runs`
- `GET /api/v1/agents/runs/{agent_run_id}`

### 功能效果

- 输入至少包含技能文本或简历内容之一；
- 岗位 ID、当前匹配度、补课后匹配度和推荐分由后端确定性计算；
- LLM 仅生成学习步骤、周期、项目建议和解释；
- AgentRun 保存 provider、model、prompt version、耗时、状态、结构化输出和失败原因；
- DeepSeek 不可用时返回模板结果，状态标记为 degraded；
- `Idempotency-Key` 相同且请求摘要一致时复用任务；摘要冲突时拒绝；
- 普通用户只能读取自己创建的 AgentRun，管理员可分页查看审计记录。

### 测试判定

- 未登录调用被拒绝；
- Mock LLM 返回值按 Pydantic Schema 校验；
- 超时、非法 JSON、重试耗尽均进入明确失败或降级路径；
- Agent 解释必须引用已保存证据，未知证据 ID 被过滤；
- 单元测试不使用真实外部 LLM 随机输出计算准确率，以保证结果可重复。

对应测试：`test/api/test_agents.py`、`test/api/test_career.py`、`test/services/test_jd_generation_service.py`、`test/services/test_llm_provider.py`、`test/services/test_matching_grounding.py`。

## 3.8 技能图谱

### 接口

- `POST /api/v1/graph/sync`
- `GET /api/v1/graph/snapshots`
- `GET /api/v1/graph/snapshots/{snapshot_id}`
- `POST /api/v1/graph/enrichment/generate`
- `GET /api/v1/graph/enrichment/candidates`
- `PATCH /api/v1/graph/enrichment/candidates/{candidate_id}/review`
- `POST /api/v1/graph/enrichment/candidates/reject-machine-failed`
- `POST /api/v1/graph/enrichment/publish`
- `GET /api/v1/graph/panorama`
- `GET /api/v1/graph/overview`
- `GET /api/v1/graph/nodes/{node_id}`
- `GET /api/v1/graph/nodes/{node_id}/neighbors`
- `GET /api/v1/graph/expand`
- `GET /api/v1/graph/search`
- `GET /api/v1/graph/path`
- `GET /api/v1/graph/jobs/{job_id}/tree`

### 图谱进入门槛

- MySQL 仍是源数据事实源；Neo4j 只重建 `namespace=jiebang`；
- 仅 `accepted/warning`、未排除的岗位记录参与；
- 技能事实必须 verified；自动进入图谱的事实置信度通常要求 ≥ 0.75；
- L4/L5 候选先保存为待审核，不直接发布；
- 深层知识点通常要求置信度 ≥ 0.75 且至少 2 个不同证据 ID；
- Grounding 证据质量门槛为 0.55；
- 同名节点和后缀变体经过确定性 name key 合并。

### 测试判定

- 图谱写入使用参数化 Cypher 并始终带 namespace；
- 不会删除其他 Neo4j 命名空间；
- expand/path 只允许系统已写入的关系类型；
- 非法全文检索字符有兼容降级；
- 单技能增强失败不会中断整个同步；
- 未通过证据和置信度门禁的候选不能发布。

对应测试：`test/api/test_graph.py`、`test/services/test_graph_service.py`、`test/services/test_graph_enrichment.py`、`test/repositories/test_graph_repository.py`、`test/integrations/test_neo4j.py`。

## 3.9 趋势分析与岗位洞察

### 接口

- `GET /api/v1/analysis/overview`
- `GET /api/v1/analysis/reference-standards`
- `GET /api/v1/analysis/job-insights`
- `PUT /api/v1/analysis/emerging-jobs/{standard_job_id}/decision`

### 计算逻辑

薪资统一转换为月薪 K：

```text
范围薪资 = (最低值 + 最高值) / 2
仅保留 1K～500K 的合理月薪值
城市/月平均薪资 = Σ有效薪资 / 有效记录数
```

岗位洞察置信度：

```text
confidence = min(99, 60 + source_count × 6 + core_skill_count × 2)
```

历史技能普及率：

```text
prevalence = 包含该技能的去重岗位证据簇数 / 历史基线全部证据簇数
```

只有同一标准岗位在历史期和当前期都有证据时，才计算能力变化。新技能、新岗位在证据不足时标记为“待历史核验”，不会伪装成已确认趋势。

### 测试判定

- 支持日、月、季度、半年等窗口；
- 城市归一化只保留城市级，拆分多城市记录；
- 已知历史技术不会因本地基线缺失被误判为新兴技能；
- 未审核技能不进入确认趋势；
- 空数据返回明确 `insufficient_data`，而不是虚构百分比。

对应测试：`test/api/test_analysis.py`、`test/services/test_analysis_service.py`、`test/services/test_historical_baseline_service.py`。

## 3.10 工作台与热门需求

### 接口

- `GET /api/v1/dashboard/overview`

### 计算逻辑

岗位评估覆盖率：

```text
coverage = round(已评估简历数 / 人才池简历总数 × 100)
pending = max(人才池简历总数 - 已评估简历数, 0)
```

匹配阶段：

- 高匹配：`score ≥ 80`；
- 可推进：`60 ≤ score < 80`；
- 待补强：`score < 60`；
- 待评估：尚未生成匹配记录。

热门岗位：

```text
demand = 该标准岗位关联的有效原始岗位记录数
spark[i] = 最近 6 个月中第 i 月的记录数
trend = spark[-1] - spark[-2]
```

生命周期：

- mature：证据簇 ≥ 5 且活跃月份 ≥ 3；
- established：证据簇 ≥ 3 且活跃月份 ≥ 2；
- observed：其他。

新兴技能：

```text
growth = 最近一个月更新的 verified 技能事实数
confidence = round(技能事实平均置信度 × 100)
```

### 测试判定

- 只使用开放岗位、有效简历及当前岗位的匹配记录；
- 旧岗位匹配不会污染当前看板；
- 热门岗位、新兴技能支持服务端分页；
- 无数据时返回 0 和空列表，不出现除零错误。

对应测试：`test/api/test_dashboard.py`、`test/services/test_analysis_service.py`。

## 3.11 证据检索与 RAG

### 接口

- `POST /api/v1/retrieval/indexes/rebuild`
- `GET /api/v1/retrieval/indexes`
- `POST /api/v1/retrieval/search`
- `GET /api/v1/retrieval/evidence/{evidence_id}`

### 混合检索得分

当命中岗位/技能权威过滤条件时：

```text
score = min(1,
    0.15 × vector_score
  + 0.15 × keyword_score
  + 0.15 × quality_score
  + 0.25 × graph_score
  + 0.30 × semantic_skill_score)
```

普通检索时：

```text
score = min(1,
    0.40 × vector_score
  + 0.20 × keyword_score
  + 0.15 × quality_score
  + 0.15 × graph_score
  + 0.10 × semantic_skill_score)
```

结果还必须满足：

- 数据质量状态为 accepted/warning；
- `quality_score ≥ minimum_quality_score`；
- `score ≥ minimum_retrieval_score`；
- 无关键词、无向量相关性且没有权威匹配时拒绝返回；
- 根据近重复分组去重，保留可追踪 Evidence ID、来源和索引版本。

### 测试判定

- 管理员才能重建索引；
- 内存与 Chroma 后端都能保存、过滤并查询；
- Evidence ID、原文窗口偏移和来源可追踪；
- 无证据问题正确拒答，不生成伪引用。

对应测试：`test/api/test_retrieval.py`、`test/domain/test_retrieval.py`、`test/services/test_chroma_vector_store.py`、Phase 2 Golden Set 测试。

## 3.12 企业内部转岗

### 接口

- `GET/POST /api/v1/internal-transfer/employee-directory`
- `GET/POST /api/v1/internal-transfer/talents`
- `POST /api/v1/internal-transfer/talents/from-directory/{employee_id}`
- `GET/POST /api/v1/internal-transfer/positions`
- `PUT /api/v1/internal-transfer/positions/{position_id}/status`
- `GET /api/v1/internal-transfer/skill-demands`
- `GET/POST /api/v1/internal-transfer/rule-sets`
- `POST /api/v1/internal-transfer/matches/by-talent`
- `POST /api/v1/internal-transfer/matches/by-position`
- `GET/POST /api/v1/internal-transfer/decisions`

### 内部匹配公式

```text
skill_coverage = matched_required_skills / required_skills
tenure_ratio = min(1, 员工司龄 / 要求司龄)
score = round(skill_coverage × skill_weight + tenure_ratio × tenure_weight)
```

默认规则：技能权重 85、司龄权重 15、最低匹配分 60。

硬性资格还检查：

- 岗位已配置必备技能；
- 司龄、当前岗位任职月数达标；
- 部门在允许范围内；
- 人才状态 active；
- 岗位处于开放日期范围；
- 岗位状态为 open。

培养周期估计：

```text
estimated_development_weeks =
    min(52, max(1, missing_required_skills × 2 + trainable_gaps))
```

技能供需缺口：

```text
gap = max(0, demand_headcount - talent_supply)
```

### 测试判定

- 公共招聘岗位、简历与企业内部人才数据相互隔离；
- 内部岗位必须从 draft 开始，不能绕过审批状态机；
- 员工编号搜索可自动填充人才档案；
- 不满足硬规则的组合不能创建确认决策；
- 名额已满或员工已有确认转岗时拒绝重复确认。

对应测试：`test/api/test_internal_transfer.py`。

## 3.13 管理后台、爬虫和 Pipeline

### 接口

- `GET /api/v1/admin/overview`
- `GET /api/v1/admin/resources`
- `GET/PUT /api/v1/admin/data-sources/automation`
- `PUT /api/v1/admin/data-sources/{spider_id}`
- `POST /api/v1/admin/data-sources/{spider_id}/run`
- `GET /api/v1/admin/data-sources/{spider_id}/status`
- `GET /api/v1/admin/data-sources/{spider_id}/poll`
- `POST/GET /api/v1/admin/pipeline/runs`
- `GET /api/v1/admin/pipeline/runs/{run_id}`

### Pipeline 阶段

```text
collect
→ validate_import
→ quality_gate
→ graph_publish
→ baseline_refresh
→ trend_verify
→ succeeded / failed
```

- PipelineRun 记录 stage、progress、heartbeat、质量汇总和各阶段结果；
- Pipeline 状态先读 Redis，未命中回源 MySQL；
- 活跃/终态投影使用与任务状态相同的单调写入保护；
- 调度幂等键防止相同周期重复创建运行记录；
- 管理接口全部要求管理员角色。

### 测试判定

- 管理员可创建、分页查询、查看 Pipeline；普通用户被拒绝；
- 自动采集配置可持久化周期、来源和数量限制；
- 相同调度幂等键返回同一运行记录；
- Pipeline 坏缓存被删除并回源数据库。

对应测试：`test/api/test_admin_pipeline.py`、`test/services/test_pipeline_service.py`、`test/services/test_pipeline_status_cache.py`、`test/services/test_crawler_service.py`。

## 3.14 收藏、浏览历史与行为洞察

### 接口

- `GET/POST /api/v1/favorites`
- `POST /api/v1/favorites/batch-delete`
- `PUT /api/v1/favorites/{favorite_id}/note`
- `GET/POST/DELETE /api/v1/history`
- `DELETE /api/v1/history/{history_id}`
- `GET /api/v1/history/insights`

### 计算逻辑

- 收藏采用 toggle 语义：未收藏时创建，已收藏时取消；
- 收藏和历史均按 user_id 隔离；
- 行为类型占比：

```text
percent = round(某类型访问次数 / 全部访问次数 × 100)
```

- 空历史时所有占比返回 0。

### 测试判定

- 收藏切换、备注、批量删除正确；
- 目标资源不存在时拒绝收藏；
- 用户之间互不可见；
- 历史聚合、单条删除和清空正确。

对应测试：`test/api/test_user_activity.py`。

## 3.15 查询缓存与定时预热

### 缓存接口范围

- Dashboard overview：TTL 45 秒；
- Analysis overview：TTL 120 秒；
- Analysis job-insights：TTL 90 秒；
- Graph panorama、overview、node、neighbors、expand、search、path、job-tree：TTL 600 秒；
- 热门岗位：TTL 300 秒。

### Key 与失效逻辑

```text
cache_key = namespace + operation + generation + canonicalized(params)
```

- 参数排序后计算稳定哈希，相同参数得到相同 Key；
- 用户级结果必须把 user_id 放入参数，防止跨用户复用；
- 写事务成功后 `generation + 1`，旧 Key 立即不可达并等待 TTL 自然清理；
- 单条缓存最大 1MiB，超过时跳过写入；
- Redis 错误始终 fail-open，直接执行数据库/Neo4j loader；
- Celery Beat 每 60 秒向独立 `cache_warmup` 队列预热热门岗位、默认趋势和图谱概览；
- 预热 Worker 与长任务 Worker 分离，避免互相阻塞。

### 测试判定

- Pydantic 模型命中后恢复原模型类型；
- generation bump 后旧结果不可见；
- 用户参数隔离；
- 大结果不写缓存；
- force refresh 替换旧值；
- Redis 停机不使 API 失败。

对应测试：`test/core/test_cache.py`、`test/services/test_query_cache.py`、Dashboard/Analysis/Graph API 测试。

## 3.16 兼容模块入口

### 接口

- `GET /api/v1/matching/`

`matching/` 用于兼容已有模块健康检查和前端入口，不代表独立计算功能。旧
`/changes/` 与 `/changes/health` 无消费者，其需求已由 Analysis 和岗位版本接口覆盖，
于 2026-08-12 移除；回归测试验证两条旧路径返回 404。

## 4. 覆盖率计算方法

当前环境不依赖联网安装 pytest-cov，使用 Python 标准库完成可重复统计：

1. 递归读取 `app/services/*.py` 的 CPython code object；
2. 通过 `dis.findlinestarts` 识别可执行行；
3. 运行全部 FYZ pytest 时，通过 `sys.settrace` 记录实际执行行；
4. 排除测试代码、依赖库、JTT 和前端；
5. 聚合得到：

```text
Service coverage = 7233 / 8644 = 83.68%
```

该指标是行覆盖率，不代表分支覆盖率，也不应表述为“83.68% 的业务场景绝对无缺陷”。覆盖率用于说明测试触达范围，准确率指标用于说明特定算法效果，两者不能互相替代。

## 5. 策划书推荐表述

可直接采用以下文字：

> 项目针对 FYZ 管理与决策端建立了接口契约、业务算法、异步状态、缓存降级和数据一致性五层测试体系。当前 OpenAPI 覆盖 93 个路径、106 个 HTTP 操作，共执行 311 项自动化测试且全部通过，其中 96 项为直接 API 测试；Service 可执行行覆盖率为 83.68%，高于 60% 门槛。质量评测使用 100 条真实爬取 JD、60 条简历技能边界样本和 60 条端到端匹配样本，JD 正例关键词锚点召回率为 99.03%，简历技能抽取 micro-F1 为 99.17%，匹配分数精确准确率为 100%。JD 来源标签为不完整正例集合，因此该项严格表述为锚点召回率，不将其夸大为完整人工金标准 F1。

## 6. 复现方式

在 `fyz-src/backend` 中执行：

```powershell
& 'E:\Computer_tools\Anaconda\dld\envs\jiebang\python.exe' scripts/evaluate_fyz_quality.py --jd-limit 100 --case-count 60
& 'E:\Computer_tools\Anaconda\dld\envs\jiebang\python.exe' scripts/run_fyz_coverage.py
& 'E:\Computer_tools\Anaconda\dld\envs\jiebang\python.exe' scripts/generate_fyz_test_report.py
```

生成文件：

- `evaluation/fyz_quality_metrics.json`：准确率及失败样本；
- `evaluation/fyz_coverage.json`：总体及逐文件覆盖率；
- `evaluation/fyz_pytest_results.xml`：311 项测试的 JUnit 明细；
- `evaluation/fyz_test_report.html`：简洁可视化报告；
- `evaluation/fyz_interface_test_calculation_logic.md`：本说明文档。
