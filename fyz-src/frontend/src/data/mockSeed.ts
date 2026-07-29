import type { MockDatabase } from "@/domain/types";
import { graphSeed } from "./graphSeed";

export const createMockSeed = (): MockDatabase => ({
  version: 1,
  jobs: [
    { id: 1, title: "Java 高级开发工程师", department: "后台开发组", headcount: 2, status: "open", created_at: "2026-06-15", level: "高级", salary_range: "25K-40K·14薪", responsibilities: ["负责核心业务系统的架构设计","主导关键模块编码与代码审查","技术难点攻关与性能优化"], requirements: ["5年以上Java开发经验","精通Spring Cloud微服务架构","有大型分布式系统经验"], bonus_skills: ["Docker/K8s","大模型应用"], location: "杭州", company: "智联职引 · 研发中心", experience: "5–10 年", education: "本科", skills: ["Java","Spring Cloud","MySQL","Redis","Kubernetes"], match: 92, urgent: true },
    { id: 2, title: "AI 算法工程师", department: "AI 研究院", headcount: 3, status: "open", created_at: "2026-06-10", level: "高级", salary_range: "30K-50K·14薪", responsibilities: ["大模型训练与微调","算法模型推理优化"], requirements: ["硕士及以上","精通PyTorch/TensorFlow","有LLM相关经验"], bonus_skills: ["CUDA优化","模型部署"], location: "北京", company: "智联职引 · AI 研究院", experience: "3–5 年", education: "硕士", skills: ["Python","PyTorch","NLP","Transformer","CUDA"], match: 94, urgent: true },
    { id: 3, title: "Python 后端开发", department: "数据平台组", headcount: 1, status: "draft", created_at: "2026-06-08", level: "中级", salary_range: "18K-28K·13薪", responsibilities: ["数据平台后端服务开发","API设计与优化"], requirements: ["3年以上Python经验","熟悉FastAPI/Django","熟悉PostgreSQL"], bonus_skills: ["Docker","Redis"], location: "成都", company: "智联职引 · 数据平台组", experience: "3–5 年", education: "本科", skills: ["Python","FastAPI","PostgreSQL","Docker"], match: 89 },
    { id: 4, title: "AI 大模型应用工程师", department: "AI 研究院", headcount: 4, status: "open", created_at: "2026-06-18", level: "高级", salary_range: "25K-40K", responsibilities: ["企业级大模型应用研发"], requirements: ["熟悉 RAG 和 Agent"], bonus_skills: ["模型微调"], location: "合肥", company: "科大讯飞 · AI 研究院", experience: "3–5 年", education: "本科", skills: ["Python","RAG","LangChain","向量数据库","模型微调"], match: 94, urgent: true },
    { id: 5, title: "云原生架构师", department: "平台架构部", headcount: 2, status: "open", created_at: "2026-06-16", level: "专家", salary_range: "35K-55K", responsibilities: ["云原生架构设计"], requirements: ["精通 Kubernetes"], bonus_skills: ["Service Mesh"], location: "上海", company: "星环科技 · 平台架构部", experience: "5–10 年", education: "本科", skills: ["Kubernetes","Service Mesh","Go","DevOps","微服务"], match: 87 },
    { id: 6, title: "数据安全专家", department: "安全产品中心", headcount: 1, status: "open", created_at: "2026-06-12", level: "专家", salary_range: "30K-50K", responsibilities: ["数据安全体系建设"], requirements: ["熟悉等保和零信任"], bonus_skills: ["云安全"], location: "北京", company: "天翼云 · 安全产品中心", experience: "5–10 年", education: "本科", skills: ["数据安全","零信任","等保","云安全","风险评估"], match: 82 },
  ],
  emergingJobs: [
    { id: 101, name: "AI 提示词工程师", core_skills: ["Prompt设计","RAG","LLM微调"], description: "负责企业级大模型应用的提示词工程设计与优化", confidence: 92 },
    { id: 102, name: "云原生安全专家", core_skills: ["K8s安全","零信任架构","容器逃逸检测"], description: "面向云原生架构的端到端安全方案设计", confidence: 88 },
    { id: 103, name: "MLOps 工程师", core_skills: ["模型部署","特征平台","MLflow"], description: "打通从模型训练到生产部署的全流程", confidence: 85 },
    { id: 104, name: "AI 产品体验设计师", core_skills: ["交互设计","Prompt UX","A/B测试"], description: "专注于大模型应用的人机交互体验优化", confidence: 81 },
    { id: 105, name: "向量数据库管理员", core_skills: ["Milvus","ChromaDB","向量索引优化"], description: "管理企业级向量数据库集群", confidence: 76 },
  ],
  capabilityChanges: [
    { id: 1, job_id: 1, job: "Java 开发工程师", period: "近 6 个月变化", added: ["RAG 集成","Spring AI","向量数据库基础"], modified: ["微服务架构（Spring Cloud → K8s 云原生）"], removed: ["Struts","JSP","WebLogic"] },
    { id: 2, job_id: 3, job: "Python 后端开发", period: "近 6 个月变化", added: ["FastAPI","大模型 API 开发","LangChain"], modified: ["异步编程（asyncio 从可选→必备）"], removed: ["Python 2 兼容"] },
    { id: 3, job_id: 7, job: "前端开发工程师", period: "近 6 个月变化", added: ["Next.js/SSR","WebAssembly","AI 组件集成"], modified: ["TypeScript（从推荐→必备）"], removed: ["jQuery","IE 兼容","AngularJS 1.x"] },
  ],
  talents: [
    { id: 1, resume_id: 1, match_id: 1, name: "李思远", position: "Java 高级开发", score: 92, isNew: true, experience: "5 年", education: "本科", department: "后台开发组", matched: ["Java","Spring Boot","MySQL","Redis","微服务","MyBatis"], missing: ["K8s","Docker"], targetJobs: ["Java 高级开发工程师","系统架构师"], targetJobIds: [1,5], resumeFile: "李思远_Java开发_5年.pdf", urgent: true, company: "现任职于某头部电商平台", location: "杭州", salary: "期望 30–35K" },
    { id: 2, resume_id: 2, match_id: 2, name: "王语晴", position: "Python 后端开发", score: 89, isNew: true, experience: "3 年", education: "硕士", department: "数据平台组", matched: ["Python","Django","PostgreSQL","Linux","Docker"], missing: ["FastAPI","Redis"], targetJobs: ["Python 后端开发"], targetJobIds: [3], resumeFile: "王语晴_Python_3年.pdf", urgent: false, company: "专注数据平台研发", location: "成都", salary: "期望 20–28K" },
    { id: 3, resume_id: 3, match_id: 3, name: "赵明哲", position: "AI 算法工程师", score: 87, isNew: true, experience: "4 年", education: "硕士", department: "AI 研究院", matched: ["Python","PyTorch","TensorFlow","NLP","Transformer"], missing: ["大模型部署","CUDA"], targetJobs: ["AI 算法工程师","NLP 工程师"], targetJobIds: [2], resumeFile: "赵明哲_AI算法_4年.pdf", urgent: true, company: "专注 NLP 与知识图谱方向", location: "北京", salary: "期望 28–32K" },
    { id: 4, resume_id: 4, match_id: 4, name: "陈晓雯", position: "前端开发工程师", score: 85, isNew: false, experience: "3 年", education: "本科", department: "前端开发组", matched: ["Vue","TypeScript","Element Plus","HTML/CSS"], missing: ["React","Node.js"], targetJobs: ["前端开发工程师","全栈开发"], targetJobIds: [], urgent: false, company: "B 端平台与数据可视化方向", location: "深圳", salary: "期望 25–32K" },
    { id: 5, resume_id: 5, match_id: 5, name: "刘志强", position: "Java 高级开发", score: 83, isNew: false, experience: "6 年", education: "大专", department: "后台开发组", matched: ["Java","Spring Cloud","Oracle","MyBatis","JPA"], missing: ["微服务","K8s","Redis"], targetJobs: ["Java 高级开发工程师"], targetJobIds: [1], urgent: false },
    { id: 6, resume_id: 6, match_id: 6, name: "孙晓琳", position: "DevOps 工程师", score: 81, isNew: false, experience: "4 年", education: "本科", department: "运维组", matched: ["Docker","K8s","Jenkins","Linux","Shell"], missing: ["Terraform","Ansible"], targetJobs: ["DevOps 工程师","SRE"], targetJobIds: [], resumeFile: "孙晓琳_DevOps_4年.pdf", urgent: true },
    { id: 7, resume_id: 7, match_id: 7, name: "周明辉", position: "大数据工程师", score: 78, isNew: false, experience: "5 年", education: "硕士", department: "数据平台组", matched: ["Spark","Hadoop","Hive","Python","SQL"], missing: ["Flink","Kafka"], targetJobs: ["大数据工程师"], targetJobIds: [], urgent: false },
    { id: 8, resume_id: 8, match_id: 8, name: "吴佳琪", position: "软件测试工程师", score: 76, isNew: false, experience: "3 年", education: "本科", department: "测试组", matched: ["Selenium","JMeter","Python","SQL"], missing: ["性能测试","自动化框架设计"], targetJobs: ["软件测试工程师","测试开发"], targetJobIds: [], urgent: false },
  ],
  matches: Array.from({ length: 8 }, (_, index) => ({ id: index + 1, resume_id: index + 1, job_id: index < 3 ? index + 1 : 1, score: [92,89,87,85,83,81,78,76][index], matched: [], missing: [] })),
  favorites: [
    { id: 1, target_type: "job", target_id: 4, title: "AI 大模型应用工程师", subtitle: "研发类岗位", company: "科大讯飞 · AI 研究院", location: "合肥", salary: "25–40K", experience: "3–5 年", education: "本科", skills: ["Python","RAG","LangChain","向量数据库","模型微调"], match: 94, savedAt: "今天 10:32", savedOrder: 6, note: "技术方向与企业 Agent 项目高度吻合", urgent: true },
    { id: 2, target_type: "resume", target_id: 1, title: "李思远", subtitle: "Java 高级开发", company: "现任职于某头部电商平台", location: "杭州", salary: "期望 30–35K", experience: "5 年经验", education: "本科", skills: ["Java","Spring Boot","MySQL","Redis","微服务"], match: 92, savedAt: "今天 09:18", savedOrder: 5, note: "微服务经验完整，可优先安排技术面" },
    { id: 3, target_type: "job", target_id: 5, title: "云原生架构师", subtitle: "架构类岗位", company: "星环科技 · 平台架构部", location: "上海", salary: "35–55K", experience: "5–10 年", education: "本科", skills: ["Kubernetes","Service Mesh","Go","DevOps","微服务"], match: 87, savedAt: "昨天 16:45", savedOrder: 4, note: "" },
    { id: 4, target_type: "resume", target_id: 3, title: "赵明哲", subtitle: "AI 算法工程师", company: "专注 NLP 与知识图谱方向", location: "北京", salary: "期望 28–32K", experience: "4 年经验", education: "硕士", skills: ["NLP","PyTorch","知识图谱","Transformer"], match: 87, savedAt: "昨天 14:06", savedOrder: 3, note: "知识图谱项目经历值得进一步确认", urgent: true },
    { id: 5, target_type: "job", target_id: 6, title: "数据安全专家", subtitle: "安全类岗位", company: "天翼云 · 安全产品中心", location: "北京", salary: "30–50K", experience: "5–10 年", education: "本科", skills: ["数据安全","零信任","等保","云安全","风险评估"], match: 82, savedAt: "06月16日", savedOrder: 2, note: "关注零信任与数据合规能力要求" },
    { id: 6, target_type: "resume", target_id: 4, title: "陈晓雯", subtitle: "前端开发工程师", company: "B 端平台与数据可视化方向", location: "深圳", salary: "期望 25–32K", experience: "3 年经验", education: "本科", skills: ["Vue 3","TypeScript","ECharts","工程化"], match: 85, savedAt: "06月15日", savedOrder: 1, note: "" },
  ],
  history: [
    { id: 1, type: "resume", targetId: 1, title: "李思远 · Java 高级开发", description: "查看候选人技能覆盖、项目经历与岗位匹配分析。", source: "人才匹配", dateKey: "today", date: "06月20日 · 星期六", time: "14:36", tags: ["Java","Spring Boot","92% 匹配"], url: "/matching/1", badge: "高匹配" },
    { id: 2, type: "job", targetId: 4, title: "AI 大模型应用工程师", description: "浏览岗位画像、技能要求与市场薪资区间。", source: "岗位洞察", dateKey: "today", date: "06月20日 · 星期六", time: "13:52", tags: ["RAG","LangChain","25–40K"], url: "/jobs" },
    { id: 3, type: "search", title: "搜索：具备 RAG 项目经验的后端工程师", description: "筛选条件：3 年以上经验、Python、向量数据库、北京或远程。", source: "全局搜索", dateKey: "today", date: "06月20日 · 星期六", time: "11:08", tags: ["RAG","Python","北京"], url: "/matching" },
    { id: 4, type: "graph", targetId: "job-ai", title: "AI 应用开发 · 五层技能树", description: "展开查看岗位、技能域、技能项与知识点之间的关联。", source: "技能图谱", dateKey: "today", date: "06月20日 · 星期六", time: "10:24", tags: ["AI 应用","技能树","L1–L5"], url: "/graph" },
    { id: 5, type: "match", targetId: 3, title: "赵明哲 × AI 算法工程师", description: "查看 87% 综合匹配报告。", source: "智能匹配", dateKey: "yesterday", date: "06月19日 · 星期五", time: "17:42", tags: ["87% 匹配","PyTorch","NLP"], url: "/matching/3" },
  ],
  graph: graphSeed,
});
