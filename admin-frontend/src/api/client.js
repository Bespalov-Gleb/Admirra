import axios from 'axios'

export const ADMIN_TOKEN_KEY = 'admirra_internal_admin_token'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(ADMIN_TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const isLogin = error.config?.url?.includes('/admin/auth/login')
    if (status === 401 && !isLogin) {
      localStorage.removeItem(ADMIN_TOKEN_KEY)
      if (window.location.pathname !== '/login') {
        window.location.assign(`/login?next=${encodeURIComponent(window.location.pathname)}`)
      }
    }
    return Promise.reject(error)
  },
)

export function apiError(error, fallback = 'Не удалось выполнить запрос') {
  const detail = error?.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join(', ')
  if (typeof detail === 'string') {
    const map = {
      'Invalid credentials': 'Неверный логин или пароль',
      'Account blocked': 'Аккаунт заблокирован',
      'Staff account unavailable': 'Аккаунт сотрудника недоступен',
      'Invalid 2FA code': 'Неверный код подтверждения',
      'Invalid MFA session': 'Сессия подтверждения истекла. Войдите заново',
      'Staff invite not accepted yet': 'Приглашение сотрудника ещё не принято',
      'Internal admin is disabled': 'Внутренняя панель отключена',
    }
    return map[detail] || detail
  }
  return error?.message || fallback
}

export default api
