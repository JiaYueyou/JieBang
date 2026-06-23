# 成员 C：Agent 工程

## 1. 职责

负责四类 Agent 能力：

- JD 生成；
- 简历解析；
- 人岗匹配解释；
- 转岗规划。

同时负责 Prompt、RAG、Memory、结构化输出、引用证据、评测和幻觉防控。
不负责两套前端页面、爬虫采集和 Neo4j 底层 CRUD。

## 2. 当前基线

- 后端已有 DeepSeek Provider、技能抽取和图谱 L4/L5 补全调用。
- DeepSeek 未配置时已有规则降级。
- 当前尚无统一 Agent 运行记录、Prompt 版本库、Memory 边界和四类业务 Agent API。
- MySQL 已具备来源、技能事实和 enrichment candidate 等可复用数据。

## 3. 设计边界

- RAG 只检索 MySQL 已验证事实和 Neo4j 可追溯图谱，不新增独立向量数据库。
- MySQL 是事实来源；模型输出默认是建议或候选。
- 所有 Agent 返回 Pydantic 结构化结果，禁止调用方解析自由文本。
- 每个结论携带 `evidence_ids`、`confidence`、`model` 和 `prompt_version`。
- Memory 只保存必要用户偏好和任务摘要，不保存原始简历全文到无边界长期记忆。

## 4. 4 周 MVP

### 第 1 周：统一 Agent 基础

- 定义 AgentRun、PromptVersion、EvidenceRef 和结构化错误约定。
- 封装超时、重试、JSON 校验、Token 预算和无密钥降级。
- 建立 Prompt 文件目录和版本规则。

### 第 2 周：JD 与简历

- JD 生成：输入岗位、级别、技能事实，输出职责、必备技能、加分技能和引用。
- 简历解析：输出个人信息、经历、项目、教育和技能，保留原文位置证据。
- 处理空文档、扫描件、字段冲突和不确定值。

### 第 3 周：匹配解释

- 评分由确定性规则/图谱计算，Agent 只解释已计算结果。
- 输出匹配优势、缺口、风险、证据和可执行建议。
- 禁止模型凭空增加候选人经历或岗位要求。

### 第 4 周：转岗规划

- 输入当前能力、目标岗位和时间约束。
- 输出分阶段学习目标、前置关系、项目建议和验证方式。
- 完成四类 Agent API 契约、测试样例和演示数据。

## 5. 后 8 周优化

- W5-W6：小规模人工标注评测集、Prompt A/B 和失败案例库。
- W7-W8：RAG 排序、证据冲突处理、Memory 生命周期和隐私删除。
- W9-W10：成本、延迟、缓存、并发和多模型降级。
- W11-W12：可观测性、评测报告、演示解释和比赛答辩材料。

## 6. 幻觉防控验收

- 无证据时明确返回“不足以判断”，不能补写事实。
- 匹配事实必须能回指简历片段、JD 或图谱来源。
- 图谱 L4/L5 正式内容必须至少两个独立来源且置信度不低于 `0.75`。
- 模型输出 Schema 校验失败时重试一次，仍失败则结构化降级。
- DeepSeek 超时不得回滚已确认的规则结果。

## 7. 测试

- Provider 单元测试：正常、超时、HTTP 错误、非法 JSON、空 Key。
- Agent 合约测试：结构、证据、置信度和版本字段。
- 幻觉测试：提示注入、无证据、冲突证据和越权信息。
- 回归测试：固定样本与 Prompt 版本对比。

```powershell
cd fyz-src\backend
python -m pytest test -q
```

## 8. Git 建议

- 分支：`feat/c-agent-runtime`、`feat/c-match-explanation`
- 提交：`feat(agent): add evidence-backed match explanation`
- Prompt、Schema、测试和文档必须在同一 PR 中提交。

## 9. 主要风险

- Agent 直接修改事实库；
- RAG 检索未验证候选并当作事实；
- Prompt 改动没有版本和回归评测；
- 简历敏感数据进入日志或长期 Memory；
- 解释文本与实际评分算法不一致。