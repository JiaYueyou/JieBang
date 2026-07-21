import api from './index'
import type { ApiResponse, CareerPlan, CareerTransitionAssessment, LearningBudget } from '@/types'

export const careerApi = {
  // 职业计划 CRUD
  getPlan: () => api.get<ApiResponse<CareerPlan>>('/career/plan'),
  savePlan: (data: Partial<CareerPlan>) =>
    api.post<ApiResponse<CareerPlan>>('/career/plan', data),

  // 转岗评估
  assess: (data: { resumeId: string; targetPositionId: string; budget: LearningBudget }) =>
    api.post<ApiResponse<CareerTransitionAssessment>>('/career/assess', data),
}
