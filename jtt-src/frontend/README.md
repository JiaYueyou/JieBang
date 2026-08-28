# 求职者端前端

> 文档类型：现行模块说明
> 状态：部分实现 / 真实联调阻塞
> 核验日期：2026-08-28（`28a4cc5b`）
> 生产构建与类型检查通过；未配置前端测试；只读 ESLint 为 217 errors、1 warning。

组员 JTT 负责的 Vue 3 求职者端，包括岗位浏览、简历管理、人岗匹配、
学习路径、知识图谱、收藏和个人中心等页面。

## 开发命令

要求 Node.js `^20.19.0` 或 `>=22.12.0`。

```powershell
npm.cmd ci
npm.cmd run dev
npm.cmd run build
```

## 当前服务与联调状态

- JTT 主后端：`jtt-src/backend`，FastAPI，源码默认端口 8000，API 前缀 `/api/v1`。
- JTT AI 助手：`jtt-src/ai-assistant`，独立 FastAPI，默认端口 8001，API 前缀 `/api`。
- 前端 Axios 默认前缀是 `/api/v1`，MSW handlers 仍使用 `/api`。无环境变量时虽然会启动
  MSW，但默认请求不会命中 handlers，而是继续进入 Vite proxy。
- 当前 Vite 开发代理已将 `/api/v1/assistant/*`、`/api/v1/learning/assistant/*` 和短语优化
  请求改写到 AI 服务 8001，其余 `/api/*` 请求转发到主后端 8000。旧文档中“兜底全部指向
  8001”的描述已经过时。

本地开发应同时启动 JTT 主后端 8000 与 AI 服务 8001，并保持默认相对 Base URL。直接把
`VITE_API_BASE_URL` 配置成主后端绝对地址会使共享 Axios 实例中的 AI 请求也发往该地址。
生产构建不包含 Vite proxy，必须由 Nginx/网关复刻相同分流；仓库当前尚无 JTT 生产部署配置。

## 已实现与缺口

- 已有岗位、简历、匹配诊断、学习、图谱、收藏、个人中心等 13 个命名路由；生产构建通过。
- `resume/Upload.vue`、`resume/Detail.vue`、`resume/Tailor.vue`、`match/Result.vue` 尚未路由。
- 当前无鉴权守卫、无 404；Header 退出只跳转，不清除 token。
- 岗位、resume、auto-match、favorites 和 graph 的主路径已与当前 JTT 后端基本对齐；
  `/career/*` 尚无对应 JTT 后端路由，学习路径 `position_id` 仍存在测试/Schema 漂移。
- AI 文本存在未经消毒的 `v-html`，修复前不要渲染不可信模型或用户内容。
- 当前没有测试脚本；`npm.cmd run lint` 会执行 `--fix`，审计时不要把它当只读命令。

## 当前验证

```powershell
cd jtt-src\frontend
npm.cmd run build
npx.cmd eslint . --no-cache
```

2026-08-28 实测：构建和类型检查通过；Vite 报告两个超过 1 MB 的大 chunk；ESLint 为
217 errors、1 warning。尚未执行真实浏览器 E2E、主后端/AI/Neo4j/MySQL 端到端验收。

仓库级完成度与验证结果见 [当前实现状态](../../docs/implementation-status.md)。
