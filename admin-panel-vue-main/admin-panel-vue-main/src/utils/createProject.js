import api from '@/api/axios'
import { useOverflowModal } from '@/composables/useOverflowModal'

const { requestOverflowConfirm, openOverflowInfo } = useOverflowModal()

// Создание проекта с обработкой границы тарифа (§8.5). Возвращает ответ axios при
// успехе или null, если пользователь отменил / упёрся в исчерпанный запас.
// Бросает исключение только на «настоящих» ошибках (не 409-превышение).
export async function createProjectWithOverflow(payload) {
  try {
    return await api.post('clients/', payload)
  } catch (e) {
    const status = e?.response?.status
    const detail = e?.response?.data?.detail
    if (status === 409 && detail && typeof detail === 'object' && detail.reason) {
      if (detail.reason === 'confirmation_required') {
        const confirmed = await requestOverflowConfirm(detail)
        if (!confirmed) return null
        // Повторяем с флагом согласия — бэкенд создаёт проект в счёт запаса.
        return await api.post('clients/', payload, { params: { confirm_overflow: true } })
      }
      // Запас исчерпан или блок второго продления — только апгрейд.
      await openOverflowInfo(detail)
      return null
    }
    throw e
  }
}
