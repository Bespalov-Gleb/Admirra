import api from '@/api/axios'
import { useOverflowModal } from '@/composables/useOverflowModal'
import { purchaseSlots } from '@/utils/purchaseSlots'
import { requiredProjectSlots } from '@/utils/projectSlots'

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
      const canConfirm = detail.reason === 'confirmation_required'
      const choice = await (canConfirm ? requestOverflowConfirm(detail) : openOverflowInfo(detail))
      if (choice === 'buy') {
        // Докупка слотов: после подтверждения сервером создаём обычным путём.
        const pay = await purchaseSlots(requiredProjectSlots(detail))
        if (pay?.status !== 'success') return null
        return await api.post('clients/', payload)
      }
      if (canConfirm && choice === 'confirm') {
        return await api.post('clients/', payload, { params: { confirm_overflow: true } })
      }
      if (canConfirm) api.post('billing/overflow/decline').catch(() => {})
      return null
    }
    throw e
  }
}
