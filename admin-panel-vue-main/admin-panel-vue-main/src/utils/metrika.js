// Яндекс.Метрика — счётчик 109911357. Хелпер для целей (reachGoal),
// SPA-хитов на смену роута, получения ClientID и захвата yclid.
import api from '@/api/axios'

export const YM_COUNTER_ID = 109911357

function callYm(...args) {
  if (typeof window !== 'undefined' && typeof window.ym === 'function') {
    try {
      window.ym(YM_COUNTER_ID, ...args)
    } catch (e) {
      // не роняем приложение из-за аналитики
    }
  }
}

// Просмотр страницы при клиентском переходе (SPA). Первую загрузку счётчик
// считает сам — её отправлять не нужно (см. router.afterEach).
export function metrikaHit(url) {
  callYm('hit', url || window.location.href, { referer: document.referrer })
}

// Достижение цели. params — третий аргумент reachGoal (срезы plan/billing/method,
// сумма order_price/currency для денежных целей).
export function reachGoal(goal, params) {
  if (!goal) return
  if (params && Object.keys(params).length) callYm('reachGoal', String(goal), params)
  else callYm('reachGoal', String(goal))
}

// ClientID Метрики (асинхронно через колбэк) → Promise<string|null>.
export function getClientID() {
  return new Promise((resolve) => {
    if (typeof window === 'undefined' || typeof window.ym !== 'function') {
      return resolve(null)
    }
    let settled = false
    const done = (v) => { if (!settled) { settled = true; resolve(v) } }
    try {
      window.ym(YM_COUNTER_ID, 'getClientID', (clientID) => done(clientID || null))
    } catch (e) {
      done(null)
    }
    setTimeout(() => done(null), 3000) // не ждём вечно
  })
}

// yclid — клик из Яндекс.Директа. Ловим из URL при первом заходе и храним,
// чтобы потом привязать серверную офлайн-конверсию к рекламному источнику.
const YCLID_KEY = 'ym_yclid'

export function captureYclid() {
  try {
    const yclid = new URL(window.location.href).searchParams.get('yclid')
    if (yclid && !localStorage.getItem(YCLID_KEY)) {
      localStorage.setItem(YCLID_KEY, yclid)
    }
  } catch (e) { /* ignore */ }
}

export function getStoredYclid() {
  try {
    return localStorage.getItem(YCLID_KEY) || null
  } catch (e) {
    return null
  }
}

// Цели по созданию проекта с дедупликацией «первого раза» по счётчику с бэка:
// 1-й проект → project_created, 2-й → second_project.
export function trackProjectCreated(ownerProjectCount) {
  const n = Number(ownerProjectCount)
  if (n === 1) trackFirstMilestone('project_created', 'project_created')
  else if (n === 2) trackFirstMilestone('second_project', 'second_project')
}

// Цель «первого раза» через серверную «веху» (дедупликация на бэке).
// goal сработает только при первом достижении на аккаунт.
export async function trackFirstMilestone(name, goal) {
  try {
    const { data } = await api.post('auth/metrika/milestone', { name })
    if (data && data.first) reachGoal(goal || name)
  } catch (e) {
    // аналитика не критична
  }
}

// Отправить ClientID Метрики + yclid на бэкенд (привязать к аккаунту для
// серверных офлайн-конверсий). Вызывать после успешной аутентификации.
// Бэкенд фиксирует первое значение, повторные вызовы безопасны.
export async function sendMetrikaIdentity() {
  try {
    const clientId = await getClientID()
    const yclid = getStoredYclid()
    if (!clientId && !yclid) return
    await api.post('auth/metrika/identity', { client_id: clientId, yclid })
  } catch (e) {
    // аналитика не должна мешать входу
  }
}
