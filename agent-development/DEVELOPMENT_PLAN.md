# Agent 开发计划

## 阶段 0：契约冻结与现状验证（已完成）

产出：`AGENT_API_CONTRACT.md`、目录约定、接口字段评审。

验收：后端、前端和产品确认 Agent 清单、字段语义、任务状态、人工确认边界；未确认的产品行为不进入实现。

## 阶段 1：夯实 JD Generation 基线（已完成）

1. 已将 JD、技能补全、图谱补全的 Agent 主程序、Prompt 和输出 Schema 迁移到 `agent-development/src/jiebang_agents/`；后端通过目录加载适配接入。
2. 为请求、LLM JSON、模板降级、运行查询和 Celery eager 模式补齐契约测试。
3. 在岗位编辑页接入创建、轮询、草稿预览、警示和“人工确认发布”闭环。

验收：模型不可用时仍返回可编辑模板草稿；不产生自动发布；每次运行有 `prompt_version`、模型、耗时、错误和结构化输出审计。

## 阶段 2：技能抽取 Agent 统一化（P0，部分完成）

L4/L5 图谱补全的细化方案见 `SKILL_L45_COMPLETION_PLAN.md`。

1. 定义 `SkillExtractionRequest/Output` 与路由，统一同步规则抽取和异步 LLM 补全入口。
2. 接入现有技能词典归一化、证据字段和验证状态；区分候选结果与已验证事实。
3. 实现幂等任务、Provider Mock、无效 JSON、重复技能、无证据和词典未命中测试。

当前状态：岗位技能规则抽取、LLM 补全、运行审计以及 L4/L5 独立 Agent 已完成；统一的 `/agents/skill-extractions` 文本/简历公共入口和对应异步任务协议仍待实现。

验收：相同来源重复提交不产生重复正式事实；未经验证的技能不进入 Neo4j 正式层。

## 阶段 3：匹配解释与职业规划（P1，首版已完成）

详细方案见 `CAREER_PLANNING_AGENT_PLAN.md`。

1. 先完成/核验确定性 `match_record`、技能差距和来源证据查询。
2. 实现 Match Explanation Agent；输入只接受持久化的 `match_id`，输出与快照分数强校验。
3. 实现 Career Planning Agent；复用已验证的差距，不让模型虚构技能、课程或周期。

当前状态：简历原文件私有保存与鉴权下载、解析结果/技能/匹配快照/证据持久化、确定性匹配服务、独立 Match Explanation Agent、异步 Career/Match 任务、模板降级及 FYZ 页面联调均已完成。Career Planning 仍保留即时文本分析兼容入口，下一步改为优先消费已保存匹配快照。

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

## 阶段 3 已交付：确定性匹配与 Match Explanation

1. 已新增 `resume`、`resume_parse_result`、`resume_skill`、`match_record` 和 `match_evidence` 模型及 Alembic migration。
2. 把当前职业规划中的临时技能覆盖率计算抽成统一 `MatchingService`，保存算法版本、分数快照、已具备技能、缺口和证据引用。
3. 提供简历创建/查询、匹配任务创建、匹配结果查询接口；保持分数由确定性服务计算。
4. 在独立包实现 `MatchExplanationAgent`，输入只能使用已保存 `match_id` 和快照，输出优势、差距、风险、面试建议与引用证据。
5. 将 Career Planning 改为优先消费持久化匹配快照，保留当前文本即时分析入口作为兼容模式。
6. 已联调 FYZ Matching/MatchingDetail 的上传、列表、下载和解释；JTT 后续复用相同的简历与匹配接口。

## 下一阶段：Career Planning 消费匹配快照

1. 为 Career Planning 增加 `match_id` 输入模式，优先读取持久化技能差距和证据。
2. 保留当前 `resume_text` 即时分析入口作为兼容模式，并明确两种模式的响应来源。
3. 将学习路径中的技能逐项绑定 `match_evidence`，补充资源来源和人工确认状态。
4. 完成权限、无匹配记录、旧算法版本、模型降级与快照一致性回归测试。

验收：相同简历和岗位在同一算法版本下结果可复现；改变模型输出不改变分数；每条解释能回指简历片段、岗位技能或图谱事实；模型不可用时匹配事实仍可查询。

## 后续推荐实现顺序

```text
Career Planning 消费匹配快照
        ↓
Emerging Job Review
```

每完成一个阶段，执行受影响的后端 pytest、前端类型检查/构建、`git diff --check`，并以 Provider Mock 验证结构化输出，不调用真实收费模型。
