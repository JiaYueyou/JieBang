import api from './index'
import type { ApiResponse, JobPosition, PaginatedData, Neo4jGraphSubgraph } from '@/types'

export const positionsApi = {
  getList: (params: { category?: string; keyword?: string; page?: number; pageSize?: number }) =>
    api.get<ApiResponse<PaginatedData<JobPosition>>>('/positions', {
      params: {
        category: params.category,
        keyword: params.keyword,
        page: params.page,
        page_size: params.pageSize,
      },
    }),

  getDetail: (id: string) => api.get<ApiResponse<JobPosition>>(`/positions/${id}`),

  getKnowledgeGraph: (params?: { techStack?: string }) =>
    api.get<ApiResponse<Neo4jGraphSubgraph>>('/positions/graph', {
      params: { root_tech: params?.techStack },
    }),
}
