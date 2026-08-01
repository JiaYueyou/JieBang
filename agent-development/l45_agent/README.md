# L4/L5 早期原型说明

`agent-development/l45_agent/` 是早期 L4/L5 补全原型。当前生产运行时已经迁移到：

```text
agent-development/src/jiebang_agents/graph_enrichment/
```

后端不再使用 `fyz-src/backend/scripts/05_enrich_l45.py` 或
`run_all_l45.py` 直接写 Neo4j。旧脚本无法表达当前的机器校验、人工审核、发布
状态、乐观锁、异步进度和失败审计，因此已从仓库移除。

## 当前调用链

```text
POST /api/v1/graph/enrichment/generate
→ GraphTaskService 创建异步任务
→ SkillGraphCompletionAgent 生成结构化 L4/L5 候选
→ GraphService 保存机器校验状态和证据
→ 管理员批准或驳回候选
→ POST /api/v1/graph/enrichment/publish
→ 发布任务增量同步 Neo4j
```

任务进度通过 `GET /api/v1/tasks/{task_id}` 查询。正式图谱只接收已经批准并进入
发布状态的候选，不允许 Agent 或脚本绕过 MySQL 审核记录直接写图。

## 当前测试

```powershell
cd agent-development
python -m pytest tests -q

cd ..\fyz-src\backend
python -m pytest test\services\test_graph_enrichment.py test\api\test_graph.py -q
```

Prompt 或结构化输出发生变化时，应修改
`src/jiebang_agents/graph_enrichment/`，提升 `prompt_version`，并同步更新上述测试。
