import api from '../api/axios'

function assertVkAdsAuthorizeUrl(url) {
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
  if (!host.includes('ads.vk.com') && !host.includes('vk.com')) {
    throw new Error('Ожидался редирект на VK Ads (ads.vk.com)')
  }
  const clientId = parsed.searchParams.get('client_id')
  if (!clientId || !clientId.trim()) {
    throw new Error(
      'В ссылке нет client_id. Задайте VK_CLIENT_ID в .env на сервере и перезапустите backend.'
    )
  }
}

/**
 * Вход/регистрация: Яндекс ID и VK Ads OAuth (как у интеграции VK).
 * redirect_uri — /auth/yandex|vk/callback; ветвление — по sessionStorage.oauth_site_login.
 */
export function useOAuthLogin() {
  const yandexCallbackPath = '/auth/yandex/callback'
  const vkCallbackPath = '/auth/vk/callback'

  const startYandexLogin = async () => {
    const redirect_uri = `${window.location.origin}${yandexCallbackPath}`
    sessionStorage.setItem('oauth_site_login', 'yandex')
    const { data } = await api.get('auth/oauth/yandex/authorize-url', {
      params: { redirect_uri }
    })
    window.location.href = data.url
  }

  const startVkLogin = async () => {
    const redirect_uri = `${window.location.origin}${vkCallbackPath}`
    sessionStorage.setItem('oauth_site_login', 'vk')
    const { data } = await api.get('auth/oauth/vk/authorize-url', {
      params: { redirect_uri }
    })
    assertVkAdsAuthorizeUrl(data.url)
    window.location.href = data.url
  }

  return { startYandexLogin, startVkLogin, yandexCallbackPath, vkCallbackPath }
}
