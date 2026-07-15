import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { MatchResult } from '@/types'
import { matchApi } from '@/api/match'

export const useMatchStore = defineStore('match', () => {
  const currentResult = ref<MatchResult | null>(null)
  const history = ref<MatchResult[]>([])
  const loading = ref(false)

  const doMatch = async (resumeId: string, positionId: string) => {
    loading.value = true
    try {
      const res: any = await matchApi.match(resumeId, positionId)
      currentResult.value = res.data
      return res.data
    } finally {
      loading.value = false
    }
  }

  const getResult = async (resumeId: string, positionId: string) => {
    loading.value = true
    try {
      const res: any = await matchApi.getResult(resumeId, positionId)
      currentResult.value = res.data
    } finally {
      loading.value = false
    }
  }

  const fetchHistory = async () => {
    const res: any = await matchApi.getHistory()
    history.value = res.data
  }

  const autoDetect = async (resumeId: string) => {
    loading.value = true
    try {
      const res: any = await matchApi.autoDetect(resumeId)
      return res.data as MatchResult[]
    } finally {
      loading.value = false
    }
  }

  return { currentResult, history, loading, doMatch, getResult, fetchHistory, autoDetect }
})
