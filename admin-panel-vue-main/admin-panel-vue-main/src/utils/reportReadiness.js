export function reportReadiness(delivery) {
  const state = delivery?.data_readiness
  if (!state || !['waiting', 'held'].includes(state.status)) return null
  const waiting = state.status === 'waiting'
  const reasons = {
    deadline_expired: 'Данные не успели обновиться. Можно повторить подготовку; отчёт не будет отправлен автоматически.',
    schedule_changed: 'Настройки расписания изменились. Проверьте получателей и создайте новый отчёт.',
    schedule_or_account_changed: 'Расписание или доступ к аккаунту изменились. Проверьте настройки.',
    schedule_unavailable: 'Расписание отключено или недоступно. Проверьте настройки отчёта.',
    scope_unavailable: 'Проект или источник данных недоступен. Проверьте доступ и подключение кабинета.',
    scope_unavailable_or_too_large: 'Проверьте доступ к проектам или выберите меньший набор проектов.',
    no_statistical_sources: 'Подключите рекламный кабинет или счётчик со статистикой.',
    unverified_snapshot: 'Для этого старого снимка нет подтверждения актуальности. Создайте новый отчёт.',
    invalid_goal_settings: 'Проверьте выбранные цели в настройках интеграции.',
    source_limit: 'Слишком много источников для одного отчёта. Выберите меньший набор проектов.',
  }
  return {
    waiting,
    title: waiting ? 'Ожидаем данные' : 'Нужна проверка',
    detail: waiting
      ? 'Обновляем недостающие даты, включая период сравнения. Отчёт пока не отправляется.'
      : reasons[state.reason] || 'Подготовка приостановлена. Проверьте интеграции и настройки отчёта.',
    canRetry: !waiting && state.can_retry === true,
    deadline: state.deadline || null,
  }
}
