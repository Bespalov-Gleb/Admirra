/**
 * Распознавание сценария «вход на сайт» по state из URL.
 * Префиксы: site-yandex_ / site-vk_ (актуально), поддержка legacy site-yandex. / site-vk. сохранена.
 * (короткий HMAC-state на бэкенде); раньше — JWT (три части).
 * Подпись на клиенте не проверяется; валидация на сервере.
 */
export function oauthLoginProviderFromState(state) {
  if (!state || typeof state !== 'string') return null
  if (state.startsWith('site-yandex.') || state.startsWith('site-yandex_')) return 'yandex'
  if (state.startsWith('site-vk.') || state.startsWith('site-vk_')) return 'vk'
  const parts = state.split('.')
  if (parts.length !== 3) return null
  try {
    const b64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const pad = b64.length % 4
    const padded = pad ? b64 + '='.repeat(4 - pad) : b64
    const json = JSON.parse(atob(padded))
    if (json.pur !== 'oauth_login' || !json.prv) return null
    if (json.prv === 'yandex' || json.prv === 'vk') return json.prv
  } catch {
    return null
  }
  return null
}
