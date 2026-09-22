// Does not know users/emails or widget-supplied amounts. Input comes from the
// authenticated confirmation endpoint after the server accepts the webhook.
const seen = new Set()
const KEY = 'admirra:tracked-purchases:v1'

export function trackPurchase(payment, { win = globalThis.window, counterId = 109911357, goalIds = {} } = {}) {
  if (!win || !['admirra.ru', 'www.admirra.ru'].includes(win.location?.hostname)
      || typeof win.ym !== 'function' || !Array.isArray(win.dataLayer)) return Promise.resolve(false)
  const p = payment
  if (!p || typeof p.payment_id !== 'string' || !p.payment_id || p.currency !== 'RUB'
      || !Number.isFinite(p.amount) || p.amount <= 0 || !Number.isFinite(p.list_price)
      || !Number.isFinite(p.discount) || p.discount < 0 || p.list_price < p.amount
      || !['month', 'year'].includes(p.billing) || typeof p.name !== 'string'
      || !/^(start|basic|standard|white_label)_(month|year)$/.test(p.sku)
      || !['payment_success', 'plan_upgrade'].includes(p.goal)) return Promise.resolve(false)
  let stored = []
  try { const data = JSON.parse(win.sessionStorage.getItem(KEY) || '[]'); if (Array.isArray(data)) stored = data } catch { /* storage blocked */ }
  if (seen.has(p.payment_id) || stored.includes(p.payment_id)) return Promise.resolve(false)
  const actionField = { id: p.payment_id, revenue: p.amount }
  if (p.coupon) actionField.coupon = p.coupon
  const goalId = Number(goalIds[p.goal])
  if (Number.isSafeInteger(goalId) && goalId > 0) actionField.goal_id = goalId
  const product = { id: p.sku, name: p.name, category: `Подписка / ${p.billing === 'year' ? 'Годовая' : 'Месячная'}`,
    variant: p.billing, price: p.list_price, quantity: 1 }
  if (p.discount > 0) product.discount = p.discount
  try {
    win.dataLayer.push({ ecommerce: { currencyCode: 'RUB', purchase: { actionField, products: [product] } } })
    seen.add(p.payment_id)
    try { win.sessionStorage.setItem(KEY, JSON.stringify([...stored, p.payment_id])) } catch { /* memory dedup remains */ }
  } catch { return Promise.resolve(false) }
  return new Promise(resolve => {
    const done = () => resolve(true)
    setTimeout(done, 300)
    try {
      win.ym(counterId, 'reachGoal', p.goal, { order_price: p.amount, currency: 'RUB',
        plan: p.plan, billing: p.billing, signup_discount: Boolean(p.signup_discount) }, done)
      win.ym(counterId, 'reachGoal', 'subscription_paid', { signup_discount: Boolean(p.signup_discount) })
    } catch { done() }
  })
}
