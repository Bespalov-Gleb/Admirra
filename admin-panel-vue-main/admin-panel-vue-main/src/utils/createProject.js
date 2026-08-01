import api from '@/api/axios'
import { useOverflowModal } from '@/composables/useOverflowModal'
import { purchaseSlots } from '@/utils/purchaseSlots'

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
        const choice = await requestOverflowConfirm(detail)
        if (choice === 'buy') {
          // Докупка слота: после успешной оплаты лимит вырос — создаём обычным путём.
          const pay = await purchaseSlots(1)
          if (pay?.status !== 'success') return null
          return await api.post('clients/', payload)
        }
        if (choice === 'confirm') {
          // Добавить в счёт запаса — повтор с флагом согласия.
          return await api.post('clients/', payload, { params: { confirm_overflow: true } })
        }
        return null
      }
      // Запас исчерпан или блок второго продления — только апгрейд.
      await openOverflowInfo(detail)
      return null
    }
    throw e
  }
}
