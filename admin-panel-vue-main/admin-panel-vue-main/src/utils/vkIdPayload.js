/**
 * Параметр payload в redirect_uri после VK ID OAuth 2.1 (JSON с code, state, device_id, type).
 * @see https://id.vk.com/about/business/go/docs/ru/vkid/latest/vk-id/connection/start-integration/auth-without-sdk/auth-without-sdk-web
 */
export function parseVkIdPayload(route) {
  let p = route.query.payload
  if (Array.isArray(p)) p = p[0]
  if (p == null || p === '') return null
  try {
    if (typeof p === 'object' && p !== null && !Array.isArray(p)) return p
    const s = typeof p === 'string' ? p : String(p)
    const decoded = /%[0-9A-Fa-f]{2}/.test(s) ? decodeURIComponent(s.replace(/\+/g, ' ')) : s
    const obj = JSON.parse(decoded)
    return obj && typeof obj === 'object' ? obj : null
  } catch {
    return null
  }
}
