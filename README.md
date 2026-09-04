# 智联职引

> 面向数字产业的人才岗位智能适配体系

“智联职引”围绕企业岗位能力更新与人才智能适配场景，构建了从多源岗位数据治理、能力图谱构建、人才画像分析，到可解释匹配与智能决策的完整技术链路。项目同时提供用户端与管理决策端，使岗位认知、能力评估、成长路径规划和组织人才决策形成闭环。

## 项目亮点

- **多源异构数据治理**：对公开招聘数据执行标准化、去重、质量校验和结构化抽取，形成可持续更新的数据底座。
- **岗位能力图谱**：以岗位、技能、行业和能力层级为核心组织知识，支持岗位画像、技能关系和能力演进分析。
- **可解释智能适配**：结合规则、图谱、向量检索与大模型生成，输出带证据引用的岗位匹配、能力差距和发展建议。
- **双端协同体验**：用户端聚焦个人画像、岗位探索和成长规划；管理决策端聚焦数据治理、图谱分析、趋势洞察和人才决策。
- **可复现工程交付**：提供容器化部署、脱敏数据快照、自动化测试与验收证据，便于赛方快速启动和复核。

## 已验证成果

| 验收项 | 结果 |
| --- | ---: |
| 后端自动化测试 | 395 / 395 通过 |
| 后端服务层覆盖率 | 85.58% |
| 管理决策端前端测试 | 49 / 49 通过 |
| MySQL 数据快照 | 47 张表，54,474 行 |
| Neo4j 能力图谱 | 5,077 个节点，5,680 条关系 |
| 向量知识库 | 4 个集合，646 条 3072 维向量 |
| 岗位数据 | 200 条真实岗位，8 个来源，1,081 条技能事实 |
| RAG Recall@5 / MRR@10 | 94.29% / 94.71% |
| 引用精度 / 拒答准确率 | 97.41% / 96.00% |

完整测试口径、数据来源和运行证据见 [比赛测试报告](docs/final-test-files/智联职引-比赛测试报告.md) 与 [测试数据说明](data/competition-test/README.md)。

## 系统组成

```text
JieBang/
├─ jtt-src/                  # 用户端：Vue 3 前端与配套服务
├─ fyz-src/                  # 管理决策端：Vue 3 + FastAPI + 数据与图谱服务
├─ agent-development/        # 检索增强、匹配与智能分析能力
├─ deploy/                   # Docker Compose、镜像构建与反向代理配置
├─ data/                     # 岗位数据与离线数据资源
├─ test-data/                # 岗位输入、能力图谱输出与证据示例
└─ docs/                     # 设计、测试、部署和项目规范
```

主要技术栈包括 Vue 3、TypeScript、FastAPI、MySQL、Neo4j、Chroma、Redis、Celery、Docker Compose，以及面向知识检索与生成的模型服务。

## 快速启动管理决策端

环境要求：Docker Desktop 或 Docker Engine、Docker Compose v2，建议至少 8 GB 可用内存。

```powershell
Copy-Item deploy\.env.example deploy\.env
# 按 deploy/.env.example 的说明填写本地配置

docker compose --env-file deploy\.env `
  -f deploy\compose.yml `
  -f deploy\compose.local.yml up -d --build
```

启动完成后访问 `http://localhost:18080`。系统会在空数据库上自动执行迁移、导入脱敏比赛快照，并恢复图数据库与向量知识库。详细步骤、健康检查和故障处理见 [Docker 部署说明](deploy/README.md)。

## 源码开发与测试

- 后端开发、测试与数据恢复命令：[开发规范](docs/dev-spec.md)
- 管理决策端整体设计：[系统实现计划](fyz-src/docs-plans/FULLSTACK_PLAN.md)
- 能力图谱与智能分析设计：[图谱架构](fyz-src/docs-plans/GRAPH_ARCHITECTURE.md)
- 数据库快照导入与校验：[数据迁移说明](fyz-src/backend/scripts/DATABASE_TRANSFER.md)
- Git 协作与提交规范：[协作流程](docs/git-workflow.md)

仓库中的 `.env.example` 仅提供配置结构。实际账号、密码和模型密钥不进入公开源码仓库；比赛部署所需配置随私下提交的软件模块单独提供。

## 作品说明

本仓库用于“智联职引—面向数字产业的人才岗位智能适配体系”的源码展示与复核。赛方可结合提交材料中的设计方案、测试报告、部署说明、账号信息和测试数据完成系统验收。
