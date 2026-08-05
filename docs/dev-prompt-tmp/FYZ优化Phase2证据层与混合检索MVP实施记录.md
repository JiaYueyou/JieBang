# FYZ 优化 Phase 2 证据层与混合检索 MVP 实施记录

> 实施日期：2026-07-31
>
> 开发分支：`feat/fyz-rag-evidence`
>
> 依赖提交：`0dee662 feat(data): 完成FYZ数据质量与事实认证链路`
>
> 当前结论：Evidence Chunk、索引版本、Neo4j 向量试点、混合检索、证据回链、170 条 Phase 2 工程评测样本和可重复评测器已完成。Phase 2.1 已选择 ChromaDB 并接入 `text-embedding-3-large` Provider；真实语义索引仍等待 API Key。

## 1. 数据模型与迁移

Alembic 已从 `20260730_0013` 升级到 `20260731_0014`，新增：

- `evidence_chunk`：MySQL 权威证据片段。
- `retrieval_index_version`：可重建索引版本和状态。
- `retrieval_index_entry`：索引版本与证据的映射、向量镜像和校验值。
- `retrieval_query_log`：脱敏查询摘要、过滤条件、结果 Evidence ID 和耗时。
- `agent_claim_citation`：为 Phase 3 预留的 Claim—Evidence 引用契约。

`EvidenceChunk` 保存：

- 稳定 Evidence ID。
- `JobSkillFact`、原始岗位、来源文档、标准岗位和技能外键。
- 原文片段及字符范围。
- 来源平台、URL、发布时间。
- 数据质量分、认证状态、内容指纹和近重复组。

索引可以删除重建，但 Evidence Chunk 必须从 MySQL 事实链恢复，Neo4j 不承担权威事实存储。

## 2. 证据生成门禁

只有同时满足以下条件的事实进入索引：

```text
JobSkillFact.verification_status = verified
RawJobRecord.quality_status in (accepted, warning)
RawJobRecord.is_excluded = false
Skill.validation_status = approved
standard_job_id 不为空
```

人工审核通过的事实映射为 `human_approved`；同岗位跨来源机器认证的事实映射为 `machine_validated`。不再满足门禁的历史 Evidence Chunk 标记为 `expired`，不直接删除。

Evidence ID 由事实 ID、原始岗位 ID 和技能 ID 确定性生成；正文变化不会造成引用身份漂移。

## 3. Embedding 与索引后端

定义了可替换 `EmbeddingProvider` 协议。当前实现：

| 项目 | 值 |
|---|---|
| Provider | `local_deterministic` |
| Model | `signed-token-hash-v1` |
| 维度 | 256 |
| Chunking | `evidence-window-v1` |
| Neo4j index | `jiebang_evidence_embedding` |

确定性哈希向量用于：

- 无外部模型和无网络环境下的回归。
- 验证索引重建、版本、过滤和引用链路。
- 为后续语义 Embedding Provider 提供接口基线。

它不具备完整语义理解能力。API 响应会显式返回警告，且当前基线要求至少有词法命中，避免哈希碰撞把无关证据作为答案返回。

### 3.1 Phase 2.1 语义 Embedding

已新增 OpenAI-compatible Provider：

| 项目 | 配置 |
|---|---|
| Provider | `openai_compatible` |
| Model | `text-embedding-3-large` |
| Base URL | `https://api.openai-proxy.org/v1` |
| 维度 | 3072 |
| API Key | `OPENAI_EMBEDDING_API_KEY`，已在本地配置且未写入版本库 |
| Vector Store | ChromaDB |

API Key 为空时 Provider 会在网络调用前明确失败，索引版本标记 `failed`，不会降级生成一个伪装成语义模型的哈希索引。Base URL 使用完整配置值，Provider 不追加 API 路径；真实调用已经验证 3072 维响应。旧索引检索时根据持久化的 Provider、Model 和 Dimension 恢复对应 Provider，因此 Neo4j/hash 报告仍可重现。

FAISS、ChromaDB、Milvus 对比、选型依据、配置和密钥后验证步骤见 [Phase 2.1 Embedding 与向量数据库选型补充](./FYZ优化Phase2.1Embedding与向量数据库选型补充.md)。

## 4. 混合检索

当前综合分包含：

- 词法命中分。
- Neo4j 向量召回分；不可用时降级到 MySQL 中的可重建向量镜像。
- 数据质量分。
- 标准岗位或技能过滤命中的图约束分。
- 技能别名和受控语义说明；这些内容只用于索引，不替换引用原文。

检索器会先识别查询中显式出现的标准岗位和规范技能名。岗位名会先从查询中移除，避免把“Java开发工程师”中的 `Java` 错当成用户单独指定的技能；`Spring Boot` 等长规范名优先于其子串 `Spring`。显式实体命中后，只在对应事实集合内排序，防止确定性哈希向量噪声压过权威外键。

支持过滤：

- 标准岗位。
- 技能集合。
- 来源平台。
- 发布时间。
- 最低质量分。
- `human_approved / machine_validated` 认证状态。
- 指定索引版本。

同一近重复组只保留最高分证据。低于检索阈值或无词法相关性的确定性基线结果不会返回，并携带“证据不足”警告。语义检索还使用 `0.04` 的相对分数窗口，只返回与最高分处于同一相关性带的证据，避免用固定 Top-K 填充低相关引用。

## 5. API

```text
POST /api/v1/retrieval/search
POST /api/v1/retrieval/indexes/rebuild
GET  /api/v1/retrieval/indexes
GET  /api/v1/retrieval/evidence/{evidence_id}
```

- 搜索和证据详情要求登录。
- 索引重建和版本列表仅管理员可用。
- 搜索结果返回 Evidence ID、原始外键、来源、质量分、认证状态、各分项分数和索引版本。
- 查询日志会对邮箱和手机号做脱敏，禁止保存密钥或完整个人联系信息。

## 6. 真实环境验证

### 6.1 MySQL

| 项目 | 数量 |
|---|---:|
| Evidence Chunk | 323 |
| 成功索引版本 | 6 |
| 失败索引版本 | 1 |
| 索引条目 | 760 |
| Phase 2 机器认证事实 | 285 |

第一次 Neo4j DDL 因多余右花括号失败。该版本被正确标记为 `failed` 并保留审计记录；修正后创建新的 `ready` 版本，没有覆盖失败历史。

当前评测使用的最新成功版本：

```text
20260730T180337-b884da9e
```

### 6.2 Neo4j

| 项目 | 结果 |
|---|---|
| `namespace=jiebang` EvidenceChunk | 38 |
| 向量索引 | `jiebang_evidence_embedding` |
| 状态 | `ONLINE` |
| 查询方式 | Cypher 25 `SEARCH` |

最新索引使用 `text-embedding-3-large` 3072 维向量与 ChromaDB，Collection 为 `jiebang-evidence-e93abd41a75aab10f84a`。`job-skill-evidence-v2` 检索文本包含标准岗位、规范技能名、别名、受控语义说明和原文片段，但引用返回仍保持原文片段。评测器会批量预取去重后的查询向量，避免 120 条样本逐条调用外部 Embedding。

岗位技能事实曾通过 `phase2-machine-validation-v1` 策略补齐：只认证由现有规则抽取器从 MySQL 原始 JD 重新命中、置信度不低于 `0.70`、质量状态为 `accepted/warning` 且未排除的事实。新增 285 条机器认证事实，未通过重新抽取或置信度门槛的事实保持 `unverified`。该阶段性脚本现已移除，后续事实变更统一通过 `/api/v1/skills/facts/reviews`、批量审核和一键同意接口完成并保留审核记录。

## 7. 自动化验证

- 新增 Domain 测试：确定性向量、相似度、稳定 Evidence ID、字符范围、词法分和岗位/技能实体消歧。
- 新增 API 测试：管理员重建、普通用户越权、检索、Evidence 回链、查询审计和无答案。
- 新增评测集测试：50 条近重复负样本、120 条检索样本、类别分布、工程审核字段、开发集冻结和负样本阈值。
- 新增 Phase 2.1 测试：OpenAI Provider 批次与维度、缺 Key 失败、Chroma cosine/Metadata Filter、Chroma API 重建与检索。
- Phase 2 定向回归：`7 passed`。
- Phase 2.1 定向回归：`11 passed`。
- 后端完整回归：`179 passed in 149.07s`。
- Alembic 当前版本：`20260731_0014 (head)`。

## 8. Phase 2 工程评测集

产物：

- `fyz-src/backend/evaluation/phase2_retrieval_golden_set.json`
- `fyz-src/backend/evaluation/phase2_retrieval_report.json`
- `fyz-src/backend/evaluation/phase2_retrieval_report.md`

样本构成：

| 类别 | 数量 |
|---|---:|
| 近重复负样本 | 50 |
| 技能原词查询 | 25 |
| 岗位职责语义改写 | 25 |
| 岗位与技能联合过滤 | 20 |
| 来源与质量过滤 | 15 |
| 冲突过滤拒答 | 15 |
| 语料外拒答 | 20 |

共 170 条样本均已填充工程审核人、审核时间、理由和预期结果，`human_domain_gold=false`。当前真实语料只覆盖：

- 323 条 Evidence。
- 10 个标准岗位。
- 78 个技能。
- 2 个来源平台。

120 条检索样本按标准岗位隔离：development 76、validation 22、test 22。同一标准岗位不会跨分区。最终开发岗位为 `[1,2,5,26,29,32]`，验证岗位为 `[39,64]`，冻结测试岗位为 `[89,123]`；验证与测试岗位在 Retriever 最终调优完成后才冻结并首次评测。

## 9. 评测结果

评测口径与阈值均写入 JSON 报告，逐样本保存期望 Evidence ID、返回 Evidence ID、过滤违规、耗时、索引版本和失败状态。

| 指标 | 结果 | 门槛 | 状态 |
|---|---:|---:|---|
| Recall@5 | 97.06% | >= 85% | 通过 |
| MRR@10 | 100.00% | >= 75% | 通过 |
| Citation Precision@5 | 100.00% | >= 95% | 通过 |
| Top-1 命中率 | 100.00% | >= 80% | 通过 |
| 无答案拒答准确率 | 100% | >= 90% | 通过 |
| 过滤违规率 | 0% | = 0 | 通过 |
| 近重复负样本误报率 | 0% | <= 5% | 通过 |
| 暖态 P95 | 95ms | <= 500ms | 通过 |

明确技能原词、职责语义改写、结构化过滤、冲突过滤和语料外拒答均通过。语义说明使职责改写能够召回对应技能证据，相对分数窗口避免固定 Top-K 用低相关证据补位，`0.30` 无权威语义阈值阻断语料外补答。开发、验证、冻结测试分区门禁均通过，因此 `performance_gate=true`、`coverage_gate=true`、`release_gate=true`。

第一次评测中“职责改写”仍包含技能原词，实体约束修正后曾出现开发集 100% 指标。复核发现该口径不能证明语义召回能力，因此主动改为不含技能规范名的能力表达。扩容后又发现最初测试岗位参与了排序诊断，因此废弃该分区并引入 4 个新岗位重新冻结验证/测试集；既定指标门槛和期望标签均未降低。

## 10. 未完成项

以下事项不应被误报为已完成：

1. 当前没有业务专家双人复核的 Retrieval Golden Set。
2. `text-embedding-3-large` 与 Chroma 真实链路已完成，但尚未建立 API 调用费用、限额和代理可用性的持续监控。
3. Retriever 尚未接入具体 Agent 生成前流程。
4. `agent_claim_citation` 只完成数据契约，Phase 3 才写入真实 Claim 引用。
5. 尚未实现 Admin 检索调试页面。

评测集的补充规模、负样本类型、审核流程和门禁见 [Phase 2 评测集补充与审核方案](./FYZ优化Phase2评测集补充与审核方案.md)。
