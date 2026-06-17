# 知识图谱 & 岗位更新 & 新岗位发现 — 架构与开发方案

> 基于五层技能森林结构，Neo4j 图数据库存储，Agent 辅助抽取，动态更新

---

## 一、五层技能森林数据模型

### 1.1 Neo4j 节点设计

```
节点标签：
  Job           — 岗位（第1层）
  SkillArea     — 技能领域（第2层）
  TechStack     — 技术栈（第3层）
  TechPoint     — 技术细节点（第4层）
  KnowledgePoint — 知识要点（第5层）
```

| 层级 | 标签 | 属性 | 示例 |
|------|------|------|------|
| L1 | `Job` | `{name, aliases[], description, source, updated_at}` | `Python开发工程师` |
| L2 | `SkillArea` | `{name, category, importance}` | `Python后端`, `前端`, `数据库` |
| L3 | `TechStack` | `{name, category, frequency}` | `Django`, `Flask`, `Vue`, `MySQL` |
| L4 | `TechPoint` | `{name, detail, frequency}` | `Flask-蓝图注册`, `Vue-生命周期` |
| L5 | `KnowledgePoint` | `{name, description, difficulty, interview_weight}` | `蓝图注册流程与最佳实践` |

### 1.2 关系设计

```
(Job)-[:REQUIRES_AREA {importance: 0.9}]->(SkillArea)
(SkillArea)-[:CONTAINS {frequency: 15}]->(TechStack)
(TechStack)-[:REFINES_TO {frequency: 8}]->(TechPoint)
(TechPoint)-[:HAS_KNOWLEDGE {difficulty: '中级'}]->(KnowledgePoint)

// 跨树共享（森林结构）
(TechStack)-[:RELATED_TO {strength: 0.7}]->(TechStack)
(TechPoint)-[:SAME_AS {confidence: 0.95}]->(TechPoint)
(KnowledgePoint)-[:PREREQUISITE]->(KnowledgePoint)
```

**关键设计**：同一 TechPoint（如"索引优化"）可被多个 TechStack（MySQL、PostgreSQL）通过 `REFINES_TO` 连接，天然形成森林。`SAME_AS` 关系处理跨岗位的技能点重合。

### 1.3 各层级用途

```
L1-L3  → 生成岗位 JD 描述（技能领域+技术栈列举）
L4     → 简历解析匹配（精确到技术细节点）
L5     → 面试问题生成（知识要点可作为面试考察点）
```

---

## 二、数据 Pipeline

```
┌──────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────┐
│ 爬虫采集  │ →  │ Agent 预处理 │ →  │ Agent 技能抽取│ →  │ Neo4j   │
│ (定时/手动)│    │ 去重/消歧/清洗│    │ 五层结构化输出 │    │ 增量写入 │
└──────────┘    └─────────────┘    └──────────────┘    └─────────┘
                                                              ↓
                                                     ┌──────────────┐
                                                     │ 后端 API 读取 │
                                                     │ (实时查询图谱) │
                                                     └──────────────┘
```

### 2.1 爬虫采集
- 复用现有 `data_analysis/` 数据作为初始源
- 新增定时爬虫模块（Scrapy + Playwright），目标 ≥3 个招聘网站
- 输出固定 JSON 格式（对齐 `data/jd_crawl_ifly.json` 字段）

### 2.2 Agent 预处理
- **去重**：基于 title + company + posted_at 复合键
- **岗位名标准化**：AI 消歧（"Java开发" = "Java工程师" = "Java软件工程师"）
- **格式清洗**：统一 salary 单位、地点格式、日期格式

### 2.3 Agent 技能抽取（核心）
调用 DeepSeek API，输入为单条 JD 的 `jd_text + responsibilities + requirements`，输出为五层结构化 JSON：

```json
{
  "job_title": "Python开发工程师",
  "skill_areas": [
    {
      "name": "Python后端",
      "importance": 0.95,
      "tech_stacks": [
        {
          "name": "Flask",
          "frequency": 8,
          "tech_points": [
            {"name": "蓝图注册", "detail": "模块化路由管理"},
            {"name": "API设计", "detail": "RESTful接口规范"}
          ],
          "knowledge_points": [
            {"name": "Flask蓝图注册流程", "description": "...",
             "difficulty": "中级", "interview_weight": 0.7}
          ]
        }
      ]
    }
  ]
}
```

### 2.4 Neo4j 增量写入
- 检查节点是否存在（按 name + 层级去重）
- 不存在 → 创建新节点
- 已存在 → 更新 frequency 计数，追加来源引用
- 共享节点：如果两个岗位的 TechPoint 相同（如"索引优化"），自动建立 `SAME_AS` 关系

---

## 三、三个模块的 API 设计

### 3.1 知识图谱模块

```
GET  /api/v1/graph/panorama?stack=ai&level=senior   # 全景视图（按技术栈/级别过滤）
GET  /api/v1/graph/node/{label}/{id}                  # 节点详情（含子节点）
GET  /api/v1/graph/expand?node_id=X&depth=2           # 展开节点子树
GET  /api/v1/graph/search?q=Python&types=SkillArea    # 模糊搜索
GET  /api/v1/graph/path?from=X&to=Y                   # 两节点间路径
GET  /api/v1/graph/tree/{job_title}                   # 某岗位的完整五层树
```

### 3.2 现有岗位能力更新模块

```
GET  /api/v1/jobs/{id}/versions                       # 版本历史列表
GET  /api/v1/jobs/{id}/diff?v1=xxx&v2=yyy             # 两版本技能差异
GET  /api/v1/jobs/{id}/trend?months=6                 # 6个月内技能变化趋势

// 差异输出格式
{
  "job_title": "Java开发工程师",
  "changes": [
    {"skill": "RAG", "change": "added", "first_seen": "2026-03", "frequency_growth": "+340%"},
    {"skill": "Struts", "change": "declining", "frequency_drop": "-60%"},
    {"skill": "Spring Boot", "change": "stable"}
  ]
}
```

实现原理：每次爬虫更新后，对同一岗位的新旧图谱做 diff 对比。`TechStack` 节点的 `frequency` 变化即为趋势信号。

### 3.3 新岗位发现模块

```
POST  /api/v1/jobs/discover/trigger                   # 触发新岗位检测
GET   /api/v1/jobs/discover                           # 候选新岗位列表
GET   /api/v1/jobs/discover/{id}                      # 新岗位详情
PUT   /api/v1/jobs/discover/{id}                      # 人工审核/修改定义
POST  /api/v1/jobs/discover/{id}/approve              # 确认为新岗位 → 写入图谱
```

**发现算法**：
1. 聚类新出现的技能组合（技能共现频率突增超过阈值）
2. 如果某技能组合不属于任何现有 `Job` 节点 → 标记为候选新岗位
3. Agent 生成岗位定义（名称、核心职责、技能要求、应用场景）
4. 人工审核后可手动添加用户偏好（如目标行业、技术方向），系统据此定向搜索

---

## 四、用户手动输入支持

```
POST  /api/v1/user/preferences                        # 设置偏好
{
  "target_industries": ["AI", "物联网"],
  "target_skills": ["大模型", "边缘计算"],
  "alert_frequency": "weekly"                         # 周报/即时
}

GET   /api/v1/user/preferences                        # 查看当前偏好
POST  /api/v1/jobs/discover/custom                    # 手动提交技能组合 → 系统匹配
{
  "skills": ["Python", "PyTorch", "CUDA", "模型部署"],
  "context": "AI推理优化方向"
}
// → 返回：该系统是否有匹配的岗位？需要补充哪些技能？关联哪些现有岗位？
```

---

## 五、动态更新机制

```
┌──────────────────────────────────────────────────┐
│  Celery Beat 定时任务                              │
│  ├── 每周一 02:00  → 爬虫全量采集                  │
│  ├── 每日 06:00   → 增量爬取 + 数据预处理           │
│  ├── 采集完成后    → Agent 技能抽取 + Neo4j 增量写入 │
│  └── 每周一 08:00  → 新岗位检测 + 能力变更分析       │
└──────────────────────────────────────────────────┘
```

- 图谱中的 `updated_at` 时间戳记录每次更新
- 前端通过轮询或 WebSocket 获取最新数据
- 版本化存储：每次全量更新创建 `GraphSnapshot` 节点

---

## 六、Neo4j 索引与性能

```cypher
CREATE INDEX job_name FOR (j:Job) ON (j.name);
CREATE INDEX skill_name FOR (s:SkillArea) ON (s.name);
CREATE INDEX tech_name  FOR (t:TechStack) ON (t.name);
CREATE INDEX point_name FOR (p:TechPoint) ON (p.name);
CREATE FULLTEXT INDEX job_ft FOR (j:Job) ON EACH [j.name, j.description];
```

---

## 七、开发阶段

### Phase 1：Neo4j 集成 + 数据模型（1 周）
- [ ] 安装 Neo4j，配置 `neo4j.conf`
- [ ] 编写 `core/database.py` 增加 Neo4j 驱动连接
- [ ] 编写 `models/graph.py` 定义节点/关系常量
- [ ] 编写 `services/graph_service.py`：CRUD + 五层树查询
- [ ] 编写 `api/v1/graph.py`：替换占位路由

### Phase 2：Agent 技能抽取 Pipeline（1.5 周）
- [ ] 编写 `services/agent_service.py`：DeepSeek 调用封装
- [ ] 编写 `services/skill_extract_service.py`：JD → 五层结构化输出
- [ ] 编写 `services/data_preprocess_service.py`：去重+消歧+清洗
- [ ] 编写 `tasks/crawl_to_graph.py`：Celery 任务链

### Phase 3：岗位能力更新 + 新岗位发现（1 周）
- [ ] 编写 `services/change_detection_service.py`：版本 diff + 趋势
- [ ] 编写 `services/discover_service.py`：技能聚类 + 候选生成
- [ ] 编写 `api/v1/changes.py` + `api/v1/jobs.py`（替换占位）
- [ ] 编写 `api/v1/user_preferences.py`

### Phase 4：动态更新 + 联调（0.5 周）
- [ ] Celery Beat 定时任务配置
- [ ] 前端图谱页面联调
- [ ] 端到端验证：爬虫 → 图谱 → API → 前端

---

> **状态**：等待确认后开始开发
