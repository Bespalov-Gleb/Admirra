export function trialDate(value) {
  const d = new Date(value)
  return value && Number.isFinite(d.getTime()) ? d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', timeZone: 'Europe/Moscow' }) : ''
}
export function canOffer(state) {
  return state.eligible === true && state.discount_state === 'not_granted' && state.cabinets_count === 0 && state.trial_days_left > 0
}
export function trialCard(state) {
  if (!state.trial_visible) return null
  const days = Math.max(0, Number(state.trial_days_left) || 0), expired = days === 0
  const n = days % 100, last = days % 10
  const noun = n >= 11 && n <= 14 ? 'дней' : last === 1 ? 'день' : last >= 2 && last <= 4 ? 'дня' : 'дней'
  const offer = canOffer(state), create = state.projects_count === 0 && !expired && !state.active
  const connect = !create && state.cabinets_count === 0 && !expired && !state.active
  return {
    title: expired ? 'Пробный период закончился' : 'Пробный период',
    days: expired ? trialDate(state.trial_ends_at) : `${last === 1 && n !== 11 ? 'остался' : 'осталось'} ${days} ${noun}`,
    text: expired ? 'Проекты и настройки сохранены' : state.active ? `Скидка 20% ваша — действует до ${trialDate(state.expires_at)}`
      : offer ? `${create ? 'Создайте проект и подключите' : 'Подключите'} кабинет — закрепим скидку 20% на первую оплату`
      : 'Проекты и отчёты доступны до окончания пробного периода',
    action: create ? 'Создать проект' : connect ? 'Подключить кабинет' : 'Выбрать тариф',
    path: create ? '/create' : connect ? '/integrations/wizard' : '/tariffs',
    offer, progress: Math.min(100, Math.max(0, (1 - days / Math.max(1, state.trial_total_days || days)) * 100)),
  }
}
