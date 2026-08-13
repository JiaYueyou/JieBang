/**
 * AI 助手 API —— 全局浮窗 AI 聊天 + 短语润色。
 */
import api from './index'
import type { AssistantChatRequest, AssistantChatResponse } from '@/types'

export interface OptimizePhraseRequest {
  text: string
  style: 'professional' | 'concise' | 'match' | 'impact'
}

export interface OptimizePhraseResponse {
  suggestions: string[]
}

export interface LearningPathStep {
  title: string
  description: string
  duration: string
  resources: { title: string; type: string; platform: string }[]
}

export interface GeneratePathResponse {
  pathName: string
  positionName: string
  steps: LearningPathStep[]
  totalDuration: string
  sourceNote: string
  searchResultsCount: number
}

export const assistantApi = {
  chat: (data: AssistantChatRequest): Promise<{ code: number; message: string; data: AssistantChatResponse }> =>
    api.post('/assistant/chat', data),

  optimizePhrase: (data: OptimizePhraseRequest): Promise<{ code: number; message: string; data: OptimizePhraseResponse }> =>
    api.post('/assistant/optimize-phrase', data, { timeout: 90000 }),

  generateLearningPath: (positionName: string): Promise<{ code: number; message: string; data: GeneratePathResponse }> =>
    api.post('/assistant/generate-learning-path', { positionName }, { timeout: 90000 }),

  generatePathFromGoal: (goal: string): Promise<{ code: number; message: string; data: GeneratePathResponse }> =>
    api.post('/assistant/generate-learning-path-from-goal', { goal }, { timeout: 90000 }),

  optimizeResume: (resume: any, position: any): Promise<{ code: number; message: string; data: { suggestions: any[] } }> =>
    api.post('/assistant/optimize-resume', { resume, position }, { timeout: 90000 }),
}
