/**
 * Распознавание сценария «вход на сайт» по state из URL (JWT от бэкенда oauth_login).
 * Подпись здесь не проверяется — только выбор ветки на клиенте; валидация на сервере.
 */
export function oauthLoginProviderFromState(state) {
  if (!state || typeof state !== 'string') return null
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
