// Transport/provider errors are not decisions to reject a customer lead.
export function diagnosticError(error) {
  const status = Number(error?.response?.status)
  const rawDelay = Number(error?.response?.headers?.['retry-after'])
  const delay = Number.isFinite(rawDelay) && rawDelay > 0
    ? Math.min(1440, Math.ceil(rawDelay / 60)) : null
  if (status === 429) return delay
    ? `Лимит проверок исчерпан. Повторите через ${delay} мин.`
    : 'Лимит проверок исчерпан. Повторите позже.'
  if (status === 503) return 'Сервис проверки временно недоступен. Попробуйте позже.'
  if (status === 401 || status === 403) return 'Нет доступа к проверке. Проверьте авторизацию.'
  if (status === 404) return 'Проект недоступен. Обновите список проектов.'
  if (status === 422) return 'Проверьте формат и длину введённых данных.'
  return 'Не удалось завершить проверку. Проверьте соединение и повторите запрос.'
}
