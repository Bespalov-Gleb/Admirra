import { ref } from 'vue'
import api from '../api/axios'

const isAuthenticated = ref(false)
const user = ref(null)
const isLoading = ref(true)
const tokenKey = 'auth_token'
const isDevSkipAuth =
  import.meta.env.DEV &&
  String(import.meta.env.VITE_DEV_SKIP_AUTH || '').toLowerCase() === 'true'

const devUser = {
  id: 'dev-local-user',
  email: 'devlocal@admirra.test',
  username: 'devlocal',
  first_name: 'Dev',
  last_name: 'Local'
}

let authPromise = null
let initialCheckDone = false

export function useAuth() {
  const getErrorMessage = (error, defaultMsg) => {
    const detail = error.response?.data?.detail
    if (!detail) return defaultMsg

    if (typeof detail === 'string') {
      if (detail === 'Incorrect email or password') return 'Неверный email или пароль'
      if (detail === 'Email already registered') return 'Этот Email уже зарегистрирован'
      if (detail === 'Username already taken') return 'Имя пользователя уже занято'
      if (detail === 'Could not validate credentials') return 'Сессия истекла. Пожалуйста, войдите снова'
      if (detail === 'Email not verified') return 'Сначала подтвердите email'
      if (detail === 'Email delivery is not configured on server') return 'Отправка почты не настроена на сервере'
      if (detail === 'Invalid or expired token') return 'Ссылка недействительна или истекла'
      if (detail === 'Invalid or expired challenge') return 'Сессия ввода кода истекла. Войдите снова'
      if (detail === 'Challenge expired') return 'Время ввода кода истекло'
      if (detail === 'Invalid code') return 'Неверный код'
      if (detail === 'Too many attempts') return 'Слишком много попыток. Запросите новый код'
      if (detail.startsWith('Повторная отправка возможна через')) return detail
      return detail
    }

    if (Array.isArray(detail)) {
      return detail.map((err) => err.msg).join('. ')
    }

    return defaultMsg
  }

  const fetchCurrentUser = async () => {
    if (isDevSkipAuth) {
      user.value = devUser
      isAuthenticated.value = true
      return { success: true, data: devUser }
    }

    try {
      const response = await api.get('auth/me')
      user.value = response.data
      isAuthenticated.value = true
      return { success: true, data: response.data }
    } catch (error) {
      console.error('Fetch user error:', error)
      const status = error.response?.status
      const detail = error.response?.data?.detail

      user.value = null
      isAuthenticated.value = false

      if (status === 403 && detail === 'Email not verified') {
        forceLogout()
        return { success: false, emailNotVerified: true }
      }
      if (status === 401) {
        forceLogout()
      }
      return { success: false }
    }
  }

  const checkAuth = async () => {
    if (isDevSkipAuth) {
      user.value = devUser
      isAuthenticated.value = true
      isLoading.value = false
      initialCheckDone = true
      return true
    }

    const token = localStorage.getItem(tokenKey)

    if (authPromise) {
      return authPromise
    }

    authPromise = (async () => {
      try {
        if (!token) {
          isAuthenticated.value = false
          user.value = null
          isLoading.value = false
          initialCheckDone = true
          return false
        }

        if (!initialCheckDone) {
          isLoading.value = true
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

  /**
   * Шаг 1 входа: пароль. JWT приходит только после OTP или не выдаётся, если почта не подтверждена.
   */
  const login = async (email, password) => {
    try {
      const response = await api.post('auth/login', {
        email,
        password
      })

      const data = response.data

      if (data.access_token) {
        setToken(data.access_token)
        const userResult = await fetchCurrentUser()
        if (!userResult.success) {
          throw new Error('Could not fetch user data after login')
        }
        initialCheckDone = true
        return { success: true }
      }

      if (data.step === 'email_not_verified') {
        return {
          success: false,
          needsEmailVerification: true,
          email: data.email || email
        }
      }

      if (data.step === 'otp_required' && data.challenge_id) {
        return {
          success: false,
          needsOtp: true,
          challenge_id: String(data.challenge_id),
          email_masked: data.email_masked || ''
        }
      }

      return {
        success: false,
        message: 'Неожиданный ответ сервера'
      }
    } catch (error) {
      console.error('Login error:', error)
      return {
        success: false,
        message: getErrorMessage(error, 'Ошибка авторизации')
      }
    }
  }

  const completeLoginWithOtp = async (challengeId, code) => {
    try {
      const response = await api.post('auth/login/verify', {
        challenge_id: challengeId,
        code: String(code).trim()
      })
      const { access_token } = response.data
      setToken(access_token)
      const userResult = await fetchCurrentUser()
      if (!userResult.success) {
        throw new Error('Could not fetch user data after OTP')
      }
      initialCheckDone = true
      return { success: true }
    } catch (error) {
      console.error('OTP verify error:', error)
      return {
        success: false,
        message: getErrorMessage(error, 'Неверный код или ошибка сервера')
      }
    }
  }

  const verifyEmailWithToken = async (token) => {
    try {
      const response = await api.post('auth/verify-email', { token: String(token).trim() })
      const { access_token } = response.data
      setToken(access_token)
      const userResult = await fetchCurrentUser()
      if (!userResult.success) {
        throw new Error('Could not fetch user after email verification')
      }
      initialCheckDone = true
      return { success: true }
    } catch (error) {
      console.error('Verify email error:', error)
      return {
        success: false,
        message: getErrorMessage(error, 'Не удалось подтвердить email')
      }
    }
  }

  const resendVerification = async (email) => {
    try {
      await api.post('auth/resend-verification', { email })
      return { success: true }
    } catch (error) {
      const status = error.response?.status
      if (status === 429) {
        return {
          success: false,
          message: getErrorMessage(error, 'Слишком часто. Подождите немного.')
        }
      }
      return {
        success: false,
        message: getErrorMessage(error, 'Не удалось отправить письмо')
      }
    }
  }

  const register = async (email, password, username, first_name = null, last_name = null) => {
    try {
      const response = await api.post('auth/register', {
        email,
        password,
        username,
        first_name,
        last_name
      })

      return {
        success: true,
        needsVerification: true,
        email: response.data.email || email
      }
    } catch (error) {
      console.error('Registration error:', error)
      return {
        success: false,
        message: getErrorMessage(error, 'Ошибка регистрации')
      }
    }
  }

  const setToken = (token) => {
    localStorage.setItem(tokenKey, token)
    isAuthenticated.value = true
  }

  const getToken = () => {
    return localStorage.getItem(tokenKey)
  }

  const forceLogout = () => {
    localStorage.removeItem(tokenKey)
    isAuthenticated.value = false
    user.value = null
    initialCheckDone = false
  }

  return {
    isAuthenticated,
    user,
    isLoading,
    checkAuth,
    fetchCurrentUser,
    login,
    completeLoginWithOtp,
    verifyEmailWithToken,
    resendVerification,
    register,
    setToken,
    getToken,
    forceLogout,
    getErrorMessage
  }
}
