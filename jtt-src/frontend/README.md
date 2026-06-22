# 求职者端前端

组员 JTT 负责的 Vue 3 求职者端，包括岗位浏览、简历管理、人岗匹配、
学习路径、知识图谱、收藏和个人中心等页面。

## 开发命令

要求 Node.js `^20.19.0` 或 `>=22.12.0`。

```bash
npm ci
npm run dev
npm run build
npm run lint
```

开发环境使用 MSW 提供模拟接口。后续与 FastAPI 联调时，应保持
`src/api/` 的接口封装，并逐步替换 `src/mock/`，不要在页面中直接请求后端。
