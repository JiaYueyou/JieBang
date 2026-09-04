# 智联职引 · 管理决策端小程序

「智联职引」**管理决策端**的移动演示版。基于 **uni-app + Vue 3 + Vite + TS + Pinia**，视觉延续项目 "Refined Technica" 设计系统（品牌靛蓝 `#4f6ef6`、深空五层色、玻璃拟态、星图 hero）。

> **纯前端演示版**：全部数据由内置 Mock 提供（`src/mock/data.ts`），**无需启动任何后端服务**，导入微信开发者工具即可运行。数据形态对齐 fyz-src 管理与决策端，后续可无缝替换为真实接口。

## 功能总览

| Tab | 功能 |
|-----|------|
| 工作台 | 星图 hero + KPI 玻璃卡（管理岗位/需求席位/人才池/待审核）、待办卡片、Canvas 双序列趋势图、系统动态流水 |
| 职位 | 搜索 / 新兴·既有分类 / 状态标签（急缺/在招/评估中）、席位·人才池·独立来源统计、管理视角详情、下线/上架 |
| 图谱 | 自研 Canvas 五层技能森林（L1-L5 着色）、关键词搜索高亮、节点下钻展开 |
| 洞察 | 技能热度榜（趋势评分/生命周期/涨跌）、新兴 vs 既有 conic-gradient 环图、城市热度条 |
| 管理 | 运行总览（质量门禁/滚动基线）、图谱审核队列、数据导入状态、成员管理、审计日志 |

演示账号：**admin / admin123**（Mock 校验，任意断网环境可用）

## 快速开始

```bash
# 1. 安装依赖
npm install

# 2. 启动小程序编译（watch 模式，产物在 dist/dev/mp-weixin）
npm run dev:mp-weixin

# 3. 微信开发者工具
#    导入目录：Applet/dist/dev/mp-weixin（必须选这一层，里面直接可见 app.json）
#    详情 → 本地设置 → 勾选「不校验合法域名」（本版无网络请求，可选）
```

无需后端、无需数据库 —— 打开即是完整可演示状态。

### 常用命令

```bash
npm run dev:mp-weixin     # 开发 watch
npm run build:mp-weixin   # 生产构建（导入 dist/build/mp-weixin）
npm run type-check        # vue-tsc 类型检查
```

## 目录结构

```
src/
├── pages/            # 5 个 tabBar 页面（工作台/职位/图谱/洞察/管理）
├── pages-sub/        # 登录、职位详情（管理视角）
├── mock/data.ts      # 全量 Mock 数据集（KPI/职位/图谱/趋势/审核/审计）
├── api/              # admin.ts + graph.ts（Mock 实现，签名贴近真实接口）
├── stores/           # Pinia（user: token/profile 持久化）
├── components/       # AppTabBar / SkillGraph / TrendChart / BarRank / EmptyState
├── styles/           # common.scss（工具类：卡片/骨架屏/动效/分数环）
└── uni.scss          # Refined Technica Mobile 设计令牌
```

## 切换真实数据

`src/api/admin.ts` 与 `src/api/graph.ts` 的函数签名刻意贴近真实后端契约：把函数体替换为 `request()` HTTP 调用（见主仓库 jtt-src / fyz-src 后端）即可接入真实数据，页面层无需改动。

## 注意事项

- 正式发布需 HTTPS 备案域名；比赛演示用**体验版**即可
- 求职者端（连 jtt-src 后端的版本）代码保留在 git 历史（提交 `fc3da43`），可随时回退
