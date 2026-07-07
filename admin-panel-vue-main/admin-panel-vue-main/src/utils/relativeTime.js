// Относительная метка времени синхронизации (ТЗ «Правки UI», п. 5).
// Градация: «только что» → «N мин назад» → «N ч назад» → «вчера в HH:MM» → «04 июл».
// Календарные границы («вчера») считаем по Москве — как и полная дата в тултипе.

const MS_MIN = 60 * 1000
const MS_HOUR = 60 * MS_MIN

const mskFormat = (ms, options) =>
  new Intl.DateTimeFormat('ru-RU', { timeZone: 'Europe/Moscow', ...options }).format(new Date(ms))

const mskDayKey = (ms) => mskFormat(ms, { year: 'numeric', month: '2-digit', day: '2-digit' })

export function relativeSyncLabel(tsMs, nowMs = Date.now()) {
  if (!Number.isFinite(tsMs)) return ''
  const diff = Math.max(0, nowMs - tsMs)
  if (diff < MS_MIN) return 'только что'
  if (diff < MS_HOUR) return `${Math.floor(diff / MS_MIN)} мин назад`
  if (mskDayKey(tsMs) === mskDayKey(nowMs)) return `${Math.floor(diff / MS_HOUR)} ч назад`
  if (mskDayKey(tsMs) === mskDayKey(nowMs - 24 * MS_HOUR)) {
    return `вчера в ${mskFormat(tsMs, { hour: '2-digit', minute: '2-digit' })}`
  }
  return mskFormat(tsMs, { day: '2-digit', month: 'short' }).replace(/\.$/, '')
}
