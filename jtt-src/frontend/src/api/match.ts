import api from './index'
import type { ApiResponse, MatchResult } from '@/types'

export const matchApi = {
  // 单次匹配走 LLM 语义匹配，后端最坏约 2 分钟，超时放宽到 180s（全局默认 15s 不够）
  match: (resumeId: string, positionId: string) =>
    api.post<ApiResponse<MatchResult>>('/match', {
      resume_id: Number(resumeId),
      position_id: Number(positionId),
    }, { timeout: 180000 }),

  getResult: (resumeId: string, positionId: string) =>
    api.get<ApiResponse<MatchResult>>(`/match/result/${resumeId}/${positionId}`),

  getHistory: () => api.get<ApiResponse<MatchResult[]>>('/match/history'),

  matchBatch: (data: { resumeId: string; positionIds: string[] }) =>
    api.post<ApiResponse<MatchResult[]>>('/match/batch', {
      resume_id: Number(data.resumeId),
      position_ids: data.positionIds.map(Number),
    }),

  // [Agent 3] 自动匹配：将简历与所有岗位逐一匹配，按分数降序返回诊断报告
  // 走规则+图谱批量模式（不调 LLM），但需加载全部岗位，放宽到 60s
  autoMatch: (resumeId: string) =>
    api.post<ApiResponse<MatchResult[]>>(`/match/auto/${resumeId}`, null, { timeout: 60000 }),
}
