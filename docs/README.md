# JieBang 文档中心

本文档是项目资料的统一索引。根 [README](../README.md) 用于首次上手，
这里用于开发过程中按主题查找详细说明。

> 文档类型：现行索引
> 状态：现行
> 核验日期：2026-08-12
> 当前实现、测试结果与已知缺口统一见 [当前实现状态](implementation-status.md)。

## 必读

| 文档 | 阅读时机 |
| --- | --- |
| [当前实现状态](implementation-status.md) | 判断功能已实现、部分实现、占位或历史时 |
| [技术文档状态登记表](document-status-register.md) | 判断每份技术文档是否仍是当前依据时 |
| [项目需求](requirements.md) | 评估功能是否符合赛题和验收目标时 |
| [开发规范](dev-spec.md) | 新增 API、数据库、代码或公共类型前 |
| [Git 协作指南](git-workflow.md) | 创建分支、提交和发起 PR 前 |
| [仓库安全](repository-security.md) | 配置密钥、处理生成文件或安全事故时 |
| [统一文档规范](documentation-standard.md) | 新增或修改需求、接口、迁移和 Agent 文档时 |

## 环境与运行

- [数据库、数据导入与运行指南](database-and-runtime.md)
- [完整数据迁移脚本](../fyz-src/backend/scripts/DATABASE_TRANSFER.md)：当前 0017 快照与
  0020 head 不兼容，处于阻塞状态，仅供修复迁移包时参考。
- [后端脚本清单](../fyz-src/backend/scripts/README.md)：当前受支持的迁移、维护和
  工程评测入口，以及已移除旧脚本的替代路径。
- [后端专项说明](../fyz-src/backend/README.md)
- [JTT 独立后端早期说明](../jtt-src/backend/backend.md)：当前代码已有 8 组路由，但本文部分技术选型与接口已漂移。
- [JTT 求职者端前端](../jtt-src/frontend/README.md)
- [离线数据分析配置](../data_analysis/README.md)
- [AI 助手独立服务（JTT 求职端）](../jtt-src/ai-assistant/README.md)

## 智能体

- [智能体产品需求文档（完整版）](../jtt-src/agent.md)
- [智能体前端实现文档（JTT 求职端）](../jtt-src/zyq-agent.md)

## 接口

- [静态 API 参考](api-reference.md)
- FYZ 本地 Swagger：`http://localhost:8000/docs`
- FYZ 本地 ReDoc：`http://localhost:8000/redoc`
- FYZ OpenAPI JSON：`http://localhost:8000/openapi.json`

JTT 是另一套 FastAPI 应用，启动后也在其所选端口提供 `/docs`；不要把 FYZ 静态接口摘要
当作 JTT 契约。静态文档用于协作阅读，各 FastAPI 实例的 OpenAPI 是其运行时接口最终来源。
任何接口变更必须同时更新 Schema、测试、前端类型和静态参考。

## 历史分工计划

以下文档用于追溯早期职责与任务拆分，不代表当前完成状态。

| 成员 | 职责 | 指南 |
| --- | --- | --- |
| A | FYZ 管理与决策端全栈 | [打开](team/member-a-fyz-fullstack.md) |
| B | JTT 求职者端全栈 | [打开](team/member-b-jtt-fullstack.md) |
| C | Agent 工程 | [打开](team/member-c-agent.md) |
| D | 爬虫与数据标准化 | [打开](team/member-d-crawler.md) |
| E | 知识图谱与分级抽取 | [打开](team/member-e-graph.md) |
| F | 平台集成与质量保障 | [打开](team/member-f-platform.md) |

## 架构与规划

本节均为设计或计划材料。实现差异以 [当前实现状态](implementation-status.md) 和运行时代码为准。

- [全栈实施计划](../fyz-src/docs-plans/FULLSTACK_PLAN.md)
- [五级能力图谱架构](../fyz-src/docs-plans/GRAPH_ARCHITECTURE.md)
- [Agent 开发工作区](../agent-development/README.md)：独立运行包、接口契约、Prompt 与测试。
- [L4/L5 补全方案](../agent-development/SKILL_L45_COMPLETION_PLAN.md)
- [职业规划 Agent 方案](../agent-development/CAREER_PLANNING_AGENT_PLAN.md)
- [前端设计说明](../fyz-src/docs-plans/FRONTEND_DESIGN.md)
- [原开发计划](dev-plan.md)：历史参考，实际目录和分工以当前 README 为准。

## 竞赛材料

- [赛题需求整理](requirements.md)
- `analy_orig_ques/`：原始图片、音频、文档及清洗后的文本材料。
- `resume.txt`：阶段性整理材料，不作为代码契约。
