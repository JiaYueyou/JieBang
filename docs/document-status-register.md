# 技术文档状态登记表

> 文档类型：治理登记表
> 状态：现行
> 核验日期：2026-08-28
> 核验提交：`28a4cc5b`
> 状态事实来源：[当前实现状态](implementation-status.md)

本表覆盖仓库中的技术说明、架构、运行、接口、计划、Agent 和专项报告。状态含义：

- **现行**：可指导当前开发或运行；仍需以代码、OpenAPI 和实际环境为最终依据。
- **部分现行**：部分操作/结论有效，但有已标明的漂移或阻塞。
- **历史/规划**：保留原始决策，不滚动改写为现状。
- **时间点报告**：只说明生成当时的样本、数据或测试结果。
- **原始材料**：输入资料，不是工程契约。

## 1. 仓库级与 docs

| 文档 | 状态 | 说明 |
| --- | --- | --- |
| `README.md` | 现行 | 项目入口；完成度链接到状态基线 |
| `AGENTS.md`、`CLAUDE.md` | 现行治理 | Agent/协作约束，不承担功能状态说明 |
| `docs/README.md` | 现行 | 文档中心 |
| `docs/implementation-status.md` | 现行 | 当前代码、验证结果与缺口的统一事实页 |
| `docs/document-status-register.md` | 现行 | 本登记表 |
| `docs/api-reference.md` | 部分现行 | FYZ 主要接口摘要，不覆盖 JTT；记录旧 `/changes` 已移除，OpenAPI 权威 |
| `docs/database-and-runtime.md` | 现行 | FYZ 运行说明；已标迁移包阻塞 |
| `docs/automatic-data-pipeline.md` | 现行 | 自动闭环首版实现 |
| `docs/crawler-data-flow.md` | 现行 | 当前采集、导入与事实链路 |
| `docs/graph-dedup-mechanism.md` | 现行 | 当前标准化与图谱去重机制 |
| `docs/historical-baseline-v2.md` | 现行专项 | 当前历史参考基线 v2 |
| `docs/skill-dictionary-migration.md` | 历史迁移说明 | 保留字典迁移决策，现状以代码词典为准 |
| `docs/dev-spec.md` | 部分过时 | 早期规范草案；原则可用，端点/工具/拓扑已漂移 |
| `docs/documentation-standard.md` | 现行 | 文档编写与状态元数据规范 |
| `docs/git-workflow.md` | 现行 | Git 协作流程 |
| `docs/repository-security.md` | 现行 | 仓库安全规则 |
| `docs/requirements.md` | 需求基线 | 赛题目标，不代表实现状态 |
| `docs/dev-plan.md` | 历史规划 | 早期 5 人/12 周方案 |
| `docs/7.21任务规划.md` | 历史规划 | 多项已完成且接口路径已漂移 |
| `docs/team/member-a-fyz-fullstack.md` | 历史分工 | 成员 A 早期职责指南 |
| `docs/team/member-b-jtt-fullstack.md` | 部分过时 | JTT 后端已存在，但联调仍阻塞 |
| `docs/team/member-c-agent.md` | 历史分工 | Agent 早期职责指南 |
| `docs/team/member-d-crawler.md` | 历史分工 | 爬虫早期职责指南 |
| `docs/team/member-e-graph.md` | 历史分工 | 图谱早期职责指南 |
| `docs/team/member-f-platform.md` | 历史分工 | 平台早期职责指南 |
| `docs/dev-prompt-tmp/**` | 时间点记录 | 实施记录与窗口交接，不滚动更新历史结论 |
| `docs/analy_orig_ques/**` | 原始材料 | 赛题图片/文本清洗输入，不是工程契约 |
| `doc/checker-tool.md` | 辅助材料 | 早期检查工具记录，不是项目状态页 |

## 2. FYZ 后端、部署与数据

| 文档 | 状态 | 说明 |
| --- | --- | --- |
| `fyz-src/backend/README.md` | 现行 | FYZ 后端运行、迁移和模块边界 |
| `fyz-src/backend/test/README.md` | 现行 | 测试分层；2026-08-12 为 311 passed |
| `fyz-src/backend/scripts/README.md` | 部分现行 | 维护/评测脚本可用；完整迁移入口阻塞 |
| `fyz-src/backend/scripts/DATABASE_TRANSFER.md` | 部分现行 | 0025 快照已重导并通过离线严格校验；隔离接收环境覆盖式验收待完成 |
| `fyz-src/backend/scripts/CRAWLER_STATUS.md` | 时间点记录 | 爬虫状态快照，当前代码与流水线优先 |
| `fyz-src/backend/evaluation/fyz_interface_test_calculation_logic.md` | 现行评测说明 | 指标算法与适用边界 |
| `fyz-src/backend/evaluation/phase1_data_quality_report.md` | 时间点报告 | Phase 1 冻结结果 |
| `fyz-src/backend/evaluation/phase2_retrieval_report.md` | 时间点报告 | Phase 2 冻结结果，不代表本次联网复测 |
| `deploy/README.md` | 现行首版 | FYZ Docker Compose；本次未完整启动容器验收 |
| `data_analysis/README.md` | 现行边界说明 | 离线配置/词典，不作为独立事实导入管线 |
| `data_analysis/知识图谱数据链路说明.md` | 部分现行 | 架构说明；运行事实以 FYZ service 和流水线为准 |
| `data/official_group_*_report.md` | 时间点报告 | 指定采集批次的结果报告 |

## 3. FYZ 设计与计划

| 文档 | 状态 | 说明 |
| --- | --- | --- |
| `fyz-src/docs-plans/FULLSTACK_PLAN.md` | 历史设计 | 大部分 P0/P1 已落地，未逐项回填 |
| `fyz-src/docs-plans/GRAPH_ARCHITECTURE.md` | 历史设计/部分落地 | L1-L5 主链已实现，旧待办未回填 |
| `fyz-src/docs-plans/FRONTEND_DESIGN.md` | 设计基线/大部分落地 | 当前图谱组件已变化 |
| `fyz-src/docs-plans/DEVELOPMENT_PLAN.md` | 历史基线 | 早期登录/占位骨架方案 |
| `fyz-src/docs-plans/FYZ_MANAGEMENT_OPTIMIZATION_TASK1_PLAN.md` | 历史专项计划 | 原“尚未修改”只适用于 2026-07-30 |
| `fyz-src/docs-plans/FYZ_AGENT_REPAIR_OPTIMIZATION_PLAN.md` | 专项实施记录 | 核心 MVP 已实现，旧测试数为历史采样 |

## 4. Agent 工作区

| 文档 | 状态 | 说明 |
| --- | --- | --- |
| `agent-development/README.md` | 现行 | 独立 Agent 包当前能力与边界 |
| `agent-development/AGENT_API_CONTRACT.md` | 部分现行 | 契约基线；具体 HTTP/Schema 仍以代码/OpenAPI 为准 |
| `agent-development/architecture/README.md` | 现行 | 当前独立包依赖方向 |
| `agent-development/test-cases/README.md` | 现行 | Provider mock 与回归样例约定 |
| `agent-development/prompts/JD_GENERATION_V3.md` | 现行版本记录 | JD Prompt v3 设计与评审材料 |
| `agent-development/DEVELOPMENT_PLAN.md` | 历史滚动计划 | 阶段 0–3 已大量落地，下一阶段描述已过时 |
| `agent-development/SKILL_L45_COMPLETION_PLAN.md` | 历史专项计划 | L4/L5 首版已实现 |
| `agent-development/CAREER_PLANNING_AGENT_PLAN.md` | 历史专项计划 | 职业规划首版已实现 |
| `agent-development/CAREER_PLANNING_PRODUCT_FLOW_PLAN.md` | 历史产品计划 | FYZ 转岗产品早期设计 |
| `agent-development/l45_agent/README.md` | 历史原型 | 已被 `src/jiebang_agents/graph_enrichment` 取代 |

## 5. JTT

| 文档 | 状态 | 说明 |
| --- | --- | --- |
| `jtt-src/README.md` | 现行 | JTT 代码、数据、测试、运行与部署的统一入口 |
| `jtt-src/frontend/README.md` | 现行 | 记录开发代理、MSW/生产分流缺口、构建与质量状态 |
| `jtt-src/frontend/CLAUDE.md` | 部分过时治理 | 目录/API/Store/路由计数已漂移，不作状态依据 |
| `jtt-src/backend/backend.md` | 历史设计 | 八组路由已实现；岗位读取共享 FYZ 表；推荐技术栈多项未落地 |
| `jtt-src/backend/evaluation/README.md` | 现行评测边界 | 说明伪金标数量、复现依赖和当前测试阻塞 |
| `jtt-src/backend/evaluation/JTT_TEST_REPORT.md` | 时间点报告/已复核 | 旧结果保留；当前为 37 passed、1 failed，覆盖率不可复现 |
| `jtt-src/ai-assistant/README.md` | 部分现行 | 开发代理已对接；无生产部署和自动化测试 |
| `jtt-src/ai-assistant/SETUP.zh-CN.md` | 部分现行 | 本地 Key/启动可用；生产反向代理待实现 |
| `jtt-src/shuomingwendang.md` | 历史说明/待重写 | 已加 2026-08-28 纠偏摘要；正文仍为历史参考 |
| `jtt-src/shujuku.md` | 历史数据库快照 | “无 Alembic”已过时 |
| `jtt-src/agent.md` | 阻塞草稿 | 含未解决冲突标记，不能作契约 |
| `jtt-src/zyq-agent.md` | 部分过时 | 已加当前开发代理边界；页面路径与部分流程仍可能漂移 |
| `jtt-src/CHANGELOG.md` | 历史时间线 | 历史修复不保证当前仍有效 |
| `jtt-src/docs/**` | 原始材料 | 需求图片/文本提取，不是工程契约 |
| `jtt-src/jie_bang.raw_job_record.md` | 现行数据说明 | 共享岗位事实表、快照、映射和权限边界 |

## 6. 其他专项记录

| 文档 | 状态 | 说明 |
| --- | --- | --- |
| `幻觉问题/幻觉问题.md` | 问题材料 | 历史问题输入 |
| `幻觉问题/agent_hallucination_analysis.md` | 专项分析 | 时间点分析，当前 grounding 实现与评测优先 |

新增或修改技术文档时，应先判断属于“现状、规范、计划、历史还是报告”，并按
[统一文档规范](documentation-standard.md) 写入状态元数据；不得通过改写历史报告来制造当前结论。
