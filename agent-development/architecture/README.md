# 运行时结构

```text
agent-development/src/jiebang_agents/
  base.py                         后端需要实现的 Provider 协议
  jd_generation/schemas.py        输入与结构化输出契约
  jd_generation/prompt.py         Prompt v3 与上下文构造
  jd_generation/agent.py          无状态生成、合并、模板降级
  skill_extraction/               技能 LLM 补全 Prompt、Schema、Agent
  graph_enrichment/               图谱证据补全 Prompt、Schema、Agent

fyz-src/backend/app/
  core/agent_runtime.py           独立目录加载接口
  api/v1/agents.py                HTTP 与鉴权，保持既有 URL
  services/jd_generation_service.py 任务创建、审计持久化、查询
  tasks/jd_generation.py          Celery 调度，保持既有任务名
  schemas/agent.py                API 响应及独立 DTO 转发
```

依赖方向为 `api/task -> service -> core.agent_runtime -> jiebang_agents`。独立 Agent 包只依赖 Pydantic 和 Provider 协议，不依赖 FastAPI、SQLAlchemy、Celery 或后端 `app` 包。
