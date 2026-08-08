import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import type { LearningPath, LearningStep } from '@/types'
import { learningApi } from '@/api/learning'
import { pathFromApi } from '@/utils/transform'

const STORAGE_KEY = 'jiebang_learning_paths'

function loadSavedPaths(): LearningPath[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch { return [] }
}

function savePaths(paths: LearningPath[]) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(paths)) } catch {}
}

export const useLearningStore = defineStore('learning', () => {
  const paths = ref<LearningPath[]>(loadSavedPaths())
  const loading = ref(false)

  // Persist to localStorage on every change
  watch(paths, (val) => savePaths(val), { deep: true })

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

  // 手动点击只允许"取消完成"；标记完成必须通过测验（≥80%）
  const toggleStep = (pathId: string, stepId: string) => {
    const path = paths.value.find((p) => p.id === pathId)
    if (path) {
      const step = path.steps.find((s: LearningStep) => s.id === stepId)
      if (step && step.completed) step.completed = false
    }
  }

  // 测验达到 80% 后标记完成
  const completeStep = (pathId: string, stepId: string) => {
    const path = paths.value.find((p) => p.id === pathId)
    if (path) {
      const step = path.steps.find((s: LearningStep) => s.id === stepId)
      if (step) step.completed = true
    }
  }

  const getCompletionPercent = (pathId: string): number => {
    const path = paths.value.find((p) => p.id === pathId)
    if (!path || path.steps.length === 0) return 0
    const done = path.steps.filter((s: LearningStep) => s.completed).length
    return Math.round((done / path.steps.length) * 100)
  }

  const generateFromGaps = async (positionName: string, missingSkills: string[], matchedSkills: string[], resumeId: string) => {
    loading.value = true
    try {
      const res: any = await learningApi.generatePath({
        position_name: positionName,
        missing_skills: missingSkills,
        matched_skills: matchedSkills,
        resume_id: Number(resumeId),
      })
      if (res.data) paths.value.push(pathFromApi(res.data))
      return res.data
    } finally {
      loading.value = false
    }
  }

  return { paths, loading, fetchPaths, addPath, removePath, renamePath, toggleStep, completeStep, getCompletionPercent, generateFromGaps }
})
