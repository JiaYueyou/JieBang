# Skill L4/L5 Completion Agent 开发计划

## 目标

基于已验证的五层图谱上游上下文生成深层候选：

```text
L1 Job → L2 SkillArea → L3 TechStack → L4 TechPoint → L5 KnowledgePoint
```

Agent 只生成 L4/L5 candidate，不直接写正式图谱。MySQL 保留候选、证据、置信度和 AgentRun；只有通过确定性证据门槛的候选才进入可重建的 Neo4j 读模型。

## 输入契约

- `job_directions[]`：与当前 L3 技术栈存在已验证事实关系的标准岗位名称。
- `skill_area`：由技能分类确定性映射出的 L2 名称。
- `tech_stack`：当前 L3 技术栈名称。
- `evidence[]`：`source_id`、独立来源名 `source`、原文证据 `text`。

## 输出契约

- L4 `tech_points[]`：名称、说明、置信度、来源 ID。
- L5 `knowledge_points[]`：名称、说明、难度、前置知识、置信度、来源 ID。
- 输出继续兼容现有 `GraphEnrichmentOutput`，避免破坏图谱同步消费者。

## 确定性门槛

1. 每个 L4/L5 置信度不低于 `0.75`。
2. 引用 ID 必须全部存在于本次输入证据中。
3. 每个 L4/L5 必须覆盖至少两个不同 `source`，不能只用同一平台的两条记录。
4. L5 必须挂在通过门槛的 L4 下。
5. 过滤后的结构写入 candidate；模型原始结构仅留在 `AgentRun` 审计。
6. 没有合格 L4 时 candidate 保持 `unverified`，不得进入 Neo4j。

## 实现步骤

1. 扩充独立 Agent 输入 Schema 和上下文 Prompt。
2. 提供 `SkillGraphCompletionAgent`，保留 `GraphEnrichmentAgent` 别名。
3. 后端从已验证事实查询 L1 岗位方向，并传入 L2/L3 上下文。
4. 在后端候选写入前执行独立来源、允许 ID 和置信度过滤。
5. 增加 Agent 单测与后端证据门槛回归测试。

## 验收

- 独立 Agent 不依赖 FastAPI、SQLAlchemy、Celery 或 Neo4j。
- 旧图谱同步入口及 `full | incremental` 行为不变。
- 同源双文档、虚构 source_id、低置信度节点均不能进入 verified candidate。
- 合格 L4/L5 能保留岗位方向和证据上下文，并由现有同步流程写入图谱。
