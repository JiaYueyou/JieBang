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

  // AI 生成路径的序号：扫描已有路径名里的「学习路径X：」，取当前存在的最大编号 +1 顺延
  const nextPathSeq = () => {
    const cnMap: Record<string, number> = { '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10 }
    let max = 0
    for (const p of paths.value) {
      const m = (p.name || '').match(/学习路径([一二三四五六七八九十]|\d+)[：:]/)
      if (m && m[1]) {
        const n = cnMap[m[1]] ?? parseInt(m[1], 10)
        if (!isNaN(n) && n > max) max = n
      }
    }
    return max + 1
  }

  // 新建路径：与左侧 AI 聊天框「生成学习路径」一致 —— 调同一 LLM 接口、同一命名、同一加入列表方式
  const addPath = async (goal: string) => {
    const aiRes: any = await assistantApi.generateLearningPath(goal)
    const data = aiRes.data
    if (!data || !data.steps || data.steps.length === 0) {
      throw new Error('未生成有效路径')
    }
    const cnNum = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
    const nextSeq = nextPathSeq()
    const seqLabel = nextSeq <= 10 ? cnNum[nextSeq - 1] : String(nextSeq)
    const newPath: any = {
      id: 'lp-gen-' + Date.now(),
      name: '学习路径' + seqLabel + '：' + (data.positionName || data.pathName || goal.slice(0, 20)),
      positionId: '',
      positionName: data.positionName || '',
      steps: data.steps.map((s: any, idx: number) => ({
        id: 'step-gen-' + idx + '-' + Date.now(),
        order: idx + 1,
        title: s.title,
        description: s.description,
        duration: s.duration,
        resources: (s.resources || []).map((r: any, ri: number) => ({
          id: 'res-gen-' + idx + '-' + ri,
          title: r.title,
          type: r.type || 'course',
          url: r.url || '',
          platform: r.platform || '',
        })),
        completed: false,
      })),
      totalDuration: data.totalDuration || '',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    paths.value.unshift(newPath)
    return newPath
  }

  const removePath = async (id: string) => {
    // 本地生成的路径（lp-gen-/mock 前缀）直接本地删，不调后端
    const isLocal = !/^\d+$/.test(id)
    if (!isLocal) {
      try {
        await learningApi.delete(id)
      } catch {
        // 后端删除失败也继续本地删（避免删不掉）
      }
    }
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

  return { paths, loading, fetchPaths, nextPathSeq, addPath, removePath, renamePath, toggleStep, completeStep, getCompletionPercent, generateFromGaps }
})
