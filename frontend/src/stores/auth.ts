import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '../api/http'
import type { User, UserRole } from '../types'

const TOKEN_KEY = 'student-care-token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) ?? '')
  const user = ref<User | null>(null)
  const loading = ref(false)

  const isAuthenticated = computed(() => Boolean(token.value))
  const role = computed(() => user.value?.role ?? null)

  async function login(username: string, password: string): Promise<void> {
    loading.value = true
    try {
      const response = await api.post('/auth/login', { username, password })
      token.value = response.data.access_token
      user.value = response.data.user
      localStorage.setItem(TOKEN_KEY, token.value)
    } finally {
      loading.value = false
    }
  }

  async function fetchMe(): Promise<User | null> {
    if (!token.value) return null
    const response = await api.get<User>('/auth/me')
    user.value = response.data
    return user.value
  }

  function logout(): void {
    token.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
  }

  function hasRole(...roles: UserRole[]): boolean {
    return user.value !== null && roles.includes(user.value.role)
  }

  return {
    token,
    user,
    loading,
    isAuthenticated,
    role,
    login,
    fetchMe,
    logout,
    hasRole,
  }
})
