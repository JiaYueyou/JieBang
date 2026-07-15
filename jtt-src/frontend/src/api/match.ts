import api from './index'
import type { ApiResponse, MatchResult } from '@/types'

export const matchApi = {
  match: (resumeId: string, positionId: string) =>
    api.post<ApiResponse<MatchResult>>('/match', {
      resume_id: Number(resumeId),
      position_id: Number(positionId),
    }),

  getResult: (resumeId: string, positionId: string) =>
    api.get<ApiResponse<MatchResult>>(`/match/result/${resumeId}/${positionId}`),

  getHistory: () => api.get<ApiResponse<MatchResult[]>>('/match/history'),

  matchBatch: (data: { resumeId: string; positionIds: string[] }) =>
<<<<<<< HEAD
    api.post<ApiResponse<MatchResult[]>>('/match/batch', {
      resume_id: Number(data.resumeId),
      position_ids: data.positionIds.map(Number),
    }),

  // [Agent 3] 自动匹配：将简历与所有岗位逐一匹配，按分数降序返回诊断报告
  autoMatch: (resumeId: string) =>
    api.post<ApiResponse<MatchResult[]>>(`/match/auto/${resumeId}`),
=======
    api.post<ApiResponse<MatchResult[]>>('/match/batch', data),

  autoDetect: (resumeId: string) =>
    api.post<ApiResponse<MatchResult[]>>('/match/auto-detect', { resumeId }),
>>>>>>> aa08688 (feat(fyz-backend): add job filtering)
}
