import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { MatchResult, ImprovementSuggestion } from '@/types'
import { matchApi } from '@/api/match'
import { tailorApi } from '@/api/tailor'
import { matchResultFromApi, suggestionFromApi } from '@/utils/transform'

export const useMatchStore = defineStore('match', () => {
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

  const fetchAiSuggestions = async (resumeId: string, positionId: string) => {
    suggestionsLoading.value = true
    try {
      const res: any = await tailorApi.getSuggestions(resumeId, positionId)
      aiSuggestions.value = (res.data || []).map(suggestionFromApi)
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

  const doAutoMatch = async (resumeId: string) => {
    batchLoading.value = true
    try {
      const res: any = await matchApi.autoMatch(resumeId)
      batchResults.value = (res.data || []).map(matchResultFromApi)
        .sort((a: MatchResult, b: MatchResult) => b.totalScore - a.totalScore)
      // 自动展开第一名
      if (batchResults.value.length > 0 && !selectedBatchResult.value) {
        const first = batchResults.value[0]!
        selectedBatchResult.value = first
        fetchAiSuggestions(resumeId, first.positionId)
      }
      return batchResults.value
    } finally {
      batchLoading.value = false
    }
  }

  const selectBatchResult = (result: MatchResult) => {
    selectedBatchResult.value = result
    fetchAiSuggestions(result.resumeId, result.positionId)
  }

  return {
    currentResult, history, loading,
    doMatch, getResult, fetchHistory,
    aiSuggestions, suggestionsLoading, optimizing, optimizeResult,
    fetchAiSuggestions, applyOptimization, toggleAiSuggestion,
    // 自动匹配
    batchResults, batchLoading, selectedBatchResult,
    doAutoMatch, selectBatchResult,
  }
})
