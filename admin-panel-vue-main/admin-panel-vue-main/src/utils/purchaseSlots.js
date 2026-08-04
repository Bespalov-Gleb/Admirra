import api from '@/api/axios'
import { payWithCloudPayments } from '@/composables/useBillingCloudPayments'

// Докупка слотов проекта (§8.6): пропорция за остаток периода через виджет
// CloudPayments. Возвращает результат оплаты ({ status: 'success' | 'cancelled' }).
export async function purchaseSlots(count = 1) {
  const { data } = await api.post('billing/slots/purchase', { count })
  const result = await payWithCloudPayments({
    public_id: data.public_id,
    description: data.description,
    amount: data.amount,
    currency: data.currency,
    account_id: data.account_id,
    email: data.email,
    plan_code: data.plan_code,
    billing_period: data.billing_period,
    receipt: data.receipt || null,
    invoice_id: data.invoice_id || null,
    purpose: data.purpose,        // 'slot_purchase' → маркер для webhook
    slot_count: data.slot_count,
  })
  if (result?.status !== 'success') return result

  // Успех виджета наступает раньше серверного webhook. Не даём вызывающему коду
  // сразу повторить создание проекта со старым лимитом: ждём подтверждения БД.
  const expected = Number(data.expected_purchased_slots || 0)
  if (expected > 0) {
    const deadline = Date.now() + 25000
    while (Date.now() < deadline) {
      try {
        const { data: subscription } = await api.get('billing/subscription')
        if (Number(subscription?.purchased_slots || 0) >= expected) {
          return { ...result, confirmed: true }
        }
      } catch { /* повторим */ }
      await new Promise((resolve) => setTimeout(resolve, 1200))
    }
    throw new Error('Оплата прошла, но подтверждение ещё обрабатывается. Проект можно добавить через несколько секунд.')
  }
  return result
}
