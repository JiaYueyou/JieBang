# 当前实现状态

> 文档类型：现状基线
> 状态：现行
> 核验日期：2026-08-12
> 核验提交：`c995a09e`（`main`）
> 权威来源：仓库代码、Alembic 迁移、已提交评测产物与本页“验证结果”中的实际命令

本文用于回答“代码现在实际具备什么”。需求目标仍以 [requirements.md](requirements.md) 为准；
接口细节以各 FastAPI 实例运行时 OpenAPI 为准；历史计划和设计稿不再作为完成状态依据。

## 1. 状态口径

| 状态 | 含义 |
| --- | --- |
| 已实现 | 代码、路由或页面已存在，并有本地自动化检查支撑 |
| 基本实现 | 主流程已存在，但仍有权限、异常状态、测试或交互缺口 |
| 部分实现 | 只有部分页面/接口完成，或默认配置下无法完成真实联调 |
| 占位 | 路由或页面明确返回占位内容，未形成业务闭环 |
| 规划/历史 | 仅表达目标或过去决策，不代表当前代码 |

## 2. 仓库运行拓扑

```text
FYZ 管理端 Vue 3 ──HTTP──> fyz-src/backend FastAPI
                                  ├── MySQL：事实与审计
                                  ├── Neo4j：可重建图查询模型
                                  ├── ChromaDB：可重建向量索引
                                  ├── Redis：缓存
                                  └── Celery/Redis：部分后台任务

JTT 求职端 Vue 3 ──HTTP──> jtt-src/backend FastAPI
        └──────────AI─────> jtt-src/ai-assistant FastAPI
```

FYZ 和 JTT 当前是两套独立 FastAPI 应用、独立模型/迁移链。两者源码都默认使用 8000，不能在
同一主机上同时占用该端口；JTT AI 助手默认使用 8001。JTT 前端当前的默认代理配置并未正确
分流这两个服务，详见“已知缺口”。

## 3. 分系统状态

| 分系统 | 状态 | 已实现范围 | 尚未闭环 |
| --- | --- | --- | --- |
| FYZ 后端 | 基本实现 | 91 个 OpenAPI 路径、104 个 HTTP 操作；认证、岗位/版本、技能事实、导入、图谱、L4/L5、检索、分析、Dashboard、匹配、转岗、用户活动、爬虫、流水线、审计 | 真实 MySQL/Redis/外部模型端到端未在本次核验中启动；旧 `/changes` 占位已因需求重复且无消费者而移除 |
| FYZ 管理端 | 基本实现 | 12 个路由页面均有业务实现；运行时固定使用真实 HTTP provider；管理、图谱、趋势、匹配、转岗等页面已接 API | 普通用户仍可见部分仅 recruiter/admin 可调用的操作；缺少 E2E 与组件级测试；图谱 tooltip/外链需安全收敛 |
| 独立 Agent 包 | 基本实现 | JD 生成、技能抽取、L4/L5 图谱补全、职业规划、匹配解释；L4/L5 分类重试、调用诊断、审核质量门槛与离线压测 | 统一文本/简历技能抽取公共入口未完成；Emerging Job Review 未实现；真实外部模型仍需持续压测 |
| 自动数据闭环 | 已实现首版 | 手动/定时流水线、持久化运行记录、恢复、采集、导入、图谱同步、历史基线、质量摘要、状态缓存 | 生产调度、失败恢复和多源长期运行仍需真实基础设施验收；`pipeline_service.py` 覆盖率偏低 |
| 爬虫与数据 | 基本实现 | 通用蜘蛛框架、多来源脚本、持久化增量检查点、标准化金标评测与比赛质量门禁 | 真实外站长期增量、数据授权、反爬变化和对外发布脱敏仍需人工复核 |
| FYZ Docker 部署 | 已实现首版 | MySQL、Neo4j、两套 Redis、迁移、API、Celery worker/beat、缓存 worker、Nginx 编排 | 本次只审查配置，未执行完整容器启动验收 |
| JTT 后端 | 基本实现 | auth、positions、resume、match、tailor、learning、favorites、graph 共 8 组路由；独立迁移与种子数据 | 与 FYZ 事实库/契约未统一；启动时 `create_all` 与独立 Alembic 并存；缺少更完整接口与集成测试 |
| JTT 求职端 | 部分实现 | 13 个命名路由，岗位、简历、诊断、学习、图谱、收藏、个人中心等页面；生产构建通过 | 默认 `/api/v1`、MSW `/api`、Vite 代理和 8000/8001 端口不一致；4 个视图未路由；无测试；lint 未通过；部分失败会静默回退 mock |
| JTT AI 助手 | 部分实现 | 独立 FastAPI 服务与聊天/推荐类接口 | 前端未按当前端点和端口正确分流；文档中的 rewrite 与实际 Vite 配置不一致 |

## 4. FYZ 数据与迁移状态

- FYZ Alembic 当前 head：`20260809_0020`，在 0017 后新增分析基线快照、岗位来源观测和
  自动流水线运行记录。
- 团队共享 SQL 快照已于 2026-08-12 按 `20260809_0020` 重导：42 张表、41667 行；
  SQL SHA-256、逐表行数/内容摘要、迁移新增表与 manifest 配对均通过独立离线校验。
- 迁移包的覆盖式接收端导入尚未在隔离环境执行；该步骤会替换目标 MySQL、Chroma 和
  `namespace=jiebang` 的 Neo4j 数据，不能在当前源库直接自导入验收。
- 快照 manifest 仍记录 ChromaDB 与 Neo4j 的可重建摘要；
  Neo4j 最近快照 474 个节点、817 条关系。
- 2026-08-10 的已提交质量评测产物报告：JD 正向锚点召回率 0.9903、简历技能 micro-F1
  0.991736、确定性匹配精确结果准确率 1.0。JD 数据是正向关键词代理集，不能据此推出完整
  标注集上的 precision 或总体 F1。
- 同日覆盖率产物报告 FYZ `app/services` 可执行行覆盖率 83.6765%；其中
  `pipeline_service.py` 39.219%、`resume_parser.py` 53.4884%，低于整体水平。

## 5. 2026-08-12 验证结果

| 检查 | 结果 |
| --- | --- |
| FYZ 后端 pytest | 343 passed、0 failed、0 skipped；完整运行约 307 秒 |
| Agent 包 pytest | 16 passed；有 pytest cache 目录权限警告，不影响用例结果 |
| JTT 后端 pytest | 9 passed；有 1 个 Pydantic v2 class-based config 弃用警告 |
| FYZ 前端 Vitest | 5 个文件、44 项测试全部通过 |
| FYZ 前端生产构建 | 通过；主 chunk 约 1.19 MB、图谱 chunk 约 633 kB，存在分块警告 |
| JTT 前端生产构建/类型检查 | 通过；两个 chunk 约 1.12 MB 与 1.20 MB，存在分块警告 |
| JTT 前端测试 | 未配置测试框架或 test 脚本 |
| JTT 前端只读 ESLint | 158 errors、1 warning；主要为 `no-explicit-any`、组件命名、未使用变量和 slot 问题 |

本轮完整 FYZ 后端单命令在约 307 秒完成，共 343 项通过。Neo4j integration 用例本次没有 skip，并在
当前环境通过；MySQL 业务测试仍主要使用 SQLite 内存库。Redis、DeepSeek、OpenAI-compatible
Embedding 和爬虫外站均不能仅凭 343 passed 宣称已真实联网联调。上述检查也不等价于完整
浏览器 E2E。

## 6. 已知优先级缺口

### P0：联调与安全

1. 统一 JTT 前端、JTT 后端、AI 助手和 MSW 的 Base URL、端口与路径；当前默认开发模式
   会把大量 `/api/v1/*` 请求发向错误服务或得到 404。
2. 在隔离接收环境对 FYZ `0020` 团队数据库迁移包执行覆盖式导入验收，并复核授权与脱敏边界。
3. 修复 JTT 真实契约漂移：profile/改密字段、`raw-{id}` 岗位标识、resume、auto-match、
   favorites 和 graph 等接口。
4. 对 FYZ 图谱 tooltip 及 JTT AI 消息的 HTML 输出做可信转义/消毒，并限制外链协议。
5. 清理 `jtt-src/agent.md` 中未解决的冲突标记；该文档在清理前只能作为草稿。

### P1：完整性与质量

1. 为 JTT 增加鉴权守卫、404、正确退出流程，并路由或移除 4 个孤立视图。
2. 为 FYZ 前端补齐角色可见性，避免普通用户看到必然返回 403 的 Agent/图谱操作。
3. 增加 JTT 测试、两套前端浏览器 E2E、真实服务集成测试和恶意内容回归测试。
4. 优化两套前端的超大 chunk；FYZ 可同时清理未使用的旧 G6/Sigma 组件与 Store。
5. 对自动流水线、爬虫、Neo4j、Redis、Celery 和外部模型执行长时间生产化验收。

## 7. 文档有效性

| 文档类别 | 当前用途 |
| --- | --- |
| 本文、根 README、`docs/README.md` | 当前状态与导航 |
| `docs/api-reference.md` | FYZ 静态接口摘要；运行时 OpenAPI 为准 |
| `docs/database-and-runtime.md`、`deploy/README.md` | FYZ 数据库、运行与部署操作 |
| `docs/automatic-data-pipeline.md`、`docs/crawler-data-flow.md` | 当前自动流水线与采集链路 |
| `fyz-src/docs-plans/*`、`docs/dev-plan.md`、`docs/7.21任务规划.md` | 规划或历史决策，不作为完成状态 |
| `jtt-src/backend/backend.md`、`jtt-src/shuomingwendang.md`、`jtt-src/shujuku.md` | JTT 早期设计/说明，部分内容已与代码漂移 |
| `docs/dev-prompt-tmp/*`、评测报告、采集报告 | 时间点记录，只读归档，不滚动改写历史事实 |
