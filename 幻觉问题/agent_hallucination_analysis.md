# 智联职引 Agent AI 幻觉风险分析与优化方案

> 分析目标：结合比赛赛题“如何解决招聘数据中的‘时滞’、‘噪声’与‘抄袭’问题，并通过技术手段有效防控 AI 生成内容‘幻觉’的产生，提升图谱构建的科学性”，对项目中所有涉及 Agent、LLM 调用、Prompt 设计、RAG 检索增强、知识图谱构建、多智能体协作、AI 生成内容处理的模块进行代码级审查。

---

# 1. Agent 架构分析

| 模块                                | 代码位置                                                                   | 功能                                                       | 可能幻觉风险                                                                                       |
| --------------------------------- | ---------------------------------------------------------------------- | -------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| **LLM Provider（结构化输出）**           | `fyz-src/backend/app/providers/llm.py:54-153`                          | DeepSeek 结构化 JSON 调用，temperature=0，注入 JSON Schema，失败重试一次 | Schema 约束只保证格式，不保证内容真实；LLM 仍可在合法 JSON 内编造字段值                                                 |
| **Skill Extraction Agent**        | `agent-development/src/jiebang_agents/skill_extraction/agent.py:6-22`  | 在规则抽取后，调用 LLM 补充“规则未识别的明确技能”                             | LLM 补充的新技能未与词典/原文做二次校验，可直接进入 `JobSkillFact`                                                  |
| **Skill Extraction Prompt**       | `agent-development/src/jiebang_agents/skill_extraction/prompt.py:3-10` | 要求“只输出文本中明确出现且可验证的技术技能，不得推测”                             | 仅有软提示，无事实约束机制；模型对“明确出现”理解不一                                                                  |
| **Graph Enrichment Agent（L4/L5）** | `agent-development/src/jiebang_agents/graph_enrichment/agent.py:36-60` | 为已验证 L3 技能补全技术点/知识点                                      | 可生成与 evidence 文本语义不符的 L4/L5 节点，只要 source_ids 存在                                              |
| **Graph Enrichment Prompt**       | `agent-development/src/jiebang_agents/graph_enrichment/prompt.py:3-36` | 要求“每个技术点必须能被输入原文直接支持，引用至少两个不同平台来源”                       | 无自动语义校验，source_ids 可被模型任意关联                                                                  |
| **L45 Standalone Agent**          | `agent-development/l45_agent/agent.py:9-95`                            | 独立 DeepSeek 调用生成 L4/L5，temperature=0.1                   | 输出不强制绑定 source_id；`verify.py` 的置信度只按来源数计算，不看内容                                               |
| **JD Generation Agent**           | `agent-development/src/jiebang_agents/jd_generation/agent.py:46-237`   | 根据岗位名称/技能输入生成可编辑 JD 草稿                                   | `standardized_title` 自由生成；skills 不受词典约束；可生成未经验证的“常见”技能                                       |
| **JD Generation Prompt**          | `agent-development/src/jiebang_agents/jd_generation/prompt.py:8-133`   | 禁止虚构薪资、福利、学历、工作年限                                        | 对“技能是否真实存在/是否匹配岗位”无外部校验                                                                      |
| **Career Planning Agent**         | `agent-development/src/jiebang_agents/career_planning/agent.py:16-177` | 基于简历与目标岗位差距生成学习路径                                        | `ResumeProfile` 中 current_role/years_experience/education 可由 LLM 自由推断；suggested_project 自由生成 |
| **Career Planning Prompt**        | `agent-development/src/jiebang_agents/career_planning/prompt.py:7-38`  | 要求学习步骤必须对应 candidate.gaps，禁止重复 verified_skills           | 无法防止模型为同一 gap 编造不同名称；resources 仅口头约束                                                         |
| **Match Explanation Agent**       | `agent-development/src/jiebang_agents/match_explanation/agent.py:7-53` | 解释确定性匹配快照                                                | evidence_id 被后验过滤，但 explanation 文本与 evidence_text 的语义一致性未校验                                  |
| **Import Service（数据导入）**          | `fyz-src/backend/app/services/import_service.py:51-120`                | 幂等导入 JD，内容指纹去重，交叉验证技能事实                                  | 交叉验证只要求 skill 跨源出现 ≥2 次，不保证该技能真属于该岗位                                                         |
| **Rule Skill Extractor**          | `fyz-src/backend/app/services/skill_extractor.py:132-184`              | 基于技能词典扫描 JD 文本，生成 `JobSkillFact`                         | 软技能/噪声词可能命中；非技术岗位文本中技术词误识别无法自动剔除                                                             |
| **Graph Service（同步与补全）**          | `fyz-src/backend/app/services/graph_service.py:123-218, 357-472`       | L1-L3 确定性构图，L4/L5 候选验证                                   | L1-L3 依赖 `verification_status=verified`，但验证规则未考虑时间衰减；L4/L5 过滤只看 source_id 存在性和置信度数值          |
| **Data Analysis 清洗流水线**           | `data_analysis/scripts/01_merge_clean.py:28-199`                       | URL/指纹/标题+公司相似度三级去重                                      | 未对 JD 正文做 MinHash/SimHash 近重复检测；未做时滞/可信度评分                                                   |
| **Job Standardizer**              | `fyz-src/backend/app/domain/job_standardizer.py:17-63`                 | 规则清洗标题、推断级别/技术栈                                          | 硬编码城市列表和噪声词，对新招聘平台/新工种覆盖不足                                                                   |
| **Skill Dictionary**              | `fyz-src/backend/app/domain/skill_dictionary.py:14-116`                | 标准 IT 技能词典与别名                                            | 词表有限，LLM 补充的新技能可能不在词典中，导致图谱节点不可控                                                             |

---

# 2. AI 幻觉风险清单

| 幻觉类型 | 产生模块 | 触发原因 | 影响 |
|---|---|---|---|
| **事实幻觉：虚构技能** | `skill_service.py:139-164` | LLM 补充的技能 `additions` 只要 `canonical_key` 不在已知集合即被接受；未校验该技能是否真实存在或是否确实在 JD 中出现 | 技能库混入模型“认为合理”但实际不存在的技能，污染 L3 节点 |
| **事实幻觉：错误岗位要求** | `jd_generation/agent.py:111-158` | `LLMGeneratedJDDraft` 的 `requirements`、`skills` 为自由文本数组，未与标准岗位画像或技能词典交叉 | 生成 JD 包含不相关技能或不符合实际的任职门槛 |
| **事实幻觉：虚假岗位画像** | `career_planning/agent.py:76` | `output.resume_profile` 由 LLM 生成，包含 current_role、years_experience、education | 简历解析结果可能包含模型推断的错误个人信息 |
| **关系幻觉：错误技能关联** | `graph_service.py:416-472` | `_filter_verified_completion` 只检查 `source_id` 存在且 ≥2 平台，不检查 tech_point 名称是否与 evidence_text 语义匹配 | 可生成“Java → 必须掌握 → 深度学习”这类无依据关系 |
| **关系幻觉：L4/L5 节点来源造假** | `graph_enrichment/agent.py:44-60` | Schema 要求 `source_ids` 长度 ≥2，但模型可以把任意两个有效 source_id 填到任意 tech_point | 节点被“证据”背书，实际内容与证据无关 |
| **推理幻觉：过度泛化趋势** | `career_planning` 等解释型 Agent | Career Agent 的 explanation 和学习路径可能基于少量样本推断“该岗位未来必须掌握 XX” | 给学生/HR 误导性职业规划建议 |
| **推理幻觉：无依据匹配解释** | `match_explanation/agent.py:15-33` | explanation 文本无约束必须与 `evidence_text` 语义一致；模型可能编造“项目经验丰富”等无法从 evidence 推出的结论 | 匹配解释失去可审计性 |
| **数据污染幻觉：过时技能需求** | `graph_service.py:501-517` | `first_seen_at`/`last_seen_at` 被记录，但未用于权重或过滤；2022 年的 JD 与 2026 年的 JD 同等贡献 | 旧岗位画像拉低图谱时效性 |
| **数据污染幻觉：抄袭 JD 放大技能需求** | `import_service.py:65` / `01_merge_clean.py:86-109` | 内容指纹只能去重完全相同的记录；`dedup_by_similarity` 只比较 title+company，未对 `jd_text` 做 MinHash/SimHash | 大量抄袭/微改 JD 会让某技能被错误标记为高频需求 |
| **数据污染幻觉：噪声职位污染** | `skill_extractor.py:132-184` | 规则抽取器仅按关键词命中，未判断岗位类别是否与技术相关；非技术岗 JD 若出现技术词也会被抽取 | 产生“行政岗位要求 PyTorch”等错误事实 |
| **数据污染幻觉：单平台事实被认证** | `import_service.py:141-145` | `_cross_validate_facts` 的 `source_count` 是“该 skill 在不同 source_document.source 出现的次数”，不是“同一 skill-job 关系跨平台” | 某技能若在同一平台多个岗位出现，可被动通过验证 |

---

# 3. 针对赛题要求的解决方案

| 问题 | 技术方案 | 实现方式（对应模块改造） |
|---|---|---|
| **招聘数据时滞** | **时间感知知识图谱** | 在 `graph_service.py:501-517` 的边属性中增加 `recency_weight`；按 `last_seen_at` 与当前时间差做指数衰减（如半衰期 6 个月），聚合时以时间加权置信度代替简单 max；同步任务增加 `max_posted_at_age_months` 参数过滤过期 JD |
| **招聘数据噪声** | **可信度评估 Agent + 岗位-技能一致性校验** | 新增 `JobSkillConsistencyAgent`，输入岗位标题、JD 文本、抽取技能，输出 `consistency_score`；在 `skill_service.py:_persist_facts` 中只保留 consistency_score ≥ 0.7 的事实；对非技术岗位使用标题分类器预过滤 |
| **招聘 JD 抄袭** | **正文级近重复检测** | 在 `import_service.py:65` 和 `01_merge_clean.py` 中增加 `MinHash`/`SimHash` 对 `jd_text` 计算签名，相似度 ≥ 0.85 且非同一 URL 的记录标记为 `plagiarized` 并降权/剔除 |
| **LLM 事实幻觉** | **RAG + Graph Validation 双层校验** | 对 LLM 生成的每个 L4/L5 节点，先用 Embedding 检索 Top-K evidence 片段，计算生成文本与证据的语义相似度（≥0.75 才保留），再执行现有 source_id 校验；改造 `graph_service.py:_filter_verified_completion` |
| **LLM 关系幻觉** | **关系规则库 + 本体约束** | 在 Neo4j 写入前增加 `Relation Ontology`（如 `TechStack` 只能 `REFINES_TO` `TechPoint`，禁止跨领域 `REQUIRES`）；对新生成关系做共现统计，低于阈值的关系人工审核 |
| **LLM 推理幻觉** | **证据链锁定 + 拒答机制** | 在 `match_explanation` 和 `career_planning` 中，要求每个 explanation 必须引用 evidence_id，并增加 `entailment_check`；无足够证据时返回 `warnings` 并建议人工复核，而不是让模型自由发挥 |
| **数据可信度不足** | **多维度数据评分卡** | 在 `RawJobRecord` 增加 `data_quality_score`（字段完整度 + 来源可信度 + 时间新鲜度 + 去重状态），仅 quality ≥ 0.6 的记录参与 `JobSkillFact` 验证 |
| **LLM 输出无审计** | **Reviewer Agent + Human-in-the-loop** | 新增 `GraphFactCheckerAgent` 对 L4/L5 候选做二次审查；`GraphEnrichmentCandidate` 增加 `review_status`，未人工确认前不写入 Neo4j；关键图谱写入需管理员审批 |

---

# 4. 最终比赛技术路线建议

结合当前代码基础，建议以 **“数据治理 → 证据约束 → 生成后验 → 人机共治”** 四层防线构建低幻觉的岗位技能图谱。

## 4.1 数据层：先把“时滞、噪声、抄袭”挡在图谱外

当前项目已有内容指纹和 URL 去重，但缺少正文级抄袭检测和时间感知机制。

- **时滞**：在 `graph_service.py` 的边聚合中引入时间衰减权重，使旧 JD 对技能关系置信度的贡献随时间下降；同步任务支持按 `posted_at` 过滤近 N 个月数据。
- **噪声**：在 `skill_extractor.py` 的命中逻辑前增加岗位类别预判定，非技术岗位的技术词命中需提高证据阈值；引入 `JobSkillConsistencyAgent` 对抽取结果打分。
- **抄袭**：在导入层和离线清洗层同时增加 `MinHash`/`SimHash` 近重复检测，抄袭 JD 不仅去重，还要对对应技能事实降权。

## 4.2 规则层：L1-L3 坚持“无 LLM 生成”

当前 `GraphService.sync()` 已经做到 L1-L3 只读取 `verification_status=verified` 的 `JobSkillFact`，这是项目最坚实的防幻觉基础。

- 继续保持 **MySQL 事实源、Neo4j 读模型** 的架构。
- 强化 `JobSkillFact` 的验证规则：把“skill 跨平台出现次数”改为“skill-job 关系跨平台出现次数”，避免单平台抄袭泛滥导致的事实误认证。
- 对 `skill` 表增加 `canonical_key` 严格管控，LLM 补充的新技能必须先进入待审核池，不能直接创建标准节点。

## 4.3 生成层：Agent 输出必须经过“证据绑定 + 语义校验”

当前 L4/L5 Agent 已有 source_id 和置信度门槛，但缺少内容级校验。

- **证据绑定**：要求每个 L4/L5 节点不仅引用 source_id，还要给出对应 evidence 片段；后端用 Embedding/向量相似度校验生成文本与证据的语义一致性。
- **RAG 增强**：把 JD evidence 向量化存入向量库，Agent 生成前先检索 Top-K 相关片段，生成后做“检索-生成”一致性检查。
- **Reviewer Agent**：新增 `GraphFactCheckerAgent`，对 L4/L5 候选做二次审查，标记可疑节点，未人工确认不入图。

## 4.4 应用层：Agent 只生成“可编辑草稿”，不直接发布

当前 JD Generation、Career Planning、Match Explanation 都已经是“草稿/解释”定位，这点很好。

- **JD 生成**：`standardized_title` 和 `skills` 必须回填时与标准岗位画像/技能词典做交叉校验，不一致时高亮提示。
- **职业规划**：`ResumeProfile` 中的推断字段必须标记为“AI 推断，请核对”；`learning_plan` 中的 skill 必须能在目标岗位 gap 中找到。
- **匹配解释**：explanation 文本必须能通过 `evidence_id` 反查到证据，无证据支持的解释直接丢弃并提示。

## 4.5 最终技术路线图

```
多源招聘数据
    ↓
[MinHash/SimHash 去重] → [时滞过滤] → [质量评分]
    ↓
规则技能抽取 + 一致性校验 → JobSkillFact（verified/unverified）
    ↓
确定性聚合 → L1 Job / L2 SkillArea / L3 TechStack（MySQL → Neo4j）
    ↓
Top 技能 → RAG 检索 evidence → L4/L5 Agent 生成
    ↓
Reviewer Agent 语义校验 + source_id 校验 + 人工审核
    ↓
写入 Neo4j 读模型
    ↓
JD/职业规划/匹配解释 Agent（仅草稿/解释，不直接写事实）
```

**一句话总结**：把当前已经建立的“规则优先、MySQL 事实源、Neo4j 读模型、候选后验证”架构继续加固，在数据入口增加时滞/噪声/抄袭治理，在 Agent 生成层增加 RAG 证据绑定和语义校验，在关键写入点增加 Reviewer Agent 和人机确认，即可系统性降低 AI 幻觉，提高岗位技能图谱的科学性。
