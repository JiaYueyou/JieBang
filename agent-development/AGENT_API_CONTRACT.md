# 智联职引 Agent 开发接口契约 v1.0

更新日期：2026-07-11
适用范围：FYZ 管理端（FastAPI、MySQL、Celery、DeepSeek Provider）

## 1. 目标与边界

Agent 的职责是把已有、可追溯的业务数据整理为**可编辑草稿**或**可解释建议**。MySQL 是业务事实源，Neo4j 是可重建的查询模型；大模型不是事实源，也不能直接发布岗位、修改技能图谱、覆盖匹配分数或执行人工审核。

所有 Agent 必须：

- 使用结构化 JSON 输出并经过 Pydantic 校验；
- 记录 `AgentRun` 审计信息和异步 `AsyncTask` 状态；
- 对模型超时、限流、无效 JSON 提供有限重试和可见失败/降级结果；
- 将输入最小化、脱敏，日志中不记录简历全文、Token、API Key；
- 由确定性服务计算分数、趋势和验证结论，Agent 仅解释它们。

## 2. Agent 范围与优先级

| Agent | 业务目标 | 当前状态 | 写入边界 | 优先级 |
| --- | --- | --- | --- | --- |
| JD Generation | 根据招聘需求生成可编辑 JD 草稿 | 已有首版 | 仅 `AgentRun`、`AsyncTask` 与草稿输出；不得直接发布岗位 | P0 |
| Skill Extraction | 从 JD/简历文本抽取候选技能和证据 | 规则抽取已存在，待统一 Agent 审计与 LLM 补全 | 候选事实必须经词典、来源和规则验证后才可入库/入图 | P0 |
| Skill L4/L5 Completion | 基于已验证 L1–L3 和多来源证据补全技术点、知识点 | 已实现独立 Agent 与后端证据门槛 | 只写候选；通过双来源和置信度门槛后随图谱快照进入读模型 | P0 |
| Match Explanation | 解释确定性匹配算法已得出的得分、缺口与建议 | 待开发 | 仅生成匹配报告；不得生成或覆盖最终分数 | P1 |
| Career Planning | 基于已验证技能差距生成学习路径草稿 | 待开发 | 仅写分析结果，学习资源需校验 | P1 |
| Emerging Job Review | 汇总趋势、聚类和来源证据，生成新兴岗位候选说明 | 趋势与人工决策接口已存在，Agent 待开发 | 仅候选说明；审核通过后才可创建正式岗位 | P1 |

不单独建设“趋势预测 Agent”：趋势指标必须由 `analysis_service` 等确定性服务计算，Agent 可在上述 Agent 中解释指标。

## 3. 通用传输约定

- 基路径：`/api/v1`；除登录等公开路由外均需 `Authorization: Bearer <JWT>`。
- 请求和响应使用 UTF-8 JSON；时间为 ISO 8601 UTC；ID 采用 UUID（业务资源 ID 仍为整数）。
- 成功外层统一为 `{"code": 200, "message": "success", "data": ..., "meta": null}`。
- 参数校验失败由 FastAPI 返回 422；无认证为 401；无权限为 403；资源不存在为 404；业务错误沿用项目统一错误码。
- 提交异步任务只返回任务标识，不等待模型生成完成；前端轮询任务接口，终态后读取运行记录中的结构化输出。

### 3.1 异步任务状态

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `task_id` | string(UUID) | `AsyncTask.id` |
| `task_type` | string | `jd_generation`、`skill_extraction`、`match_explanation`、`career_planning`、`emerging_job_review` |
| `status` | enum | `queued`、`running`、`succeeded`、`failed` |
| `progress` | integer | 0–100；终态为 100 |
| `result` | object/null | 成功或降级时的结构化输出摘要 |
| `error_code` | string/null | 可程序处理的错误码 |
| `error_message` | string/null | 面向用户的简短错误信息，不含敏感数据 |
| `created_at` / `started_at` / `finished_at` | datetime/null | 任务生命周期时间 |

若生成出受控模板，`AsyncTask.status` 保持 `succeeded`，以兼容现有任务消费方；对应 `AgentRun.status` 为 `degraded`，前端应展示“需人工复核”。`failed` 表示无可用结果。

### 3.2 AgentRun 审计记录

所有 Agent 统一返回或可查询如下字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string(UUID) | `agent_run_id` |
| `agent_type` | string | Agent 类型 |
| `provider` / `model` | string | 实际模型提供方与模型名 |
| `prompt_version` | string | 与本次输出绑定的 Prompt/Schema 版本 |
| `input_summary` | string | 脱敏且截断后的输入摘要 |
| `structured_output` | object/null | 已通过 Schema 校验的完整输出 |
| `status` | enum | 与任务状态一致的运行状态 |
| `duration_ms` / `retry_count` | integer/null | 性能与重试审计 |
| `error_code` / `error_message` | string/null | 错误审计 |
| `created_at` / `finished_at` | datetime/null | 运行时间 |

## 4. 接口清单

### 4.1 已有：JD 生成

#### `POST /api/v1/agents/jd-generations`

创建 JD 草稿生成任务。请求字段：

| 字段 | 类型 | 必填 | 约束/说明 |
| --- | --- | --- | --- |
| `mode` | `requirements | profile` | 否 | 默认 `requirements` |
| `title` | string | 是 | 1–120 字符 |
| `level` | string/null | 否 | 最长 30 |
| `department` | string/null | 否 | 最长 100 |
| `skills_input` | string | 否 | 最长 3000；需求或人才画像原文 |
| `location` | string/null | 否 | 最长 100 |
| `company` | string/null | 否 | 最长 150 |
| `headcount` | integer/null | 否 | 1–10000 |

响应 `data`：`{ "task": TaskStatus, "agent_run_id": "uuid" }`。

`structured_output`（终态读取）字段为 `title`、`standardized_title`、`level`、`department`、`responsibilities[]`、`requirements[]`、`skills[]`、`bonus_skills[]`、`jd_text`、`assumptions[]`、`warnings[]`、`generation_mode(llm|template)`。草稿需由岗位编辑页面人工确认后再调用既有岗位发布接口。

### 4.2 已有：查询运行审计

#### `GET /api/v1/agents/runs/{agent_run_id}`

返回第 3.2 节的 `AgentRun`。前端轮询间隔建议 2 秒，连续 30 次未进入终态后改为提示用户稍后刷新；不得将轮询当作无限重试机制。

### 4.3 待开发：技能抽取

#### `POST /api/v1/agents/skill-extractions`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `source_type` | `job_posting | resume | text` | 是 | 输入来源类型 |
| `source_id` | integer/null | 条件必填 | 非 `text` 时必填，服务端读取原文 |
| `text` | string/null | 条件必填 | `source_type=text` 时必填，1–12000 字符 |
| `enable_llm_enrichment` | boolean | 否 | 默认 `false`；规则结果不足时才启用 |

输出 `skills[]`，每项包含：`name`、`category`、`kind(required|preferred)`、`confidence(0~1)`、`evidence`、`extraction_method(rule|llm)`、`verification_status(verified|unverified)`。接口仅创建候选结果；正式写入必须复用现有技能词典归一化、来源核验与图谱同步流程。

#### L4/L5 内部补全契约

该 Agent 不新增独立 HTTP 路由，由现有 `POST /api/v1/graph/sync` 在 `enrich_top_skills=true` 时调用。

输入为 `job_directions[]`、`skill_area`、`tech_stack` 和 `evidence[]`；证据项包含 `source_id`、`source`、`text`。输出沿用 `GraphEnrichmentOutput`：`skill_name`、`job_directions[]`、`skill_area`、`tech_points[]`，每个技术点可包含 `knowledge_points[]`。

后端只接受置信度不低于 `0.75`、引用 ID 全部存在且覆盖至少两个不同来源平台的 L4/L5。模型原始输出记录在 `AgentRun`，过滤后的输出写入 `graph_enrichment_candidate`；无合格 L4 时保持 `unverified`。

### 4.4 待开发：匹配解释

#### `POST /api/v1/agents/match-explanations`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `match_id` | integer | 是 | 已由匹配算法计算并保存的记录 |
| `language` | `zh-CN | en-US` | 否 | 默认 `zh-CN` |
| `focus` | `summary | gaps | interview` | 否 | 默认 `summary` |

输出：`match_id`、`score_snapshot`、`strengths[]`、`gaps[]`、`evidence[]`、`interview_suggestions[]`、`disclaimer`。其中 `score_snapshot` 必须与数据库既有得分一致；每条 `evidence` 必须包含 `source_type`、`source_id`、`text`。

### 4.5 已实现：简历分析与职业规划

#### `POST /api/v1/career/resume-extractions`

使用 multipart 字段 `file` 上传 TXT、Markdown、PDF 或 DOCX，返回 `filename`、`text`、`character_count`、`warnings[]`。文件最大 20MB；解析文本最多保留 20000 字符。

#### `POST /api/v1/career/analyses`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `skill_text` | string | 条件必填 | 与 `resume_text` 至少提供一项 |
| `resume_text` | string | 条件必填 | 后端文件解析或已有简历服务提供的文本 |
| `enterprise_tech` | string | 否 | 企业内部技术栈和规范 |
| `internal_jobs` | string[] | 否 | 内部需求岗位名称，用于优先级标记 |
| `target_job_ids` | integer[] | 否 | 限定目标岗位范围 |
| `time_budget_weeks` | integer | 否 | 1–52，默认 12 |

输出：`resume_profile`、`recommendations[]`、`agent_run_id`、`warnings[]`。每条推荐包含确定性的 `job_id`、`recommend_score`、`current_match`、`after_match`、`existing[]`、`gaps[]`，以及 Agent 生成的 `learning_plan[]`、`suggested_project`、`total_time` 和 `explanation`。

### 4.6 待开发：新兴岗位复核草稿

#### `POST /api/v1/agents/emerging-job-reviews`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `standard_job_id` | integer | 是 | `analysis` 识别的候选岗位 |
| `period_months` | integer | 否 | 2–24，默认 12 |
| `include_competitors` | boolean | 否 | 默认 `false`，仅使用授权数据源 |

输出：`standard_job_id`、`candidate_name`、`summary`、`trend_evidence[]`、`skill_evidence[]`、`confidence`、`review_questions[]`、`recommendation(draft|needs_review|reject)`。人工仍通过已有 `PUT /api/v1/analysis/emerging-jobs/{standard_job_id}/decision` 提交 `approve|reject` 决策及 `note`。

## 5. 服务端实现约束

每个新增 Agent 使用同一分层：`schemas/<agent>.py` → `services/<agent>_service.py` → `tasks/<agent>.py` → `api/v1/agents.py`（或同域路由）→ `test/`。复用 `DeepSeekProvider.generate_structured`、`AgentRun`、`AsyncTask` 和任务查询协议，不引入第二套编排框架。

每个模型输出必须经历：JSON 解析 → Pydantic Schema → 枚举/长度/范围 → 业务资源存在性 → 证据存在性 → 业务规则。允许一次带错误反馈的修复调用，最多两次模型尝试；仍失败时执行受控模板降级或明确失败。

## 6. 前端联调规则

1. 提交表单后保存 `task_id` 和 `agent_run_id`，展示排队/运行/完成/降级/失败状态。
2. 在任务 `succeeded` 后读取 `structured_output`；若 `AgentRun.status=degraded`，必须展示警示与编辑入口。
3. 不以模型文本直接驱动发布、审核、图谱写入或分数展示；这些操作必须调用各自的业务确认接口。
4. 所有数组字段按空数组处理，所有可空字段按 `null` 处理；不得假定模型一定返回非空字符串。
