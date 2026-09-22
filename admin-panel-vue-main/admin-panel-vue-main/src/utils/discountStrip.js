// Dismissal is presentation-only: never changes eligibility or payment amounts.
// A newly granted offer reappears even if its pre-connection invitation was hidden.
export function discountStripKey(userId, offer = {}) {
  if (!userId || !offer.eligible || !offer.expires_at) return null
  return `admirra:discount-strip:v1:${userId}:${offer.active ? 'granted' : 'invitation'}:${offer.expires_at}`
}

export function isDiscountStripHidden(storage, key) {
  if (!key) return false
  try { return storage?.getItem(key) === 'hidden' } catch { return false }
}

export function hideDiscountStrip(storage, key) {
  if (!key) return
  try { storage?.setItem(key, 'hidden') } catch { /* in-memory dismissal still works */ }
}
