import api from '../api/axios'

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
    window.location.href = data.url
  }

  return { startYandexLogin, startVkLogin, yandexCallbackPath, vkCallbackPath }
}
