# Agent 开发工作区

本目录是 `feat/fyz-job-agent` 分支上 Agent 需求、接口契约、Prompt、运行时代码和验收用例的独立工作区。后端只保留加载适配、HTTP/进程内异步编排和审计持久化；Agent 执行不依赖 Redis/Celery。本目录不放密钥、真实简历或模型原始响应。

## 当前交付

- [接口契约](AGENT_API_CONTRACT.md)：Agent 范围、前后端字段、HTTP 接口、异步状态、审计和错误约定。
- [开发计划](DEVELOPMENT_PLAN.md)：按依赖关系拆分的实现顺序、每阶段产出和验收标准。
- [当前下一阶段](DEVELOPMENT_PLAN.md#下一阶段career-planning-消费匹配快照)：让职业规划优先复用已持久化的匹配差距与证据。

## 目录约定

```text
agent-development/
├── README.md
├── AGENT_API_CONTRACT.md
├── DEVELOPMENT_PLAN.md
├── architecture/             # 运行时分层与依赖方向
├── prompts/                 # Prompt 设计说明与评审记录
├── src/jiebang_agents/      # 可独立导入的 Agent Python 包
├── tests/                   # 独立包单元测试
├── pyproject.toml           # 独立包元数据与依赖
└── test-cases/              # Provider Mock、契约测试和回归样例
```

可执行 Agent 位于 `agent-development/src/jiebang_agents/`。后端通过 `fyz-src/backend/app/core/agent_runtime.py` 加载该目录，并可用 `JIEBANG_AGENT_PATH` 覆盖部署路径。新增 Agent 前先更新接口契约与测试样例；接口字段或 Prompt 输出 Schema 变更时必须提升 `prompt_version`，并保留旧运行记录的可读性。

> **数据库版本变更**：简历持久化与匹配解释引入 revision `20260712_0006`。更新本分支后，先在 `fyz-src/backend` 执行 `alembic upgrade head`，再重启 Uvicorn；仅更新前端或未重启旧进程会导致 `/api/v1/talents` 仍返回 404。

## 当前能力状态

| 能力 | 状态 | 说明 |
| --- | --- | --- |
| JD Generation | 已完成输入建议增强 | 岗位名称自动补全、异步任务、审计、结构化草稿和规则模板降级可用 |
| Skill Extraction | 部分完成 | 岗位技能抽取与补全可用，统一文本/简历公共入口待开发 |
| Skill L4/L5 Completion | 已完成首版 | L1-L3 上下文、双来源和 `0.75` 门槛可用 |
| Career Planning | 已完成首版 | 文件文本解析、即时确定性推荐、学习路径和 FYZ 联调可用 |
| Match Explanation | 已完成首版 | 私有简历、确定性快照、证据引用、模板降级和 FYZ 联调可用 |
| Emerging Job Review | 待开发 | 在匹配解释闭环后实施 |
