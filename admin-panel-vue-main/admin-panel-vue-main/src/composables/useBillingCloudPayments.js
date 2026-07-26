const SCRIPT_URL = 'https://widget.cloudpayments.ru/bundles/cloudpayments.js'

let scriptPromise = null

function loadCloudPaymentsScript() {
  if (typeof window === 'undefined') {
    return Promise.reject(new Error('Нет окна браузера'))
  }
  if (window.cp?.CloudPayments) {
    return Promise.resolve()
  }
  if (scriptPromise) return scriptPromise
  scriptPromise = new Promise((resolve, reject) => {
    const s = document.createElement('script')
    s.src = SCRIPT_URL
    s.async = true
    s.onload = () => resolve()
    s.onerror = () => reject(new Error('Не удалось загрузить виджет оплаты'))
    document.head.appendChild(s)
  })
  return scriptPromise
}

function normalizeAmount(amount) {
  const n = Number(amount)
  if (Number.isNaN(n) || n <= 0) {
    throw new Error('Некорректная сумма платежа')
  }
  return Math.round(n * 100) / 100
}

/**
 * Одностадийная оплата + опционально рекуррент (подписка на стороне CloudPayments).
 * plan_code попадает в JsonData уведомлений; рекуррент — в data.cloudPayments.recurrent.
 * @returns {Promise<{ status: 'success' | 'cancelled' }>}
 */
export async function payWithCloudPayments(payload) {
  await loadCloudPaymentsScript()
  const CP = window.cp?.CloudPayments
  if (!CP) {
    throw new Error('Виджет CloudPayments недоступен')
  }
  const widget = new CP()

  const data = {
    plan_code: payload.plan_code,
    billing_period: payload.billing_period || 'month',
  }
  if (payload.recurrent?.interval) {
    data.cloudPayments = {
      recurrent: {
        interval: payload.recurrent.interval,
        period: Number(payload.recurrent.period) || 1,
      },
    }
  }
  // Онлайн-чек («Cloud Чеки»/CloudKassir): по документации CP чек передаётся в
  // data.cloudPayments.CustomerReceipt (разовый платёж) и recurrent.customerReceipt
  // (автосписания) — https://developers.cloudpayments.ru/#format-peredachi-dannyh-dlya-onlayn-cheka
  // Раньше чек клали в options.receipt — виджет его игнорировал, чеки не формировались.
  if (payload.receipt && typeof payload.receipt === 'object') {
    data.cloudPayments = data.cloudPayments || {}
    data.cloudPayments.CustomerReceipt = payload.receipt
    if (data.cloudPayments.recurrent) {
      data.cloudPayments.recurrent.customerReceipt = payload.receipt
    }
  }

  const options = {
    publicId: payload.public_id,
    description: payload.description,
    amount: normalizeAmount(payload.amount),
    currency: payload.currency || 'RUB',
    accountId: payload.account_id,
    email: payload.email || '',
    language: 'ru-RU',
    skin: 'classic',
    data,
  }
  // Идентификатор заказа с бэкенда. Возвращается в вебхуке как InvoiceId и
  // позволяет связать платёж с намерением: без него повторный клик создавал
  // полностью независимый платёж, который нечем было опознать.
  if (payload.invoice_id) {
    options.invoiceId = payload.invoice_id
  }

  return new Promise((resolve, reject) => {
    let finished = false
    const finish = (fn) => {
      if (finished) return
      finished = true
      fn()
    }

    widget.pay(
      'charge',
      options,
      {
        onSuccess: () => finish(() => resolve({ status: 'success' })),
        onFail: (reason) => {
          const r =
            reason === null || reason === undefined
              ? ''
              : String(reason).trim().toLowerCase()
          if (
            !r ||
            r === 'undefined' ||
            r.includes('cancel') ||
            r.includes('отмен')
          ) {
            finish(() => resolve({ status: 'cancelled' }))
          } else {
            finish(() =>
              reject(new Error(typeof reason === 'string' ? reason : 'Оплата не выполнена'))
            )
          }
        },
        onComplete: (paymentResult) => {
          if (finished || !paymentResult) return
          if (paymentResult.type === 'cancel') {
            finish(() => resolve({ status: 'cancelled' }))
          }
        },
      }
    )
  })
}
