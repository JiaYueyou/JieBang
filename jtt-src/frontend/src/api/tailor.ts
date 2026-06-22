import api from './index'
import type { ApiResponse, ImprovementSuggestion } from '@/types'

export const tailorApi = {
  getSuggestions: (resumeId: string, positionId: string) =>
    api.get<ApiResponse<ImprovementSuggestion[]>>(`/tailor/suggestions/${resumeId}/${positionId}`),

  acceptSuggestion: (resumeId: string, suggestionId: string) =>
    api.post<ApiResponse<null>>(`/tailor/accept`, { resumeId, suggestionId }),

  applyAll: (resumeId: string, suggestionIds: string[]) =>
    api.post<ApiResponse<{ newResumeId: string }>>(`/tailor/apply-all`, { resumeId, suggestionIds }),

  optimizePhrase: (text: string, style: 'professional' | 'concise' | 'match' | 'impact') =>
    api.post<ApiResponse<{ suggestions: string[] }>>('/tailor/optimize-phrase', { text, style }),

  saveAsNew: (resumeId: string, suggestionIds: string[]) =>
    api.post<ApiResponse<{ newResumeId: string }>>('/tailor/save-as-new', { resumeId, suggestionIds }),
}
