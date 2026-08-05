# FYZ Phase 0 基线报告

- 生成时间：`2026-07-30T15:50:14.725813Z`
- Git HEAD：`28379574a251b46dcce9a82136e15f0bb8ca388b`
- 分支：`feat/fyz-job-agent`
- 工作区变更条目：`56`
- 数据库方言：`mysql`
- Alembic revision：`20260730_0013`
- Neo4j 连通：`True`
- Neo4j 服务信息：`{'name': 'Neo4j Kernel', 'versions': ['2026.05.0'], 'edition': 'community'}`
- Neo4j 图计数：`{'nodes': 152, 'edges': 189}`
- Neo4j 向量能力：`{'supported': True, 'procedures': ['db.index.vector.queryNodes', 'db.index.vector.queryRelationships'], 'functions': ['vector.similarity.cosine', 'vector.similarity.euclidean'], 'probe_errors': []}`

## MySQL/关系库计数

- `job_posting`：`7`
- `source_document`：`190`
- `raw_job_record`：`190`
- `skill`：`107`
- `job_skill_fact`：`1143`
- `standard_job`：`130`
- `agent_run`：`86`
- `async_task`：`85`
- `graph_snapshot`：`13`
- `graph_sync_batch`：`13`
- `graph_enrichment_candidate`：`100`

## 状态分布

- `job_skill_fact`：`{'unverified': 1102, 'verified': 41}`
- `agent_run`：`{'degraded': 31, 'succeeded': 55}`
- `async_task`：`{'queued': 2, 'succeeded': 83}`
- `graph_snapshot`：`{'succeeded': 13}`
- `graph_sync_batch`：`{'succeeded': 13}`
- `graph_enrichment_candidate`：`{'unverified': 100}`

## Agent耗时

`[{'agent_type': 'career_planning', 'status': 'degraded', 'count': 19, 'avg_duration_ms': 20942.16, 'max_duration_ms': 38975}, {'agent_type': 'career_planning', 'status': 'succeeded', 'count': 10, 'avg_duration_ms': 17506.7, 'max_duration_ms': 28537}, {'agent_type': 'jd_generation', 'status': 'degraded', 'count': 4, 'avg_duration_ms': 22242.25, 'max_duration_ms': 24778}, {'agent_type': 'jd_generation', 'status': 'succeeded', 'count': 14, 'avg_duration_ms': 9769.36, 'max_duration_ms': 19232}, {'agent_type': 'jd_input_suggestion', 'status': 'degraded', 'count': 3, 'avg_duration_ms': 10045.67, 'max_duration_ms': 10071}, {'agent_type': 'jd_input_suggestion', 'status': 'succeeded', 'count': 24, 'avg_duration_ms': 3582.92, 'max_duration_ms': 5436}, {'agent_type': 'match_explanation', 'status': 'degraded', 'count': 5, 'avg_duration_ms': 16332.4, 'max_duration_ms': 26757}, {'agent_type': 'match_explanation', 'status': 'succeeded', 'count': 7, 'avg_duration_ms': 8848.43, 'max_duration_ms': 17214}]`

## RAG索引决策

- 权威数据：MySQL stores source, evidence, review and publication metadata.
- 索引角色：Vector indexes are derived, rebuildable retrieval read models.
- Phase 1 默认后端：`neo4j_vector_index_pilot`
- 原因：The connected Neo4j server exposes vector procedures/functions.
