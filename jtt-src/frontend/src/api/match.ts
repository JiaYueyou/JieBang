import api from './index'
import type { ApiResponse, MatchResult } from '@/types'

export const matchApi = {
  match: (resumeId: string, positionId: string) =>
    api.post<ApiResponse<MatchResult>>('/match', { resumeId, positionId }),

  getResult: (resumeId: string, positionId: string) =>
    api.get<ApiResponse<MatchResult>>(`/match/result/${resumeId}/${positionId}`),

  getHistory: () => api.get<ApiResponse<MatchResult[]>>('/match/history'),

  matchBatch: (data: { resumeId: string; positionIds: string[] }) =>
    api.post<ApiResponse<MatchResult[]>>('/match/batch', data),
}
