# JTT 求职者端现状与运行说明

> 文档类型：JTT 子系统现行入口
> 状态：部分实现；本地开发链路基本具备，测试与生产部署未闭环
> 核验日期：2026-08-28
> 核验提交：`28a4cc5b`
> 权威来源：`frontend/src`、`backend/app`、`ai-assistant/main.py`、JTT OpenAPI、共享快照 manifest

JTT 是智联职引的求职者业务端，由 Vue 前端、JTT FastAPI 主后端和独立 AI 助手组成。
它拥有独立的用户端业务表和迁移链，但岗位列表、岗位详情及自动匹配会读取 FYZ 共享
`jie_bang` 事实库，因此不能按完全独立、空数据的应用部署。

## 1. 当前能力

| 模块 | 状态 | 说明 |
| --- | --- | --- |
| 前端 | 部分实现 | 13 个命名路由；覆盖认证、岗位、图谱、收藏、简历编辑、诊断、职业发展、学习和个人中心 |
| 主后端 | 基本实现 | auth、positions、resume、match、tailor、learning、favorites、graph 8 组路由 |
| AI 助手 | 部分实现 | 聊天、Agent 对话、简历优化、学习路径、资源推荐和测验；无自动化测试 |
| 数据 | 共享依赖 | 岗位读取 FYZ 快照；JTT 自有前端 mock、后端种子和伪金标评测集 |
| 部署 | 未实现 | 没有 JTT Dockerfile、Compose、Nginx 或生产验收记录 |

前端还有 4 个未路由视图：`resume/Upload.vue`、`resume/Detail.vue`、
`resume/Tailor.vue`、`match/Result.vue`。当前无鉴权守卫和 404，退出操作也没有完整清理 Token。

## 2. 运行拓扑

```text
JTT Vue（Vite 开发端口 5173）
  ├─ /api/v1/assistant/*、learning/assistant/*、指定优化端点
  │       └─ rewrite /api/v1 → /api → AI 助手 8001
  └─ 其余 /api/* → JTT 主后端 8000
                         ├─ JTT 用户端业务表
                         ├─ FYZ 共享 jie_bang 岗位事实表（只读）
                         └─ Neo4j 图谱
```

Axios 默认 Base URL 是 `/api/v1`，MSW handlers 当前使用 `/api`，因此默认 mock 不会命中。
Vite proxy 只在开发服务器存在；生产环境必须由网关重新实现上述分流。前端目前也没有独立
`VITE_AI_BASE_URL` 请求实例，不能仅设置一个绝对 `VITE_API_BASE_URL` 完成双后端部署。

## 3. 数据边界

- FYZ 共享比赛快照：`20260820_0025`，47 张表、54474 行；包含 4683 条
  `raw_job_record`、4800 条 `standard_job`，离线严格校验通过。
- JTT Alembic head：`34d9b68a59ff`；版本表：`alembic_version_jtt`。
- JTT evaluation：120 条 JD、10 条简历、100 条匹配、20 条防幻觉样本，全部属于自动规则
  `pseudo_gold`，不能作为人工独立金标准或最终 90% 准确率证明。
- 前端 mock 与后端种子仅用于开发演示，不是数据库快照。后端种子简历固定依赖
  `user_id=1`，全新空库且未创建初始用户时存在外键失败风险。

## 4. 本地启动

先导入共享 FYZ 数据快照并准备 Neo4j；完整流程见
[数据库、数据导入与运行指南](../docs/database-and-runtime.md)。随后配置并启动 JTT：

```powershell
Copy-Item jtt-src\backend\.env.example jtt-src\backend\.env
Copy-Item jtt-src\ai-assistant\.env.example jtt-src\ai-assistant\.env

cd jtt-src\backend
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 新终端
cd jtt-src\ai-assistant
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# 新终端
cd jtt-src\frontend
npm.cmd ci
npm.cmd run dev
```

JTT 与 FYZ 后端都默认使用 8000。如需同时启动，必须修改其中一个服务端口及对应代理。
JTT 主后端 CORS 和 AI CORS 当前主要面向本地 5173，生产域名需要显式加入配置。

## 5. 当前验证结果

2026-08-28 在项目指定 Python 3.10 环境和现有 `node_modules` 上验证：

| 检查 | 结果 |
| --- | --- |
| `npm.cmd run build` | 通过类型检查与生产构建；存在两个超过 1 MB 的 chunk |
| `npx.cmd eslint . --no-cache` | 217 errors、1 warning |
| 前端自动化测试 | 未配置 |
| 默认 `python -m pytest -q` | 缺少 `pytest-cov`，收集前失败 |
| `python -m pytest -q -o addopts=` | 37 passed、1 failed |
| AI 助手测试 | 未配置；未执行真实 DeepSeek/搜索联调 |

失败用例是学习路径创建契约：测试传入字符串 `position_id`，当前 Schema 要求整数。
`backend/requirements.txt` 还缺 pytest 系列、aiosqlite、python-docx 和 pdfplumber，空环境安装
不能复现当前开发机能力。

## 6. 生产部署前置清单

1. 补齐运行/测试依赖并恢复覆盖率门禁，修复全部测试。
2. 新建 JTT 前端、主后端、AI 服务的镜像和 Compose/Nginx 分流。
3. 清除 `alembic.ini` 中硬编码凭据，统一 Alembic 与启动时 `create_all()` 的职责。
4. 修复 MSW 前缀、鉴权守卫、退出流程、404、孤立视图和 `/career` 接口边界。
5. 对 AI `v-html` 做消毒，并补充上传大小、文件名、内容类型和恶意文档测试。
6. 使用共享 `0025` 快照执行 MySQL、Neo4j、主后端、AI 与浏览器完整验收。

## 7. 文档入口

- [前端说明](frontend/README.md)
- [后端历史设计](backend/backend.md)
- [评测方案](backend/evaluation/README.md)
- [测试时间点报告](backend/evaluation/JTT_TEST_REPORT.md)
- [AI 助手说明](ai-assistant/README.md)
- [数据库历史设计](shujuku.md)
- [共享岗位事实表说明](jie_bang.raw_job_record.md)
- [项目当前实现状态](../docs/implementation-status.md)
