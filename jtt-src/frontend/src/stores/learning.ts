import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { LearningPath, LearningStep } from '@/types'
import { learningApi } from '@/api/learning'
import { pathFromApi } from '@/utils/transform'

export const useLearningStore = defineStore('learning', () => {
  const paths = ref<LearningPath[]>([])
  const loading = ref(false)

  const fetchPaths = async () => {
    loading.value = true
    try {
      const res: any = await learningApi.getList()
      if (res.data) paths.value = (res.data || []).map(pathFromApi)
    } finally {
      loading.value = false
    }
  }

  const addPath = async (path: LearningPath) => {
    const res: any = await learningApi.create({ name: path.name, positionId: parseInt(path.positionId) || 1 })
    if (res.data) paths.value.push(pathFromApi(res.data))
  }

  const removePath = async (id: string) => {
    await learningApi.delete(id)
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
