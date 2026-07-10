# JieBang 文档中心

本文档是项目资料的统一索引。根 [README](../README.md) 用于首次上手，
这里用于开发过程中按主题查找详细说明。

## 必读

| 文档 | 阅读时机 |
| --- | --- |
| [项目需求](requirements.md) | 评估功能是否符合赛题和验收目标时 |
| [开发规范](dev-spec.md) | 新增 API、数据库、代码或公共类型前 |
| [Git 协作指南](git-workflow.md) | 创建分支、提交和发起 PR 前 |
| [仓库安全](repository-security.md) | 配置密钥、处理生成文件或安全事故时 |
| [统一文档规范](documentation-standard.md) | 新增或修改需求、接口、迁移和 Agent 文档时 |

## 环境与运行

- [数据库、数据导入与运行指南](database-and-runtime.md)
- [完整数据迁移脚本](../fyz-src/backend/scripts/DATABASE_TRANSFER.md)
- [后端专项说明](../fyz-src/backend/README.md)
- [离线数据分析配置](../data_analysis/README.md)

## 接口

- [静态 API 参考](api-reference.md)
- 本地 Swagger：`http://localhost:8000/docs`
- 本地 ReDoc：`http://localhost:8000/redoc`
- OpenAPI JSON：`http://localhost:8000/openapi.json`

静态文档用于协作阅读，FastAPI OpenAPI 是当前运行时接口的最终来源。
任何接口变更必须同时更新 Schema、测试、前端类型和静态参考。

## 六人开发计划

| 成员 | 职责 | 指南 |
| --- | --- | --- |
| A | FYZ 管理与决策端全栈 | [打开](team/member-a-fyz-fullstack.md) |
| B | JTT 求职者端全栈 | [打开](team/member-b-jtt-fullstack.md) |
| C | Agent 工程 | [打开](team/member-c-agent.md) |
| D | 爬虫与数据标准化 | [打开](team/member-d-crawler.md) |
| E | 知识图谱与分级抽取 | [打开](team/member-e-graph.md) |
| F | 平台集成与质量保障 | [打开](team/member-f-platform.md) |

## 架构与规划

- [全栈实施计划](../fyz-src/FULLSTACK_PLAN.md)
- [五级能力图谱架构](../fyz-src/GRAPH_ARCHITECTURE.md)
- [前端设计说明](../fyz-src/FRONTEND_DESIGN.md)
- [原开发计划](dev-plan.md)：历史参考，实际目录和分工以当前 README 为准。

## 竞赛材料

- [赛题需求整理](requirements.md)
- `analy_orig_ques/`：原始图片、音频、文档及清洗后的文本材料。
- `resume.txt`：阶段性整理材料，不作为代码契约。
