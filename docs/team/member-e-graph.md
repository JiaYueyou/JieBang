# 成员 E：知识图谱与分级抽取

## 1. 职责

负责标准岗位、五级能力树、MySQL 到 Neo4j 同步、图谱查询、
DeepSeek 辅助 L4/L5 候选生成和证据门槛。

不负责爬虫采集、JTT 页面和通用 Agent Memory。

## 2. 当前基线

- MySQL 已有标准岗位、来源、快照、同步批次和 enrichment candidate 表。
- GraphService 支持 `full/incremental` 同步。
- Neo4j 使用 `namespace=jiebang`，存在 panorama、expand、search、path、tree。
- FYZ GraphView 已走真实 HTTP Provider。
- 已有 DeepSeek L4/L5 结构化输出与双来源、`0.75` 置信度约束。

## 3. 五级模型

```text
L1 Job
→ L2 SkillArea
→ L3 TechStack
→ L4 TechPoint
→ L5 KnowledgePoint
```

- L1-L3 只使用可验证的岗位、技能事实和确定性标准化结果。
- L4/L5 模型输出先进入 candidate，不直接成为事实。
- 每个正式关系保留来源、置信度、快照和生成/验证方式。

## 4. 4 周 MVP

### 第 1 周：数据与约束

- 核对 ORM、migration、Neo4j 节点 ID、约束和索引。
- 固化标准岗位归一化、技术栈和层级规则。
- 建立图谱数据字典和 Cypher 命名规范。

### 第 2 周：同步

- 验证全量与增量同步幂等。
- 全量清理只作用于 `namespace=jiebang`。
- 完成失败批次、快照、节点/边/事实计数和恢复行为。

### 第 3 周：L4/L5

- 对 Top 技能生成 TechPoint/KnowledgePoint 候选。
- 校验证据 ID、来源独立性、置信度和前置关系。
- 提供候选审核/拒绝/重跑的数据接口。

### 第 4 周：查询与联调

- 优化 panorama、job tree、search、expand 和 path。
- 与成员 A/B 完成真实图谱和学习路径联调。
- 建立 1000 节点内交互和三层查询的基线指标。

## 5. 后 8 周优化

- W5-W6：时间快照、版本对比、来源钻取和变化检测。
- W7-W8：实体消歧、候选评测和人工审核闭环。
- W9-W10：Cypher 性能、索引、分页/截断和大图可视化策略。
- W11-W12：指标报告、可解释演示、灾难重建和比赛数据快照。

## 6. 交付与验收

- MySQL 删除 Neo4j 后可重新构建一致读模型。
- 重复 incremental 不产生重复业务节点和关系。
- panorama 不混入 SourceDocument、GraphSnapshot 等辅助节点。
- 主能力树只沿图谱业务关系遍历，不被证据节点放大。
- 未验证 L4/L5 不进入正式图谱。

## 7. 验证

```powershell
cd fyz-src\backend
alembic upgrade head
python -m pytest test -q
python diagnose_neo4j.py
```

数据库变更还必须完成临时库：

```powershell
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

## 8. Git 建议

- 分支：`feat/e-graph-enrichment-review`、`fix/e-tree-traversal`
- 提交：`feat(graph): add evidence-gated l5 candidates`
- Schema、migration、服务、API 和测试尽量在同一可回滚 PR 中。

## 9. 主要风险

- 把 Neo4j 变成第二事实库；
- 全量同步误删其他业务数据；
- 大模型输出没有证据就进入正式层；
- 查询遍历辅助关系导致性能和可视化混乱；
- API 节点类型或状态枚举与前端不兼容。