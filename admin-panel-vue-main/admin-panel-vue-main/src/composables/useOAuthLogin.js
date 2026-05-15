import api from '../api/axios'

function assertVkAuthorizeUrl(url) {
  if (!url || typeof url !== 'string') {
    throw new Error('Сервер не вернул ссылку для входа через VK')
  }
  let parsed
  try {
    parsed = new URL(url)
  } catch {
    throw new Error('Некорректная ссылка авторизации VK')
  }
  const host = parsed.hostname.toLowerCase()
  if (!host.includes('id.vk.ru')) {
    throw new Error('Ожидался редирект на VK ID (id.vk.ru)')
  }
  const clientId = parsed.searchParams.get('client_id')
  if (!clientId || !clientId.trim()) {
    throw new Error(
      'В ссылке нет client_id. Задайте VK_LOGIN_CLIENT_ID (или VK_CLIENT_ID) в .env на сервере и перезапустите backend.'
    )
  }
  if (parsed.searchParams.get('code_challenge_method') !== 'S256') {
    throw new Error('Сервер вернул ссылку VK ID без PKCE (code_challenge_method=S256)')
  }
}

function randomString(length = 64) {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
  const arr = new Uint8Array(length)
  crypto.getRandomValues(arr)
  let out = ''
  for (let i = 0; i < arr.length; i += 1) {
    out += alphabet[arr[i] % alphabet.length]
  }
  return out
}

function bytesToBase64Url(bytes) {
  const bin = String.fromCharCode(...bytes)
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
}

async function createPkcePair() {
  const codeVerifier = randomString(64)
  const encoded = new TextEncoder().encode(codeVerifier)
  const digest = await crypto.subtle.digest('SHA-256', encoded)
  const codeChallenge = bytesToBase64Url(new Uint8Array(digest))
  return { codeVerifier, codeChallenge }
}

function saveVkPkceByState(state, codeVerifier) {
  if (!state || !codeVerifier) return
  localStorage.setItem(`vk_login_pkce:${state}`, codeVerifier)
}

export function consumeVkPkceByState(state) {
  if (!state) return ''
  const key = `vk_login_pkce:${state}`
  const verifier = localStorage.getItem(key) || ''
  localStorage.removeItem(key)
  return verifier
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * Вход/регистрация: Яндекс ID и VK ID OAuth 2.1.
 * Для VK ID используется PKCE, code_verifier сохраняется локально до callback.
 */
export function useOAuthLogin() {
  const yandexCallbackPath = '/auth/yandex/callback'
  const vkCallbackPath = '/auth/login/vk/callback'

  const startYandexLogin = async () => {
    const redirect_uri = `${window.location.origin}${yandexCallbackPath}`
    sessionStorage.setItem('oauth_site_login', 'yandex')
    const { data } = await api.get('auth/oauth/yandex/authorize-url', {
      params: { redirect_uri }
    })
    window.location.href = data.url
  }

  const startMaxLogin = async () => {
    const popup = window.open('', '_blank')
    try {
      sessionStorage.setItem('oauth_site_login', 'max')
      const { data } = await api.get('auth/oauth/max/authorize-url')
      if (!data?.url || !data?.state) {
        throw new Error('Сервер не вернул ссылку для входа через MAX')
      }

      if (popup) {
        popup.location.href = data.url
        try {
          popup.focus()
        } catch {
          /* ignore */
        }
      } else {
        window.open(data.url, '_blank')
      }

      const startedAt = Date.now()
      const timeoutMs = Math.max(60000, Number(data.expires_in_seconds || 300) * 1000)
      const intervalMs = Math.max(1000, Number(data.poll_interval_ms || 2000))

      while (Date.now() - startedAt < timeoutMs) {
        await delay(intervalMs)
        const { data: statusData } = await api.get('auth/oauth/max/status', {
          params: { state: data.state }
        })

        if (statusData?.status === 'completed' && statusData.access_token) {
          try {
            popup?.close()
          } catch {
            /* ignore */
          }
          return statusData
        }
        if (statusData?.status === 'expired') {
          throw new Error('Ссылка для входа через MAX истекла. Попробуйте снова.')
        }
        if (statusData?.status === 'used') {
          throw new Error('Ссылка для входа через MAX уже использована. Попробуйте снова.')
        }
      }

      throw new Error('Не удалось подтвердить вход через MAX за отведённое время.')
    } catch (error) {
      try {
        if (popup && !popup.closed && popup.location.href === 'about:blank') popup.close()
      } catch {
        /* ignore */
      }
      throw error
    }
  }

  const startVkLogin = async () => {
    const redirect_uri = `${window.location.origin}${vkCallbackPath}`
    sessionStorage.setItem('oauth_site_login', 'vk')
    const { codeVerifier, codeChallenge } = await createPkcePair()
    const { data } = await api.get('auth/oauth/vk/authorize-url', {
      params: {
        redirect_uri,
        code_challenge: codeChallenge
      }
    })
    assertVkAuthorizeUrl(data.url)
    const authUrl = new URL(data.url)
    const state = authUrl.searchParams.get('state')
    if (!state) {
      throw new Error('VK ID не вернул state. Повторите вход.')
    }
    saveVkPkceByState(state, codeVerifier)
    window.location.href = data.url
  }

  return { startYandexLogin, startVkLogin, startMaxLogin, yandexCallbackPath, vkCallbackPath }
}
