export const FALLBACK_PLANS = {
  start: {
    code: 'start',
    name: 'Старт',
    price_rub: 1590,
    max_projects: 1,
    max_ai_requests_per_period: 30,
    trial_days: 14,
  },
  basic: {
    code: 'basic',
    name: 'Базовый',
    price_rub: 3990,
    max_projects: 5,
    max_ai_requests_per_period: 120,
    trial_days: 14,
  },
  standard: {
    code: 'standard',
    name: 'Стандартный',
    price_rub: 9990,
    max_projects: 30,
    max_ai_requests_per_period: 450,
    trial_days: 14,
  },
}

export function normalizePlansFromApi(rows) {
  const by = {}
  for (const p of rows || []) {
    if (p?.code) by[String(p.code).toLowerCase()] = p
  }
  return {
    start: by.start || FALLBACK_PLANS.start,
    basic: by.basic || FALLBACK_PLANS.basic,
    standard: by.standard || FALLBACK_PLANS.standard,
  }
}

/** Месяц × 12, минус 30%, округление вверх до десятков рублей. */
export function yearlyPriceFromMonthly(monthlyRub) {
  const m = Number(monthlyRub)
  if (Number.isNaN(m) || m < 0) return 0
  const afterDiscount = m * 12 * 0.7
  return Math.ceil(afterDiscount / 10) * 10
}

export function formatRub(n) {
  const v = Number(n)
  if (Number.isNaN(v)) return '—'
  return `${new Intl.NumberFormat('ru-RU').format(v)}\u00A0₽`
}

export function perProjectLine(priceRub, maxProjects) {
  const max = Number(maxProjects)
  const price = Number(priceRub)
  if (!max || Number.isNaN(price)) return ''
  return `${Math.round(price / max)}\u00A0руб/проект`
}

export function projectBullet(plan) {
  const n = Number(plan?.max_projects)
  if (!n || Number.isNaN(n)) return 'Проекты'
  if (n <= 1) return '1 проект'
  return `До ${n} проектов`
}

export function channelsBullet(code) {
  const c = String(code || '').toLowerCase()
  if (c === 'start') return 'Каналы: Яндекс.Директ, ВК'
  return 'Все доступные подключения'
}

export function usersBullet(code) {
  const c = String(code || '').toLowerCase()
  if (c === 'start') return '1 пользователь'
  if (c === 'basic') return 'До 5 пользователей'
  if (c === 'standard') return 'До 10 пользователей'
  return ''
}

export function aiBullet(plan) {
  const n = Number(plan?.max_ai_requests_per_period)
  if (!n || Number.isNaN(n)) return 'Запросы AI'
  return `${n} запросов AI`
}

export function trialPhrase(trialDays) {
  const d = Number(trialDays)
  if (!d || Number.isNaN(d)) return 'Пробный период'
  return `${d} ${d === 1 ? 'день' : d < 5 ? 'дня' : 'дней'} бесплатно`
}
