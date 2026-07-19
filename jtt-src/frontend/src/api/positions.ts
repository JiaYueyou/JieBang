import api from './index'
import type { ApiResponse, JobPosition, PaginatedData } from '@/types'

export const positionsApi = {
  getList: (params: { category?: string; keyword?: string; techStack?: string; page?: number; pageSize?: number }) =>
    api.get<ApiResponse<PaginatedData<JobPosition>>>('/positions', {
      params: {
        category: params.category,
        keyword: params.keyword,
        tech_stack: params.techStack,
        page: params.page,
        page_size: params.pageSize,
      },
    }),

  getDetail: (id: string) => api.get<ApiResponse<JobPosition>>(`/positions/${id}`),

  getKnowledgeGraph: (params?: { techStack?: string; level?: string }) =>
    api.get<ApiResponse<{ nodes: any[]; edges: any[] }>>('/positions/graph', {
      params: { root_tech: params?.techStack },
    }),
}
