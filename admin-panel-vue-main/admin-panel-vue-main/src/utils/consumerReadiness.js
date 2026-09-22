export function consumerReadiness(value, now = Date.now()) {
  if (value === 'waiting_data') return { status: 'held', can_retry: false }
  if (!value || typeof value !== 'object' || !['waiting', 'held', 'ready'].includes(value.status)) return null
  const state = { ...value }
  if (state.status === 'waiting') {
    const deadline = Date.parse(state.deadline)
    if (!state.id || !Number.isFinite(deadline) || deadline <= now) {
      state.status = 'held'
      state.can_retry = Boolean(state.id)
      state.message = 'Время ожидания истекло. Можно повторить подготовку данных.'
    }
  }
  return state
}
