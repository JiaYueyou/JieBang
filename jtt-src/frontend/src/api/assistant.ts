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

export interface GeneratedResource {
  title: string
  type: string
  url: string
  platform: string
}

export interface GenerateLinksResponse {
  resources: GeneratedResource[]
}

export interface AgentChatResponse {
  reply: string
  thinkingSteps: { icon: string; text: string }[]
  toolsCalled: string[]
  followUpQuestions: string[]
}

export const assistantApi = {
  chat: (data: AssistantChatRequest): Promise<{ code: number; message: string; data: AssistantChatResponse }> =>
    api.post('/assistant/chat', data),

  // [P1] Agent 循环：LLM 自主调工具（图谱/搜索/差距分析）→ 综合
  agentChat: (data: AssistantChatRequest): Promise<{ code: number; message: string; data: AgentChatResponse }> =>
    api.post('/assistant/agent-chat', data, { timeout: 120000 }),

  optimizePhrase: (data: OptimizePhraseRequest): Promise<{ code: number; message: string; data: OptimizePhraseResponse }> =>
    api.post('/assistant/optimize-phrase', data),

  generateLearningPath: (positionName: string): Promise<{ code: number; message: string; data: GeneratePathResponse }> =>
    api.post('/assistant/generate-learning-path', { positionName }, { timeout: 90000 }),

  generateLinks: (topic: string): Promise<{ code: number; message: string; data: GenerateLinksResponse }> =>
    api.post('/assistant/generate-links', { message: topic }, { timeout: 90000 }),
}
