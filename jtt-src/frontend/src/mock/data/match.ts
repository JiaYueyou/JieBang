import type { MatchResult } from '@/types'

export const mockMatchResults: Record<string, MatchResult> = {
  'r-1_ep-1': {
    id: 'm-1',
    resumeId: 'r-1',
    positionId: 'ep-1',
    positionName: 'Java 开发工程师',
    resumeName: 'Java后端开发简历',
    totalScore: 68,
    dimensions: [
      { name: '技能匹配', score: 72, weight: 0.4, details: '核心技能Java/Spring匹配；缺少LLM集成和智能体开发经验' },
      { name: '经验匹配', score: 65, weight: 0.3, details: '后端开发经验较匹配，但缺少AI相关项目经历' },
      { name: '学历匹配', score: 80, weight: 0.15, details: '本科计算机专业，满足岗位要求' },
      { name: '综合素质', score: 55, weight: 0.15, details: '全栈能力和AI意识有待提升' },
    ],
    gapAnalysis: {
      missingSkills: [
        { id: 'gs1', name: '智能体开发', level: 'required', category: 'AI集成' },
        { id: 'gs2', name: 'LLM API 集成', level: 'required', category: 'AI集成' },
        { id: 'gs3', name: 'Kubernetes', level: 'required', category: '云原生' },
        { id: 'gs4', name: 'RAG 框架', level: 'preferred', category: 'AI集成' },
      ],
      weakSkills: [
        { id: 'ws1', name: '微服务架构', level: 'preferred', category: '架构' },
      ],
      matchSkills: [
        { id: 'ms1', name: 'Java', level: 'advanced', category: '编程语言' },
        { id: 'ms2', name: 'Spring Boot', level: 'advanced', category: '框架' },
        { id: 'ms3', name: 'MySQL', level: 'required', category: '数据存储' },
        { id: 'ms4', name: 'Redis', level: 'required', category: '数据存储' },
        { id: 'ms5', name: 'Docker', level: 'preferred', category: '云原生' },
      ],
    },
    suggestions: [
      {
        id: 'sg-1',
        section: 'skills',
        field: 'skills',
        original: '未包含 LLM API 集成相关技能',
        suggested: '添加"LLM API 集成（OpenAI/讯飞星火）"到技能清单',
        reason: '该岗位已将LLM API集成列为必备技能，建议在简历中明确列出',
        changeType: 'small',
        verified: true,
        accepted: false,
      },
      {
        id: 'sg-2',
        section: 'workExperience',
        field: 'description',
        original: '负责电商平台订单系统后端开发，使用 Spring Boot + MySQL + Redis 技术栈，参与微服务拆分与容器化部署。',
        suggested: '负责电商平台订单系统后端开发，使用 Spring Boot + MySQL + Redis 技术栈，主导微服务拆分与 Docker/K8s 容器化部署，并接入 AI 能力实现智能订单路由。',
        reason: '增加对云原生和AI集成的描述，更贴合当前岗位要求',
        changeType: 'small',
        verified: true,
        accepted: false,
      },
      {
        id: 'sg-3',
        section: 'selfEvaluation',
        field: 'selfEvaluation',
        original: '三年Java后端开发经验，熟悉企业级应用开发，具备良好的系统设计能力和团队协作精神。',
        suggested: '三年Java后端开发经验，熟悉企业级应用开发与微服务架构。持续学习AI技术，正在拓展LLM集成与智能体开发能力，致力于成为AI时代的技术全栈工程师。',
        reason: '展示对新技术的主动学习意愿，符合岗位"动态更新"的特点',
        changeType: 'small',
        verified: true,
        accepted: false,
      },
    ],
    matchDate: '2026-06-18',
  },
  'r-2_np-1': {
    id: 'm-2',
    resumeId: 'r-2',
    positionId: 'np-1',
    positionName: 'AI 智能体开发工程师',
    resumeName: 'AI方向简历',
    totalScore: 78,
    dimensions: [
      { name: '技能匹配', score: 82, weight: 0.4, details: 'Python/AI技能较匹配；LLM和Agent框架经验丰富' },
      { name: '经验匹配', score: 75, weight: 0.3, details: '有AI项目落地经验，但工作年限较短' },
      { name: '学历匹配', score: 85, weight: 0.15, details: '硕士学历，AI研究方向' },
      { name: '综合素质', score: 70, weight: 0.15, details: '学习能力强，具备跨领域协作能力' },
    ],
    gapAnalysis: {
      missingSkills: [
        { id: 'gs5', name: '多模态模型', level: 'preferred', category: 'AI技术' },
      ],
      weakSkills: [
        { id: 'ws2', name: '分布式训练', level: 'preferred', category: 'AI工程' },
        { id: 'ws3', name: '模型部署', level: 'required', category: 'MLOps' },
      ],
      matchSkills: [
        { id: 'ms6', name: 'Python', level: 'advanced', category: '编程语言' },
        { id: 'ms7', name: 'PyTorch', level: 'advanced', category: '框架' },
        { id: 'ms8', name: 'LangChain', level: 'required', category: 'AI框架' },
        { id: 'ms9', name: 'Agent框架', level: 'required', category: 'AI集成' },
      ],
    },
    suggestions: [
      {
        id: 'sg-4',
        section: 'skills',
        field: 'skills',
        original: '熟练使用 PyTorch、TensorFlow 等深度学习框架',
        suggested: '熟练使用 PyTorch、TensorFlow 等深度学习框架，具备 LangChain/LlamaIndex 等 LLM 应用框架经验',
        reason: '增加LLM应用框架经验，更贴合智能体开发岗位需求',
        changeType: 'small',
        verified: true,
        accepted: false,
      },
    ],
    matchDate: '2026-06-15',
  },
  'r-1_ep-2': {
    id: 'm-3',
    resumeId: 'r-1',
    positionId: 'ep-2',
    positionName: '前端开发工程师',
    resumeName: 'Java后端开发简历',
    totalScore: 42,
    dimensions: [
      { name: '技能匹配', score: 30, weight: 0.4, details: 'Java后端技术栈，前端技能缺失严重' },
      { name: '经验匹配', score: 35, weight: 0.3, details: '无前端项目经验' },
      { name: '学历匹配', score: 75, weight: 0.15, details: '本科计算机专业，基础满足' },
      { name: '综合素质', score: 45, weight: 0.15, details: '转方向需要较多学习和实践' },
    ],
    gapAnalysis: {
      missingSkills: [
        { id: 'gs6', name: 'JavaScript/TypeScript', level: 'required', category: '编程语言' },
        { id: 'gs7', name: 'Vue.js', level: 'required', category: '前端框架' },
        { id: 'gs8', name: 'HTML/CSS', level: 'required', category: '前端基础' },
      ],
      weakSkills: [],
      matchSkills: [
        { id: 'ms10', name: 'Git', level: 'required', category: '工具' },
      ],
    },
    suggestions: [
      {
        id: 'sg-5',
        section: 'selfEvaluation',
        field: 'selfEvaluation',
        original: '三年Java后端开发经验',
        suggested: '三年Java后端开发经验，对全栈开发有浓厚兴趣',
        reason: '若考虑转前端方向，建议补充相关技能后再进行匹配',
        changeType: 'large',
        verified: true,
        accepted: false,
      },
    ],
    matchDate: '2026-06-10',
  },
  'r-1_np-2': {
    id: 'm-4',
    resumeId: 'r-1',
    positionId: 'np-2',
    positionName: '上下文工程专家',
    resumeName: 'Java后端开发简历',
    totalScore: 55,
    dimensions: [
      { name: '技能匹配', score: 50, weight: 0.4, details: '后端工程能力可迁移，但上下文工程概念不熟悉' },
      { name: '经验匹配', score: 55, weight: 0.3, details: '系统工程经验有一定基础' },
      { name: '学历匹配', score: 70, weight: 0.15, details: '本科学历基本满足' },
      { name: '综合素质', score: 50, weight: 0.15, details: '需补足领域知识' },
    ],
    gapAnalysis: {
      missingSkills: [
        { id: 'gs9', name: 'Prompt Engineering', level: 'required', category: 'AI技能' },
        { id: 'gs10', name: 'Context Window 优化', level: 'required', category: 'AI技能' },
      ],
      weakSkills: [
        { id: 'ws4', name: 'Python', level: 'preferred', category: '编程语言' },
      ],
      matchSkills: [
        { id: 'ms11', name: '系统设计', level: 'required', category: '工程能力' },
        { id: 'ms12', name: 'API 设计', level: 'required', category: '工程能力' },
      ],
    },
    suggestions: [],
    matchDate: '2026-06-05',
  },
  'r-2_ep-3': {
    id: 'm-5',
    resumeId: 'r-2',
    positionId: 'ep-3',
    positionName: '数据工程师',
    resumeName: 'AI方向简历',
    totalScore: 72,
    dimensions: [
      { name: '技能匹配', score: 70, weight: 0.4, details: 'Python和数据处理技能匹配较好' },
      { name: '经验匹配', score: 68, weight: 0.3, details: '有数据相关项目经验' },
      { name: '学历匹配', score: 85, weight: 0.15, details: '硕士学历优势明显' },
      { name: '综合素质', score: 72, weight: 0.15, details: 'AI背景对数据处理有加成' },
    ],
    gapAnalysis: {
      missingSkills: [
        { id: 'gs11', name: 'Spark', level: 'required', category: '大数据' },
        { id: 'gs12', name: 'Flink', level: 'preferred', category: '大数据' },
      ],
      weakSkills: [
        { id: 'ws5', name: 'SQL 调优', level: 'required', category: '数据存储' },
      ],
      matchSkills: [
        { id: 'ms13', name: 'Python', level: 'advanced', category: '编程语言' },
        { id: 'ms14', name: 'SQL', level: 'required', category: '数据查询' },
        { id: 'ms15', name: 'ETL工具', level: 'preferred', category: '数据处理' },
      ],
    },
    suggestions: [
      {
        id: 'sg-6',
        section: 'skills',
        field: 'skills',
        original: '精通 Python，熟悉数据处理与机器学习',
        suggested: '精通 Python 与 SQL，熟悉 Spark/Flink 大数据处理框架，有 ETL 流程设计经验',
        reason: '数据工程师岗位更看重大数据处理能力，建议突出相关技术栈',
        changeType: 'small',
        verified: true,
        accepted: false,
      },
    ],
    matchDate: '2026-05-28',
  },
}

export const mockHistoryMatches: MatchResult[] = [
  mockMatchResults['r-1_ep-1']!,
  mockMatchResults['r-2_np-1']!,
  mockMatchResults['r-1_ep-2']!,
  mockMatchResults['r-1_np-2']!,
  mockMatchResults['r-2_ep-3']!,
]
