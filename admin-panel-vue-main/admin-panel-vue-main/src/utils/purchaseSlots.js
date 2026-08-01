import api from '@/api/axios'
import { payWithCloudPayments } from '@/composables/useBillingCloudPayments'

// Докупка слотов проекта (§8.6): пропорция за остаток периода через виджет
// CloudPayments. Возвращает результат оплаты ({ status: 'success' | 'cancelled' }).
export async function purchaseSlots(count = 1) {
  const { data } = await api.post('billing/slots/purchase', { count })
  return payWithCloudPayments({
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
}
