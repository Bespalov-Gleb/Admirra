import { ref } from 'vue'
import api from '../api/axios'

const isAuthenticated = ref(false)
const user = ref(null)
const isLoading = ref(true)
const tokenKey = 'auth_token'

let authPromise = null
let initialCheckDone = false

export function useAuth() {
  // Helper to map API errors to friendly messages
  const getErrorMessage = (error, defaultMsg) => {
    const detail = error.response?.data?.detail
    if (!detail) return defaultMsg
    
    // Map common FastAPI/Pydantic error details
    if (typeof detail === 'string') {
      if (detail === 'Incorrect email or password') return 'Неверный email или пароль'
      if (detail === 'Email already registered') return 'Этот Email уже зарегистрирован'
      if (detail === 'Username already taken') return 'Имя пользователя уже занято'
      if (detail === 'Could not validate credentials') return 'Сессия истекла. Пожалуйста, войдите снова'
      return detail
    }
    
    // Handle list of validation errors (Pydantic)
    if (Array.isArray(detail)) {
      return detail.map(err => err.msg).join('. ')
    }
    
    return defaultMsg
  }

  // Получение данных текущего пользователя
  const fetchCurrentUser = async () => {
    try {
      console.log('useAuth: Fetching current user details...')
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
          console.log('useAuth: No token found, user is guest.')
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

        const result = await fetchCurrentUser()
        return result.success
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
      console.log('useAuth: Attempting login for', email)
      const response = await api.post('auth/login', { email, password })
      const { access_token } = response.data
      
      // 1. Set token first
      setToken(access_token)
      
      // 2. Fetch user data immediately and WAIT for it
      const userResult = await fetchCurrentUser()
      
      if (!userResult.success) {
        throw new Error('Could not fetch user data after successful login')
      }
      
      console.log('useAuth: Login successful, user state updated.')
      initialCheckDone = true
      return { success: true }
    } catch (error) {
      console.error('Login error:', error)
      removeToken() // Cleanup on failure
      return { 
        success: false, 
        message: getErrorMessage(error, 'Ошибка авторизации') 
      }
    }
  }

  // Регистрация
  const register = async (email, password, username, first_name = null, last_name = null) => {
    try {
      console.log('useAuth: Registering new user...')
      const response = await api.post('auth/register', { 
        email, 
        password, 
        username,
        first_name,
        last_name
      })
      
      // 1. Set token
      setToken(response.data.access_token)
      
      // 2. Fetch user data immediately and WAIT
      const userResult = await fetchCurrentUser()
      
      if (!userResult.success) {
        throw new Error('Could not fetch user data after successful registration')
      }

      console.log('useAuth: Registration successful.')
      initialCheckDone = true
      return { success: true }
    } catch (error) {
      console.error('Registration error:', error)
      removeToken()
      return { 
        success: false, 
        message: getErrorMessage(error, 'Ошибка регистрации') 
      }
    }
  }

  // Сохранение токена
  const setToken = (token) => {
    console.log('useAuth: Token saved to storage.')
    localStorage.setItem(tokenKey, token)
    isAuthenticated.value = true
  }

  // Получение токена
  const getToken = () => {
    return localStorage.getItem(tokenKey)
  }

  // Удаление токена (выход)
  const removeToken = () => {
    console.log('useAuth: Removing token and clearing session.')
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

