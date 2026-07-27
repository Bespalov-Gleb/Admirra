import { defineStore } from 'pinia'
import api, { ADMIN_TOKEN_KEY } from '../api/client'

export const useAuthStore = defineStore('admin-auth', {
  state: () => ({
    token: localStorage.getItem(ADMIN_TOKEN_KEY),
    user: null,
    loading: false,
    initialized: false,
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token && state.user),
    role: (state) => state.user?.role || null,
    isSuperadmin: (state) => ['SUPERADMIN', 'ADMIN'].includes(state.user?.role),
    isManager: (state) => ['STAFF_MANAGER', 'SUPPORT'].includes(state.user?.role),
    isSeo: (state) => state.user?.role === 'SEO',
    homeRoute() {
      if (this.isManager) return '/manager'
      if (this.isSeo) return '/seo/blog'
      return '/dashboard'
    },
  },
  actions: {
    setToken(token) {
      this.token = token
      if (token) localStorage.setItem(ADMIN_TOKEN_KEY, token)
      else localStorage.removeItem(ADMIN_TOKEN_KEY)
    },
    async login(payload) {
      const { data } = await api.post('/admin/auth/login', payload)
      if (data.access_token) this.setToken(data.access_token)
      return data
    },
    async fetchMe() {
      if (!this.token) {
        this.initialized = true
        return null
      }
      this.loading = true
      try {
        const { data } = await api.get('/admin/auth/me')
        this.user = data
        return data
      } catch {
        this.setToken(null)
        this.user = null
        return null
      } finally {
        this.loading = false
        this.initialized = true
      }
    },
    async logout() {
      try {
        if (this.token) await api.post('/admin/auth/logout')
      } finally {
        this.setToken(null)
        this.user = null
      }
    },
  },
})
