import type { CareerTransitionAssessment, CareerPlan } from '@/types'

export const mockCareerAssessments: Record<string, CareerTransitionAssessment> = {
  // Java 后端 → AI Agent 开发
  'r-1_np-1': {
    currentMatchDegree: 68,
    transferableSkills: [
      { id: 'ts1', name: 'Java', level: 'advanced', category: '编程语言' },
      { id: 'ts2', name: '系统设计', level: 'required', category: '工程能力' },
      { id: 'ts3', name: '数据库', level: 'required', category: '数据存储' },
    ],
    missingSkills: [
      { id: 'ms1', name: 'Python', level: 'required', category: '编程语言' },
      { id: 'ms2', name: 'LangChain', level: 'required', category: 'AI框架' },
      { id: 'ms3', name: 'Prompt Engineering', level: 'required', category: 'AI技术' },
      { id: 'ms4', name: 'RAG', level: 'preferred', category: 'AI技术' },
    ],
    recommendationReasons: [
      'Java 后端工程能力可直接迁移到 AI 工程领域，代码质量和系统设计能力是 AI 团队急需的',
      '具备数据库和分布式系统基础，学习向量数据库和 RAG 有优势',
      'AI 行业人才缺口大，薪资增长空间广阔',
    ],
    advantages: [
      '扎实的工程基础，代码质量和系统稳定性意识强',
      '3 年后端经验，有完整的项目交付能力',
      '计算机本科，基础理论扎实，学习新知识有方法',
    ],
    risks: [
      'AI 领域需要补充大量新知识（Python 生态、LLM 原理、Agent 架构），学习曲线陡峭',
      '从后端转向 AI 可能面临初级岗位薪资短期下降',
      'Python 生态和开发模式需要从头适应',
    ],
    learningTimeline: '4-6个月',
    feasibilityRating: 'medium',
  },
  // Java 后端 → 数据工程师
  'r-1_ep-3': {
    currentMatchDegree: 72,
    transferableSkills: [
      { id: 'ts4', name: 'Java', level: 'advanced', category: '编程语言' },
      { id: 'ts5', name: 'SQL', level: 'advanced', category: '数据存储' },
      { id: 'ts6', name: '系统设计', level: 'required', category: '工程能力' },
    ],
    missingSkills: [
      { id: 'ms5', name: 'Python', level: 'required', category: '编程语言' },
      { id: 'ms6', name: 'Spark/Flink', level: 'required', category: '大数据' },
      { id: 'ms7', name: '数据仓库建模', level: 'required', category: '数据工程' },
    ],
    recommendationReasons: [
      'SQL 和数据处理能力强，转数据工程方向技术跨度较小',
      'Java 和大数据生态（Spark/Flink）天然契合',
      '大数据工程师需求持续增长',
    ],
    advantages: [
      'SQL 能力强，数据处理经验丰富',
      'Java 基础扎实，Spark/Flink 的 Java API 易上手',
      '分布式系统经验可复用',
    ],
    risks: [
      '需要系统学习数据仓库建模方法论',
      'Python 在数据领域更主流，需要切换语言习惯',
    ],
    learningTimeline: '2-4个月',
    feasibilityRating: 'high',
  },
  // AI简历 → Java 后端（反向转岗）
  'r-2_ep-1': {
    currentMatchDegree: 55,
    transferableSkills: [
      { id: 'ts7', name: 'Python', level: 'advanced', category: '编程语言' },
      { id: 'ts8', name: 'API 开发', level: 'required', category: '工程能力' },
    ],
    missingSkills: [
      { id: 'ms8', name: 'Java', level: 'required', category: '编程语言' },
      { id: 'ms9', name: 'Spring Boot', level: 'required', category: '框架' },
      { id: 'ms10', name: 'MySQL/Redis', level: 'required', category: '数据存储' },
      { id: 'ms11', name: '微服务', level: 'preferred', category: '架构' },
    ],
    recommendationReasons: [
      'Python 到 Java 语法迁移较容易，面向对象思想通用',
      'AI 背景可帮助传统后端开发引入 AI 能力',
    ],
    advantages: [
      'AI 和 LLM 应用经验是差异化竞争优势',
      'API 开发经验可直接复用',
    ],
    risks: [
      'Java 生态庞大（Spring/MyBatis/Maven），学习内容多',
      '后端开发模式和 AI 开发差异较大',
      '需要补充大量中间件知识',
    ],
    learningTimeline: '5-7个月',
    feasibilityRating: 'low',
  },
}

export const mockCareerPlans: CareerPlan[] = [
  {
    id: 'cp-1',
    resumeId: 'r-1',
    preferences: {
      targetIndustry: '互联网',
      targetRoleType: '技术研发',
      preferredCity: '北京',
      salaryExpectation: '25K-40K',
    },
    budget: {
      weeklyHours: 15,
      totalWeeks: 24,
    },
    targetPositionId: 'np-1',
    targetPositionName: 'AI智能体开发工程师',
    assessment: null,
    createdAt: '2026-07-10',
    updatedAt: '2026-07-10',
  },
]
