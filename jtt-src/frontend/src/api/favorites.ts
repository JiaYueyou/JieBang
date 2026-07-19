import api from './index'
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
}
