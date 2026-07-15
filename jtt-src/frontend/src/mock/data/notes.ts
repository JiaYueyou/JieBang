import type { Note } from '@/types'

export const mockNotes: Note[] = [
  {
    id: 'n-1',
    title: 'Spring Boot 自动配置原理笔记',
    content: 'Spring Boot 通过 @EnableAutoConfiguration 和 @Conditional 系列注解实现智能化自动配置...',
    type: 'note',
    tags: ['Spring Boot', 'Java'],
    createdAt: '2026-06-20',
    updatedAt: '2026-06-20',
  },
  {
    id: 'n-2',
    title: 'RAG 系统设计参考链接',
    content: '企业级 RAG 的最佳实践资源汇总',
    type: 'link',
    url: 'https://example.com/rag-best-practices',
    tags: ['RAG', 'LLM', 'AI'],
    createdAt: '2026-06-18',
    updatedAt: '2026-06-19',
  },
  {
    id: 'n-3',
    title: 'Kubernetes 学习资源合集',
    content: 'Docker + K8s 从入门到实践的学习资料',
    type: 'resource',
    tags: ['Kubernetes', 'Docker', '云原生'],
    createdAt: '2026-06-15',
    updatedAt: '2026-06-15',
  },
]
