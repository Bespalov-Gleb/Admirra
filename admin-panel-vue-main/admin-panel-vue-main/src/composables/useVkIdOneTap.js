import {
  Auth,
  Config,
  ConfigResponseMode,
} from '@vkid/sdk'
import api from '@/api/axios'

function randomPkceVerifier() {
  const a = new Uint8Array(32)
  crypto.getRandomValues(a)
  const s = btoa(String.fromCharCode(...a))
  return s.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

function randomState() {
  return randomPkceVerifier()
}

function parseAppId(raw) {
  const s = String(raw ?? '').trim()
  if (!s) return null
  const n = Number.parseInt(s, 10)
  if (!Number.isFinite(n) || n <= 0) return null
  return n
}

/**
 * Вход через VK ID Web SDK: Config + Auth.login() (в новой вкладке по умолчанию), обмен кода на бэкенде.
 * One Tap (iframe button_one_tap_auth) в части окружений открывал authorize.js без client_id; Auth.login
 * формирует URL /authorize с client_id явно (см. @vkid/sdk auth.js).
 *
 * Док: https://id.vk.com/about/business/go/docs/ru/vkid/latest/vk-id/connection/start-integration/web/setup
 */
export async function mountVkIdOneTap(container, options) {
  const { mode, onSuccess, onError, onExchangeStart, onExchangeEnd } = options
  if (!container) {
    return () => {}
  }

  const { data: cfg } = await api.get('auth/oauth/vk/sdk-config')
  const appId = parseAppId(cfg.app_id)
  if (appId == null) {
    throw new Error('Некорректный app_id в ответе сервера')
  }

  const redirectUrl = `${window.location.origin}/auth/vk/callback`
  const state = randomState()
  const codeVerifier = randomPkceVerifier()
  sessionStorage.setItem('oauth_site_login', 'vk')

  const scope = (cfg.scope || 'vkid.personal_info email').replace(/,/g, ' ').trim()

  Config.init({
    app: appId,
    redirectUrl,
    state,
    codeVerifier,
    scope,
    responseMode: ConfigResponseMode.Callback,
  })

  const snap = Config.get()
  if (snap.app == null || snap.app === '' || Number(snap.app) === 0) {
    throw new Error('VK ID SDK: в Config не попал app (client_id)')
  }

  const label =
    mode === 'signup'
      ? 'Зарегистрироваться с VK ID'
      : 'Войти с VK ID'

  const btn = document.createElement('button')
  btn.type = 'button'
  btn.textContent = label
  btn.className =
    'vkid-sdk-login-btn inline-flex w-full items-center justify-center gap-3 rounded-lg bg-gray-100 px-8 py-4 text-base font-normal text-gray-700 transition-colors hover:bg-gray-200 hover:text-gray-800 disabled:opacity-50'

  const runLogin = async () => {
    onExchangeStart?.()
    try {
      const payload = await Auth.login()
      const code = payload?.code
      const deviceId = payload?.device_id
      const retState = payload?.state ?? state
      if (!code || !deviceId) {
        onError('VK ID не вернул данные для входа.')
        return
      }
      const { data: tokenPayload } = await api.post('auth/oauth/vk/callback', {
        code,
        state: retState,
        redirect_uri: redirectUrl,
        device_id: deviceId,
        code_verifier: codeVerifier,
      })
      await onSuccess(tokenPayload.access_token)
    } catch (err) {
      if (err?.code != null && err?.error) {
        onError(typeof err.error === 'string' ? err.error : 'Вход через VK отменён или прерван')
        return
      }
      const detail = err.response?.data?.detail
      const msg =
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
            ? detail.map((x) => x.msg || JSON.stringify(x)).join('. ')
            : err.message || 'Не удалось завершить вход через VK'
      onError(msg)
    } finally {
      onExchangeEnd?.()
    }
  }

  btn.addEventListener('click', () => {
    void runLogin()
  })

  container.appendChild(btn)

  return () => {
    try {
      btn.remove()
    } catch {
      /* ignore */
    }
  }
}
