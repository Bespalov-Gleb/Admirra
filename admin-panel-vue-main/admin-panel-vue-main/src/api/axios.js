import axios from 'axios'
import { clearAccessToken, getAccessToken, setAccessToken } from '@/utils/authToken'

const API_URL = '/api/'
let refreshPromise = null

const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
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

const isAuthEndpoint = (url = '') => {
  return String(url).includes('auth/login') ||
    String(url).includes('auth/refresh') ||
    String(url).includes('auth/logout') ||
    String(url).includes('auth/verify-email') ||
    String(url).includes('auth/reset-password/confirm') ||
    String(url).includes('auth/oauth/')
}

export const refreshAccessToken = async () => {
  if (!refreshPromise) {
    refreshPromise = api
      .post('auth/refresh', null, { skipAuthRefresh: true })
      .then((response) => {
        const token = response.data?.access_token
        if (!token) throw new Error('Refresh response does not contain access token')
        setAccessToken(token)
        return token
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

// Добавляем токен авторизации к каждому запросу
api.interceptors.request.use(
  (config) => {
    const token = getAccessToken()
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
  async (error) => {
    const originalRequest = error.config || {}

    if (
      error.response &&
      error.response.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.skipAuthRefresh &&
      !isAuthEndpoint(originalRequest.url)
    ) {
      originalRequest._retry = true
      try {
        const token = await refreshAccessToken()
        originalRequest.headers = originalRequest.headers || {}
        originalRequest.headers.Authorization = `Bearer ${token}`
        return api(originalRequest)
      } catch {
        // Fall through to redirect below.
      }
    }

    if (error.response && error.response.status === 401) {
      const currentPath = window.location.pathname
      // Normalize path (remove trailing slash)
      const normalizedPath = currentPath.replace(/\/$/, '') || '/'
      const isOAuthCallback =
        normalizedPath === '/auth/yandex/callback' ||
        normalizedPath === '/auth/vk/callback' ||
        normalizedPath === '/auth/mytarget/callback' ||
        normalizedPath === '/auth/login/yandex/callback' ||
        normalizedPath === '/auth/login/vk/callback'

      const isAuthPage =
        isOAuthCallback ||
        normalizedPath === '/login' ||
        normalizedPath === '/' ||
        normalizedPath === '/signup' ||
        normalizedPath === '/signin' ||
        normalizedPath === '/verify-email' ||
        normalizedPath === '/pending-email-verification' ||
        normalizedPath === '/two-step-verification'

      // На страницах авторизации 401 - это нормально, не логируем как ошибку
      if (isAuthPage) {
        // Тихий отказ, не логируем
        return Promise.reject(error)
      }

      // На защищенных страницах - это ошибка авторизации
      console.warn(`Axios: Unauthenticated request (401) from path: ${currentPath}`)
      clearAccessToken()
      window.location.href = '/signin'
    }
    return Promise.reject(error)
  }
)

export default api
