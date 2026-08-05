# 智能体产品需求文档

> 智联职引 —— 人才分析与决策系统  
> 版本: 0.1.0 | 更新: 2026-07-20

---

## 1. 概述

### 1.1 项目背景

智联职引是一个 AI 驱动的人才分析与决策系统，帮助求职者完成从"探索岗位"到"诊断简历"再到"规划学习"的完整职业发展闭环。系统包含三个核心智能体（Agent），分别覆盖简历优化、学习路径、岗位匹配三大场景。

### 1.2 智能体总览

| 编号 | 智能体名称 | 定位 | 触发场景 | 后端 Service | 前端组件 |
|------|-----------|------|----------|-------------|---------|
| Agent 1 | 简历优化智能体 | 基于岗位需求优化简历内容，识别技能差距 | 匹配诊断报告 / 简历编辑器 | `TailorService` | `MatchPanel.vue` / `Editor.vue` |
| Agent 2 | 学习助手智能体 | 生成学习路径、推荐资源、答疑解惑 | 学习页面 / 职业发展页 | `LearningService` | `learning/Index.vue` / `career/Index.vue` |
| Agent 3 | 智能匹配智能体 | 简历与岗位的智能匹配与解读 | 岗位探索页 "+" / 简历诊断页 | `MatchService` | `QuickMatchFab.vue` / `diagnosis/Index.vue` |

### 1.3 LLM 配置

- **模型**: DeepSeek（通过 OpenAI 兼容接口调用）
- **配置位置**: `backend/app/core/config.py` → `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`
- **调用方式**: `backend/app/providers/llm.py` → `DeepSeekProvider`
- **超时**: 90 秒（路径生成 / 优化建议）/ 30 秒（普通对话）
- **温度**: 0.3（降低随机性，保证输出稳定）
- **重试**: 最多 3 次，指数退避（1s → 2s → 失败）
- **降级兜底**: 所有 Agent 都有 LLM → 规则降级的双路径，LLM 不可用时不阻塞功能

### 1.4 知识图谱（Neo4j）

所有 Agent 均集成 Neo4j 知识图谱，核心用途：

- **防幻觉**（Agent 1）: AI 生成的技能建议回查图谱，验证技能是否属于目标岗位的技能树
- **技能依赖关系**（Agent 2）: 查询岗位的技能层级（Position → SkillsetBranch → Module → Knowledge），决定学习顺序
- **上下文增强**（Agent 2）: 对话时注入图谱中的关联概念节点
- **数据模型**: `(Position)-[:COMPOSES]->(SkillsetBranch)-[:CONTAINS]->(Module)-[:INCLUDES]->(Knowledge)`

---

## 2. Agent 1: 简历优化智能体

### 2.1 职责定位

分析用户简历与目标岗位之间的差距，生成**具体、可执行**的修改建议。覆盖两个用户场景：

- **场景 A（诊断优化）**: 在匹配诊断报告中，对简历的每个模块（技能、工作经历、自我评价）生成逐条优化建议
- **场景 B（编辑润色）**: 在简历编辑器中，对单段文本（工作描述、自我评价）进行 AI 润色改写

两个场景由**同一个 Agent 统一处理**，共享底层 LLM 和 Prompt 体系。

### 2.2 场景 A: 诊断优化 —— 交互流程

```
用户在简历诊断页展开匹配报告
  → 看到匹配分数、维度评分、技能差距分析
  → 点击「一键优化简历」
  → 系统调用 POST /tailor/suggestions/{resumeId}/{positionId}
  → 返回建议列表，每条含: 模块 | 原文 | 优化后 | 理由 | 改动大小
  → 用户逐条「接受」或「拒绝」
  → 已接受的建议高亮（绿色边框）
  → 点击「应用已接受的建议到简历」
  → 系统调用 POST /tailor/apply-all → 生成新版简历（标题加 "AI优化版"）
  → 提示成功
```

#### 输出示例

| 字段 | 说明 | 示例 |
|------|------|------|
| section | 简历模块 | `skills` / `workExperience` / `selfEvaluation` |
| original | 原文 | `熟悉 Java 开发` |
| suggested | 优化后 | `精通 Java 及 Spring Boot 微服务开发，具备高并发系统设计经验` |
| reason | 理由 | `在技能描述中体现具体技术栈和解决过的问题，更能吸引招聘方` |
| changeType | 改动大小 | `small`（微调）/ `large`（大改） |
| verified | 图谱校验 | `true`（已通过）/ `false`（未通过，附 warning） |

### 2.3 场景 B: 编辑润色 —— 交互流程

```
用户在简历编辑器中输入工作描述或自我评价
  → 点击「AI 优化」
  → 选择润色风格: 更专业 / 更简洁 / 更匹配 / 更有冲击力
  → 系统调用 POST /tailor/optimize-phrase
  → 返回 3 个改写版本
  → 用户点击其中一个版本 → 替换原文
```

#### 润色风格说明

| 风格 | 适用场景 | 效果 |
|------|---------|------|
| `professional` | 正式场合 | 用词专业、句式完整 |
| `concise` | 简历空间有限 | 精简表达、去掉冗余 |
| `match` | 对标岗位 | 突出与目标岗位相关的关键词 |
| `impact` | 展示成果 | 用数据化、结果导向表达 |

### 2.4 System Prompt（诊断优化）

```
你是专业的简历优化专家。根据目标岗位要求，为求职者的简历提供具体修改建议。
输出严格的 JSON 对象：{"suggestions": [...]}，每条建议包含：
  id (字符串), section (skills/workExperience/education/selfEvaluation),
  field (具体字段), original (原文), suggested (优化后), reason (理由),
  changeType (small=小改/large=大改)
只输出技能、工作经历中可以实际对照岗位优化的内容，不要编造不存在的技能或经验。
```

### 2.5 System Prompt（编辑润色）

```
你是简历文字润色专家。将用户提供的文本改写为更{style_desc}的版本。
输出 JSON: {"suggestions": ["版本1", "版本2", "版本3"]}
每个版本 30 字以内，保持原意但表达更精炼专业。
```

### 2.6 API 接口

| 方法 | 路径 | 说明 | 超时 |
|------|------|------|------|
| GET | `/api/v1/tailor/suggestions/{resumeId}/{positionId}` | 生成优化建议列表 | 90s |
| POST | `/api/v1/tailor/apply-all` | 批量应用建议，生成新版简历 | 30s |
| POST | `/api/v1/tailor/accept` | 记录单条建议的接受状态 | 10s |
| POST | `/api/v1/tailor/optimize-phrase` | 短语润色 | 90s |

#### POST /tailor/apply-all 请求体

```json
{
  "resume_id": 1,
  "suggestion_ids": ["sg-1", "sg-3"],
  "suggestions": [
    {
      "id": "sg-1", "section": "skills", "field": "skills",
      "original": "", "suggested": "LangChain 框架应用",
      "reason": "目标岗位必备技能", "change_type": "large", "accepted": true
    }
  ]
}
```

#### 响应

```json
{
  "code": 200,
  "message": "ok",
  "data": { "new_resume_id": 2 }
}
```

### 2.7 降级策略

当 LLM 不可用时，TailorService._fallback_suggestions() 基于规则生成建议：

1. **技能层面**: 模糊匹配简历技能 ↔ 岗位技能，找出缺失的必备技能 + 加分技能
2. **生成建议**: 
   - 缺失技能 → `"学习并添加技能: {技能名}"`（大改）
   - 加分技能 → `"补充加分技能: {技能名}"`（小改）
3. **自我评价**: 将被匹配的核心技能追加到自我评价末尾
4. **编辑润色**: LLM 不可用时原文返回

### 2.8 知识图谱防幻觉

每条 AI 生成的技能建议在返回前经过 Neo4j 校验：

```
MATCH (p:Position {id: $pid})-[:COMPOSES|CONTAINS|INCLUDES*1..3]->(k:Knowledge)
RETURN collect(k.label) AS skills
```

- 建议中的技能名在图谱中存在 → `verified: true`, 无警告
- 技能名不在图谱中 → `verified: true`, 附带 `warning: "部分建议的技能未在知识图谱中充分验证，请人工确认"`
- Neo4j 不可用 → 跳过校验，标记 `verified: true`

---

## 3. Agent 2: 学习助手智能体

### 3.1 职责定位

围绕用户的学习需求提供全方位 AI 支持：

1. **生成学习路径**: 根据岗位技能要求和用户现状，生成分步骤的学习计划（含周期估算）
2. **推荐学习资源**: 根据学习内容推荐视频、网站、书籍、项目
3. **智能问答**: 解答学习相关问题（技术概念、转行建议、学习方法）
4. **学习测试**: 根据已完成的步骤生成测试题，错题可收藏
5. **技能差距分析**: 对比用户技能 vs 岗位要求，识别待学习技能

### 3.2 用户交互流程

#### 场景 A: 生成学习路径

```
触发方式:
  1. 匹配诊断报告 → 点击「生成学习路径」
  2. 职业发展页 → 分析技能差距后 → 点击「生成学习路径」
  3. 学习页面 → 点击快捷指令「生成学习路径」
  4. 学习页面 → AI 对话中输入需求

流程:
  系统收集: 目标岗位信息 + 岗位技能列表 + 用户简历已有技能 + Neo4j 技能依赖关系
  → LLM 分析技能差距，按"先基础后进阶"排序
  → 生成 4-6 个学习步骤，每个步骤包含:
    - 标题、描述、预计周数
    - 学习资源（课程/书籍/文章/视频 + 推荐平台）
  → 展示为路径卡片，可展开查看步骤流程图和时间线
  → 用户可标记步骤完成、重命名路径、删除路径
```

#### 场景 B: AI 学习助手对话

```
学习页面左侧面板 → 两种交互方式:

  方式 1（快捷指令）: 4 个预设按钮
    - 生成学习路径: "请根据 {岗位名} 岗位，为我生成一份学习路径"
    - 推荐学习资源: "推荐 {技能名} 的学习资源"
    - 学习路线咨询: "我是一名后端开发，想转行 AI 方向，应该怎么学？"
    - 技能差距分析: "分析我当前技能与目标岗位的差距"

  方式 2（自由对话）: 输入任意问题
    - "LangChain 是什么？需要什么前置知识？"
    - "微服务架构的学习路线是什么？"
    - "Kubernetes 和 Docker 有什么区别？"

系统处理:
  构建上下文（岗位图谱 + 用户简历技能）
  → LLM 生成回复（Markdown 格式）
  → 提取图谱中的关联概念节点（"你可能还想了解..."）
  → 推荐相关学习资源（含类型图标和外部链接）
  → 生成建议追问
```

#### 场景 C: 学习测试

```
学习路径卡片 → 点击「学习测试」
  → 系统选择已完成的步骤作为测试范围
  → 调用 POST /learning/assistant/quiz
  → 生成选择题（选项 A-D）+ 解析
  → 用户作答 → 提交 → 显示正确/错误 + 解析
  → 错题可「加入错题本」（收藏到 quiz_error 类型）
```

### 3.3 System Prompt（对话）

```
你是专业的学习导师和职业规划顾问。你的任务是：
1. 结合知识图谱中的岗位-技能关系，给出准确的职业建议
2. 解释技术概念时，说明前置知识和学习路径
3. 推荐具体的学习资源（课程、书籍、项目）
4. 回答简洁专业，用 Markdown 格式

当前知识图谱上下文:
{graph_context}

用户简历技能: {user_skills}
```

### 3.4 System Prompt（路径生成）

```
你是学习路径设计师。根据目标岗位的技能要求、知识图谱的技能依赖关系、
以及用户现有技能，设计一个分步骤的学习路径。
输出 JSON: {"name": "路径名", "steps": [{"title": "步骤名",
  "description": "描述", "duration": "X周",
  "resources": [{"title": "资源名", "type": "course/book/article/video",
  "url": "", "platform": "推荐平台"}]}]}
```

### 3.5 API 接口

| 方法 | 路径 | 说明 | 超时 |
|------|------|------|------|
| GET | `/api/v1/learning/paths` | 获取用户所有学习路径 | 10s |
| POST | `/api/v1/learning/paths` | 创建学习路径 | 10s |
| PUT | `/api/v1/learning/paths/{id}` | 更新路径（名称/步骤/完成状态） | 10s |
| DELETE | `/api/v1/learning/paths/{id}` | 删除路径 | 10s |
| POST | `/api/v1/learning/assistant/chat` | AI 学习助手对话 | 90s |
| POST | `/api/v1/learning/assistant/generate-path` | AI 生成学习路径 | 90s |
| POST | `/api/v1/learning/assistant/recommend-resources` | 按技能名推荐资源 | 90s |
| POST | `/api/v1/learning/assistant/quiz` | 生成学习测试题 | 90s |

#### POST /learning/assistant/chat 请求/响应

```json
// 请求
{
  "message": "我想从 Java 后端转 AI Agent 开发，应该怎么学？",
  "context": {
    "resume_id": 1,
    "target_position_id": "np-1"
  },
  "history": [
    { "role": "user", "content": "你好" },
    { "role": "assistant", "content": "你好！有什么可以帮你的？" }
  ]
}

// 响应
{
  "code": 200,
  "data": {
    "reply": "从 Java 后端转 AI Agent 开发，建议按以下路线...",
    "related_concepts": [
      { "name": "LangChain", "node_id": "...", "relation": "Knowledge" }
    ],
    "suggested_resources": [
      { "title": "LangChain 入门到实战", "type": "course", "platform": "慕课网" }
    ],
    "follow_up_questions": [
      "需要哪些前置知识？", "学习周期大概多久？"
    ]
  }
}
```

#### POST /learning/assistant/generate-path 请求/响应

```json
// 请求
{
  "position_id": 1,
  "resume_id": 1
}

// 响应
{
  "code": 200,
  "data": {
    "name": "AI Agent 工程师学习路径",
    "position_id": 1,
    "position_name": "AI Agent 工程师",
    "steps": [
      {
        "id": "step-a1b2c3d4",
        "order": 1,
        "title": "掌握 Python 基础",
        "description": "学习 Python 语法、数据处理、异步编程...",
        "duration": "2周",
        "completed": false,
        "resources": [
          {
            "id": "res-e5f6g7h8",
            "title": "Python 入门到实战",
            "type": "course",
            "url": "",
            "platform": "慕课网 / B站"
          }
        ]
      }
    ],
    "total_duration": "10周"
  }
}
```

### 3.6 降级策略

当 LLM 不可用时，`_fallback_plan()` 基于规则生成学习路径：

1. 对比用户已有技能 ↔ 岗位必备/加分技能（模糊匹配）
2. 缺失技能按优先级排列：必备技能在前，加分技能在后
3. 每个缺失技能生成一个学习步骤（2周/步，最多 5 步）
4. 末尾追加「综合实战与作品集」步骤
5. 资源推荐使用通用平台（慕课网 / B站 / GitHub）
6. 对话降级返回: "AI 助手暂时不可用，请稍后重试。"

### 3.7 知识图谱集成

**学习路径生成时**:
```
MATCH (p:Position {id: $pid})-[:COMPOSES]->(s:SkillsetBranch)
  -[:CONTAINS]->(m:Module)-[:INCLUDES]->(k:Knowledge)
RETURN s.label AS skillset, m.label AS module, collect(k.label) AS knowledge
```
→ 输出注入 LLM Prompt 作为"图谱技能树"，决定学习依赖顺序

**对话时**:
```
MATCH (p:Position {id: $pid})-[:COMPOSES*1..3]->(related)
RETURN related.label AS label, related.type AS type
```
→ 输出注入 System Prompt 作为"知识图谱上下文"

**关联概念提取**:
```
MATCH (n) WHERE n.label CONTAINS $keyword
RETURN n.id AS id, n.label AS label, n.type AS type LIMIT 5
```

---

## 4. Agent 3: 智能匹配智能体

### 4.1 职责定位

将用户简历与系统中所有岗位进行匹配，按匹配度排序返回结果。当前为规则引擎，计划升级为 LLM 驱动的语义匹配。

### 4.2 用户交互流程

```
岗位探索页 → 右下角 "+" 按钮
  → 弹出简历选择面板（列出用户所有简历）
  → 用户选择一份简历
  → 系统调用 POST /match/auto/{resumeId}
  → 返回所有岗位的匹配结果，按分数降序排列
  → 弹窗展示:
    - 每个岗位一行: 岗位名 + 匹配分（颜色: 绿≥80 / 黄≥50 / 红<50）
    - 点击某行 → 跳转到对应岗位详情页
```

### 4.3 匹配算法（当前规则版）

| 维度 | 权重 | 评分依据 |
|------|------|---------|
| 技能匹配 | 40% | 模糊匹配简历技能 ↔ 岗位技能（词元拆分 + 中文包含关系），必备技能权重 70%，加分技能权重 30% |
| 经验匹配 | 30% | 基于工作经历数量（0段=30 分, 每段+20, 上限 100） |
| 学历匹配 | 15% | 基于教育经历数量（0段=50 分, 每段+20, 上限 100） |
| 综合素质 | 15% | 基于项目数量（每项+25）+ 自我评价长度（≥20字+25） |

**模糊匹配逻辑** (`_skill_names_match`):
1. 全名相等（忽略大小写）
2. 词元交集: "LangChain" ↔ "LangChain / LangGraph"、"RAG" ↔ "RAG 检索增强生成"
3. 中文包含: "微服务" ↔ "微服务架构"

### 4.4 升级方向（AI 增强）

| 维度 | 当前（规则） | 升级后（LLM） |
|------|-------------|--------------|
| 技能匹配 | 词元模糊匹配 | **语义级匹配**: "懂 Python 数据分析" ↔ "Pandas/NumPy 经验"，识别同义词、上下位关系 |
| 维度解读 | 数值统计文字 | **自然语言解读**: "您的 Python 技能完全满足要求，但缺少 LangChain 框架经验，这是该岗位的核心要求" |
| 结果排序 | 纯分数降序 | **语义排序**: 结合岗位描述与简历内容的深层匹配度微调排序 |
| 技能推断 | 无 | **隐性技能推断**: 从项目描述中推断未显式列出的技能 |

### 4.5 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/match` | 单次人岗匹配（简历 vs 单个岗位） |
| POST | `/api/v1/match/batch` | 批量匹配（简历 vs 多个岗位） |
| POST | `/api/v1/match/auto/{resume_id}` | **[Agent 3]** 自动匹配简历 vs 所有岗位，按分数降序返回 |
| GET | `/api/v1/match/result/{resume_id}/{position_id}` | 获取已有匹配结果 |
| GET | `/api/v1/match/history` | 获取用户匹配历史 |

#### POST /match/auto/{resume_id} 响应

```json
{
  "code": 200,
  "data": [
    {
      "id": 1,
      "resume_id": 1,
      "position_id": 1,
      "position_name": "AI Agent 工程师",
      "resume_name": "Java后端开发简历",
      "total_score": 68,
      "dimensions": [
        { "name": "技能匹配", "score": 72, "weight": 0.4,
          "details": "匹配 3/7 项技能，缺失 4 项" },
        { "name": "经验匹配", "score": 65, "weight": 0.3,
          "details": "2 段工作经历" },
        { "name": "学历匹配", "score": 80, "weight": 0.15,
          "details": "1 段教育经历" },
        { "name": "综合素质", "score": 55, "weight": 0.15,
          "details": "1 个项目，有自我评价" }
      ],
      "gap_analysis": {
        "missing_skills": [
          { "name": "智能体开发", "level": "required", "category": "AI集成" }
        ],
        "weak_skills": [
          { "name": "LLM API 集成", "level": "preferred", "category": "AI集成" }
        ],
        "match_skills": [
          { "name": "Java", "level": "required", "category": "编程语言" }
        ]
      },
      "suggestions": [...],
      "match_date": "2026-07-20T10:30:00"
    }
  ]
}
```

### 4.6 降级策略

当前匹配算法为纯规则引擎，不依赖 LLM，因此**无降级问题**。升级为 AI 匹配后：
- LLM 可用: 语义匹配 + 自然语言解读
- LLM 不可用: 退回当前规则算法作为 baseline

---

## 5. 附录

<<<<<<< HEAD
### 5.1 前端组件对照表
=======
### 5.1 AI 助手独立服务（选项 A）

JTT 前端 AI 浮窗（FloatingAIButton）支持接入真实大模型，通过独立的 LLM 代理服务实现，**不依赖 MySQL/Neo4j/Redis**。

#### 架构

```
JTT 前端 (port 5173)
  │
  ├── /api/assistant/chat ──────────► AI 助手服务 (port 8001) ──► DeepSeek API
  │                                    (standalone, 仅需 API Key)
  │
  └── /api/* （其他请求）────────────► 主后端 (port 8000)
                                       (需 MySQL + Neo4j)
```

#### 位置

`jtt-src/ai-assistant/` — 完整的独立服务，含 README 和配置模板。

#### 快速启动

```bash
cd jtt-src/ai-assistant
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

详见 `jtt-src/ai-assistant/README.md`。

#### API 端点

| 方法 | 路径 | 说明 | 超时 |
|------|------|------|------|
| POST | `/api/assistant/chat` | AI 对话（支持上下文+页面数据） | 60s |
| GET | `/health` | 健康检查 | — |

#### 降级策略

AI 助手服务不可用时（服务未启动或无 API Key）：
- 前端请求会返回 503 错误
- FloatingAIButton 显示"AI 服务暂不可用"提示
- 其他业务功能（岗位浏览、简历管理、匹配诊断）不受影响

### 5.2 前端组件对照表
>>>>>>> 2c75d7d (feat(jtt): AI assistant DeepSeek integration + career page + auto-match + path persistence)

| Agent | 页面 | 前端组件 | 触发操作 |
|-------|------|---------|---------|
| Agent 1 | 简历诊断页 | `diagnosis/Index.vue` + `MatchPanel.vue` | 展开匹配报告 → 查看建议 → 接受/应用 |
| Agent 1 | 简历编辑器 | `resume/Editor.vue` | 点击「AI 优化」→ 选择风格 → 选择版本 |
| Agent 2 | 学习页面 | `learning/Index.vue` | AI 助手面板 → 快捷指令 / 自由对话 |
| Agent 2 | 职业发展页 | `career/Index.vue` | 分析差距 → 「生成学习路径」 |
| Agent 3 | 岗位探索页 | `QuickMatchFab.vue` | 右下角 "+" → 选择简历 → 查看匹配结果 |
| Agent 3 | 简历诊断页 | `diagnosis/Index.vue` | 展开简历 → 自动加载匹配结果 |

<<<<<<< HEAD
### 5.2 LLM Provider 配置

```
# backend/app/core/config.py
LLM_API_KEY = "your-deepseek-api-key"    # 当前为占位符，替换为真实 key 后生效
LLM_BASE_URL = "https://api.deepseek.com"
LLM_MODEL = "deepseek-chat"
LLM_TIMEOUT_SECONDS = 90
TESTING = False  # True 时使用 MockLLMProvider，不调用真实 API
```

### 5.3 Neo4j 图谱 Schema
=======
### 5.3 LLM Provider 配置

#### 主后端（FYZ，全功能模式）

```
# fyz-src/backend/.env
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_TIMEOUT_SECONDS=60
```

#### AI 助手独立服务（JTT，选项 A）

```
# jtt-src/ai-assistant/.env
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT_SECONDS=60
SERVICE_PORT=8001
```

### 5.4 Neo4j 图谱 Schema
>>>>>>> 2c75d7d (feat(jtt): AI assistant DeepSeek integration + career page + auto-match + path persistence)

```
(Position {id, name})
  -[:COMPOSES]-> (SkillsetBranch {label})      -- 技能分支
    -[:CONTAINS]-> (Module {label})             -- 技能模块
      -[:INCLUDES]-> (Knowledge {label})         -- 知识点

(Skill {name, level, kind})                      -- 岗位技能（存储在 SQL 中）
(SkillChange {skill_name, change_type, description}) -- 技能变化历史
```

<<<<<<< HEAD
### 5.4 文件索引
=======
### 5.5 文件索引
>>>>>>> 2c75d7d (feat(jtt): AI assistant DeepSeek integration + career page + auto-match + path persistence)

| 层级 | 文件 | 对应 Agent |
|------|------|-----------|
| 后端 Service | `app/services/tailor_service.py` | Agent 1 |
| 后端 Service | `app/services/learning_service.py` | Agent 2 |
| 后端 Service | `app/services/match_service.py` | Agent 3 |
| 后端 API | `app/api/v1/tailor.py` | Agent 1 |
| 后端 API | `app/api/v1/learning.py` | Agent 2 |
| 后端 API | `app/api/v1/match.py` | Agent 3 |
| 后端 LLM | `app/providers/llm.py` | 所有 Agent |
| 后端 图谱 | `app/core/neo4j.py` | Agent 1, 2 |
| 前端组件 | `components/diagnosis/MatchPanel.vue` | Agent 1 |
| 前端组件 | `components/common/QuickMatchFab.vue` | Agent 3 |
| 前端视图 | `views/learning/Index.vue` | Agent 2 |
| 前端视图 | `views/resume/Editor.vue` | Agent 1 |
| 前端视图 | `views/career/Index.vue` | Agent 2 |
| 前端 Store | `stores/match.ts` | Agent 1, 3 |
| 前端 Store | `stores/learning.ts` | Agent 2 |
| 前端 API | `api/tailor.ts` | Agent 1 |
| 前端 API | `api/learning.ts` | Agent 2 |
| 前端 API | `api/match.ts` | Agent 3 |
<<<<<<< HEAD
=======
| 前端 API | `api/assistant.ts` | 全局 AI 助手 |
| 前端组件 | `components/common/FloatingAIButton.vue` | 全局 AI 助手 |
| 前端 Store | `stores/pageContext.ts` | 全局 AI 助手 |
| AI 服务 | `ai-assistant/main.py` | 全局 AI 助手（选项 A） |
>>>>>>> 2c75d7d (feat(jtt): AI assistant DeepSeek integration + career page + auto-match + path persistence)
