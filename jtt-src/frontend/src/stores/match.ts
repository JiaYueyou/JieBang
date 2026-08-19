import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { MatchResult, ImprovementSuggestion } from '@/types'
import { matchApi } from '@/api/match'
import { tailorApi } from '@/api/tailor'
import { assistantApi } from '@/api/assistant'
import { useResumeStore } from '@/stores/resume'
import { matchResultFromApi, suggestionFromApi } from '@/utils/transform'

export const useMatchStore = defineStore('match', () => {
  const resumeStore = useResumeStore()
  const currentResult = ref<MatchResult | null>(null)
  const history = ref<MatchResult[]>([])
  const loading = ref(false)

  const doMatch = async (resumeId: string, positionId: string) => {
    loading.value = true
    try {
      const res: any = await matchApi.match(resumeId, positionId)
      currentResult.value = matchResultFromApi(res.data)
      return currentResult.value
    } finally {
      loading.value = false
    }
  }

  const getResult = async (resumeId: string, positionId: string) => {
    loading.value = true
    try {
      const res: any = await matchApi.getResult(resumeId, positionId)
      currentResult.value = matchResultFromApi(res.data)
    } finally {
      loading.value = false
    }
  }

  const fetchHistory = async () => {
    const res: any = await matchApi.getHistory()
    history.value = (res.data || []).map(matchResultFromApi)
  }


  // === AI 优化建议（Agent 1: 简历优化智能体）===

  const aiSuggestions = ref<ImprovementSuggestion[]>([])
  const suggestionsLoading = ref(false)
  const optimizing = ref(false)
  const optimizeResult = ref<{ newResumeId: number } | null>(null)

  // 从 MatchResult 构造岗位上下文，供 AI 优化建议使用
  const toPositionCtx = (r: MatchResult) => ({
    name: r.positionName,
    missingSkills: r.gapAnalysis.missingSkills.map((s: any) => s.name),
    weakSkills: r.gapAnalysis.weakSkills.map((s: any) => s.name),
    matchSkills: r.gapAnalysis.matchSkills.map((s: any) => s.name),
  })

  const fetchAiSuggestions = async (resumeId: string, positionCtx: any) => {
    suggestionsLoading.value = true
    try {
      await resumeStore.fetchDetail(resumeId)
      const resume = resumeStore.currentResume
      if (!resume) throw new Error('未找到待优化的简历')
      const res: any = await assistantApi.optimizeResume(resume, positionCtx)
      aiSuggestions.value = (res.data?.suggestions || []).map(suggestionFromApi)
      return aiSuggestions.value
    } finally {
      suggestionsLoading.value = false
    }
  }

  const applyOptimization = async (resumeId: string) => {
    optimizing.value = true
    try {
      // 优先应用已接受的建议；一条都没选时默认应用全部
      const accepted = aiSuggestions.value.filter(s => s.accepted)
      const chosen = accepted.length > 0 ? accepted : aiSuggestions.value
      const res: any = await tailorApi.applyAll(resumeId, chosen)
      optimizeResult.value = { newResumeId: res.data.new_resume_id || res.data.newResumeId }
      return optimizeResult.value
    } finally {
      optimizing.value = false
    }
  }

  const toggleAiSuggestion = (suggestionId: string) => {
    const sg = aiSuggestions.value.find(s => s.id === suggestionId)
    if (sg) sg.accepted = !sg.accepted
  }

  // === 自动匹配（Agent 3）：简历 vs 所有岗位 ===

  const batchResults = ref<MatchResult[]>([])
  const batchLoading = ref(false)
  const selectedBatchResult = ref<MatchResult | null>(null)

  const batchStats = ref<{
    totalMatched: number; educationFiltered: number; scoreFiltered: number; dataSource: string
  } | null>(null)

  const doAutoMatch = async (resumeId: string) => {
    batchLoading.value = true
    try {
      const res: any = await matchApi.autoMatch(resumeId)
      const data = res.data || {}
      // 新版 API 返回 { results, total_matched, education_filtered, score_filtered, data_source }
      batchResults.value = (data.results || data || []).map(matchResultFromApi)
        .sort((a: MatchResult, b: MatchResult) => b.totalScore - a.totalScore)
      batchStats.value = {
        totalMatched: data.total_matched ?? batchResults.value.length,
        educationFiltered: data.education_filtered ?? 0,
        scoreFiltered: data.score_filtered ?? 0,
        dataSource: data.data_source ?? '',
      }
      // 自动展开第一名
      if (batchResults.value.length > 0 && !selectedBatchResult.value) {
        const first = batchResults.value[0]!
        selectedBatchResult.value = first
        fetchAiSuggestions(resumeId, toPositionCtx(first))
      }
      return batchResults.value
    } finally {
      batchLoading.value = false
    }
  }

  const selectBatchResult = (result: MatchResult) => {
    selectedBatchResult.value = result
    fetchAiSuggestions(result.resumeId, toPositionCtx(result))
  }

  return {
    currentResult, history, loading,
    doMatch, getResult, fetchHistory,
    aiSuggestions, suggestionsLoading, optimizing, optimizeResult,
    fetchAiSuggestions, applyOptimization, toggleAiSuggestion,
    // 自动匹配
    batchResults, batchStats, batchLoading, selectedBatchResult,
    doAutoMatch, selectBatchResult,
  }
})
