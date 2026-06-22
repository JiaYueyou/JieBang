import type { ResumeData } from '@/types'

export const mockResumes: ResumeData[] = [
  {
    id: 'r-1',
    name: 'Java后端开发简历',
    targetPosition: 'Java 开发工程师',
    personalInfo: {
      name: '张三',
      email: 'zhangsan@example.com',
      phone: '138****1234',
      location: '北京',
      avatar: '',
    },
    jobIntent: {
      desiredPosition: 'Java 开发工程师',
      desiredCity: '北京',
      salaryExpectation: '15K-25K',
      workMode: 'fulltime',
    },
    education: [
      {
        school: '某科技大学',
        degree: '本科',
        major: '计算机科学与技术',
        startDate: '2019-09',
        endDate: '2023-06',
      },
    ],
    workExperience: [
      {
        company: '某互联网公司',
        position: 'Java 后端开发',
        startDate: '2023-07',
        endDate: '2026-06',
        description: '负责电商平台订单系统后端开发，使用 Spring Boot + MySQL + Redis 技术栈，参与微服务拆分与容器化部署。',
        skills: ['Java', 'Spring Boot', 'MySQL', 'Redis', 'Docker'],
      },
    ],
    projects: [
      {
        name: '电商订单系统',
        role: '核心开发',
        description: '负责订单模块的设计与开发，日均处理订单量 10万+，采用微服务架构，保证数据一致性。',
        technologies: ['Java', 'Spring Cloud', 'RocketMQ', 'MySQL'],
        highlights: ['系统QPS从500优化至2000', '引入消息队列解耦订单流程'],
      },
    ],
    skills: [
      { id: 'rs1', name: 'Java', level: 'advanced', category: '编程语言' },
      { id: 'rs2', name: 'Spring Boot', level: 'advanced', category: '框架' },
      { id: 'rs3', name: 'MySQL', level: 'required', category: '数据存储' },
      { id: 'rs4', name: 'Redis', level: 'required', category: '数据存储' },
      { id: 'rs5', name: 'Docker', level: 'preferred', category: '云原生' },
      { id: 'rs6', name: '微服务', level: 'preferred', category: '架构' },
    ],
    selfEvaluation: '三年Java后端开发经验，熟悉企业级应用开发，具备良好的系统设计能力和团队协作精神。',
    createdAt: '2026-06-01',
    updatedAt: '2026-06-15',
  },
  {
    id: 'r-2',
    name: 'AI方向简历',
    targetPosition: 'AI 智能体开发工程师',
    personalInfo: {
      name: '李四',
      email: 'lisi@example.com',
      phone: '139****5678',
      location: '上海',
    },
    jobIntent: {
      desiredPosition: 'AI 工程师',
      desiredCity: '上海',
      salaryExpectation: '25K-40K',
      workMode: 'fulltime',
    },
    education: [
      {
        school: '某理工大学',
        degree: '硕士',
        major: '人工智能',
        startDate: '2021-09',
        endDate: '2024-06',
      },
    ],
    workExperience: [
      {
        company: '某AI公司',
        position: 'AI 算法工程师',
        startDate: '2024-07',
        endDate: '2026-05',
        description: '负责基于 LLM 的对话系统开发，使用 LangChain + FastAPI 构建 RAG 问答系统，参与 Agent 框架预研。',
        skills: ['Python', 'LangChain', 'FastAPI', '向量数据库'],
      },
    ],
    projects: [
      {
        name: '企业智能知识库',
        role: '项目负责人',
        description: '搭建基于 RAG 的企业级智能问答系统，支持多文档格式解析与检索。',
        technologies: ['Python', 'LangChain', 'ChromaDB', 'FastAPI', 'Vue 3'],
        highlights: ['检索召回率 95%+', '日均问答量 5000+'],
      },
    ],
    skills: [
      { id: 'rs10', name: 'Python', level: 'advanced', category: '编程语言' },
      { id: 'rs11', name: 'LangChain', level: 'required', category: 'AI框架' },
      { id: 'rs12', name: 'LLM API', level: 'required', category: 'AI技术' },
      { id: 'rs13', name: 'RAG', level: 'required', category: 'AI技术' },
      { id: 'rs14', name: 'Prompt Engineering', level: 'required', category: 'AI技术' },
      { id: 'rs15', name: 'FastAPI', level: 'preferred', category: '后端' },
    ],
    selfEvaluation: '对 AI Agent 和 RAG 方向有浓厚兴趣，持续跟踪前沿技术，具备独立项目交付能力。',
    createdAt: '2026-05-15',
    updatedAt: '2026-06-12',
  },
]
