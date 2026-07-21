import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ResumeData } from '@/types'
import { resumeApi } from '@/api/resume'
import { resumeFromApi, resumeToApi } from '@/utils/transform'

export const useResumeStore = defineStore('resume', () => {
  const resumes = ref<ResumeData[]>([])
  const currentResume = ref<ResumeData | null>(null)
  const loading = ref(false)

  const fetchList = async () => {
    loading.value = true
    try {
      const res: any = await resumeApi.getList()
      resumes.value = (res.data || []).map(resumeFromApi)
    } finally {
      loading.value = false
    }
  }

  const fetchDetail = async (id: string) => {
    loading.value = true
    try {
      const res: any = await resumeApi.getDetail(id)
      currentResume.value = resumeFromApi(res.data)
    } finally {
      loading.value = false
    }
  }

  const create = async (data: Partial<ResumeData>) => {
    const res: any = await resumeApi.create(resumeToApi(data))
    const created = resumeFromApi(res.data)
    resumes.value.unshift(created)
    return created
  }

  const update = async (id: string, data: Partial<ResumeData>) => {
    const res: any = await resumeApi.update(id, resumeToApi(data))
    const updated = resumeFromApi(res.data)
    const idx = resumes.value.findIndex((r) => r.id === id)
    if (idx > -1) resumes.value[idx] = updated
    if (currentResume.value?.id === id) currentResume.value = updated
    return updated
  }

  const remove = async (id: string) => {
    await resumeApi.delete(id)
    resumes.value = resumes.value.filter((r) => r.id !== id)
    if (currentResume.value?.id === id) currentResume.value = null
  }

  const duplicate = async (id: string) => {
    const res: any = await resumeApi.duplicate(id)
    const duped = resumeFromApi(res.data)
    resumes.value.unshift(duped)
    return duped
  }

  const upload = async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const res: any = await resumeApi.upload(formData)
    const uploaded = resumeFromApi(res.data)
    resumes.value.unshift(uploaded)
    return uploaded
  }

  return { resumes, currentResume, loading, fetchList, fetchDetail, create, update, remove, duplicate, upload }
})
