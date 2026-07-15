import api from './index'
import type { ApiResponse, ResumeData, PaginatedData } from '@/types'

export const resumeApi = {
  upload: (formData: FormData) =>
    api.post<ApiResponse<ResumeData>>('/resume/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 30000,
    }),

  getList: () => api.get<ApiResponse<ResumeData[]>>('/resumes'),

  getDetail: (id: string) => api.get<ApiResponse<ResumeData>>(`/resume/${id}`),

  create: (data: Partial<ResumeData>) => api.post<ApiResponse<ResumeData>>('/resume', data),

  update: (id: string, data: Partial<ResumeData>) => api.put<ApiResponse<ResumeData>>(`/resume/${id}`, data),

  delete: (id: string) => api.delete<ApiResponse<null>>(`/resume/${id}`),

  duplicate: (id: string) => api.post<ApiResponse<ResumeData>>(`/resume/${id}/duplicate`),
}
