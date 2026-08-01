// Линейка §4 ТЗ экономики. Реальные значения приходят из /billing/plans;
// FALLBACK — только на случай недоступности API. Коды: start/agency/pro/white_label.
export const FALLBACK_PLANS = {
  start: {
    code: 'start', name: 'Старт', price_rub: 2900, price_year_rub: 29000,
    max_projects: 3, max_cabinets: 9, max_users: 2,
    max_ai_requests_per_period: 50, trial_days: 14, recommended: false, white_label: false,
  },
  agency: {
    code: 'agency', name: 'Агентство', price_rub: 6900, price_year_rub: 69000,
    max_projects: 10, max_cabinets: 30, max_users: 6,
    max_ai_requests_per_period: 250, trial_days: 14, recommended: true, white_label: false,
  },
  pro: {
    code: 'pro', name: 'Про', price_rub: 13900, price_year_rub: 139000,
    max_projects: 25, max_cabinets: 75, max_users: 15,
    max_ai_requests_per_period: 700, trial_days: 14, recommended: false, white_label: false,
  },
  white_label: {
    code: 'white_label', name: 'White Label', price_rub: 25900, price_year_rub: 0,
    max_projects: 100, max_cabinets: 300, max_users: 50,
    max_ai_requests_per_period: 2000, trial_days: 14, recommended: false, white_label: true,
  },
}

export function normalizePlansFromApi(rows) {
  const by = {}
  for (const p of rows || []) {
    if (p?.code) by[String(p.code).toLowerCase()] = p
  }
  // Старые коды из БД/кэша (basic/standard) на всякий случай маппим на новые.
  return {
    start: by.start || FALLBACK_PLANS.start,
    agency: by.agency || by.basic || FALLBACK_PLANS.agency,
    pro: by.pro || by.standard || FALLBACK_PLANS.pro,
    white_label: by.white_label || FALLBACK_PLANS.white_label,
  }
}

/** Годовая цена из месячной: −17% (§4.1). Фолбэк, если бэк не прислал price_year_rub. */
export function yearlyPriceFromMonthly(monthlyRub) {
  const m = Number(monthlyRub)
  if (Number.isNaN(m) || m < 0) return 0
  return Math.round(m * 12 * 0.83)
}

/** Годовая цена тарифа: сначала точная из бэка, иначе формула. */
export function yearlyPriceOfPlan(plan) {
  const y = Number(plan?.price_year_rub)
  if (y > 0) return y
  return yearlyPriceFromMonthly(plan?.price_rub)
}

export function formatRub(n) {
  const v = Number(n)
  if (Number.isNaN(v)) return '—'
  return `${new Intl.NumberFormat('ru-RU').format(v)} ₽`
}

export function perProjectLine(priceRub, maxProjects) {
  const max = Number(maxProjects)
  const price = Number(priceRub)
  if (!max || Number.isNaN(price)) return ''
  return `${Math.round(price / max)} руб/проект`
}

export function projectBullet(plan) {
  const n = Number(plan?.max_projects)
  if (!n || Number.isNaN(n)) return 'Проекты'
  if (n <= 1) return '1 проект'
  return `До ${n} проектов`
}

// §3: гейтинг каналов отменён — все каналы на всех тарифах.
export function channelsBullet() {
  return 'Все доступные подключения'
}

export function usersBullet(plan) {
  const n = Number(plan?.max_users ?? plan?.max_staff)
  if (!n || Number.isNaN(n)) return ''
  return n === 1 ? '1 пользователь' : `До ${n} пользователей`
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
