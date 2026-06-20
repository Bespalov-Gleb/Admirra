(() => {
  const API_BASE = '/api/'
  const TOKEN_KEY = 'auth_token'
  const DEFAULT_DASHBOARD_PATH = '/projects/create'
  const YM_COUNTER_ID = 109911357
  const YCLID_KEY = 'ym_yclid'

  function callYm(...args) {
    if (typeof window.ym !== 'function') return
    try {
      window.ym(YM_COUNTER_ID, ...args)
    } catch {
      // Метрика не должна ломать авторизацию
    }
  }

  function reachGoal(goal, params) {
    if (!goal) return
    if (params && Object.keys(params).length) callYm('reachGoal', String(goal), params)
    else callYm('reachGoal', String(goal))
  }

  function captureYclid() {
    try {
      const yclid = new URL(window.location.href).searchParams.get('yclid')
      if (yclid && !localStorage.getItem(YCLID_KEY)) {
        localStorage.setItem(YCLID_KEY, yclid)
      }
    } catch {
      // ignore
    }
  }

  function getStoredYclid() {
    try {
      return localStorage.getItem(YCLID_KEY) || null
    } catch {
      return null
    }
  }

  function getMetrikaClientId() {
    return new Promise((resolve) => {
      if (typeof window.ym !== 'function') {
        resolve(null)
        return
      }
      let settled = false
      const done = (value) => {
        if (!settled) {
          settled = true
          resolve(value || null)
        }
      }
      try {
        window.ym(YM_COUNTER_ID, 'getClientID', (clientId) => done(clientId))
      } catch {
        done(null)
      }
      setTimeout(() => done(null), 3000)
    })
  }

  async function sendMetrikaIdentity(token) {
    try {
      const clientId = await getMetrikaClientId()
      const yclid = getStoredYclid()
      if (!token || (!clientId && !yclid)) return
      await apiRequest('auth/metrika/identity', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify({ client_id: clientId, yclid }),
      })
    } catch {
      // ignore
    }
  }

  function $(selector, root = document) {
    return root.querySelector(selector)
  }

  function showError(containerId, message) {
    const box = document.getElementById(containerId)
    if (!box) return
    const text = box.querySelector('div') || box
    text.textContent = message || 'Произошла ошибка'
    box.style.display = 'block'
  }

  function hideError(containerId) {
    const box = document.getElementById(containerId)
    if (!box) return
    box.style.display = 'none'
  }

  function setButtonLoading(button, isLoading, defaultText, loadingText) {
    if (!button) return
    button.disabled = isLoading
    const textNode = button.querySelector('.btn__text')
    if (textNode) {
      textNode.textContent = isLoading ? loadingText : defaultText
    }
  }

  function getDetailMessage(detail, fallback) {
    if (!detail) return fallback
    if (typeof detail === 'string') {
      if (detail === 'Incorrect email or password') return 'Неверный email или пароль'
      if (detail === 'Email already registered') return 'Этот Email уже зарегистрирован'
      if (detail === 'Username already taken') return 'Имя пользователя уже занято'
      if (detail === 'Email delivery is not configured on server') return 'Отправка почты не настроена на сервере'
      if (detail === 'Invalid or expired challenge') return 'Сессия ввода кода истекла. Войдите снова'
      if (detail === 'Challenge expired') return 'Время ввода кода истекло'
      if (detail === 'Invalid code') return 'Неверный код'
      if (detail === 'Too many attempts') return 'Слишком много попыток. Запросите новый код'
      return detail
    }
    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg || String(item)).join('. ')
    }
    return fallback
  }

  async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
      ...options,
    })
    let data = null
    try {
      data = await response.json()
    } catch {
      data = null
    }
    if (!response.ok) {
      const error = new Error('API request failed')
      error.status = response.status
      error.data = data
      throw error
    }
    return data
  }

  function saveToken(token) {
    localStorage.setItem(TOKEN_KEY, token)
  }

  function randomString(length = 64) {
    const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
    const array = new Uint8Array(length)
    window.crypto.getRandomValues(array)
    let output = ''
    for (let i = 0; i < array.length; i += 1) {
      output += alphabet[array[i] % alphabet.length]
    }
    return output
  }

  function toBase64Url(bytes) {
    const binary = String.fromCharCode(...bytes)
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
  }

  async function createPkcePair() {
    const codeVerifier = randomString(64)
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(codeVerifier))
    return {
      codeVerifier,
      codeChallenge: toBase64Url(new Uint8Array(digest)),
    }
  }

  async function startYandexOAuth() {
    const redirectUri = `${window.location.origin}/auth/yandex/callback`
    sessionStorage.setItem('oauth_site_login', 'yandex')
    const params = new URLSearchParams({ redirect_uri: redirectUri })
    const data = await apiRequest(`auth/oauth/yandex/authorize-url?${params.toString()}`, { method: 'GET' })
    if (!data?.url) {
      throw new Error('Сервер не вернул ссылку для входа через Яндекс')
    }
    window.location.href = data.url
  }

  async function startVkOAuth() {
    const redirectUri = `${window.location.origin}/auth/login/vk/callback`
    sessionStorage.setItem('oauth_site_login', 'vk')
    const { codeVerifier, codeChallenge } = await createPkcePair()
    const params = new URLSearchParams({
      redirect_uri: redirectUri,
      code_challenge: codeChallenge,
    })
    const data = await apiRequest(`auth/oauth/vk/authorize-url?${params.toString()}`, { method: 'GET' })
    if (!data?.url) {
      throw new Error('Сервер не вернул ссылку для входа через VK')
    }
    const authUrl = new URL(data.url)
    const state = authUrl.searchParams.get('state')
    if (!state) {
      throw new Error('VK ID не вернул state. Повторите попытку.')
    }
    localStorage.setItem(`vk_login_pkce:${state}`, codeVerifier)
    window.location.href = data.url
  }

  function bindOAuthButtons(errorContainerId) {
    document.querySelectorAll('[data-oauth-provider]').forEach((button) => {
      button.addEventListener('click', async (event) => {
        event.preventDefault()
        hideError(errorContainerId)
        const provider = button.getAttribute('data-oauth-provider')
        try {
          if (provider === 'yandex') {
            await startYandexOAuth()
            return
          }
          if (provider === 'vk') {
            await startVkOAuth()
            return
          }
          showError(errorContainerId, 'Авторизация через этот провайдер пока недоступна')
        } catch (error) {
          showError(errorContainerId, getDetailMessage(error?.data?.detail, error.message || 'Ошибка OAuth'))
        }
      })
    })
  }

  function initEntryPage() {
    const form = $('#entry-form')
    if (!form) return
    const submitButton = $('#entry-submit')
    bindOAuthButtons('entry-error')

    form.addEventListener('submit', async (event) => {
      event.preventDefault()
      hideError('entry-error')

      const email = $('#login-email')?.value?.trim() || ''
      const password = $('#login-password')?.value || ''

      if (!email) {
        showError('entry-error', 'Введите Email')
        return
      }
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        showError('entry-error', 'Введите корректный Email')
        return
      }
      if (!password) {
        showError('entry-error', 'Введите пароль')
        return
      }

      setButtonLoading(submitButton, true, 'ВОЙТИ В ЛИЧНЫЙ КАБИНЕТ', 'ВХОД...')
      try {
        const data = await apiRequest('auth/login', {
          method: 'POST',
          body: JSON.stringify({ email, password }),
        })

        if (data?.access_token) {
          saveToken(data.access_token)
          await sendMetrikaIdentity(data.access_token)
          window.location.href = DEFAULT_DASHBOARD_PATH
          return
        }
        if (data?.step === 'email_not_verified') {
          window.location.href = `/pending-email-verification?email=${encodeURIComponent(data.email || email)}`
          return
        }
        if (data?.step === 'otp_required' && data.challenge_id) {
          const query = new URLSearchParams({
            mode: 'otp',
            challenge_id: String(data.challenge_id),
            email_masked: data.email_masked || '',
          })
          window.location.href = `/two-step-verification?${query.toString()}`
          return
        }
        showError('entry-error', 'Неожиданный ответ сервера')
      } catch (error) {
        showError('entry-error', getDetailMessage(error?.data?.detail, 'Ошибка авторизации'))
      } finally {
        setButtonLoading(submitButton, false, 'ВОЙТИ В ЛИЧНЫЙ КАБИНЕТ', 'ВХОД...')
      }
    })
  }

  function initRegPage() {
    const form = $('#reg-form')
    if (!form) return
    const submitButton = $('#reg-submit')
    bindOAuthButtons('reg-error')
    reachGoal('signup_start')

    form.addEventListener('submit', async (event) => {
      event.preventDefault()
      hideError('reg-error')

      const firstName = $('#reg-first-name')?.value?.trim() || ''
      const lastName = $('#reg-last-name')?.value?.trim() || ''
      const email = $('#reg-email')?.value?.trim() || ''
      const password = $('#reg-password')?.value || ''
      const agree = $('#reg-agree')?.checked

      if (!firstName) {
        showError('reg-error', 'Введите ваше имя')
        return
      }
      if (!email) {
        showError('reg-error', 'Введите Email')
        return
      }
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        showError('reg-error', 'Введите корректный Email')
        return
      }
      if (!password) {
        showError('reg-error', 'Введите пароль')
        return
      }
      if (password.length < 6) {
        showError('reg-error', 'Пароль должен быть не менее 6 символов')
        return
      }
      if (!agree) {
        showError('reg-error', 'Вы должны согласиться с условиями')
        return
      }

      setButtonLoading(submitButton, true, 'ЗАРЕГИСТРИРОВАТЬСЯ', 'РЕГИСТРАЦИЯ...')
      try {
        const data = await apiRequest('auth/register', {
          method: 'POST',
          body: JSON.stringify({
            email,
            password,
            username: firstName,
            first_name: firstName,
            last_name: lastName || null,
          }),
        })
        reachGoal('signup_complete', { method: 'email' })
        reachGoal('trial_start')
        window.location.href = `/pending-email-verification?email=${encodeURIComponent(data?.email || email)}`
      } catch (error) {
        showError('reg-error', getDetailMessage(error?.data?.detail, 'Ошибка регистрации'))
      } finally {
        setButtonLoading(submitButton, false, 'ЗАРЕГИСТРИРОВАТЬСЯ', 'РЕГИСТРАЦИЯ...')
      }
    })
  }

  document.addEventListener('DOMContentLoaded', () => {
    captureYclid()
    initEntryPage()
    initRegPage()
  })
})()
