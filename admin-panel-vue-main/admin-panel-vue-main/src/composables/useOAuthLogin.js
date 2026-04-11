import api from '../api/axios'

function assertVkIdAuthorizeUrl(url) {
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
  if (!host.endsWith('vk.ru') && !host.endsWith('vk.com')) {
    throw new Error('Ссылка входа VK должна вести на id.vk.ru / id.vk.com')
  }
  const clientId = parsed.searchParams.get('client_id')
  if (!clientId || !clientId.trim()) {
    throw new Error(
      'В ссылке нет client_id. На сервере задайте VK_LOGIN_CLIENT_ID или VK_CLIENT_ID (приложение VK ID) и перезапустите backend.'
    )
  }
}

/**
 * Вход/регистрация через Яндекс ID и VK ID.
 * Тот же redirect_uri, что у мастера интеграций (/auth/yandex|vk/callback), чтобы в кабинетах OAuth
 * не добавлять второй URL. Ветвление на странице callback — по sessionStorage.oauth_site_login.
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
    assertVkIdAuthorizeUrl(data.url)
    window.location.href = data.url
  }

  return { startYandexLogin, startVkLogin, yandexCallbackPath, vkCallbackPath }
}
