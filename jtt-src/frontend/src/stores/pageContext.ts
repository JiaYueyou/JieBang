/**
 * 页面数据共享状态
 * 各页面将当前展示的关键数据注入此处，供 AI 助手读取。
 */
import { reactive } from 'vue'
import type { ResumeData, MatchResult } from '@/types'

export const pageData = reactive<{
  resume: ResumeData | null
  match: MatchResult | null
}>({
  resume: null,
  match: null,
})
