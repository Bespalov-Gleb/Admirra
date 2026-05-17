import api from '../api/axios'

/**
 * Стандартная привязка Telegram: открывается t.me/bot?start=token, пользователь жмёт Start.
 */
export function useTelegramReportLink() {
  const openTelegramBotForLinking = async () => {
    const { data } = await api.post('auth/telegram/link')
    const url = data?.deep_link
    if (!url) throw new Error('Нет ссылки')
    const w = window.open(url, '_blank', 'noopener,noreferrer')
    if (!w) {
      try {
        await navigator.clipboard?.writeText(url)
        return { ...data, copied_to_clipboard: true }
      } catch {
        throw new Error('Браузер заблокировал открытие новой вкладки')
      }
    }
    return data
  }

  return { openTelegramBotForLinking }
}
