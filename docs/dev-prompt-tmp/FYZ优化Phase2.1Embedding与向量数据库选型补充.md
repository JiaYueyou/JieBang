# FYZ 优化 Phase 2.1 Embedding 与向量数据库选型补充

> 编制日期：2026-07-31
>
> 开发分支：`feat/fyz-rag-evidence`
>
> 当前状态：`text-embedding-3-large` 和 ChromaDB 真实链路已完成；323 条 Evidence 已重建为持久化 Chroma 索引，10 个岗位已按岗位隔离为开发、验证和冻结测试集，工程发布门禁通过。

## 1. 补充目标

Phase 2 首轮评测证明确定性哈希向量可以验证索引、过滤、审计和拒答链路，但不具备足够的语义改写召回能力。本补充任务用于：

1. 接入 OpenAI-compatible `text-embedding-3-large`。
2. 使用用户指定的 `https://api.openai-proxy.org` 作为 Base URL。
3. 只预留本地环境变量，不把 API Key 写入仓库。
4. 在 FAISS、ChromaDB 和 Milvus 中选择当前阶段的向量存储。
5. 保留 MySQL 权威事实、索引版本和可重建镜像，不让向量库成为业务事实源。

OpenAI 官方文档将 `text-embedding-3-large` 定义为适用于英文和非英文任务的高能力 Embedding 模型；默认输出维度为 3072，并支持通过 `dimensions` 参数缩短向量。本阶段数据量很小、质量优先，因此固定使用完整 3072 维。

参考：

- [OpenAI text-embedding-3-large](https://developers.openai.com/api/docs/models/text-embedding-3-large)
- [OpenAI Embeddings Guide](https://developers.openai.com/api/docs/guides/embeddings)
- [OpenAI Create Embeddings API](https://developers.openai.com/api/reference/resources/embeddings/methods/create)

## 2. 向量方案对比

| 维度 | FAISS | ChromaDB | Milvus |
|---|---|---|---|
| 产品定位 | 高性能相似度检索库，不是完整数据库 | 面向 AI/RAG 的向量数据库，可嵌入或服务化 | 面向大规模生产的向量数据库 |
| 索引能力 | Flat、IVF、PQ、HNSW、CPU/GPU 等选择丰富 | HNSW、向量检索、文档检索和元数据过滤 | FLAT、IVF、HNSW、DiskANN、稀疏/稠密及混合检索 |
| 持久化 | 需要应用自行保存和恢复索引 | `PersistentClient` 可直接落盘 | Lite、Standalone、Distributed 均支持持久化 |
| 元数据过滤 | 需要另建数据库和 ID 映射，再自行做前置/后置过滤 | Collection 原生保存 ID、Document、Embedding 和 Metadata，并支持组合过滤 | 原生标量字段和过滤表达式，能力完整 |
| 文档与证据对象 | 不直接管理 | 原生 Document + Metadata | 通过 Schema 字段管理 |
| Windows 本地开发 | Conda 安装可用，但需要自行补齐数据库能力 | Python 嵌入式持久化模式可直接使用 | Milvus Lite 官方当前主要支持 Ubuntu/macOS；Windows 通常需要 Docker、虚拟机或独立服务 |
| 多实例与高可用 | 应用自行实现 | 本地模式不适合多实例；可迁移到 Chroma Server/Cloud | Standalone/Distributed 支持更成熟的扩展与高可用 |
| 运维成本 | 库本身最低，配套代码成本高 | 当前阶段最低 | 分布式模式最高 |
| 当前项目适配 | 数据量虽小，但会引入额外的元数据、持久化和并发代码 | 与 Evidence ID、过滤、版本化和本地优先目标直接匹配 | 能力过剩，且当前 Windows 本地链路不够轻量 |

官方依据：

- [FAISS 官方仓库](https://github.com/facebookresearch/faiss)
- [FAISS Index 选择指南](https://github.com/facebookresearch/faiss/wiki/Guidelines-to-choose-an-index)
- [Chroma 架构与部署模式](https://docs.trychroma.com/docs/overview/architecture)
- [Chroma PersistentClient](https://docs.trychroma.com/reference/python/client)
- [Chroma Metadata Filtering](https://docs.trychroma.com/docs/querying-collections/metadata-filtering)
- [Milvus 架构](https://milvus.io/docs/architecture_overview.md)
- [Milvus 部署选项](https://milvus.io/docs/install-overview.md)
- [Milvus Lite 环境与限制](https://milvus.io/docs/milvus_lite.md)

## 3. 选择结果

Phase 2 选择 **ChromaDB**。

选择理由：

1. 当前本地语料为 323 条 Evidence，仍不需要 Milvus 分布式控制面、对象存储和集群运维。
2. 项目需要按标准岗位、技能、来源、质量分、认证状态和发布时间过滤；Chroma 原生 Metadata Filter 比 FAISS 外挂映射更直接。
3. Chroma `PersistentClient` 符合 Windows 本地优先和单进程开发模式。
4. Chroma 可保存 Evidence ID、检索文本和过滤元数据，但 MySQL 仍保存权威证据、索引版本和向量镜像。
5. 后续多实例部署时可以将适配器切换为 Chroma Server；如果规模增长到千万级、需要独立扩缩容或高可用，再重新评估 Milvus。

不选择 FAISS，不是因为检索性能不足，而是因为当前项目需要的是“带持久化、元数据和版本审计的检索存储”，使用 FAISS 会把这些数据库能力重新实现一遍。

不选择 Milvus，是因为当前环境为 Windows 11、本地语料极小。Milvus Lite 官方目前主要支持 Ubuntu/macOS；使用 Standalone/Distributed 会提前引入 Docker/Kubernetes 和额外运维面。

## 4. 落地架构

```text
MySQL 已认证事实
  -> Evidence Chunk + 权威外键
  -> text-embedding-3-large（3072 维）
  -> RetrievalIndexEntry（MySQL 可重建镜像）
  -> Chroma Collection（按 index_version 隔离）

查询
  -> text-embedding-3-large
  -> Chroma cosine + Metadata Filter
  -> MySQL 权威过滤与混合排序
  -> Evidence ID、原文、来源和索引版本
```

每个索引版本对应独立 Chroma Collection。Collection 使用确定性哈希名称，索引版本保存在 Metadata 和 MySQL `retrieval_index_version` 中。

Chroma 不使用内置 OpenAI Embedding Function。Embedding 统一由项目 `OpenAIEmbeddingProvider` 生成后作为预计算向量写入，确保：

- 模型、维度、Base URL 和批次策略集中配置。
- MySQL 镜像与 Chroma 中的向量完全一致。
- Chroma 不单独持有 API Key。
- 后续更换向量数据库时不影响 Embedding Provider。

## 5. 配置

`.env.example` 已增加：

```dotenv
RETRIEVAL_EMBEDDING_PROVIDER=openai
RETRIEVAL_VECTOR_BACKEND=chroma
RETRIEVAL_RELATIVE_SCORE_WINDOW=0.04
RETRIEVAL_SEMANTIC_SCORE_FLOOR=0.30
OPENAI_EMBEDDING_API_KEY=
OPENAI_EMBEDDING_BASE_URL=https://api.openai-proxy.org/v1
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
OPENAI_EMBEDDING_DIMENSIONS=3072
OPENAI_EMBEDDING_BATCH_SIZE=64
OPENAI_EMBEDDING_TIMEOUT_SECONDS=60
CHROMA_MODE=persistent
CHROMA_PERSIST_PATH=./storage/chroma
```

API Key 必须只写入本地 `fyz-src/backend/.env` 或部署密钥管理器：

```dotenv
OPENAI_EMBEDDING_API_KEY=由项目负责人填写
```

注意：

- `https://api.openai-proxy.org` 是第三方代理而不是 OpenAI 官方域名。配置 Key 前应确认代理方的信任边界、日志策略、数据保留和限额。
- Base URL 必须填写完整的 OpenAI-compatible API 地址；Provider 只移除末尾 `/`，不自动追加或改写路径。当前本地配置使用 `https://api.openai-proxy.org/v1`，真实调用已确认可返回 3072 维向量。
- 不要把 Key 写入 `.env.example`、测试、日志、查询审计或 Git 提交。

## 6. 已完成实现

- `OpenAIEmbeddingProvider`
  - 使用官方 `AsyncOpenAI` 客户端。
  - 支持自定义 Base URL。
  - 固定模型、维度、批次、超时和浮点输出。
  - 保持响应顺序并验证向量数量和维度。
  - Key 缺失时在发起网络请求前失败。
- `ChromaVectorStore`
  - 支持测试态 EphemeralClient 和开发态 PersistentClient。
  - 使用 cosine HNSW。
  - 保存 Evidence ID、检索文档和过滤元数据。
  - 支持岗位、技能、来源、质量、认证状态和发布时间过滤。
- Retriever
  - `backend=chroma` 重建和查询。
  - Chroma 不可用时降级到 MySQL 向量镜像并返回警告。
  - 查询历史索引时根据索引元数据恢复对应 Provider，旧哈希索引仍可重现。
  - Embedding 失败时将索引版本记为 `failed`，记录失败阶段，不留下伪 `ready` 版本。
  - 检索文本增加规范技能的别名和受控语义说明，引用文本仍保持原始 Evidence Chunk。
  - 结果仅保留与最高分相差不超过 `0.04` 的证据，减少低相关证据被当作引用返回；既定绝对最低分仍同时生效。
  - 无权威实体或结构化过滤命中时，语义相似度低于 `0.30` 的结果拒答。
  - Chroma 成功召回后，MySQL 只回读候选 Evidence，不再为每次查询加载整个版本的 3072 维向量镜像。
- 依赖
  - `openai==2.41.0`
  - `chromadb==1.5.9`

## 7. 当前验证状态

已验证：

- OpenAI Provider 批处理、顺序、维度和缺 Key 失败测试。
- Chroma 嵌入式写入、cosine 查询和 Metadata Filter。
- API 管理员重建 Chroma 索引并检索 Evidence。
- 旧 Neo4j/hash 索引仍可执行原 Phase 2 评测。
- 代理根地址自动补齐 `/v1` 后，`text-embedding-3-large` 真实调用成功并返回 3072 维向量。
- 最小语义探针：相关文本余弦相似度 `0.627818`，无关文本 `0.152416`。
- 已从 MySQL 权威证据重建 323 条 Chroma 向量，索引版本 `20260730T180337-b884da9e`，Collection `jiebang-evidence-e93abd41a75aab10f84a`。
- 最终跨岗位评测：Recall@5 `97.06%`、MRR@10 `100%`、Citation Precision@5 `100%`、Top-1 `100%`、拒答准确率 `100%`、过滤违规率 `0%`、P95 `95ms`。
- 开发、验证和冻结测试分区性能门禁均通过；`performance_gate=true`、`coverage_gate=true`、`release_gate=true`。
- `pip check` 无依赖冲突。
- 后端完整回归：`179 passed in 149.07s`。

仍未完成：

- 当前覆盖为 10 个标准岗位、78 个技能、2 个来源和 323 条 Evidence。
- 机器认证和工程评测不等同于业务专家金标；工程门禁通过不代表生产流量准确率。
- API 调用费用尚未建立持续统计；评测器已把重复查询批量预取，避免逐样本重复请求 Embedding。

## 8. 密钥填写后的执行顺序

```powershell
Set-Location E:\Project\JieBang\fyz-src\backend

# 1. 验证代理、模型和返回维度；脚本不会打印 API Key 或完整向量
& 'E:\Computer_tools\Anaconda\dld\envs\jiebang\python.exe' scripts\verify_embedding_provider.py

# 2. 从 MySQL 权威证据重建 Chroma 索引
& 'E:\Computer_tools\Anaconda\dld\envs\jiebang\python.exe' scripts\rebuild_retrieval_index.py --backend chroma

# 3. 使用新索引运行冻结开发集评测
& 'E:\Computer_tools\Anaconda\dld\envs\jiebang\python.exe' scripts\evaluate_phase2_retrieval.py
```

验收时必须保存：

- Embedding 模型、维度和 Provider。
- Chroma Collection 名与 Retrieval Index Version。
- 评测 Golden Set SHA-256。
- Recall@5、MRR@10、Citation Precision、拒答准确率、过滤违规率和 P95。
- 失败样本 ID。

当前覆盖和性能门禁均通过，但评测集仍为工程审核且 `human_domain_gold=false`。对外只能表述为“Phase 2 工程门禁通过”，不能宣称为生产准确率或业务专家金标。
