# FYZ 优化 Phase 2 评测集补充与审核方案

> 编制日期：2026-07-31
>
> 适用阶段：Phase 2 RAG 证据层与混合检索 MVP
>
> 当前原则：现有 100 条工程审核种子保留为回归集；新增样本单独版本化，不修改既有预期结果来迎合算法。

> 实施状态：已生成并工程审核 50 条近重复负样本和 120 条检索样本。当前覆盖 10 个标准岗位、78 个技能和 2 个来源，已按岗位形成 development/validation/test；`human_domain_gold=false`，Phase 2 工程 `release_gate=true`。

## 1. 为什么必须补充

现有评测集可以验证精确身份重复、近重复正样本、时效边界和 Agent 拒答边界，但存在两个缺口：

1. 近重复部分缺少“文本相似但业务事实不同”的负样本，无法测量误报率。
2. 尚未形成以 `expected_evidence_ids`、过滤条件和无答案边界为核心的检索评测集，无法计算 Recall@K、MRR 和引用准确率。

因此，现有 100 条集合继续冻结为 `phase0-golden-v1`；Phase 2 新建 `phase2-retrieval-golden-v1`，两者分别报告，禁止合并成一个模糊的“总体准确率”。

## 2. 建议新增样本

### 2.1 近重复负样本 50 条

| 类型 | 数量 | 示例边界 |
|---|---:|---|
| 同模板、不同岗位 | 12 | Python 后端与数据分析都包含通用公司介绍 |
| 同技能、不同职责 | 10 | Java 平台研发与 Java 测试开发 |
| 同岗位、不同公司事实 | 8 | 薪资、城市、团队和职责不同，不应合并来源事实 |
| 历史岗位重新发布 | 8 | 外部 ID 改变且职责发生实质变化 |
| 大段公共福利文本 | 6 | 福利相同但岗位正文不同 |
| 跨语言或缩写相似 | 6 | AI Engineer 与算法平台工程师的部分术语重叠 |

每条必须标注：

- `duplicate=false`
- `forbidden_group_with`
- 关键差异证据
- 不允许合并的业务理由

验收指标增加：

- 近重复正样本召回率 `>= 0.90`
- 近重复负样本误报率 `<= 0.05`
- 精确身份重复准确率 `= 1.00`

### 2.2 RAG 检索样本 120 条

| 类型 | 数量 | 核心标签 |
|---|---:|---|
| 技能原词查询 | 25 | `expected_evidence_ids` |
| 岗位职责自然语言改写 | 25 | `expected_evidence_ids`、`minimum_recall_k` |
| 岗位与技能联合过滤 | 20 | `standard_job_id`、`skill_ids` |
| 来源、时间与质量过滤 | 15 | `filters`、`forbidden_evidence_ids` |
| 冲突或单来源证据 | 15 | `answer_mode=insufficient_evidence` |
| 无答案与越界问题 | 20 | `expected_evidence_ids=[]`、拒答原因 |

建议样本结构：

```json
{
  "id": "RET-001",
  "query": "Python 后端岗位通常要求哪些 API 框架？",
  "filters": {
    "standard_job_id": 12,
    "minimum_quality_score": 0.75
  },
  "expected_evidence_ids": ["ev_..."],
  "acceptable_evidence_ids": ["ev_..."],
  "forbidden_evidence_ids": ["ev_..."],
  "answer_mode": "grounded",
  "minimum_recall_k": 5,
  "review": {
    "status": "pending",
    "reviewer": null,
    "note": null
  }
}
```

## 3. 数据划分

样本按标准岗位分组后划分，避免同一岗位的改写同时落入开发集和测试集：

- 开发集 60%：允许用于调参。
- 验证集 20%：用于确定权重与阈值。
- 冻结测试集 20%：发布前运行，开发过程中不可读取标签调参。

近重复组必须整体进入同一数据分区，防止来源泄漏。

## 4. 审核流程

1. 工程人员生成候选和证据回链，不直接批准标签。
2. 第一位审核人确认岗位、技能、来源和时间过滤是否正确。
3. 第二位审核人只处理冲突样本和无答案边界。
4. 分歧进入仲裁清单，不允许用多数投票自动覆盖。
5. 只有全部样本包含审核人、时间、意见和来源后，才设置 `release_gate=true`。

如果暂时没有业务专家：

- 可以标记为 `engineering_reviewed` 并用于开发回归。
- 必须保持 `human_domain_gold=false`。
- 不得将工程审核结果用于对外宣称业务准确率。

## 5. Phase 2 指标门禁

| 指标 | 门槛 |
|---|---:|
| Recall@5 | `>= 0.85` |
| MRR@10 | `>= 0.75` |
| 引用准确率 | `>= 0.95` |
| 无答案拒答准确率 | `>= 0.90` |
| 过滤违规率 | `= 0` |
| 近重复组重复占位率 | `<= 0.05` |
| 检索 P95（不含 LLM） | `<= 500ms` |

报告必须同时给出样本数、失败 ID 和索引版本，不能只给百分比。

## 6. 实施顺序

1. 从真实 MySQL 证据生成候选 Retrieval Golden Set，但不自动写期望标签。
2. 增加结构校验器，拒绝缺少 Evidence ID、来源或审核字段的样本。
3. 完成首轮工程审核，冻结开发/验证/测试分区。
4. 增加 `evaluate_phase2_retrieval.py`，输出 JSON 和 Markdown。
5. 在 Retriever 权重调整后只更新模型/索引版本，不修改冻结测试标签。
6. 业务专家到位后进行第二轮复核并升级数据集版本。

## 7. 已执行结果

- Golden Set：`fyz-src/backend/evaluation/phase2_retrieval_golden_set.json`
- JSON 报告：`fyz-src/backend/evaluation/phase2_retrieval_report.json`
- Markdown 报告：`fyz-src/backend/evaluation/phase2_retrieval_report.md`
- 工程审核：170/170 已填充，0 条驳回；属于同一工程审核方完成，不等同于独立双人复核。
- 数据分区：development 76、validation 22、test 22，标签已冻结，同一岗位不跨分区。
- 覆盖：323 条 Evidence、10 个标准岗位、78 个技能、2 个来源。
- 近重复负样本误报率：0%。
- 最新 Chroma / `text-embedding-3-large` 检索：Recall@5 97.06%；MRR@10 100%；引用准确率 100%；Top-1 100%；拒答准确率 100%；过滤违规率 0%；暖态 P95 95ms。
- 旧确定性哈希基线的主要失败面是不含技能规范名的职责语义改写；语义索引、受控技能说明和相对分数窗口已使性能门禁通过。

当前性能、覆盖和工程发布门禁均通过。验证岗位 `[39,64]`、冻结测试岗位 `[89,123]` 在最终 Retriever 调优后引入；后续更新索引时不得依据冻结测试失败修改期望标签。业务专家双人复核完成前仍保持 `human_domain_gold=false`。
