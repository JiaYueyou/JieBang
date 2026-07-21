import api from './index'
import type { ApiResponse, ImprovementSuggestion } from '@/types'

// 后端接口为 snake_case，回传建议时需转换字段名
const toPayload = (s: ImprovementSuggestion) => ({
  id: s.id,
  section: s.section,
  field: s.field,
  original: s.original,
  suggested: s.suggested,
  reason: s.reason,
  change_type: s.changeType,
  accepted: s.accepted,
})

export const tailorApi = {
  // AI 建议生成可能较慢（LLM 调用），放宽超时
  getSuggestions: (resumeId: string, positionId: string) =>
    api.get<ApiResponse<ImprovementSuggestion[]>>(
      `/tailor/suggestions/${resumeId}/${positionId}`,
      { timeout: 90000 },
    ),

  acceptSuggestion: (resumeId: string, suggestionId: string) =>
    api.post<ApiResponse<null>>(`/tailor/accept`, {
      resume_id: Number(resumeId),
      suggestion_id: suggestionId,
    }),

  applyAll: (resumeId: string, suggestions: ImprovementSuggestion[]) =>
    api.post<ApiResponse<{ new_resume_id: number }>>(`/tailor/apply-all`, {
      resume_id: Number(resumeId),
      suggestion_ids: suggestions.map((s) => s.id),
      suggestions: suggestions.map(toPayload),
    }),

  optimizePhrase: (text: string, style: 'professional' | 'concise' | 'match' | 'impact') =>
    api.post<ApiResponse<{ suggestions: string[] }>>(
      '/tailor/optimize-phrase',
      { text, style },
      { timeout: 90000 },
    ),

  saveAsNew: (resumeId: string, suggestions: ImprovementSuggestion[]) =>
    api.post<ApiResponse<{ new_resume_id: number }>>('/tailor/save-as-new', {
      resume_id: Number(resumeId),
      suggestion_ids: suggestions.map((s) => s.id),
      suggestions: suggestions.map(toPayload),
    }),
}
