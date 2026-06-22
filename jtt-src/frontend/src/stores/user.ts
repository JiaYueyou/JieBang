import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserProfile } from '@/types'
import { authApi } from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  const user = ref<UserProfile | null>(null)
  const token = ref<string>(localStorage.getItem('token') || '')
  const isLoggedIn = computed(() => !!token.value)

  const fetchProfile = async () => {
    const res: any = await authApi.getProfile()
    user.value = res.data
  }

  const updateProfile = async (data: Partial<UserProfile>) => {
    const res: any = await authApi.updateProfile(data)
    user.value = res.data
  }

  const changePassword = async (data: { oldPassword: string; newPassword: string }) => {
    await authApi.changePassword(data)
  }

  const login = async (username: string, password: string) => {
    const res: any = await authApi.login({ username, password })
    token.value = res.data.token
    localStorage.setItem('token', res.data.token)
    await fetchProfile()
  }

  const register = async (username: string, email: string, password: string) => {
    const res: any = await authApi.register({ username, email, password })
    token.value = res.data.token
    localStorage.setItem('token', res.data.token)
    await fetchProfile()
  }

  const logout = () => {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  return { user, token, isLoggedIn, fetchProfile, updateProfile, changePassword, login, register, logout }
})
