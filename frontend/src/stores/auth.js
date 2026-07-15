import { defineStore } from 'pinia'
import { authApi } from '@/api/auth'

// 认证状态：token 与用户名持久化到 localStorage
export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('access_token') || '',
    username: localStorage.getItem('username') || '',
  }),
  getters: {
    isAuthenticated: (state) => !!state.token,
  },
  actions: {
    setSession(token, username) {
      this.token = token
      this.username = username
      localStorage.setItem('access_token', token)
      localStorage.setItem('username', username)
    },
    async login(payload) {
      const data = await authApi.login(payload)
      this.setSession(data.access_token, data.username)
      return data
    },
    logout() {
      this.token = ''
      this.username = ''
      localStorage.removeItem('access_token')
      localStorage.removeItem('username')
    },
  },
})
