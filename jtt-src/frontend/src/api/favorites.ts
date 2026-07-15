import api from './index'
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
}
