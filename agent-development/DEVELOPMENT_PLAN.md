# Agent 开发计划

## 阶段 0：契约冻结与现状验证（已完成）

产出：`AGENT_API_CONTRACT.md`、目录约定、接口字段评审。

验收：后端、前端和产品确认 Agent 清单、字段语义、任务状态、人工确认边界；未确认的产品行为不进入实现。

## 阶段 1：夯实 JD Generation 基线（进行中）

1. 已将 JD、技能补全、图谱补全的 Agent 主程序、Prompt 和输出 Schema 迁移到 `agent-development/src/jiebang_agents/`；后端通过目录加载适配接入。
2. 为请求、LLM JSON、模板降级、运行查询和 Celery eager 模式补齐契约测试。
3. 在岗位编辑页接入创建、轮询、草稿预览、警示和“人工确认发布”闭环。

验收：模型不可用时仍返回可编辑模板草稿；不产生自动发布；每次运行有 `prompt_version`、模型、耗时、错误和结构化输出审计。

## 阶段 2：技能抽取 Agent 统一化（P0）

L4/L5 图谱补全的细化方案见 `SKILL_L45_COMPLETION_PLAN.md`。

1. 定义 `SkillExtractionRequest/Output` 与路由，统一同步规则抽取和异步 LLM 补全入口。
2. 接入现有技能词典归一化、证据字段和验证状态；区分候选结果与已验证事实。
3. 实现幂等任务、Provider Mock、无效 JSON、重复技能、无证据和词典未命中测试。

验收：相同来源重复提交不产生重复正式事实；未经验证的技能不进入 Neo4j 正式层。

## 阶段 3：匹配解释与职业规划（P1，首版已完成）

详细方案见 `CAREER_PLANNING_AGENT_PLAN.md`。

1. 先完成/核验确定性 `match_record`、技能差距和来源证据查询。
2. 实现 Match Explanation Agent；输入只接受持久化的 `match_id`，输出与快照分数强校验。
3. 实现 Career Planning Agent；复用已验证的差距，不让模型虚构技能、课程或周期。

验收：改变模型输出不会改变匹配分数；每条解释可定位到简历、岗位或图谱证据；学习资源可追溯。

## 阶段 4：新兴岗位复核（P1）

1. 固化分析服务的趋势、聚类和数据源快照输入。
2. 实现 Emerging Job Review Agent，生成候选说明和待确认问题。
3. 对接现有人工 `approve/reject` 决策、审计和前端复核页。

验收：Agent 不能绕过人工审核创建正式岗位；候选说明中每项趋势/技能结论都有来源。

## 阶段 5：质量、可观测性与发布准备（贯穿）

- 每个 Agent 具备 Schema、Service、API、Celery、Provider Mock 和权限测试。
- 将 `agent_type`、状态、耗时、重试次数、降级率纳入管理端监控，禁止记录敏感原文。
- 为每个 Agent 准备正常、空输入、无资源、越权、超时、限流、非法 JSON、无证据八类用例。
- 前端按接口契约生成/校验类型；接口变更先更新本目录文档，再同步测试和消费者。

## 推荐实现顺序

```text
JD Generation 稳定化
        ↓
Skill Extraction Agent
        ↓
确定性匹配/差距数据完备
        ↓
Match Explanation + Career Planning
        ↓
Emerging Job Review
```

每完成一个阶段，执行受影响的后端 pytest、前端类型检查/构建、`git diff --check`，并以 Provider Mock 验证结构化输出，不调用真实收费模型。
