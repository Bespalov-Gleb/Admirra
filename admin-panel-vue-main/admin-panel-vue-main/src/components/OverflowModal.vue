<template>
  <Teleport to="body">
    <div v-if="state.open" class="ovf-backdrop" @click.self="onCancel" @keydown.esc.stop="onCancel" @keydown.tab="trapFocus">
      <section ref="dialog" class="ovf-modal" role="dialog" aria-modal="true" aria-labelledby="ovf-title" aria-describedby="ovf-description" tabindex="-1">
        <button class="ovf-close" type="button" aria-label="Закрыть" @click="onCancel">×</button>
        <span class="ovf-eyebrow">МЕСТА ДЛЯ ПРОЕКТОВ</span>
        <h4 id="ovf-title" class="ovf-title">Добавьте место для роста</h4>
        <p id="ovf-description" class="ovf-text">{{ state.detail?.message }}</p>
        <div class="ovf-usage">
          <span>Занято мест <strong>{{ state.detail?.current ?? '—' }}</strong></span>
          <span>В подписке <strong>{{ state.detail?.limit ?? '—' }}</strong></span>
        </div>
        <div class="ovf-offer" aria-live="polite" :aria-busy="loading">
          <p v-if="loading" class="ovf-note">Рассчитываем стоимость…</p>
          <template v-else-if="quote?.can_buy">
            <div class="ovf-offer__heading"><strong>Дополнительные места: {{ count }}</strong><span>{{ rub(quote.amount) }}</span></div>
            <p class="ovf-note">К оплате сейчас — за оставшуюся часть периода. После покупки доступно {{ quote.effective_limit_after }} мест.</p>
            <div class="ovf-renewal"><span>Следующее продление, включая тариф и все места</span><strong>{{ rub(quote.recurring_after) }} / {{ quote.billing_period === 'year' ? 'год' : 'мес' }}</strong></div>
          </template>
          <p v-else class="ovf-note">{{ error || quote?.message || 'Посмотрите тарифы с большим количеством проектов.' }}</p>
          <button v-if="error" class="ovf-link" type="button" @click="loadQuote">Повторить расчёт</button>
        </div>
        <p v-if="state.mode === 'confirm'" class="ovf-note ovf-grace">Можно пока использовать временный запас. До конца оплаченного периода нужно докупить места, сменить тариф или убрать лишние проекты.</p>
        <div class="ovf-actions">
          <button v-if="quote?.can_buy && !loading" class="ovf-btn ovf-btn--primary" type="button" @click="close('buy')">Оплатить {{ rub(quote.amount) }}</button>
          <button v-if="state.mode === 'confirm'" class="ovf-btn ovf-btn--ghost" type="button" @click="close('confirm')">Добавить пока без оплаты</button>
          <button class="ovf-btn ovf-btn--ghost" type="button" @click="goToPlans">Посмотреть тарифы</button>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/axios'
import { useOverflowModal } from '@/composables/useOverflowModal'
import { requiredProjectSlots } from '@/utils/projectSlots'

const { state, close } = useOverflowModal()
const router = useRouter()
const dialog = ref(null)
const quote = ref(null)
const loading = ref(false)
const error = ref('')
const count = computed(() => requiredProjectSlots(state.detail || {}))
const rub = (value) => new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(value)
let requestId = 0
async function loadQuote() {
  const id = ++requestId
  loading.value = true
  quote.value = null
  error.value = ''
  try {
    const { data } = await api.post('billing/slots/quote', { count: count.value })
    if (id === requestId) quote.value = data
  } catch {
    if (id === requestId) error.value = 'Не удалось рассчитать стоимость. Оплата не запускалась.'
  } finally {
    if (id === requestId) loading.value = false
  }
}
watch(() => state.detail, async (detail, _, onCleanup) => {
  if (!detail || !state.open) return
  const previousFocus = document.activeElement
  const previousOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
  onCleanup(() => {
    requestId++
    quote.value = null
    document.body.style.overflow = previousOverflow
    previousFocus?.focus?.()
  })
  loadQuote()
  await nextTick()
  if (state.open) dialog.value?.focus()
})
function trapFocus(event) {
  const buttons = [...(dialog.value?.querySelectorAll('button:not(:disabled)') || [])]
  const first = buttons[0]
  const last = buttons.at(-1)
  const active = document.activeElement
  if (event.shiftKey && (active === first || active === dialog.value)) {
    event.preventDefault(); last?.focus()
  } else if (!event.shiftKey && (active === last || active === dialog.value)) {
    event.preventDefault(); first?.focus()
  }
}
const onCancel = () => close(false)
const goToPlans = () => {
  close(false)
  router.push({ path: '/settings', query: { tab: 'tariff', view: 'plans' } })
}
</script>

<style scoped>
.ovf-backdrop { position: fixed; inset: 0; z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 16px; box-sizing: border-box; background: rgb(15 23 42 / 40%); backdrop-filter: blur(3px); }
.ovf-modal { position: relative; box-sizing: border-box; width: min(100%, 540px); max-height: calc(100dvh - 32px); overflow-y: auto; overscroll-behavior: contain; padding: 32px; border: 1px solid #e2e8f0; border-radius: 24px; background: #fff; color: #1e293b; box-shadow: 0 24px 80px rgb(15 23 42 / 18%); outline: none; overflow-wrap: anywhere; }
.ovf-close { position: absolute; top: 12px; right: 12px; width: 36px; height: 36px; border: 0; border-radius: 12px; background: #f1f5f9; color: #64748b; font-size: 26px; cursor: pointer; }
.ovf-eyebrow { display: block; padding-right: 25px; margin-bottom: 12px; color: #4169dd; font-size: 11px; letter-spacing: .09em; font-weight: 700; }
.ovf-title { margin: 0 20px 12px 0; font-size: 24px; line-height: 1.2; font-weight: 700; }
.ovf-text { margin: 0 0 20px; font-size: 14px; line-height: 1.55; color: #64748b; }
.ovf-usage { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
.ovf-usage > span { padding: 12px 16px; border-radius: 14px; background: #f6f8fb; font-size: 13px; color: #64748b; }
.ovf-usage strong { display: block; margin-top: 4px; font-size: 23px; color: #1e293b; }
.ovf-offer { padding: 18px; border: 1px solid #dbe5fb; border-radius: 16px; background: #f7faff; }
.ovf-offer__heading { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 8px; margin-bottom: 8px; font-size: 15px; }
.ovf-offer__heading > span { font-size: 24px; font-weight: 700; white-space: nowrap; }
.ovf-note { margin: 0; font-size: 13px; line-height: 1.55; color: #64748b; }
.ovf-renewal { display: flex; flex-wrap: wrap; gap: 6px 16px; justify-content: space-between; margin-top: 14px; padding-top: 14px; border-top: 1px solid #dbe5fb; font-size: 12px; line-height: 1.5; }
.ovf-renewal > span { flex: 1 1 180px; color: #64748b; }
.ovf-renewal strong { align-self: center; white-space: nowrap; }
.ovf-grace { margin-top: 16px; }
.ovf-actions { display: grid; gap: 8px; margin-top: 20px; }
.ovf-btn { box-sizing: border-box; width: 100%; min-height: 44px; padding: 12px 16px; border: 0; border-radius: 12px; font-size: 14px; line-height: 1.4; font-weight: 600; cursor: pointer; white-space: normal; }
.ovf-btn--primary { background: #3563e9; color: #fff; }
.ovf-btn--ghost { background: #f1f5f9; color: #334155; }
.ovf-link { margin-top: 8px; padding: 0; background: none; border: 0; color: #3563e9; font-size: 13px; cursor: pointer; }
button:focus-visible { outline: 2px solid #3563e9; outline-offset: 3px; }
:global(.dark .ovf-modal) { background: #182235; color: #e2e8f0; border-color: #334155; }
:global(.dark .ovf-offer), :global(.dark .ovf-usage > span), :global(.dark .ovf-btn--ghost), :global(.dark .ovf-close) { background: #243148; border-color: #3b4b68; color: #cbd5e1; }
:global(.dark .ovf-note), :global(.dark .ovf-text), :global(.dark .ovf-renewal > span) { color: #b0bed2; }
:global(.dark .ovf-usage strong) { color: #f1f5f9; }
@media (max-width: 480px) { .ovf-modal { padding: 24px 18px; border-radius: 20px; } .ovf-title { font-size: 22px; } .ovf-offer { padding: 14px; } }
</style>
