import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AdminProfile } from '@/api/admin'

const TOKEN_KEY = 'token'
const PROFILE_KEY = 'profile'

export const useUserStore = defineStore('user', () => {
  const token = ref(uni.getStorageSync(TOKEN_KEY) || '')
  const profile = ref<AdminProfile | null>(
    (() => {
      try {
        const raw = uni.getStorageSync(PROFILE_KEY)
        return raw ? (JSON.parse(raw) as AdminProfile) : null
      } catch {
        return null
      }
    })(),
  )

  const isLoggedIn = computed(() => !!token.value)
  const displayName = computed(() => profile.value?.nickname || profile.value?.username || '管理员')
  const roleLabel = computed(() => profile.value?.role || '管理员')

  function setAuth(newToken: string, newProfile: AdminProfile) {
    token.value = newToken
    profile.value = newProfile
    uni.setStorageSync(TOKEN_KEY, newToken)
    uni.setStorageSync(PROFILE_KEY, JSON.stringify(newProfile))
  }

  function setProfile(newProfile: AdminProfile) {
    profile.value = newProfile
    uni.setStorageSync(PROFILE_KEY, JSON.stringify(newProfile))
  }

  function clear() {
    token.value = ''
    profile.value = null
    uni.removeStorageSync(TOKEN_KEY)
    uni.removeStorageSync(PROFILE_KEY)
  }

  return { token, profile, isLoggedIn, displayName, roleLabel, setAuth, setProfile, clear }
})
