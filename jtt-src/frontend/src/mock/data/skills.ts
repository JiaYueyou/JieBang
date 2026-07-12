import type { GraphNode, GraphEdge } from '@/types'

// ========== Layer 1: 岗位 (Positions) ==========
// ========== Layer 2: 框架/技术 (Technologies) ==========
// ========== Layer 3: 技能 (Skills) ==========

export const mockGraphNodes: GraphNode[] = [
  // ---- Layer 1: Positions ----
  { id: 'pos-java', label: 'Java开发工程师', type: 'position', layer: 1 },
  { id: 'pos-fe', label: '前端开发工程师', type: 'position', layer: 1 },
  { id: 'pos-de', label: '数据工程师', type: 'position', layer: 1 },
  { id: 'pos-agent', label: 'AI智能体开发', type: 'position', layer: 1 },
  { id: 'pos-ctx', label: '上下文工程专家', type: 'position', layer: 1 },

  // ---- Layer 2: Technologies / Frameworks ----
  { id: 'tech-springboot', label: 'Spring Boot', type: 'technology', layer: 2 },
  { id: 'tech-docker', label: 'Docker / K8s', type: 'technology', layer: 2 },
  { id: 'tech-mysql', label: 'MySQL / Redis', type: 'technology', layer: 2 },
  { id: 'tech-vue3', label: 'Vue 3', type: 'technology', layer: 2 },
  { id: 'tech-ts', label: 'TypeScript', type: 'technology', layer: 2 },
  { id: 'tech-vite', label: 'Vite / Webpack', type: 'technology', layer: 2 },
  { id: 'tech-python', label: 'Python', type: 'technology', layer: 2 },
  { id: 'tech-langchain', label: 'LangChain', type: 'technology', layer: 2 },
  { id: 'tech-spark', label: 'Spark / Flink', type: 'technology', layer: 2 },
  { id: 'tech-node', label: 'Node.js', type: 'technology', layer: 2 },
  { id: 'tech-fastapi', label: 'FastAPI', type: 'technology', layer: 2 },
  { id: 'tech-llm', label: 'LLM APIs', type: 'technology', layer: 2 },
  { id: 'tech-rag', label: 'RAG 框架', type: 'technology', layer: 2 },
  { id: 'tech-agent', label: 'Agent 框架', type: 'technology', layer: 2 },

  // ---- Layer 3: Skills ----
  { id: 'sk-microservice', label: '微服务架构', type: 'skill', layer: 3 },
  { id: 'sk-container', label: '容器编排', type: 'skill', layer: 3 },
  { id: 'sk-reactive', label: '响应式开发', type: 'skill', layer: 3 },
  { id: 'sk-state-mgmt', label: '状态管理', type: 'skill', layer: 3 },
  { id: 'sk-llm-integration', label: 'LLM 集成', type: 'skill', layer: 3 },
  { id: 'sk-prompt-eng', label: 'Prompt 工程', type: 'skill', layer: 3 },
  { id: 'sk-rag-impl', label: 'RAG 实现', type: 'skill', layer: 3 },
  { id: 'sk-data-pipeline', label: '数据管道', type: 'skill', layer: 3 },
  { id: 'sk-realtime', label: '实时计算', type: 'skill', layer: 3 },
  { id: 'sk-agent-design', label: '智能体设计', type: 'skill', layer: 3 },
  { id: 'sk-fullstack', label: '全栈开发', type: 'skill', layer: 3 },
  { id: 'sk-visualization', label: '可视化开发', type: 'skill', layer: 3 },
  { id: 'sk-deep-learning', label: '深度学习', type: 'skill', layer: 3 },
  { id: 'sk-cv', label: '计算机视觉', type: 'skill', layer: 3 },
  { id: 'sk-rl', label: '强化学习', type: 'skill', layer: 3 },
  { id: 'sk-api-design', label: 'API 设计', type: 'skill', layer: 3 },
  { id: 'sk-ai-tools', label: 'AI 辅助开发', type: 'skill', layer: 3 },
  { id: 'sk-nlp', label: 'NLP 基础', type: 'skill', layer: 3 },
  { id: 'sk-embedding', label: '向量与嵌入', type: 'skill', layer: 3 },
  { id: 'sk-model-finetune', label: '模型微调', type: 'skill', layer: 3 },
]

export const mockGraphEdges: GraphEdge[] = [
  // ===== Position → Technology =====

  // Java开发工程师
  { source: 'pos-java', target: 'tech-springboot', relation: 'requires', weight: 5 },
  { source: 'pos-java', target: 'tech-docker', relation: 'requires', weight: 4 },
  { source: 'pos-java', target: 'tech-mysql', relation: 'requires', weight: 5 },
  { source: 'pos-java', target: 'tech-llm', relation: 'requires', weight: 3 },
  { source: 'pos-java', target: 'tech-rag', relation: 'related_to', weight: 2 },
  { source: 'pos-java', target: 'tech-agent', relation: 'related_to', weight: 2 },

  // 前端开发工程师
  { source: 'pos-fe', target: 'tech-vue3', relation: 'requires', weight: 5 },
  { source: 'pos-fe', target: 'tech-ts', relation: 'requires', weight: 5 },
  { source: 'pos-fe', target: 'tech-vite', relation: 'requires', weight: 4 },
  { source: 'pos-fe', target: 'tech-node', relation: 'related_to', weight: 3 },

  // 数据工程师
  { source: 'pos-de', target: 'tech-python', relation: 'requires', weight: 5 },
  { source: 'pos-de', target: 'tech-spark', relation: 'requires', weight: 5 },
  { source: 'pos-de', target: 'tech-mysql', relation: 'requires', weight: 4 },

  // AI智能体开发
  { source: 'pos-agent', target: 'tech-python', relation: 'requires', weight: 5 },
  { source: 'pos-agent', target: 'tech-langchain', relation: 'requires', weight: 5 },
  { source: 'pos-agent', target: 'tech-llm', relation: 'requires', weight: 5 },
  { source: 'pos-agent', target: 'tech-rag', relation: 'requires', weight: 4 },
  { source: 'pos-agent', target: 'tech-agent', relation: 'requires', weight: 5 },
  { source: 'pos-agent', target: 'tech-fastapi', relation: 'related_to', weight: 3 },

  // 上下文工程专家
  { source: 'pos-ctx', target: 'tech-llm', relation: 'requires', weight: 5 },
  { source: 'pos-ctx', target: 'tech-python', relation: 'requires', weight: 4 },
  { source: 'pos-ctx', target: 'tech-langchain', relation: 'related_to', weight: 3 },

  // ===== Technology → Skill =====

  // Spring Boot
  { source: 'tech-springboot', target: 'sk-microservice', relation: 'requires', weight: 5 },
  { source: 'tech-springboot', target: 'sk-api-design', relation: 'requires', weight: 4 },

  // Docker / K8s
  { source: 'tech-docker', target: 'sk-container', relation: 'requires', weight: 5 },
  { source: 'tech-docker', target: 'sk-microservice', relation: 'related_to', weight: 3 },

  // Vue 3
  { source: 'tech-vue3', target: 'sk-reactive', relation: 'requires', weight: 5 },
  { source: 'tech-vue3', target: 'sk-state-mgmt', relation: 'requires', weight: 4 },

  // TypeScript
  { source: 'tech-ts', target: 'sk-reactive', relation: 'related_to', weight: 3 },

  // Vite / Webpack
  { source: 'tech-vite', target: 'sk-ai-tools', relation: 'related_to', weight: 3 },

  // Python
  { source: 'tech-python', target: 'sk-api-design', relation: 'requires', weight: 3 },
  { source: 'tech-python', target: 'sk-data-pipeline', relation: 'related_to', weight: 2 },

  // LangChain
  { source: 'tech-langchain', target: 'sk-llm-integration', relation: 'requires', weight: 5 },
  { source: 'tech-langchain', target: 'sk-rag-impl', relation: 'requires', weight: 4 },
  { source: 'tech-langchain', target: 'sk-prompt-eng', relation: 'related_to', weight: 3 },

  // LLM APIs
  { source: 'tech-llm', target: 'sk-llm-integration', relation: 'requires', weight: 5 },
  { source: 'tech-llm', target: 'sk-prompt-eng', relation: 'requires', weight: 5 },
  { source: 'tech-llm', target: 'sk-embedding', relation: 'requires', weight: 4 },
  { source: 'tech-llm', target: 'sk-model-finetune', relation: 'related_to', weight: 3 },

  // RAG 框架
  { source: 'tech-rag', target: 'sk-rag-impl', relation: 'requires', weight: 5 },
  { source: 'tech-rag', target: 'sk-embedding', relation: 'requires', weight: 4 },

  // Agent 框架
  { source: 'tech-agent', target: 'sk-agent-design', relation: 'requires', weight: 5 },
  { source: 'tech-agent', target: 'sk-llm-integration', relation: 'requires', weight: 4 },

  // Spark / Flink
  { source: 'tech-spark', target: 'sk-data-pipeline', relation: 'requires', weight: 5 },
  { source: 'tech-spark', target: 'sk-realtime', relation: 'requires', weight: 4 },

  // MySQL / Redis
  { source: 'tech-mysql', target: 'sk-data-pipeline', relation: 'related_to', weight: 2 },

  // Node.js
  { source: 'tech-node', target: 'sk-fullstack', relation: 'requires', weight: 3 },
  { source: 'tech-node', target: 'sk-api-design', relation: 'requires', weight: 3 },

  // FastAPI
  { source: 'tech-fastapi', target: 'sk-api-design', relation: 'requires', weight: 4 },
  { source: 'tech-fastapi', target: 'sk-microservice', relation: 'related_to', weight: 3 },

  // ===== Cross-technology edges =====
  { source: 'tech-python', target: 'tech-langchain', relation: 'related_to', weight: 4 },
  { source: 'tech-langchain', target: 'tech-llm', relation: 'related_to', weight: 5 },
  { source: 'tech-langchain', target: 'tech-rag', relation: 'related_to', weight: 4 },
  { source: 'tech-llm', target: 'tech-rag', relation: 'related_to', weight: 3 },
  { source: 'tech-vue3', target: 'tech-node', relation: 'related_to', weight: 3 },
  { source: 'tech-springboot', target: 'tech-docker', relation: 'related_to', weight: 3 },
  { source: 'tech-docker', target: 'tech-node', relation: 'related_to', weight: 2 },
  { source: 'tech-agent', target: 'tech-llm', relation: 'related_to', weight: 3 },
  { source: 'tech-fastapi', target: 'tech-python', relation: 'related_to', weight: 5 },
  { source: 'tech-vite', target: 'tech-ts', relation: 'related_to', weight: 4 },
]
