import type { ImprovementSuggestion } from '@/types'

export const mockTailorSuggestions: Record<string, ImprovementSuggestion[]> = {
  'r-1_ep-1': [
    {
      id: 'tl-1',
      section: 'skills',
      field: 'skills',
      original: '未包含 LLM API 集成相关技能',
      suggested: '添加"LLM API 集成（OpenAI/讯飞星火）"到技能清单',
      reason: '该岗位已将LLM API集成列为必备技能',
      changeType: 'small',
      verified: true,
      accepted: false,
    },
    {
      id: 'tl-2',
      section: 'workExperience',
      field: 'description',
      original: '负责电商平台订单系统后端开发，使用 Spring Boot + MySQL + Redis 技术栈，参与微服务拆分与容器化部署。',
      suggested: '负责电商平台订单系统后端开发，使用 Spring Boot + MySQL + Redis 技术栈，主导微服务拆分与 Docker/K8s 容器化部署，并接入 AI 能力实现智能订单路由。',
      reason: '增加对云原生和AI集成的描述',
      changeType: 'small',
      verified: true,
      accepted: false,
    },
    {
      id: 'tl-3',
      section: 'workExperience',
      field: 'description',
      original: '参与微服务拆分与容器化部署',
      suggested: '主导核心模块的微服务架构重构，推动 Docker/K8s 全量容器化部署，资源利用率提升 40%',
      reason: '用量化结果增强经历的冲击力',
      changeType: 'small',
      verified: true,
      accepted: false,
    },
    {
      id: 'tl-4',
      section: 'selfEvaluation',
      field: 'selfEvaluation',
      original: '三年Java后端开发经验，熟悉企业级应用开发，具备良好的系统设计能力和团队协作精神。',
      suggested: '三年Java后端开发经验，熟悉企业级应用开发与微服务架构。持续学习AI技术，正在拓展LLM集成与智能体开发能力，致力于成为AI时代的技术全栈工程师。',
      reason: '展示对新技术的主动学习意愿',
      changeType: 'small',
      verified: true,
      accepted: false,
    },
  ],
}

export function generateOptimizedPhrases(text: string, style: string): string[] {
  const templates: Record<string, string[]> = {
    professional: [
      `主导${text}，负责核心技术方案设计与落地，保障系统的高可用性与可扩展性`,
      `深度参与${text}，从需求分析到架构设计全流程把控，产出符合企业级标准的工程实践`,
      `负责${text}相关工作，建立完善的技术规范与协作流程，显著提升团队交付质量与效率`,
    ],
    concise: [
      `${text}（核心负责人，独立完成关键技术攻坚）`,
      `主导${text}，实现关键业务目标落地`,
      `${text}，保障系统稳定高效运行`,
    ],
    match: [
      `${text}，具备岗位要求的核心技术能力，能够快速融入团队并产出价值`,
      `拥有${text}的丰富实战经验，技术栈与目标岗位高度契合，可独立承担核心开发任务`,
      `在${text}方向持续深耕，掌握行业主流方案与最佳实践，满足岗位进阶要求`,
    ],
    impact: [
      `主导${text}，系统性能提升40%+，支撑日均百万级请求稳定运行`,
      `通过${text}，关键指标优化50%以上，推动系统从单体架构成功演进至微服务`,
      `${text}，构建高可用技术体系，系统可用性达99.9%，获团队技术创新认可`,
    ],
  }

  const styleTemplates = templates[style] ?? templates.professional!
  return styleTemplates.slice(0, 3)
}
