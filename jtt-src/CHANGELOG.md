# JTT 求职端 — 改动说明

> 文档类型：历史变更记录
> 状态：只读时间线，不代表当前配置持续有效
> 2026-08-28 复核：当前 Vite 开发代理已恢复主后端 8000 与 AI 8001 分流；Axios
> `/api/v1` 与 MSW `/api` 仍不一致，生产代理仍缺失。现状见
> [前端 README](frontend/README.md)。

> 版本: 0.3.0 | 日期: 2026-07-22
> 对应 PR: #20

---

## 概述

JTT 求职端接入 DeepSeek 大模型，所有 AI 端点移除 MSW mock，直通真实 LLM。
同时新增职业发展页、自动匹配功能、学习路径持久化，优化快捷指令流程。

---

## 新增

### AI 助手独立服务
`jtt-src/ai-assistant/`
- 独立的 FastAPI 服务，不依赖 MySQL/Neo4j，仅需 DeepSeek API Key
- 提供 6 个 AI 端点：通用对话、短语润色、联网路径生成、资源推荐、题目生成
- 完整文档：README.md、SETUP.zh-CN.md、.env.example

### 职业发展页
`jtt-src/frontend/src/views/career/Index.vue`
- 技能差距分析：选择简历 + 目标岗位 → 显示匹配分数、缺失/薄弱/已匹配技能
- 岗位推荐模式：自动匹配全部岗位 → 按分排序 → 展示推荐列表
- 学习路径生成：分析差距 → 生成路径 → 跳转到学习页面

### 页面数据共享
`jtt-src/frontend/src/stores/pageContext.ts`
- 简历详情页、匹配结果页自动将数据注入共享 store
- AI 助手无需用户重复输入即可感知当前页面的简历/匹配数据

### 自动匹配接口
`api/match.ts` — `matchAuto()` → `POST /match/auto`
- 将简历与系统中所有岗位逐一匹配，按匹配度降序返回

### 前端 AI 助手 API
`jtt-src/frontend/src/api/assistant.ts`
- `chat()` — 通用对话
- `optimizePhrase()` — 短语润色（4 种风格）
- `generateLearningPath()` — 联网搜索 + 路径生成

### 智能体实现文档
`jtt-src/zyq-agent.md`
- JTT 求职端三个 Agent 的前端实现说明
- 组件对照表、文件索引、数据流图

---

## 修改

### 全局 AI 悬浮球
`FloatingAIButton.vue` — 从 210 行 → 886 行
- 完整聊天界面：消息气泡、Markdown 渲染、打字动画、自动滚动
- 本地流程：简历优化 / 匹配诊断 — 读取本地数据生成选项按钮，不经过 LLM
- AI 流程：自由输入 / 页面上下文感知 — 调用 DeepSeek
- 图片上传：文件选择 + Ctrl+V 粘贴
- 页面感知：岗位详情、简历详情、匹配结果页自动识别并给出建议

### 学习页面 AI 助手
`views/learning/Index.vue` — AI 对话流程重构
- 4 个快捷指令全部改为**先问清再处理**，不发送预设内容
- 生成学习路径：问岗位名 → 联网搜索 → DeepSeek 重排序 → 5-7 步路径
- 推荐学习资源：问技能名 → DeepSeek 推荐课程/书籍/项目
- 学习路线咨询：问情况 → DeepSeek 定制建议
- 技能差距分析：问目标岗位 → DeepSeek 对比分析
- 路径列表：新增路径自动添加到右侧面板并展开
- 学习测试：调用 DeepSeek 生成 5 道选择题

### 学习路径持久化
`stores/learning.ts`
- AI 生成的路径自动保存到 localStorage
- 刷新页面不丢失
- 进度（步骤完成状态）同步持久化

### 简历 AI 润色
`views/resume/Editor.vue`
- 工作描述/自我评价旁的「AI 优化」按钮 → 选择风格（更专业/简洁/匹配/冲击力）
- 调用 `POST /api/assistant/optimize-phrase` → DeepSeek 返回 3 个改写版本
- 去掉 mock 直连

### Tailor 页面 API 化
`views/resume/Tailor.vue`
- 移除 `mockTailorSuggestions` 直接导入
- 改为调用 `tailorApi.getSuggestions()` + `positionsApi.getDetail()` + `matchApi.getResult()`

### 简历/匹配数据共享
`views/resume/Detail.vue` + `views/match/Result.vue`
- 页面加载时通过 `pageData` store 共享当前数据
- AI 助手自动感知，无需手动输入

### 移除 AI mock 处理器
`mock/handlers.ts`
- 移除 `/api/assistant/chat` — 直通 DeepSeek
- 移除 `/api/learning/assistant/chat` — 直通 DeepSeek
- 移除 `/api/learning/assistant/generate-path` — 直通 AI 服务
- 移除 `/api/learning/assistant/recommend-resources` — 直通 DeepSeek
- 移除 `/api/learning/assistant/quiz` — 直通 DeepSeek
- 移除 `/api/tailor/optimize-phrase` — 直通 AI 服务

### 配置文件
`vite.config.ts` — 新增代理规则：
```
/api/learning/assistant/*  →  AI 服务 (8001)
/api/assistant/*           →  AI 服务 (8001)
/api/tailor/optimize-phrase → AI 服务 (8001)
/api/*                     →  主后端 (8000)
```

### 类型定义
`types/index.ts` — 新增：
- `ChatMessage`、`ChatAction`、`PageContext` 类型
- `AssistantChatRequest`、`AssistantChatResponse` 接口

### 路由与导航
- `router/index.ts` — 新增 `/career` 路由
- `AppSidebar.vue` — 新增「职业发展」菜单项

---

## 文档

| 文件 | 说明 |
|------|------|
| `jtt-src/zyq-agent.md` | JTT 智能体前端实现文档 |
| `docs/README.md` | 文档中心新增智能体索引区 |

---

## 配置文件

### `.env.example` 新增变量
```
DEEPSEEK_API_KEY=your-deepseek-api-key    # DeepSeek API Key（必需）
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
SEARCH_PROXY=                              # DuckDuckGo 代理（可选）
BING_SEARCH_API_KEY=                       # Bing 搜索备选（可选）
```

---

## 启动方式

```bash
# 1. AI 助手服务
cd jtt-src/ai-assistant
cp .env.example .env           # 填入 DEEPSEEK_API_KEY
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# 2. JTT 前端
cd jtt-src/frontend
npm run dev
```
