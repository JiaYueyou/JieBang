/**
 * 学习路径 API —— 学习路径 CRUD + AI 学习助手。
 */
import api from './index'

export const learningApi = {
  // 学习路径 CRUD
  getList: () => api.get('/learning/paths'),
  create: (data: { name: string; positionId: number }) => api.post('/learning/paths', data),
  update: (id: string, data: Record<string, any>) => api.put(`/learning/paths/${id}`, data),
  delete: (id: string) => api.delete(`/learning/paths/${id}`),

  // AI 学习助手
  chat: (data: { message: string; context?: Record<string, any>; history?: Record<string, any>[] }) =>
    api.post('/learning/assistant/chat', data),
  generatePath: (data: { positionId: number; resumeId?: number }) =>
    api.post('/learning/assistant/generate-path', data),
  recommendResources: (skillNames: string[]) =>
    api.post('/learning/assistant/recommend-resources', { skill_names: skillNames }),
  quiz: (data: { pathId: string; stepIds?: string[]; questionCount?: number }) =>
    api.post('/learning/assistant/quiz', data),
}
