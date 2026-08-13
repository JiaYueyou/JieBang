import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import type { LearningPath, LearningStep } from '@/types'
import { learningApi } from '@/api/learning'
import { assistantApi } from '@/api/assistant'
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

  const addPath = async (goal: string) => {
    // 1. 调用 AI Assistant 根据自然语言目标生成个性化学习路径
    const aiRes: any = await assistantApi.generatePathFromGoal(goal)
    const aiData = aiRes.data
    const aiSteps = (aiData?.steps || []).map((s: any, i: number) => ({
      id: `s-${Date.now()}-${i}`,
      order: i + 1,
      title: s.title || '',
      description: s.description || '',
      duration: s.duration || '',
      resources: (s.resources || []).map((r: any) => ({
        id: r.title || `r-${i}`,
        title: r.title || '',
        type: r.type || 'article',
        url: r.url || '',
        platform: r.platform || '',
      })),
      completed: false,
    }))

    // 2. 持久化到后端 MySQL
    const res: any = await learningApi.create({
      name: aiData?.pathName || goal.slice(0, 20),
      positionId: 1,
      positionName: aiData?.goalAnalysis || goal,
      steps: aiSteps,
    })
    if (res.data) paths.value.push(pathFromApi(res.data))
    return res.data
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

  return { paths, loading, fetchPaths, addPath, removePath, renamePath, toggleStep, getCompletionPercent, generateFromGaps }
})
