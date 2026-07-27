const moscowFormatter = new Intl.DateTimeFormat('ru-RU', {
  timeZone: 'Europe/Moscow',
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

export const number = (value = 0) => new Intl.NumberFormat('ru-RU').format(Number(value) || 0)
export const money = (value = 0, currency = 'RUB') =>
  new Intl.NumberFormat('ru-RU', { style: 'currency', currency, maximumFractionDigits: 0 }).format(Number(value) || 0)
export const usd = (value = 0) =>
  new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(Number(value) || 0)
export const percent = (value = 0) => `${new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 1 }).format(Number(value) || 0)}%`
export const moscowDateTime = (value) => (value ? moscowFormatter.format(new Date(value)).replace(',', '') : '—')

export function relativeTime(value) {
  if (!value) return '—'
  const diff = Math.round((new Date(value).getTime() - Date.now()) / 1000)
  const abs = Math.abs(diff)
  const formatter = new Intl.RelativeTimeFormat('ru', { numeric: 'auto' })
  if (abs < 60) return formatter.format(diff, 'second')
  if (abs < 3600) return formatter.format(Math.round(diff / 60), 'minute')
  if (abs < 86400) return formatter.format(Math.round(diff / 3600), 'hour')
  if (abs < 604800) return formatter.format(Math.round(diff / 86400), 'day')
  return moscowDateTime(value)
}

export const planLabel = (code) =>
  ({ start: 'Старт', basic: 'Базовый', standard: 'Стандарт', white_label: 'White Label' })[code] || code || 'Без тарифа'

export const roleLabel = (role) =>
  ({ SUPERADMIN: 'Super Admin', ADMIN: 'Super Admin', STAFF_MANAGER: 'Менеджер', SUPPORT: 'Менеджер', SEO: 'SEO' })[role] || role

export const platformLabel = (platform) =>
  ({ YANDEX_DIRECT: 'Яндекс Директ', VK_ADS: 'VK Реклама', AVITO_ADS: 'Авито Реклама' })[platform] || platform
