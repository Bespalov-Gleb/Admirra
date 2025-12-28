import { ref } from 'vue'
import api from '../api/axios'

const isAuthenticated = ref(false)
const user = ref(null)
const isLoading = ref(true)
const tokenKey = 'auth_token'

let authPromise = null
let initialCheckDone = false

export function useAuth() {
  // Получение данных текущего пользователя
  const fetchCurrentUser = async () => {
    try {
      const response = await api.get('auth/me')
      user.value = response.data
      isAuthenticated.value = true
      return { success: true, data: response.data }
    } catch (error) {
      console.error('Fetch user error:', error)
      user.value = null
      isAuthenticated.value = false
      return { success: false }
    }
  }

  // Проверка токена в localStorage
  const checkAuth = async () => {
    // If a check is already in progress, return the same promise
    if (authPromise) return authPromise

    const token = localStorage.getItem(tokenKey)
    
    // If we already checked once and have a user, don't re-fetch unless token is gone
    if (initialCheckDone && user.value && token) {
      isAuthenticated.value = true
      return true
    }

    authPromise = (async () => {
      try {
        if (!token) {
          isAuthenticated.value = false
          user.value = null
          return false
        }

        // We only show the global loading spinner for the very first check
        if (!initialCheckDone) {
          isLoading.value = true
        } else {
          console.log('useAuth: Background auth check...')
        }

        await fetchCurrentUser()
        return !!user.value
      } finally {
        isLoading.value = false
        initialCheckDone = true
        authPromise = null
      }
    })()

    return authPromise
  }

  // Вход
  const login = async (email, password) => {
    try {
      const response = await api.post('auth/login', { email, password })
      const { access_token } = response.data
      setToken(access_token)
      await fetchCurrentUser()
      return { success: true }
    } catch (error) {
      console.error('Login error:', error)
      return { 
        success: false, 
        message: error.response?.data?.detail || 'Ошибка авторизации' 
      }
    }
  }

  // Регистрация
  const register = async (email, password, username, first_name = null, last_name = null) => {
    try {
      const response = await api.post('auth/register', { 
        email, 
        password, 
        username,
        first_name,
        last_name
      })
      setToken(response.data.access_token)
      await fetchCurrentUser()
      return { success: true }
    } catch (error) {
      console.error('Registration error:', error)
      return { 
        success: false, 
        message: error.response?.data?.detail || 'Ошибка регистрации' 
      }
    }
  }

  // Сохранение токена
  const setToken = (token) => {
    localStorage.setItem(tokenKey, token)
    isAuthenticated.value = true
  }

  // Получение токена
  const getToken = () => {
    return localStorage.getItem(tokenKey)
  }

  // Удаление токена (выход)
  const removeToken = () => {
    localStorage.removeItem(tokenKey)
    isAuthenticated.value = false
    user.value = null
  }

  return {
    isAuthenticated,
    user,
    isLoading,
    checkAuth,
    fetchCurrentUser,
    login,
    register,
    setToken,
    getToken,
    removeToken
  }
}

