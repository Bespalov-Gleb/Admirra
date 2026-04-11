import * as VKID from '@vkid/sdk'
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

/**
 * VK ID One Tap по доке: https://id.vk.com/about/business/go/docs/ru/vkid/latest/vk-id/connection/elements/onetap-button/onetap-web
 * PKCE на фронте, обмен кода на бэкенде: https://id.vk.com/about/business/go/docs/ru/vkid/latest/vk-id/connection/start-integration/how-auth-works/auth-flow-web#Cherez-SDK-s-obmenom-koda-na-bekende
 *
 * @param {HTMLElement} container
 * @param {object} options
 * @param {'signin'|'signup'} options.mode
 * @param {(accessToken: string) => Promise<void>} options.onSuccess
 * @param {(message: string) => void} options.onError
 * @param {() => void} [options.onExchangeStart]
 * @param {() => void} [options.onExchangeEnd]
 * @returns {Promise<() => void>} cleanup (close widget)
 */
export async function mountVkIdOneTap(container, options) {
  const { mode, onSuccess, onError, onExchangeStart, onExchangeEnd } = options
  if (!container) {
    return () => {}
  }

  const { data: cfg } = await api.get('auth/oauth/vk/sdk-config')
  const appId = Number.parseInt(String(cfg.app_id).trim(), 10)
  if (!Number.isFinite(appId) || appId <= 0) {
    throw new Error('Некорректный app_id в ответе сервера')
  }

  const redirectUrl = `${window.location.origin}/auth/vk/callback`
  const state = randomState()
  const codeVerifier = randomPkceVerifier()
  sessionStorage.setItem('oauth_site_login', 'vk')

  const scope = (cfg.scope || 'vkid.personal_info email').replace(/,/g, ' ').trim()

  VKID.Config.init({
    app: appId,
    redirectUrl,
    state,
    codeVerifier,
    scope,
    responseMode: VKID.ConfigResponseMode.Callback,
  })

  const oneTap = new VKID.OneTap()

  oneTap.on(VKID.WidgetEvents.ERROR, () => {
    onError('Ошибка виджета VK ID. Попробуйте ещё раз или войдите другим способом.')
  })

  oneTap.on(VKID.OneTapInternalEvents.LOGIN_SUCCESS, async (payload) => {
    const code = payload?.code
    const deviceId = payload?.device_id
    const retState = payload?.state ?? state
    if (!code || !deviceId) {
      onError('VK ID не вернул данные для входа.')
      return
    }
    onExchangeStart?.()
    try {
      const { data: tokenPayload } = await api.post('auth/oauth/vk/callback', {
        code,
        state: retState,
        redirect_uri: redirectUrl,
        device_id: deviceId,
        code_verifier: codeVerifier,
      })
      await onSuccess(tokenPayload.access_token)
    } catch (err) {
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
  })

  oneTap.render({
    container,
    scheme: VKID.Scheme.LIGHT,
    lang: VKID.Languages.RUS,
    contentId:
      mode === 'signup' ? VKID.OneTapContentId.SIGN_UP : VKID.OneTapContentId.SIGN_IN,
    fastAuthEnabled: true,
  })

  return () => {
    try {
      oneTap.close()
    } catch {
      /* ignore */
    }
  }
}
