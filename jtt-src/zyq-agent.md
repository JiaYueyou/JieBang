# 智能体前端实现文档

> 文档类型：JTT Agent 前端阶段性记录
> 状态：部分过时
> 核验日期：2026-08-28（`28a4cc5b`）
> 当前 Vite 开发代理已覆盖主要 AI 端点；MSW `/api` 与 Axios `/api/v1` 仍不匹配，生产
> 环境也没有独立 AI Base URL 或反向代理配置。文中页面路径和流程必须以当前源码为准。

> 智联职引 — JTT 求职端
> 版本: 0.3.0 | 更新: 2026-07-21

---

## 1. 概述

JTT 求职端实现三个核心智能体（Agent），覆盖简历优化、学习助手、智能匹配三大场景。

**架构思想**: 右下角 AI 悬浮球（FloatingAIButton）是统一入口，自身不包含复杂业务逻辑。用户点击后根据意图直接调用对应 Agent 的专用组件或 API。

```
用户操作 → FloatingAIButton（路由/上下文分析）
               │
         ┌─────┼─────┐
         ▼     ▼     ▼
     Agent 1  Agent 2  Agent 3
    简历优化  学习助手  智能匹配

所有 AI 请求 → AI 助手服务 (port 8001) → DeepSeek API
不再使用 MSW mock 处理 AI 请求
```

---

## 2. 智能体详述

### 2.1 Agent 1：简历优化智能体

**定位**：基于岗位需求优化简历内容，识别技能差距，生成具体可执行的修改建议。

#### 场景 A：诊断优化（匹配报告 → 逐条建议 → 接受/应用）

| 步骤 | 说明 | 文件 |
|------|------|------|
| 匹配诊断页查看报告 | 匹配分数 + 维度评分 + 技能差距 | `views/match/Result.vue` |
| 一键优化简历 | 调用 `GET /tailor/suggestions/{resumeId}/{positionId}`（走 API） | `views/resume/Tailor.vue` |
| 逐条接受/拒绝 | 用户逐条审核 AI 建议，绿色高亮已接受 | `views/resume/Tailor.vue` |
| 应用已接受的建议 | 调用 `POST /tailor/apply-all`，生成新版简历 | `api/tailor.ts` |
| AI 润色短语 | 选择风格 → DeepSeek 返回 3 个版本 → 点击替换原文 | `views/resume/Editor.vue` → `api/assistant.ts` |

#### 场景 B：编辑润色

- **入口**：简历编辑器中工作描述/自我评价旁的「AI 优化」按钮
- **风格**：更专业 / 更简洁 / 更匹配 / 更有冲击力
- **流程**：调用 `POST /api/assistant/optimize-phrase` → DeepSeek → 返回 3 个改写版本 → 用户选择替换
- **API**：由 AI 助手服务 (port 8001) 处理，已移除 MSW mock

#### 降级策略

LLM 不可用时，`TailorService._fallback_suggestions()` 基于规则生成建议：
- 模糊匹配简历技能 ↔ 岗位技能，提出缺失/薄弱技能建议
- 编辑润色降级返回原文

---

### 2.2 Agent 2：学习助手智能体

**定位**：围绕学习需求提供全方位 AI 支持，覆盖学习路径生成、资源推荐、问答、测试。

#### 场景 A：生成学习路径（含联网搜索+重排序）

```
用户 → 学习页面 → 点击「生成学习路径」
  → AI 询问："请问您想要生成哪个岗位的学习路径呢？"
  → 用户输入目标岗位
  → 系统：联网搜索技能要求 → LLM 重排序 → 生成 5-7 步路径
  → 自动添加到页面右侧路径列表并展开（localStorage 持久化，刷新不丢失）
```

| 步骤 | 文件 |
|------|------|
| AI 对话窗口 | `views/learning/Index.vue`（左侧面板） |
| 联网搜索 + 路径生成 | `POST /api/assistant/generate-learning-path`（AI 服务 → DeepSeek） |
| 路径展示 | `views/learning/Index.vue`（右侧路径卡片 + 流程图 + 时间线） |
| 路径持久化 | `stores/learning.ts`（localStorage） |
| 学习测试 | `views/learning/Index.vue` → `POST /api/learning/assistant/quiz`（DeepSeek 生成） |

#### 场景 B：AI 对话（4 个快捷指令均先问清再答）

| 快捷指令 | 行为 |
|----------|------|
| **生成学习路径** | → 问"哪个岗位？" → 联网生成结构化路径并添加到右侧面板 |
| **推荐学习资源** | → 问"哪个技能？" → DeepSeek 推荐课程/书籍/项目 |
| **学习路线咨询** | → 问"你的情况？" → 用户描述场景 → DeepSeek 定制建议 |
| **技能差距分析** | → 问"目标岗位？" → DeepSeek 对比分析 + 学习建议 |

所有快捷指令均通过 `POST /api/learning/assistant/chat` 走 DeepSeek 真实回复。

**回复格式**：Markdown + 关联概念标签 + 推荐资源 + 追问建议

#### 场景 C：学习测试

- 路径卡片 → 点击「学习测试」→ `POST /api/learning/assistant/quiz` → DeepSeek 生成 5 道选择题 → 作答 → 评分 + 解析
- **路径持久化**：AI 生成的路径保存到 localStorage，刷新页面不丢失

#### 降级策略

LLM 不可用时，规则引擎对比已有技能 ↔ 岗位技能，按优先级排列缺失技能生成步骤。

---

### 2.3 Agent 3：智能匹配智能体

**定位**：简历与岗位的智能匹配与解读，自动匹配所有岗位按分排序。
**增强**：技能语义匹配 + 经验相关性评估（LLM 驱动，规则降级）。

#### 用户交互流程

| 入口 | 流程 | 文件 |
|------|------|------|
| 岗位探索页 `+` 按钮 | 选择简历 → 一键匹配全部岗位 → 按分降序展示 | `QuickMatchFab.vue` → `POST /match/auto` |
| 匹配诊断页 | 选择简历 + 岗位 → 查看详细匹配报告 | `views/match/Index.vue` / `Result.vue` |
| AI 悬浮球「匹配诊断」 | 选择简历 → 自动计算高分岗位 → 跳转结果 | `FloatingAIButton.vue`（本地流程） |

#### 匹配算法（LLM 增强）

| 维度 | 权重 | 评分依据 | LLM 增强 |
|------|------|---------|---------|
| 技能匹配 | 40% | 简历技能 ↔ 岗位技能覆盖度 | **语义匹配**：识别同义词/上下位（如 "Pandas/NumPy" ↔ "数据分析"） |
| 经验匹配 | 30% | 工作经历相关性 | **LLM 相关性评估**：行业/职责/年限/技能综合判断 |
| 学历匹配 | 15% | 教育经历数量 | 规则 |
| 综合素质 | 15% | 项目数量 + 自我评价长度 | 规则 |

#### LLM 增强实现

**技能语义匹配** `_semantic_skill_match()` — `jtt-src/backend/app/services/match_service.py`
- LLM 判断岗位技能是否被简历技能**语义覆盖**（如 `Spring Boot` ↔ `微服务开发`）
- **防幻觉**：LLM 返回结果与岗位技能列表取交集，只保留真实存在的技能
- LLM 不可用/无效 → 降级为规则模糊匹配

**经验相关性评估** `_assess_experience_relevance()` — 同文件
- LLM 综合评估行业对口度、职责匹配、经验年限、技能相关性，返回 0-100 分
- 无工作经历 → 0 分
- LLM 不可用/无效分数 → 降级为计数评分（40 + 经历数×20）

#### 降级策略

| 场景 | 技能匹配 | 经验匹配 |
|------|---------|---------|
| LLM 可用 | 语义匹配 | 相关性评估 |
| LLM 不可用 / 无 API Key | 规则模糊匹配 | 计数评分 |
| LLM 返回无效结构 | 规则模糊匹配 | 计数评分 |
| 无工作经历 | — | 0 分 |

#### 测试

`jtt-src/backend/test/test_match_agent.py` — 4 个测试通过（规则匹配 + 降级逻辑 + 无经历边界）

---

### 2.4 FloatingAIButton：统一入口

**位置**：所有页面的右下角悬浮球
**文件**：`components/common/FloatingAIButton.vue`
**定位**：轻量路由入口，不包含复杂业务逻辑，按需调用各 Agent

| 用户点击 | 行为 |
|----------|------|
| **浏览岗位** | 直接跳转 → 岗位探索页 |
| **学习路径** | 直接跳转 → 学习路径页 |
| **简历优化** | 本地流程 → 列出所有简历 → 点击跳转编辑器 |
| **匹配诊断** | 本地流程 → 选简历 → 算分排序 → 点击跳转结果页 |
| **自由输入** | 调用 `POST /api/assistant/chat` → DeepSeek 通用对话 |
| **上传图片** | 支持文件选择 / Ctrl+V 粘贴 |

**关键设计**：本地流程（简历优化、匹配诊断）不经过 LLM，直接读取 mock 数据生成选项和操作按钮。需要复杂推理时才调用 DeepSeek。

---

## 3. AI 服务架构

```
JTT 前端 (port 5173) → Vite 代理
  │
  ├── /api/assistant/*               → AI 服务 (port 8001) → DeepSeek
  ├── /api/learning/assistant/*      → AI 服务 (port 8001) → DeepSeek
  ├── /api/tailor/optimize-phrase    → AI 服务 (port 8001) → DeepSeek
  │
  └── /api/* (其他)                  → 主后端 (port 8000)
```

**AI 服务端点一览**：

| 端点 | 用途 | 对应 Agent |
|------|------|-----------|
| `POST /api/assistant/chat` | 通用对话 | 所有 |
| `POST /api/assistant/optimize-phrase` | 简历短语润色 | Agent 1 |
| `POST /api/assistant/generate-learning-path` | 联网搜索+生成学习路径 | Agent 2 |
| `POST /api/learning/assistant/chat` | 学习助手对话（同 chat） | Agent 2 |
| `POST /api/learning/assistant/quiz` | 生成测试题 | Agent 2 |
| `POST /api/learning/assistant/recommend-resources` | 推荐学习资源 | Agent 2 |
| `POST /api/learning/assistant/generate-path` | 生成路径（别名） | Agent 2 |
| `POST /api/tailor/optimize-phrase` | 润色（别名） | Agent 1 |

**不再有 MSW mock**：所有 AI 相关端点已移除 mock 处理器，请求直接透传到 AI 服务。

---

## 4. 前端组件对照表

| Agent | 页面 | 前端组件 | 触发操作 |
|-------|------|---------|---------|
| Agent 1 | 简历优化页 | `views/resume/Tailor.vue` | 匹配报告 → 查看建议 → 接受/应用 |
| Agent 1 | 简历编辑器 | `views/resume/Editor.vue` | 点击「AI 优化」→ 选择风格 → 选择版本 |
| Agent 2 | 学习页面 | `views/learning/Index.vue` | AI 助手面板 → 快捷指令（先问清） / 自由对话 |
| Agent 2 | 职业发展页 | `views/career/Index.vue` | 分析差距 → 生成学习路径 |
| Agent 3 | 岗位探索页 | `components/common/QuickMatchFab.vue` | 右下角 `+` → 选择简历 → 查看匹配结果 |
| Agent 3 | 匹配诊断页 | `views/match/Index.vue` | 选择简历 + 岗位 → 获取报告 |
| Agent 3 | 匹配结果页 | `views/match/Result.vue` | 展示分数 / 维度 / 差距 |
| — | 全局入口 | `components/common/FloatingAIButton.vue` | 右下角悬浮球 → 路由/本地流程 |

---

## 5. 文件索引

| 层级 | 文件 | 对应 Agent |
|------|------|-----------|
| 前端页面 | `views/resume/Tailor.vue` | Agent 1 |
| 前端页面 | `views/resume/Editor.vue` | Agent 1 |
| 前端页面 | `views/learning/Index.vue` | Agent 2 |
| 前端页面 | `views/career/Index.vue` | Agent 2 |
| 前端页面 | `views/match/Index.vue` | Agent 3 |
| 前端页面 | `views/match/Result.vue` | Agent 3 |
| 前端组件 | `components/common/FloatingAIButton.vue` | 全局入口 |
| 前端组件 | `components/common/QuickMatchFab.vue` | Agent 3 |
| 前端 API | `api/tailor.ts` | Agent 1 |
| 前端 API | `api/assistant.ts` | 所有 Agent（通用 + 润色 + 路径生成） |
| 前端 API | `api/learning.ts` | Agent 2 |
| 前端 API | `api/match.ts` | Agent 3 |
| 前端 Store | `stores/learning.ts` | Agent 2（localStorage 持久化） |
| 前端 Store | `stores/pageContext.ts` | 全局入口 |
| 前端 Store | `stores/positions.ts` | Agent 3 |
| AI 服务 | `ai-assistant/main.py` | 所有 Agent（DeepSeek 代理） |

---

## 6. 数据流

### 6.1 本地流程（无需 LLM）

```
用户点击 → FloatingAIButton 检测关键词
  → "__resume_optimize__" → 读取 mockResumes → 显示选项按钮
  → "__match_diagnose__" → 读取 mockResumes + mockPositions → 算分排序
  → 点击按钮 → router.push() 跳转
```

### 6.2 AI 流程（需 LLM）

```
用户输入问题 → FloatingAIButton / 学习页面 AI 面板
  → POST /api/assistant/chat（或 learning/assistant/chat）
  → AI 助手服务 (port 8001)
  → DeepSeek API
  → 结构化回复（Markdown + 概念标签 + 资源推荐 + 追问按钮）
```

### 6.3 Agent 专用流程

```
Agent 1 润色 → POST /api/assistant/optimize-phrase → DeepSeek → 3 个版本
Agent 2 路径 → POST /api/assistant/generate-learning-path → 搜索 + DeepSeek → 结构化路径（localStorage 持久化）
Agent 2 测试 → POST /api/learning/assistant/quiz → DeepSeek → 5 道选择题
Agent 2 资源 → POST /api/learning/assistant/recommend-resources → DeepSeek → 资源列表
Agent 3 匹配 → POST /match/auto → mock 计算 → 排序结果
```

---

## 7. 注意事项

1. **FloatingAIButton 保持轻量**：只做路由和上下文注入，复杂逻辑由各 Agent 专用组件承载
2. **本地流程优先**：简历列表、岗位列表等前端已有数据，不经过 LLM
3. **AI 端点无 mock**：所有 AI 相关端点不再使用 MSW 拦截，直通 DeepSeek
4. **路径持久化**：AI 生成的学习路径自动保存到 localStorage，刷新不丢失
5. **快捷指令先问清**：4 个快捷指令均先询问具体需求再处理，不预设硬编码内容
6. **新 Agent 接入**：在 `presetPages` 和 `tryLocalFlow()` 中添加新入口即可
