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

// Retrying the same preparation creates a new deadline. Completion is only a
// notification, never permission to start an AI/export/send action.
export function readinessKey(value) {
  return value?.id ? `${value.id}:${value.deadline || ''}` : ''
}

export function createReadinessCompletion() {
  const completed = new Set()
  return (value) => {
    const key = readinessKey(value)
    if (value?.status !== 'ready' || !key || completed.has(key)) return false
    completed.add(key)
    return true
  }
}

export function readinessMessage(state, context = 'action', pollError = false) {
  if (pollError) return 'Не удалось проверить готовность данных. Повторите проверку.'
  if (context === 'detector') {
    if (state?.status === 'waiting') return 'Догружаем недостающую историю. После проверки выводы детектора обновятся автоматически.'
    if (state?.status === 'ready') return 'История подготовлена. Можно обновить выводы детектора.'
    if (state?.status === 'held') return state.can_retry
      ? 'Подготовка истории не завершена. Можно повторить обновление.'
      : 'Не удалось подтвердить полноту истории. Проверьте подключение проекта.'
  }
  return state?.message || 'Ожидаем полные данные синхронизации. Повторите действие после обновления данных.'
}

export function detectorReadinessTitle(states) {
  if (states.some(state => state?.status === 'waiting')) return 'Подготавливаем историю для детектора'
  if (states.some(state => state?.status === 'held')) return 'Подготовка истории приостановлена'
  if (states.length && states.every(state => state?.status === 'ready')) return 'История для детектора готова'
  return 'Проверяем полноту данных для детектора'
}
