import api from './index'
import type { ApiResponse, UserProfile } from '@/types'

export const authApi = {
  login: (data: { username: string; password: string }) =>
    api.post<ApiResponse<{ token: string; user: UserProfile }>>('/auth/login', data),

  register: (data: { username: string; email: string; password: string }) =>
    api.post<ApiResponse<{ token: string; user: UserProfile }>>('/auth/register', data),

  logout: () => api.post<ApiResponse<null>>('/auth/logout'),

  getProfile: () => api.get<ApiResponse<UserProfile>>('/auth/profile'),

  updateProfile: (data: Partial<UserProfile>) =>
    api.put<ApiResponse<UserProfile>>('/auth/profile', data),

  changePassword: (data: { oldPassword: string; newPassword: string }) =>
    api.put<ApiResponse<null>>('/auth/password', data),
}
