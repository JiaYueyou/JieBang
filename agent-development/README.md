# Agent 开发工作区

本目录是 `feat/fyz-job-agent` 分支上 Agent 需求、接口契约、Prompt、运行时代码和验收用例的独立工作区。后端只保留加载适配、HTTP/Celery 编排和审计持久化；本目录不放密钥、真实简历或模型原始响应。

## 当前交付

- [接口契约](AGENT_API_CONTRACT.md)：Agent 范围、前后端字段、HTTP 接口、异步状态、审计和错误约定。
- [开发计划](DEVELOPMENT_PLAN.md)：按依赖关系拆分的实现顺序、每阶段产出和验收标准。

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
