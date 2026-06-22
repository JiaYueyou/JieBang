import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { LearningPath, LearningStep } from '@/types'

export const useLearningStore = defineStore('learning', () => {
  const paths = ref<LearningPath[]>([])
  const loading = ref(false)

  const fetchPaths = async () => {
    // Will be replaced by real API call; mock returns data directly
    loading.value = true
    try {
      // const res = await learningApi.getList()
      // paths.value = res.data
    } finally {
      loading.value = false
    }
  }

  const addPath = (path: LearningPath) => {
    paths.value.push(path)
  }

  const removePath = (id: string) => {
    paths.value = paths.value.filter((p) => p.id !== id)
  }

  const renamePath = (id: string, name: string) => {
    const path = paths.value.find((p) => p.id === id)
    if (path) path.name = name
  }

  const toggleStep = (pathId: string, stepId: string) => {
    const path = paths.value.find((p) => p.id === pathId)
    if (path) {
      const step = path.steps.find((s: LearningStep) => s.id === stepId)
      if (step) step.completed = !step.completed
    }
  }

  const getCompletionPercent = (pathId: string): number => {
    const path = paths.value.find((p) => p.id === pathId)
    if (!path || path.steps.length === 0) return 0
    const done = path.steps.filter((s: LearningStep) => s.completed).length
    return Math.round((done / path.steps.length) * 100)
  }

  return { paths, loading, fetchPaths, addPath, removePath, renamePath, toggleStep, getCompletionPercent }
})
