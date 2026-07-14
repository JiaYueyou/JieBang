import type { GraphNode, GraphEdge } from '@/types'

// ========== 五级知识图谱 Mock 数据 ==========
// Level 1 (root): 核心技术/编程语言
// Level 2 (position): 岗位
// Level 3 (branch): domain_branch(应用领域) + skillset_branch(技能集合)
// Level 4 (module): 专项能力模块
// Level 5 (knowledge): 细分知识点/实操技能点

export const mockGraphNodes: GraphNode[] = [
  // ===== Level 1: 根技术 =====
  { id: 'root-java', label: 'Java', type: 'root', layer: 1 },
  { id: 'root-python', label: 'Python', type: 'root', layer: 1 },

  // ===== Level 2: 岗位（Java 体系） =====
  { id: 'pos-java-dev', label: 'Java开发工程师', type: 'position', layer: 2, rootId: 'root-java' },
  { id: 'pos-java-arch', label: 'Java架构师', type: 'position', layer: 2, rootId: 'root-java' },
  { id: 'pos-bigdata', label: '大数据工程师', type: 'position', layer: 2, rootId: 'root-java' },

  // ===== Level 2: 岗位（Python 体系） =====
  { id: 'pos-ai-dev', label: 'AI智能体开发', type: 'position', layer: 2, rootId: 'root-python' },
  { id: 'pos-data-sci', label: '数据科学家', type: 'position', layer: 2, rootId: 'root-python' },

  // ===== Level 3: 应用领域 (domain_branch) =====
  { id: 'domain-ecom', label: '电商', type: 'domain_branch', layer: 3, rootId: 'root-java' },
  { id: 'domain-fin', label: '金融', type: 'domain_branch', layer: 3, rootId: 'root-java' },
  { id: 'domain-enterprise', label: '企业应用', type: 'domain_branch', layer: 3, rootId: 'root-java' },
  { id: 'domain-ai-assist', label: '智能助手', type: 'domain_branch', layer: 3, rootId: 'root-python' },
  { id: 'domain-analytics', label: '数据分析', type: 'domain_branch', layer: 3, rootId: 'root-python' },

  // ===== Level 3: 综合技能集合 (skillset_branch) =====
  { id: 'skillset-backend', label: '后端开发技能', type: 'skillset_branch', layer: 3, rootId: 'root-java' },
  { id: 'skillset-arch', label: '系统架构技能', type: 'skillset_branch', layer: 3, rootId: 'root-java' },
  { id: 'skillset-data', label: '数据工程技能', type: 'skillset_branch', layer: 3, rootId: 'root-java' },
  { id: 'skillset-ai', label: 'AI开发技能', type: 'skillset_branch', layer: 3, rootId: 'root-python' },
  { id: 'skillset-ml', label: '机器学习技能', type: 'skillset_branch', layer: 3, rootId: 'root-python' },

  // ===== Level 4: 能力模块 (module) — 后端 =====
  { id: 'mod-microservice', label: '微服务架构', type: 'module', layer: 4, rootId: 'root-java' },
  { id: 'mod-database', label: '数据库设计', type: 'module', layer: 4, rootId: 'root-java' },
  { id: 'mod-messaging', label: '消息队列', type: 'module', layer: 4, rootId: 'root-java' },
  { id: 'mod-spring-eco', label: 'Spring生态', type: 'module', layer: 4, rootId: 'root-java' },

  // ===== Level 4: 能力模块 (module) — 架构 =====
  { id: 'mod-distributed', label: '分布式系统', type: 'module', layer: 4, rootId: 'root-java' },
  { id: 'mod-security', label: '安全认证', type: 'module', layer: 4, rootId: 'root-java' },
  { id: 'mod-performance', label: '性能优化', type: 'module', layer: 4, rootId: 'root-java' },
  { id: 'mod-container', label: '容器化部署', type: 'module', layer: 4, rootId: 'root-java' },

  // ===== Level 4: 能力模块 (module) — 数据工程 =====
  { id: 'mod-data-pipeline', label: '数据管道', type: 'module', layer: 4, rootId: 'root-java' },
  { id: 'mod-streaming', label: '流计算', type: 'module', layer: 4, rootId: 'root-java' },

  // ===== Level 4: 能力模块 (module) — AI =====
  { id: 'mod-llm', label: 'LLM集成', type: 'module', layer: 4, rootId: 'root-python' },
  { id: 'mod-agent', label: 'Agent框架', type: 'module', layer: 4, rootId: 'root-python' },
  { id: 'mod-rag', label: 'RAG检索增强', type: 'module', layer: 4, rootId: 'root-python' },

  // ===== Level 4: 能力模块 (module) — ML =====
  { id: 'mod-dl', label: '深度学习', type: 'module', layer: 4, rootId: 'root-python' },
  { id: 'mod-nlp', label: '自然语言处理', type: 'module', layer: 4, rootId: 'root-python' },

  // ===== Level 5: 知识点 (knowledge) — 后端 → 微服务 =====
  { id: 'kp-springboot', label: 'Spring Boot', type: 'knowledge', layer: 5, rootId: 'root-java' },
  { id: 'kp-springcloud', label: 'Spring Cloud', type: 'knowledge', layer: 5, rootId: 'root-java' },
  { id: 'kp-restful', label: 'RESTful API设计', type: 'knowledge', layer: 5, rootId: 'root-java' },
  { id: 'kp-grpc', label: 'gRPC', type: 'knowledge', layer: 5, rootId: 'root-java' },

  // ===== Level 5: 知识点 (knowledge) — 后端 → 数据库 =====
  { id: 'kp-mysql-opt', label: 'MySQL优化', type: 'knowledge', layer: 5, rootId: 'root-java' },
  { id: 'kp-transaction', label: '事务管理', type: 'knowledge', layer: 5, rootId: 'root-java' },
  { id: 'kp-mybatis', label: 'MyBatis', type: 'knowledge', layer: 5, rootId: 'root-java' },
  { id: 'kp-redis', label: 'Redis', type: 'knowledge', layer: 5, rootId: 'root-java' },

  // ===== Level 5: 知识点 (knowledge) — 后端 → 消息队列 =====
  { id: 'kp-kafka', label: 'Kafka', type: 'knowledge', layer: 5, rootId: 'root-java' },
  { id: 'kp-rabbitmq', label: 'RabbitMQ', type: 'knowledge', layer: 5, rootId: 'root-java' },

  // ===== Level 5: 知识点 (knowledge) — 架构 → 分布式 =====
  { id: 'kp-cap', label: 'CAP理论', type: 'knowledge', layer: 5, rootId: 'root-java' },
  { id: 'kp-consensus', label: '共识算法', type: 'knowledge', layer: 5, rootId: 'root-java' },
  { id: 'kp-sharding', label: '分库分表', type: 'knowledge', layer: 5, rootId: 'root-java' },

  // ===== Level 5: 知识点 (knowledge) — 架构 → 安全 =====
  { id: 'kp-jwt', label: 'JWT认证', type: 'knowledge', layer: 5, rootId: 'root-java' },
  { id: 'kp-oauth2', label: 'OAuth2.0', type: 'knowledge', layer: 5, rootId: 'root-java' },

  // ===== Level 5: 知识点 (knowledge) — 架构 → 性能 =====
  { id: 'kp-jvm-tuning', label: 'JVM调优', type: 'knowledge', layer: 5, rootId: 'root-java' },
  { id: 'kp-cache-strategy', label: '缓存策略', type: 'knowledge', layer: 5, rootId: 'root-java' },
  { id: 'kp-sql-tuning', label: 'SQL调优', type: 'knowledge', layer: 5, rootId: 'root-java' },

  // ===== Level 5: 知识点 (knowledge) — 架构 → 容器 =====
  { id: 'kp-docker', label: 'Docker', type: 'knowledge', layer: 5, rootId: 'root-java' },
  { id: 'kp-k8s', label: 'Kubernetes', type: 'knowledge', layer: 5, rootId: 'root-java' },

  // ===== Level 5: 知识点 (knowledge) — 数据工程 =====
  { id: 'kp-etl', label: 'ETL流程', type: 'knowledge', layer: 5, rootId: 'root-java' },
  { id: 'kp-spark', label: 'Apache Spark', type: 'knowledge', layer: 5, rootId: 'root-java' },
  { id: 'kp-flink', label: 'Flink', type: 'knowledge', layer: 5, rootId: 'root-java' },

  // ===== Level 5: 知识点 (knowledge) — AI =====
  { id: 'kp-prompt-eng', label: 'Prompt工程', type: 'knowledge', layer: 5, rootId: 'root-python' },
  { id: 'kp-langchain', label: 'LangChain', type: 'knowledge', layer: 5, rootId: 'root-python' },
  { id: 'kp-embedding', label: '向量嵌入', type: 'knowledge', layer: 5, rootId: 'root-python' },
  { id: 'kp-llm-api', label: 'LLM API调用', type: 'knowledge', layer: 5, rootId: 'root-python' },
  { id: 'kp-vector-db', label: '向量数据库', type: 'knowledge', layer: 5, rootId: 'root-python' },
  { id: 'kp-agent-design', label: '智能体设计', type: 'knowledge', layer: 5, rootId: 'root-python' },

  // ===== Level 5: 知识点 (knowledge) — ML =====
  { id: 'kp-pytorch', label: 'PyTorch', type: 'knowledge', layer: 5, rootId: 'root-python' },
  { id: 'kp-transformer', label: 'Transformer', type: 'knowledge', layer: 5, rootId: 'root-python' },
  { id: 'kp-finetune', label: '模型微调', type: 'knowledge', layer: 5, rootId: 'root-python' },
]

export const mockGraphEdges: GraphEdge[] = [
  // ===== Root → Position (derives) =====
  { source: 'root-java', target: 'pos-java-dev', relation: 'derives', weight: 5 },
  { source: 'root-java', target: 'pos-java-arch', relation: 'derives', weight: 4 },
  { source: 'root-java', target: 'pos-bigdata', relation: 'derives', weight: 3 },
  { source: 'root-python', target: 'pos-ai-dev', relation: 'derives', weight: 5 },
  { source: 'root-python', target: 'pos-data-sci', relation: 'derives', weight: 4 },

  // ===== Position → Domain Branch (applies_to) =====
  { source: 'pos-java-dev', target: 'domain-ecom', relation: 'applies_to', weight: 5 },
  { source: 'pos-java-dev', target: 'domain-fin', relation: 'applies_to', weight: 4 },
  { source: 'pos-java-dev', target: 'domain-enterprise', relation: 'applies_to', weight: 3 },
  { source: 'pos-java-arch', target: 'domain-fin', relation: 'applies_to', weight: 4 },
  { source: 'pos-java-arch', target: 'domain-enterprise', relation: 'applies_to', weight: 5 },
  { source: 'pos-bigdata', target: 'domain-ecom', relation: 'applies_to', weight: 4 },
  { source: 'pos-bigdata', target: 'domain-fin', relation: 'applies_to', weight: 3 },
  { source: 'pos-ai-dev', target: 'domain-ai-assist', relation: 'applies_to', weight: 5 },
  { source: 'pos-data-sci', target: 'domain-analytics', relation: 'applies_to', weight: 5 },

  // ===== Position → Skillset Branch (composes) =====
  { source: 'pos-java-dev', target: 'skillset-backend', relation: 'composes', weight: 5 },
  { source: 'pos-java-arch', target: 'skillset-backend', relation: 'composes', weight: 4 },
  { source: 'pos-java-arch', target: 'skillset-arch', relation: 'composes', weight: 5 },
  { source: 'pos-bigdata', target: 'skillset-backend', relation: 'composes', weight: 3 },
  { source: 'pos-bigdata', target: 'skillset-data', relation: 'composes', weight: 5 },
  { source: 'pos-ai-dev', target: 'skillset-ai', relation: 'composes', weight: 5 },
  { source: 'pos-data-sci', target: 'skillset-ml', relation: 'composes', weight: 5 },

  // ===== Skillset → Module (contains) =====
  { source: 'skillset-backend', target: 'mod-microservice', relation: 'contains', weight: 5 },
  { source: 'skillset-backend', target: 'mod-database', relation: 'contains', weight: 5 },
  { source: 'skillset-backend', target: 'mod-messaging', relation: 'contains', weight: 4 },
  { source: 'skillset-backend', target: 'mod-spring-eco', relation: 'contains', weight: 5 },
  { source: 'skillset-arch', target: 'mod-distributed', relation: 'contains', weight: 5 },
  { source: 'skillset-arch', target: 'mod-security', relation: 'contains', weight: 4 },
  { source: 'skillset-arch', target: 'mod-performance', relation: 'contains', weight: 4 },
  { source: 'skillset-arch', target: 'mod-container', relation: 'contains', weight: 4 },
  { source: 'skillset-data', target: 'mod-data-pipeline', relation: 'contains', weight: 5 },
  { source: 'skillset-data', target: 'mod-streaming', relation: 'contains', weight: 4 },
  { source: 'skillset-ai', target: 'mod-llm', relation: 'contains', weight: 5 },
  { source: 'skillset-ai', target: 'mod-agent', relation: 'contains', weight: 4 },
  { source: 'skillset-ai', target: 'mod-rag', relation: 'contains', weight: 5 },
  { source: 'skillset-ml', target: 'mod-dl', relation: 'contains', weight: 5 },
  { source: 'skillset-ml', target: 'mod-nlp', relation: 'contains', weight: 4 },

  // ===== Module → Knowledge (includes) =====
  { source: 'mod-microservice', target: 'kp-springboot', relation: 'includes', weight: 5 },
  { source: 'mod-microservice', target: 'kp-springcloud', relation: 'includes', weight: 5 },
  { source: 'mod-microservice', target: 'kp-restful', relation: 'includes', weight: 4 },
  { source: 'mod-microservice', target: 'kp-grpc', relation: 'includes', weight: 3 },
  { source: 'mod-database', target: 'kp-mysql-opt', relation: 'includes', weight: 5 },
  { source: 'mod-database', target: 'kp-transaction', relation: 'includes', weight: 5 },
  { source: 'mod-database', target: 'kp-mybatis', relation: 'includes', weight: 4 },
  { source: 'mod-database', target: 'kp-redis', relation: 'includes', weight: 4 },
  { source: 'mod-messaging', target: 'kp-kafka', relation: 'includes', weight: 5 },
  { source: 'mod-messaging', target: 'kp-rabbitmq', relation: 'includes', weight: 4 },
  { source: 'mod-distributed', target: 'kp-cap', relation: 'includes', weight: 5 },
  { source: 'mod-distributed', target: 'kp-consensus', relation: 'includes', weight: 4 },
  { source: 'mod-distributed', target: 'kp-sharding', relation: 'includes', weight: 5 },
  { source: 'mod-security', target: 'kp-jwt', relation: 'includes', weight: 5 },
  { source: 'mod-security', target: 'kp-oauth2', relation: 'includes', weight: 4 },
  { source: 'mod-performance', target: 'kp-jvm-tuning', relation: 'includes', weight: 5 },
  { source: 'mod-performance', target: 'kp-cache-strategy', relation: 'includes', weight: 5 },
  { source: 'mod-performance', target: 'kp-sql-tuning', relation: 'includes', weight: 4 },
  { source: 'mod-container', target: 'kp-docker', relation: 'includes', weight: 5 },
  { source: 'mod-container', target: 'kp-k8s', relation: 'includes', weight: 4 },
  { source: 'mod-data-pipeline', target: 'kp-etl', relation: 'includes', weight: 5 },
  { source: 'mod-data-pipeline', target: 'kp-spark', relation: 'includes', weight: 5 },
  { source: 'mod-streaming', target: 'kp-flink', relation: 'includes', weight: 5 },
  { source: 'mod-llm', target: 'kp-prompt-eng', relation: 'includes', weight: 5 },
  { source: 'mod-llm', target: 'kp-llm-api', relation: 'includes', weight: 5 },
  { source: 'mod-agent', target: 'kp-langchain', relation: 'includes', weight: 5 },
  { source: 'mod-agent', target: 'kp-agent-design', relation: 'includes', weight: 5 },
  { source: 'mod-rag', target: 'kp-embedding', relation: 'includes', weight: 5 },
  { source: 'mod-rag', target: 'kp-vector-db', relation: 'includes', weight: 5 },
  { source: 'mod-dl', target: 'kp-pytorch', relation: 'includes', weight: 5 },
  { source: 'mod-dl', target: 'kp-transformer', relation: 'includes', weight: 5 },
  { source: 'mod-nlp', target: 'kp-finetune', relation: 'includes', weight: 4 },

  // ===== 跨分支多对多连接 (cross_ref) =====
  // 技能跨模块关联
  { source: 'kp-redis', target: 'mod-performance', relation: 'cross_ref', weight: 3 },
  { source: 'kp-docker', target: 'mod-microservice', relation: 'cross_ref', weight: 3 },
  { source: 'kp-kafka', target: 'mod-streaming', relation: 'cross_ref', weight: 4 },
  { source: 'kp-sql-tuning', target: 'mod-database', relation: 'cross_ref', weight: 5 },
  { source: 'kp-restful', target: 'mod-security', relation: 'cross_ref', weight: 2 },
  { source: 'kp-springboot', target: 'mod-container', relation: 'cross_ref', weight: 2 },
  // 模块跨岗位关联
  { source: 'mod-microservice', target: 'pos-bigdata', relation: 'cross_ref', weight: 3 },
  { source: 'mod-distributed', target: 'pos-bigdata', relation: 'cross_ref', weight: 3 },
  { source: 'mod-llm', target: 'mod-nlp', relation: 'cross_ref', weight: 4 },
  { source: 'mod-agent', target: 'mod-llm', relation: 'cross_ref', weight: 5 },
  // Spring生态模块跨关联
  { source: 'mod-spring-eco', target: 'kp-springboot', relation: 'cross_ref', weight: 5 },
  { source: 'mod-spring-eco', target: 'kp-mybatis', relation: 'cross_ref', weight: 3 },
]
