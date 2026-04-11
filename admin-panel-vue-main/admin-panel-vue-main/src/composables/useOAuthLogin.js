import api from '../api/axios'

/**
 * Вход/регистрация через Яндекс ID и VK ID (отдельные callback от интеграций рекламы).
 */
export function useOAuthLogin() {
  const yandexCallbackPath = '/auth/login/yandex/callback'
  const vkCallbackPath = '/auth/login/vk/callback'

  const startYandexLogin = async () => {
    const redirect_uri = `${window.location.origin}${yandexCallbackPath}`
    const { data } = await api.get('auth/oauth/yandex/authorize-url', {
      params: { redirect_uri }
    })
    window.location.href = data.url
  }

  const startVkLogin = async () => {
    const redirect_uri = `${window.location.origin}${vkCallbackPath}`
    const { data } = await api.get('auth/oauth/vk/authorize-url', {
      params: { redirect_uri }
    })
    window.location.href = data.url
  }

  return { startYandexLogin, startVkLogin, yandexCallbackPath, vkCallbackPath }
}
