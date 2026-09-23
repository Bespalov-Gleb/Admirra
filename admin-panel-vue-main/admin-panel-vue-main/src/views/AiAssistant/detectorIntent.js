// One-use, same-tab handoff. A URL alone must never trigger a paid AI request.
const KEY = 'admirra-detector-intent-v1'
const TTL = 5 * 60 * 1000
let pending = null
function accountIdentity(token) {
  try { return JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))).sub || '' } catch { return '' }
}

export function detectorQuestion({ projectId, projectName, startDate, endDate, alert = {}, campaignName }) {
  const labels = { expenses: 'расходы', impressions: 'показы', clicks: 'клики', cpc: 'CPC', conversions: 'заявки', cpa: 'CPL' }
  const deviation = Number(alert.deviation_pct)
  const metric = labels[alert.metric] || alert.metric || 'показатели'
  return [
    `Разбери предупреждение детектора по проекту «${projectName || projectId}» (ID: ${projectId}).`,
    `Период: ${startDate} — ${endDate}.`,
    campaignName ? `Кампания: «${campaignName}».` : '',
    `Показатель: ${metric}${alert.deviation_pct != null && Number.isFinite(deviation) ? `, отклонение ${deviation > 0 ? '+' : ''}${deviation.toFixed(0)}%` : ''}.`,
    alert.hypothesis_text ? `Гипотеза детектора: ${alert.hypothesis_text}` : '',
    'Проверь данные этого проекта за указанный период с помощью доступных инструментов. Объясни возможные причины и предложи конкретные действия. Гипотеза детектора — не установленный факт; если данных недостаточно, скажи об этом.',
  ].filter(Boolean).join('\n')
}

export function createDetectorIntent(message, accountKey) {
  pending = { id: crypto.randomUUID(), message, accountKey: accountIdentity(accountKey), createdAt: Date.now() }
  try { sessionStorage.setItem(KEY, JSON.stringify(pending)) } catch { /* memory fallback */ }
  return { path: '/ai', query: { detector: pending.id } }
}

export function consumeDetectorIntent(id, accountKey) {
  let intent = pending
  try { intent = JSON.parse(sessionStorage.getItem(KEY)) || intent } catch { /* memory fallback */ }
  if (!intent || intent.id !== id) return null
  pending = null
  try { sessionStorage.removeItem(KEY) } catch { /* memory fallback */ }
  if (intent.accountKey !== accountIdentity(accountKey) || Date.now() - intent.createdAt > TTL || Date.now() < intent.createdAt) return null
  return typeof intent.message === 'string' ? intent.message : null
}
