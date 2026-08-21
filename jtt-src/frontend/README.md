# 求职者端前端

> 文档类型：现行模块说明
> 状态：部分实现 / 真实联调阻塞
> 核验日期：2026-08-12（`c995a09e`）
> 生产构建与类型检查通过；未配置前端测试；只读 ESLint 为 158 errors、1 warning。

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
- 前端 Axios 默认前缀是 `/api/v1`，MSW handlers 仍使用 `/api`；当前 Vite 兜底代理也把
  `/api` 指向 8001。因此“无环境变量即启用 MSW”并不代表请求可以命中 mock，默认开发
  联调状态不可用。

真实联调时必须显式配置 `VITE_API_BASE_URL` 指向 JTT 主后端，并单独修正 AI 请求分流；
在代理、MSW 与接口契约统一前，不要把页面中的静默 mock fallback 当作后端成功。

## 已实现与缺口

- 已有岗位、简历、匹配诊断、学习、图谱、收藏、个人中心等 13 个命名路由；生产构建通过。
- `resume/Upload.vue`、`resume/Detail.vue`、`resume/Tailor.vue`、`match/Result.vue` 尚未路由。
- 当前无鉴权守卫、无 404；Header 退出只跳转，不清除 token。
- profile/改密字段、`raw-{id}` 岗位 ID、resume、auto-match、favorites、graph 等契约仍漂移。
- AI 文本存在未经消毒的 `v-html`，修复前不要渲染不可信模型或用户内容。
- 当前没有测试脚本；`npm.cmd run lint` 会执行 `--fix`，审计时不要把它当只读命令。

仓库级完成度与验证结果见 [当前实现状态](../../docs/implementation-status.md)。
