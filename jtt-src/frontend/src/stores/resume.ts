import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ResumeData } from '@/types'
import { resumeApi } from '@/api/resume'

export const useResumeStore = defineStore('resume', () => {
  const resumes = ref<ResumeData[]>([])
  const currentResume = ref<ResumeData | null>(null)
  const loading = ref(false)

  const fetchList = async () => {
    loading.value = true
    try {
      const res: any = await resumeApi.getList()
      resumes.value = res.data
    } finally {
      loading.value = false
    }
  }

  const fetchDetail = async (id: string) => {
    loading.value = true
    try {
      const res: any = await resumeApi.getDetail(id)
      currentResume.value = res.data
    } finally {
      loading.value = false
    }
  }

  const create = async (data: Partial<ResumeData>) => {
    const res: any = await resumeApi.create(data)
    resumes.value.unshift(res.data)
    return res.data
  }

  const update = async (id: string, data: Partial<ResumeData>) => {
    const res: any = await resumeApi.update(id, data)
    const idx = resumes.value.findIndex((r) => r.id === id)
    if (idx > -1) resumes.value[idx] = res.data
    if (currentResume.value?.id === id) currentResume.value = res.data
    return res.data
  }

  const remove = async (id: string) => {
    await resumeApi.delete(id)
    resumes.value = resumes.value.filter((r) => r.id !== id)
    if (currentResume.value?.id === id) currentResume.value = null
  }

  const duplicate = async (id: string) => {
    const res: any = await resumeApi.duplicate(id)
    resumes.value.unshift(res.data)
    return res.data
  }

  return { resumes, currentResume, loading, fetchList, fetchDetail, create, update, remove, duplicate }
})
