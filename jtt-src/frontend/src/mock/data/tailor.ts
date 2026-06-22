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
      accepted: false,
    },
  ],
}

export function generateOptimizedPhrases(text: string, style: string): string[] {
  const templates: Record<string, string[]> = {
    professional: [
      `${text}，取得显著业务成效`,
      `基于 ${text}，持续优化并沉淀为团队最佳实践`,
      `在 ${text} 方面积累了丰富的工程经验`,
    ],
    concise: [
      `擅长 ${text}`,
      `精通 ${text}`,
      `专注 ${text}`,
    ],
    match: [
      `${text}，与目标岗位高度匹配`,
      `具备 ${text} 的实战能力`,
      `在 ${text} 领域有深入实践`,
    ],
    impact: [
      `${text}，实现性能提升30%+`,
      `主导 ${text}，推动系统从单体到微服务的成功演进`,
      `通过 ${text}，将系统吞吐量提升2倍`,
    ],
  }

  const styleTemplates = templates[style] ?? templates.professional!
  return styleTemplates.slice(0, 3)
}
