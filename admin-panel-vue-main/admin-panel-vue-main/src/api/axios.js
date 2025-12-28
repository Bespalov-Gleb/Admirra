import axios from 'axios'

const API_URL = 'http://localhost:8001/api/'

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
      // Clear token immediately to prevent further authorized requests
      localStorage.removeItem('auth_token')
      
      // Only redirect if we are not already going to or on the login page
      const currentPath = window.location.pathname
      const isLoginPage = currentPath === '/login' || currentPath === '/'
      if (!isLoginPage) {
        console.warn(`Unauthenticated request (401) from path: ${currentPath}. Redirecting to login...`)
        window.location.href = '/login'
      } else {
        console.log(`Unauthenticated request (401) on login page, staying here.`)
      }
    }
    return Promise.reject(error)
  }
)

export default api
