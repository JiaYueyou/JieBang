/**
 * 学习路径 API —— 学习路径 CRUD + AI 学习助手。
 */
import api from './index'

export const learningApi = {
  // 学习路径 CRUD
  getList: () => api.get('/learning/paths'),
  create: (data: { name: string; positionId: number }) =>
    api.post('/learning/paths', { name: data.name, position_id: data.positionId }),
  update: (id: string, data: Record<string, any>) => api.put(`/learning/paths/${id}`, data),
  delete: (id: string) => api.delete(`/learning/paths/${id}`),

  // AI 学习助手（LLM 调用可能较慢，放宽超时）
  chat: (data: { message: string; context?: Record<string, any>; history?: Record<string, any>[] }) =>
    api.post('/learning/assistant/chat', data, { timeout: 90000 }),
  generatePath: (data: { positionId: number; resumeId?: number }) =>
    api.post('/learning/assistant/generate-path', {
      position_id: data.positionId,
      resume_id: data.resumeId ?? null,
    }, { timeout: 90000 }),
  recommendResources: (skillNames: string[]) =>
    api.post('/learning/assistant/recommend-resources', { skill_names: skillNames }, { timeout: 90000 }),
  quiz: (data: { pathId: string; stepIds?: string[]; questionCount?: number }) =>
<<<<<<< HEAD
    api.post('/learning/assistant/quiz', {
      path_id: Number(data.pathId),
      step_ids: data.stepIds ?? [],
      question_count: data.questionCount ?? 5,
    }, { timeout: 90000 }),
=======
    api.post('/learning/assistant/quiz', data),

  generateFromGaps: (resumeId: string, positionId: string) =>
    api.post('/learning/generate-from-gaps', { resumeId, positionId }),
>>>>>>> aa08688 (feat(fyz-backend): add job filtering)
}
