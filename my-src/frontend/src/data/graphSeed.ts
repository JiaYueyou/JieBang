import type { GraphSubgraph } from "@/domain/types";

export const graphSeed: GraphSubgraph = {
  nodes: [
    { id:"job-ai",name:"AI 应用开发",type:"Job",stack:"ai",level:"senior",x:115,y:124,importance:.94,description:"面向企业知识库、智能问答和业务 Agent 的 AI 应用岗位。" },
    { id:"job-java",name:"Java 高级开发",type:"Job",stack:"backend",level:"senior",x:115,y:260,importance:.88,description:"负责后端服务、微服务架构与业务平台稳定性建设。" },
    { id:"job-data",name:"大数据工程师",type:"Job",stack:"data",level:"middle",x:115,y:396,importance:.82,description:"负责数据采集、数仓建模、离线与实时计算链路。" },
    { id:"area-llm",name:"大模型应用",type:"SkillArea",stack:"ai",level:"senior",x:300,y:92,importance:.95,description:"围绕 LLM API、Agent、RAG 与模型应用工程化的能力域。" },
    { id:"area-service",name:"服务架构",type:"SkillArea",stack:"backend",level:"senior",x:300,y:238,importance:.89,description:"高并发后端服务、微服务拆分与稳定性治理能力域。" },
    { id:"area-pipeline",name:"数据链路",type:"SkillArea",stack:"data",level:"middle",x:300,y:396,importance:.84,description:"覆盖数据接入、清洗、计算、调度与指标产出的能力域。" },
    { id:"stack-rag",name:"RAG",type:"TechStack",stack:"ai",level:"senior",x:486,y:72,frequency:78,description:"检索增强生成，用于降低幻觉并绑定企业知识源。" },
    { id:"stack-agent",name:"LangChain Agent",type:"TechStack",stack:"ai",level:"senior",x:486,y:142,frequency:63,description:"工具调用、任务规划和多步推理编排框架。" },
    { id:"stack-spring",name:"Spring Cloud",type:"TechStack",stack:"backend",level:"senior",x:486,y:238,frequency:86,description:"Java 微服务体系，覆盖注册发现、配置、网关和服务治理。" },
    { id:"stack-redis",name:"Redis",type:"TechStack",stack:"backend",level:"middle",x:486,y:310,frequency:74,description:"缓存、分布式锁、限流和高性能数据结构。" },
    { id:"stack-flink",name:"Flink",type:"TechStack",stack:"data",level:"middle",x:486,y:396,frequency:58,description:"实时计算引擎，适合流式指标和数据管道。" },
    { id:"point-vector",name:"向量检索",type:"TechPoint",stack:"ai",level:"senior",x:674,y:64,frequency:51,description:"Embedding、召回、重排和向量数据库查询优化。" },
    { id:"point-prompt",name:"Prompt 编排",type:"TechPoint",stack:"ai",level:"middle",x:674,y:146,frequency:67,description:"提示模板、上下文注入、输出约束和评测闭环。" },
    { id:"point-gateway",name:"网关治理",type:"TechPoint",stack:"backend",level:"senior",x:674,y:224,frequency:46,description:"鉴权、限流、灰度、熔断和链路追踪入口治理。" },
    { id:"point-cache",name:"缓存一致性",type:"TechPoint",stack:"backend",level:"middle",x:674,y:310,frequency:55,description:"缓存穿透、击穿、雪崩与数据一致性策略。" },
    { id:"point-window",name:"窗口计算",type:"TechPoint",stack:"data",level:"middle",x:674,y:396,frequency:39,description:"滚动窗口、滑动窗口及水位线机制。" },
    { id:"knowledge-rerank",name:"召回与重排评估",type:"KnowledgePoint",stack:"ai",level:"senior",x:836,y:64,frequency:32,description:"评估检索命中率、MRR 和答案引用质量。" },
    { id:"knowledge-template",name:"结构化输出约束",type:"KnowledgePoint",stack:"ai",level:"middle",x:836,y:146,frequency:44,description:"通过 JSON schema 和校验器约束模型输出。" },
    { id:"knowledge-resilience",name:"熔断降级策略",type:"KnowledgePoint",stack:"backend",level:"senior",x:836,y:224,frequency:36,description:"高可用系统中的超时、重试、隔离和降级设计。" },
    { id:"knowledge-cache",name:"热点 Key 治理",type:"KnowledgePoint",stack:"backend",level:"middle",x:836,y:310,frequency:42,description:"热点发现、本地缓存、分片和预热策略。" },
    { id:"knowledge-watermark",name:"Watermark 机制",type:"KnowledgePoint",stack:"data",level:"middle",x:836,y:396,frequency:28,description:"处理乱序数据、延迟数据和窗口触发语义。" },
  ],
  edges: [
    ["job-ai","area-llm","REQUIRES_AREA"],["job-java","area-service","REQUIRES_AREA"],["job-data","area-pipeline","REQUIRES_AREA"],
    ["area-llm","stack-rag","CONTAINS"],["area-llm","stack-agent","CONTAINS"],["area-service","stack-spring","CONTAINS"],["area-service","stack-redis","CONTAINS"],["area-pipeline","stack-flink","CONTAINS"],
    ["stack-rag","point-vector","REFINES_TO"],["stack-agent","point-prompt","REFINES_TO"],["stack-spring","point-gateway","REFINES_TO"],["stack-redis","point-cache","REFINES_TO"],["stack-flink","point-window","REFINES_TO"],
    ["point-vector","knowledge-rerank","HAS_KNOWLEDGE"],["point-prompt","knowledge-template","HAS_KNOWLEDGE"],["point-gateway","knowledge-resilience","HAS_KNOWLEDGE"],["point-cache","knowledge-cache","HAS_KNOWLEDGE"],["point-window","knowledge-watermark","HAS_KNOWLEDGE"],
    ["stack-rag","stack-redis","RELATED_TO"],["point-vector","point-cache","SAME_AS"],
  ].map(([source,target,relation],index)=>({id:`e${index+1}`,source,target,relation} as GraphSubgraph["edges"][number])),
};
