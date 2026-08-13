# 图谱重复数据处理机制说明

> 回答"爬取数据入库过程中如何处理重复性数据"以及技能图谱技术细节点（L4/L5）重复的解决方案。

## 一、入库各层去重机制

| 层面 | 机制 | 类型 |
|---|---|---|
| 原始 JD 导入 | `SourceDocument.content_fingerprint` UNIQUE（sha256 内容指纹） | 硬约束 |
| 原始 JD 导入 | `RawJobRecord.source_document_id` UNIQUE | 硬约束 |
| 原始 JD 导入 | external_id（source+external_id）应用层查重 | 软逻辑 |
| 原始 JD 导入 | simhash 近重复聚类 → `JobDuplicateCluster` + `dedup_status=near_duplicate` + 质量扣分 | 软逻辑 |
| 技能（L3） | `Skill.canonical_key` UNIQUE + `get_or_create_skill` 按 key 查重合并 aliases | 硬约束+合并 |
| 技能事实 | `JobSkillFact` 复合唯一 `(raw_job_record_id, skill_id)` / `(job_id, skill_id)` | 硬约束 |
| 标准岗位 | `StandardJob.canonical_key` UNIQUE、`StandardJobSource` 唯一 `(source_type, source_id)` | 硬约束 |
| 图谱 L1~L3 | Neo4j `MERGE (namespace, id)` 幂等 + full 模式 `cleanup_stale` 按 syncVersion 清理 | 幂等覆盖 |
| 图谱 L4/L5 | **新增**：写入前按规范化名称去重（`_dedupe_by_name`），候选落库前同样去重 | 应用层去重 |

## 二、技术细节点（L4/L5）重复的根因与修复

### 根因
L3 技能有 `canonical_key` 全局唯一约束，同名技能必然合并为一条记录；但 L4 `TechPoint` / L5 `KnowledgePoint` 节点的 id 由 **"技能 id + 序号"** 构成（`point:{skill.id}:{index}`），**不含名称**，Neo4j `MERGE` 只认该 id。因此：

- 同一候选内 LLM 输出重名 tech_point（prompt 只禁止 L3 名称原样重复为 L4，不禁止 L4 之间重名）；
- **不同技能的候选各自生成同名技术点**（如 Java 候选把 `MyBatis`、`Spring Boot` 列为 L4，而这些名字本身又是独立技能/其它候选的 L4）——这是"3 个 mybatis / 2 个 spring boot"的主根因，跨 skill 同名节点 id 前缀不同（`point:7:1` vs `point:11:2`），永不合并；

两者都会产生**同名不同 id 的多个节点**，且 MySQL 层约束无法拦截（它们不属于同一 raw/同一 fact）。

### 修复（已实施三轮）
1. **候选内按名去重（首轮）**：`GraphService._dedupe_by_name` 对每个候选的 `tech_points`/`knowledge_points` 按规范化名称去重；`_filter_grounded_completion` 对 `accepted_points` 同样去重。
2. **L4/L5 节点 id 名称全局唯一（次轮根治）**：TechPoint id 改为 `point:{name_key}`、KnowledgePoint id 改为 `knowledge:{point_key}:{name_key}`。跨技能候选生成同名技术点时 MERGE 到**同一节点**，多个 skill 通过 `REFINES_TO`/`HAS_KNOWLEDGE` 指向它——这正是五层森林模型的"多父共享"设计（`GRAPH_ARCHITECTURE.md:42`）。
3. **名称变体归一化（本轮）**：`_name_key` 升级为 `_normalize_name_key(name, *, level)`——strip+casefold+去空格 → 按层级剥修饰后缀（L4 剥复合后缀如"持久层框架/数据库开发与优化"与单后缀如"框架/技术/原理/开发/优化/基础/中间件"；L5 仅剥课程式后缀"详解/实战/入门/进阶/原理"，避免误伤"Git 三区模型"等概念短语）→ 守卫（剥离后非空且长度 ≥2）→ 复用 `canonical_key` 的 isalnum 压缩 → sha256 前缀。`_append_verified_deep_nodes` 改为**跨候选全局收集**：同一归一化 key（含变体）只生成一个节点，展示名取同 key 组内**最短名称**（"MyBatis" 而非 "MyBatis持久层框架"），每个 skill 各保留一条 `REFINES_TO`（多父共享不丢失）。
   "MyBatis" 与 "MyBatis持久层框架" 因此归一为同一节点且展示为标准短名；节点 `canonicalKey/id` 用归一化 key。
4. **LLM 命名源头约束**：`graph_enrichment` prompt（v5）增加硬性命名指令——L4 name 必须输出无修饰的标准专有名称（"MyBatis" 而非 "MyBatis持久层框架"），禁止名称后附加"框架/技术/原理/开发/优化/基础/使用/实战/详解/入门"等修饰词（放入 detail），从源头减少变体产生。
5. **Neo4j 属性与关系类型警告修复**：`query_nodes` 删除不存在的 `parent_skill`/`parent_tech_point` 属性分支；`expand`/`path`/`_deep_tree` 查询白名单与 `GRAPH_RELATIONS` 移除从未写入的 `RELATED_TO`/`PREREQUISITE`（E7 P2 实现写入列为后续）。

### 收敛验证（真实环境）
修复后执行一次 `mode=full` 同步（`cleanup_stale` 按新 syncVersion 清理旧 id 节点）：
- 修复前：MyBatis 2 节点（`point:7:1`、`point:11:2`）、Spring Boot 2 节点（`point:13:0`、`point:11:1`）；
- 次轮后：MyBatis 1 节点（`point:5996c7ef6c29`）、Spring Boot 1 节点（`point:9c3c0544259a`），TechPoint 总数 27 → 24；
- 本轮变体归一后："MyBatis" 与 "MyBatis持久层框架" 收敛为 1 节点，TechPoint 总数进一步下降。

## 三、存量重复数据的收敛

修改已生效后，执行**一次全量图谱同步**即可自动收敛：

```text
POST /api/v1/graph/sync  {"mode": "full", "enrich_top_skills": false}
```

full 模式下 `cleanup_stale` 会按新的 `syncVersion` 删除旧版本节点，只写入按名去重后的新节点。

备选（不想重跑全量时的一次性 Cypher，对 `namespace=jiebang` 下同名 TechPoint/KnowledgePoint 分组，保留 `source_count` 最优者并迁移边后删除其余）：

```cypher
// 按 (name) 分组找出保留节点（source_count 最大、id 最小）
MATCH (n:TechPoint {namespace:'jiebang'})
WITH toLower(n.name) AS key, collect(n) AS group
WHERE size(group) > 1
UNWIND group AS n
WITH key, group[0] AS keeper, n
WHERE n <> keeper
MATCH (n)-[r]-()
WITH keeper, n, collect(r) AS rels
DETACH DELETE n
```

（请在 Neo4j Browser 中人工确认 keeper 选择规则后执行，生产环境建议先备份。）

## 四、设计边界（不做的事）

- **跨技能同名合并已实现**：L4/L5 节点 id 基于归一化名称 key，多 skill 通过 `REFINES_TO`/`HAS_KNOWLEDGE` 共享同一技术点（多父语义，符合森林模型）；同一节点上来自不同 skill 候选的 evidence 属性以最后一次写入为准，证据聚合列为后续增强。
- **同义变体合并已实现**："MyBatis" 与 "MyBatis持久层框架" 等"名词+修饰后缀"变体经 `_normalize_name_key` 后缀剥离归一为同一节点；L5 仅剥课程式后缀，概念短语（"Git 三区模型"）不误合并。
- **不做**L4 与 L3 冲突检测（如 "MyBatis" 既是 L3 技能又是 Java 的 L4）：属业务规则，需产品确认预期层级行为（当前两者为不同标签，可共存）。
- **RELATED_TO/PREREQUISITE 未实现**：查询白名单已移除避免警告；按 `docs/7.21任务规划.md` E7 P2 实现写入（消费 `knowledge.prerequisites` 与新增 `related_skills`，需"≥2 来源验证"防幻觉）列为后续。

## 五、相关代码索引

- 图谱写入去重：`app/services/graph_service.py:_dedupe_by_name`、`_append_verified_deep_nodes`
- 名称变体归一化：`app/services/graph_service.py:_normalize_name_key`、`_L4_COMPOUND_SUFFIXES`、`_L4_SUFFIXES`、`_L5_SUFFIXES`
- LLM 命名约束：`agent-development/src/jiebang_agents/graph_enrichment/prompt.py`（v5）
- 候选去重：`app/services/graph_service.py:_filter_grounded_completion`
- 属性/关系类型警告修复：`app/repositories/graph_repository.py:query_nodes`、`app/services/graph_service.py:GRAPH_RELATIONS`
- 入库硬约束：`app/models/skill.py`（content_fingerprint/canonical_key/JobSkillFact 唯一约束）、`app/models/graph.py`
- 回归测试：`test/services/test_graph_enrichment.py`（含 3 个归一化单测 + 跨技能同名/变体集成用例）、`test/repositories/test_graph_repository.py`（属性断言）
