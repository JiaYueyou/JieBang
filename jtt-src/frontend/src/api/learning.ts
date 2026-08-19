/**
 * 学习路径 API —— 学习路径 CRUD + AI 学习助手。
 */
import api from './index'

export const learningApi = {
  // 学习路径 CRUD
  getList: () => api.get('/learning/paths'),
  create: (data: { name: string; positionId?: number; positionName?: string; steps?: any[] }) =>
    api.post('/learning/paths', {
      name: data.name,
      position_id: data.positionId ?? 0, // DB 列为 INT NOT NULL，空时填 0
      position_name: data.positionName ?? '',
      steps: data.steps ?? [],
    }),
  update: (id: string, data: Record<string, any>) => api.put(`/learning/paths/${id}`, data),
  delete: (id: string) => api.delete(`/learning/paths/${id}`),

  // AI 学习助手（LLM 调用可能较慢，放宽超时）
  chat: (data: { message: string; context?: Record<string, any>; pageContext?: Record<string, any>; history?: Record<string, any>[] }) =>
    api.post('/learning/assistant/chat', data, { timeout: 90000 }),
  generatePath: (data: { position_name: string; missing_skills: string[]; matched_skills: string[]; resume_id: number }) =>
    api.post('/learning/assistant/generate-path', {
      position_name: data.position_name,
      missing_skills: data.missing_skills,
      matched_skills: data.matched_skills,
      resume_id: data.resume_id,
    }, { timeout: 90000 }),
  recommendResources: (skillNames: string[]) =>
    api.post('/learning/assistant/recommend-resources', { skill_names: skillNames }, { timeout: 90000 }),
  quiz: (data: { pathId: string; stepIds?: string[]; questionCount?: number }) =>
    api.post('/learning/assistant/quiz', {
      path_id: Number(data.pathId),
      step_ids: data.stepIds ?? [],
      question_count: data.questionCount ?? 5,
    }, { timeout: 90000 }),
}
