import api from './index'
<<<<<<< HEAD
import type { ApiResponse } from '@/types'

// 收藏项的完整数据结构
export interface FavoriteItem {
  id: number
  item_type: string
  item_id: string
  title: string
  summary: string | null
  metadata: Record<string, any> | null
  tags: string[] | null
  created_at: string | null
}

// 创建收藏的请求体
export interface FavoriteCreate {
  item_type: string
  item_id: string
  title: string
  summary?: string
  metadata?: Record<string, any>
  tags?: string[]
}

export const favoritesApi = {
  getList: (type?: string) =>
    api.get<ApiResponse<FavoriteItem[]>>('/favorites', { params: type ? { type } : {} }),

  add: (data: FavoriteCreate) =>
    api.post<ApiResponse<FavoriteItem>>('/favorites', data),

  remove: (favId: number) =>
    api.delete<ApiResponse<null>>(`/favorites/${favId}`),

  check: (itemType: string, itemId: string) =>
    api.get<ApiResponse<boolean>>('/favorites/check', { params: { item_type: itemType, item_id: itemId } }),
=======
import type { ApiResponse, Note } from '@/types'

export const favoritesApi = {
  // 岗位收藏
  togglePosition: (positionId: string) =>
    api.post<ApiResponse<null>>('/favorites/position', { positionId }),

  // 学习路径收藏
  getLearningPaths: () => api.get<ApiResponse<string[]>>('/favorites/learning-paths'),
  toggleLearningPath: (pathId: string) =>
    api.post<ApiResponse<null>>('/favorites/learning-path', { pathId }),

  // 笔记 CRUD
  getNotes: () => api.get<ApiResponse<Note[]>>('/favorites/notes'),
  createNote: (data: Partial<Note>) => api.post<ApiResponse<Note>>('/favorites/notes', data),
  updateNote: (id: string, data: Partial<Note>) =>
    api.put<ApiResponse<Note>>(`/favorites/notes/${id}`, data),
  deleteNote: (id: string) => api.delete<ApiResponse<null>>(`/favorites/notes/${id}`),
>>>>>>> aa08688 (feat(fyz-backend): add job filtering)
}
