import axios from 'axios'

const API_URL = '/api/'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Добавляем токен авторизации к каждому запросу
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Обработка ошибок (например, окончание сессии)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Diagnostic log
      const currentPath = window.location.pathname
      console.warn(`Axios: Unauthenticated request (401) from path: ${currentPath}`)

      // Check if we are on an auth page (Login or Root)
      // Normalize path (remove trailing slash)
      const normalizedPath = currentPath.replace(/\/$/, '') || '/'
      const isAuthPage = normalizedPath === '/login' || normalizedPath === '/'

      if (!isAuthPage) {
        console.warn('Axios: Unauthorized access to protected route, clearing session and redirecting...')
        localStorage.removeItem('auth_token')
        window.location.href = '/login'
      } else {
        console.log('Axios: 401 encountered on auth page, staying here.')
      }
    }
    return Promise.reject(error)
  }
)

export default api
