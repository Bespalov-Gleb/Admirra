// Яндекс.Метрика — счётчик 109911357. Хелпер для целей (reachGoal),
// SPA-хитов на смену роута, получения ClientID и захвата yclid.
import api from '@/api/axios'
import { trackPurchase as sendPurchase } from './purchaseAnalytics'
import { createOAuthTracker } from './oauthAnalytics'

export const trackPurchase = payment => sendPurchase(payment, { goalIds: {
  payment_success: import.meta.env.VITE_YM_PAYMENT_SUCCESS_GOAL_ID,
  plan_upgrade: import.meta.env.VITE_YM_PLAN_UPGRADE_GOAL_ID,
} })

export const YM_COUNTER_ID = 109911357

function callYm(...args) {
  if (typeof window !== 'undefined' && typeof window.ym === 'function') {
    try {
      window.ym(YM_COUNTER_ID, ...args)
      return true
    } catch (e) {
      // не роняем приложение из-за аналитики
    }
  }
  return false
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
  if (params && Object.keys(params).length) return callYm('reachGoal', String(goal), params)
  return callYm('reachGoal', String(goal))
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
export async function trackFirstMilestone(name, goal, params) {
  try {
    const { data } = await api.post('auth/metrika/milestone', { name })
    if (data && data.first) reachGoal(goal || name, params)
  } catch (e) {
    // аналитика не критична
  }
}

// Отправить ClientID Метрики + yclid на бэкенд (привязать к аккаунту для
// серверных офлайн-конверсий). Вызывать после успешной аутентификации.
// Бэкенд фиксирует первое значение, повторные вызовы безопасны.
export async function sendMetrikaIdentity(accessToken) {
  try {
    const clientId = await getClientID()
    const yclid = getStoredYclid()
    if (!clientId && !yclid) return
    const payload = { client_id: clientId, yclid }
    if (accessToken) {
      // MAX completes before the caller installs its new token. Do not let the
      // shared Axios interceptor replace it with the previously signed-in user.
      await fetch('/api/auth/metrika/identity', { method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
        body: JSON.stringify(payload), signal: AbortSignal.timeout(5000) })
    } else await api.post('auth/metrika/identity', payload)
  } catch (e) {
    // аналитика не должна мешать входу
  }
}

export const trackOAuthCompletion = createOAuthTracker({
  goal: reachGoal, identity: sendMetrikaIdentity,
  storage: { getItem: key => sessionStorage.getItem(key), setItem: (key, value) => sessionStorage.setItem(key, value) },
})
