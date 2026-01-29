import axios from 'axios'

const API_URL = '/api/'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json'
  },
  paramsSerializer: {
    serialize: (params) => {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (Array.isArray(value)) {
          value.forEach((v) => searchParams.append(key, v));
        } else if (value !== undefined && value !== null) {
          searchParams.append(key, value);
        }
      });
      const result = searchParams.toString();
      if (result.includes('campaign_ids')) {
        console.log('[Axios] Serialized params with campaign_ids:', result);
      }
      return result;
    }
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
      const currentPath = window.location.pathname
      // Normalize path (remove trailing slash)
      const normalizedPath = currentPath.replace(/\/$/, '') || '/'
      const isAuthPage = normalizedPath === '/login' || normalizedPath === '/' || normalizedPath === '/signup' || normalizedPath === '/signin'

      // На страницах авторизации 401 - это нормально, не логируем как ошибку
      if (isAuthPage) {
        // Тихий отказ, не логируем
        return Promise.reject(error)
      }

      // На защищенных страницах - это ошибка авторизации
      console.warn(`Axios: Unauthenticated request (401) from path: ${currentPath}`)
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api
