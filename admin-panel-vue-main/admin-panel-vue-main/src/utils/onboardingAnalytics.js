import { getAccessToken } from '@/utils/authToken'
function key() {
  try {
    const subject = JSON.parse(atob(getAccessToken().split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))).sub
    return subject ? `admirra:offer-entry:${subject}` : null
  } catch { return null }
}
export function markOfferEntry() { try { const k = key(); if (k) sessionStorage.setItem(k, String(Date.now())) } catch { /* blocked storage */ } }
export function consumeOfferEntry() {
  try {
    const k = key(); if (!k) return false
    const value = Number(sessionStorage.getItem(k)); sessionStorage.removeItem(k)
    return value > 0 && Date.now() - value < 24 * 60 * 60 * 1000
  } catch { return false }
}
