# FYZ 优化 Phase 3 Agent 防幻觉门禁实施记录

> 文档版本：v0.2
> 更新日期：2026-07-31
> 当前范围：Graph Enrichment 与 Match Explanation 两条纵向闭环

## 1. 本轮目标

本轮不是只增强 Prompt，而是把图谱补全改造成可审计的证据闭环：

```text
Retriever Top-K
  -> 只向模型注入稳定 Evidence ID 和证据文本
  -> 模型生成 L4/L5 结构化声明
  -> 生成后验证引用、来源、质量、时效和语义一致度
  -> 持久化通过的 Claim-Evidence 引用
  -> machine_validated 候选进入后续人工审核
```

任何检索失败、证据不足、引用伪造或校验失败都不能进入正式图谱。

## 2. 已完成内容

### 2.1 生成前检索约束

- `GraphService` 只使用 `RetrievalService.search()` 返回的 Top-K Evidence Chunk。
- 检索按当前技能 ID、认证状态、最低质量分和最低检索分过滤。
- 候选至少需要两条证据和两个独立来源平台才会调用 LLM。
- 检索索引不可用时记录 `retrieval_unavailable`，不回退到事实表直接注入。
- LLM 未配置、检索无结果和单一平台证据均在生成前确定性降级。

### 2.2 Agent 输出契约

- 图谱补全输入由整数 `source_id` 升级为稳定字符串 `evidence_id`。
- TechPoint 和 KnowledgePoint 使用 `evidence_ids`。
- Schema 保留旧 `source_id/source_ids` 的只读兼容入口，新的序列化输出统一使用 Evidence ID 字段。
- Prompt 明确禁止引用输入中不存在的 Evidence ID。

### 2.3 生成后统一门禁

新增 `AgentGroundingService`，逐条校验：

- 引用非空且全部存在于本次 Retriever 结果中。
- 证据状态属于 `human_approved` 或 `machine_validated`。
- 证据质量分不低于 `0.55`。
- 证据时间不超过 1095 天；缺少时间时保留警告。
- 图谱声明至少引用两个独立平台。
- 声明名称和文本与每条证据的确定性 lexical/CJK n-gram 支持分不低于 `0.12`。
- 图谱声明自身置信度不低于 `0.75`。

任一硬性规则失败都会删除该声明；KnowledgePoint 失败不会连带删除已经通过的父 TechPoint。

### 2.4 引用和审计

- 通过门禁的 Claim-Evidence 关系写入 `agent_claim_citation`。
- 引用状态统一为 `machine_validated`，保存 grounding score。
- 重试同一个 AgentRun 时先清除旧引用，保证幂等。
- `AgentRun.structured_output` 记录：
  - 原始模型输出；
  - 过滤后的输出；
  - retrieval query 摘要；
  - Evidence IDs；
  - index version 和 backend；
  - 每条声明的验证结果；
  - fallback reason。
- 日志和审计摘要不记录完整简历、密钥或完整 Prompt。

### 2.5 发布隔离

- 通过机器门禁的图谱候选标记为 `machine_validated`。
- 现有正式图谱写入仍只读取 `verified` 候选。
- 因此本轮机器通过的候选不会自动发布；管理员审核和发布状态将在 Phase 4 拆分。

### 2.6 Match Explanation 门禁

- `MatchEvidenceInput.evidence_id` 升级为稳定字符串引用，例如 `match_evidence:12`。
- 优势、差距和风险统一为带 `evidence_ids` 的结构化声明。
- 模型层只负责生成候选结构；是否允许输出由后端 `AgentGroundingService` 决定。
- 每个引用必须属于当前用户可访问的已保存 MatchRecord 快照。
- 声明标题和正文必须得到被引 MatchEvidence 的确定性语义支持。
- 引用为空、引用不存在或语义不一致的声明直接删除。
- 风险从无引用字符串升级为结构化、可引用对象。
- Summary 不采用模型自由文本，只汇总通过校验的声明和不可变匹配分数。
- 面试建议由通过校验的优势确定性生成，不直接采用模型自由建议。
- LLM 所有声明均失败时自动切换确定性模板。
- 审计同时保留模型候选的原始校验结果和模板的最终校验结果，伪造引用原因不会被模板覆盖。
- 模板也必须经过同一引用门禁；完全无证据时返回明确无答案。
- 原始匹配分数、已匹配技能和缺失技能始终来自保存快照，模型无权改写。

### 2.7 多类型引用模型

迁移 `20260731_0015` 扩展 `agent_claim_citation`：

- `citation_source_type`：`evidence_chunk` 或 `match_evidence`。
- `citation_ref`：对应来源中的稳定引用。
- `source_metadata`：保存脱敏的来源定位信息。
- `evidence_id`：仅 RAG Evidence Chunk 使用，MatchEvidence 引用保持为空。
- 唯一键升级为 AgentRun、Claim、来源类型和来源引用组合。

旧 Evidence Chunk 引用会原位迁移为 `evidence_chunk`，不改变原外键关系。

## 3. 已覆盖测试

- 正常双平台证据生成并持久化引用。
- 引用不存在。
- 单一平台。
- 低质量证据。
- 过期证据。
- 语义不一致。
- 检索服务不可用。
- LLM 调用失败。
- LLM 未配置。
- 置信度边界。
- KnowledgePoint 独立过滤。
- 旧 `source_ids` 输入兼容。
- 机器候选不进入正式图谱。
- 匹配优势、差距和风险正常引用。
- MatchEvidence 多态引用持久化。
- 模型伪造 MatchEvidence 引用后模板降级。
- 部分非法风险独立过滤。
- Summary 只汇总通过校验的声明。
- 模型自由面试建议替换为确定性建议。
- 完全无 MatchEvidence 时明确拒答。
- 匹配解释 LLM 失败降级和 fallback reason。
- 原匹配分数不可被模型改写。

## 4. 当前边界

- 本轮已完成 Graph Enrichment 和 Match Explanation，尚未接入 Skill Extraction、JD Generation 和 Career Planning。
- 语义一致度为确定性轻量门禁，不是独立 NLI 模型；优点是可复现、无额外模型成本，后续可用离线 NLI 评测决定是否升级。
- 当前数据只有两个来源平台，双平台规则可能导致较高拒绝率；这是安全降级，不应通过放宽规则掩盖。
- `GraphEnrichmentCandidate` 暂时复用 `verification_status` 表示 `machine_validated`；Phase 4 将拆为机器校验、人工审核和发布三个独立状态。

## 5. 本轮验证结果

- 后端全量回归：`185 passed`。
- 图谱与匹配解释定向回归：`25 passed`。
- 独立 Agent 包：`11 passed`。
- FYZ 前端：`29 passed`，生产构建通过。
- Python 依赖检查：`pip check` 通过。
- Git 差异检查：`git diff --check` 通过。
- 真实 MySQL：Alembic 已从 `20260731_0014` 升级到 `20260731_0015`。
- 真实 MySQL 结构复核：多态引用列、JSON 元数据列、新唯一约束及 EvidenceChunk 可空外键均符合模型定义。

## 6. 下一步

1. 接入 JD Generation 的字段级来源、建议标记和发布前门禁。
2. 接入 Career Planning 的 `provided / inferred / unknown` 和差距映射。
3. 补强 Skill Extraction 的原文位置、别名和候选池门禁。
4. Phase 4 新增候选审核、审核意见、发布状态和管理员接口。
