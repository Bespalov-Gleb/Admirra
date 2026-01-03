import { ref } from 'vue'

const isAuthenticated = ref(false)
const tokenKey = 'auth_token'

export function useAuth() {
  // Проверка токена в localStorage
  const checkAuth = () => {
  const token = localStorage.getItem(tokenKey)
  isAuthenticated.value = !!token
  return !!token
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
  }

  // Инициализация при загрузке
  checkAuth()

  return {
    isAuthenticated,
    checkAuth,
    setToken,
    getToken,
    removeToken
  }
}

