<template>
  <div v-if="state.eligible && !stripHidden" class="signup-strip" role="region" aria-label="Скидка на первую оплату">
    <span class="signup-strip__badge" aria-hidden="true">−20%</span>
    <div class="signup-strip__copy">
      <strong>{{ state.active ? 'Ваша скидка 20% готова' : 'Первый кабинет — первая скидка' }}</strong>
      <span>{{ state.active ? `На первую оплату тарифа до ${expiry}.` : 'Подключите рекламный кабинет и получите 20% на первую оплату.' }}</span>
    </div>
    <button class="signup-strip__action" type="button" @click="go">
      {{ state.active ? 'Выбрать тариф' : 'Подключить кабинет' }}
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" /></svg>
    </button>
    <button class="signup-strip__close" type="button" aria-label="Скрыть плашку скидки" title="Скрыть плашку — скидка останется в тарифах" @click="dismissStrip">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" /></svg>
    </button>
  </div>
  <Teleport to="body">
    <dialog ref="dialog" class="signup-modal" @cancel="close" @click="backdrop">
      <template v-if="showRequest">
        <h2>Текст запроса для клиента</h2>
        <p class="signup-request">{{ requestText }}</p>
        <div class="signup-actions"><button class="signup-primary" type="button" @click="copy">Скопировать</button><button type="button" @click="showRequest = false">Назад</button></div>
      </template>
      <template v-else>
        <h2>Подключите первый кабинет — получите 20%</h2>
        <p>Скидка на первую оплату любого доступного онлайн тарифа. Данные подтянутся за несколько минут, и отчёт можно будет отправить клиенту.</p>
        <div class="signup-actions"><button class="signup-primary" type="button" @click="go">Подключить кабинет</button><button type="button" @click="close">Позже</button></div>
        <p class="signup-help">Нет доступа к кабинету клиента? <button type="button" @click="showRequest = true">Текст запроса для клиента</button></p>
      </template>
    </dialog>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch, onBeforeUnmount, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import { useToaster } from '@/composables/useToaster'
import api from '@/api/axios'
import { reachGoal } from '@/utils/metrika'
import { discountStripKey, isDiscountStripHidden, hideDiscountStrip } from '@/utils/discountStrip'

const route = useRoute(), router = useRouter(), { user, getToken } = useAuth(), toaster = useToaster()
const state = ref({}), dialog = ref(null), showRequest = ref(false)
const stripHidden = ref(false)
const stripKey = computed(() => discountStripKey(user.value?.id, state.value))
function stripStorage() { try { return window.localStorage } catch { return null } }
watch(stripKey, key => { stripHidden.value = isDiscountStripHidden(stripStorage(), key) }, { immediate: true })
function dismissStrip() {
  stripHidden.value = true
  hideDiscountStrip(stripStorage(), stripKey.value)
}
const expiry = computed(() => state.value.expires_at ? new Date(state.value.expires_at).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', timeZone: 'Europe/Moscow' }) : '')
const requestText = 'Здравствуйте! Чтобы настроить аналитику и отчёты по вашей рекламе в AdMirra, предоставьте мне доступ к рекламному кабинету и счётчику Яндекс Метрики, если он используется. Для VK Рекламы я могу отправить отдельную ссылку подключения. Пароль и коды подтверждения передавать не нужно — доступ выдаётся через настройки рекламной системы.'
let generation = 0, expiryTimer
function close() { dialog.value?.close(); showRequest.value = false }
function backdrop(event) { if (event.target === dialog.value && (event.offsetX < 0 || event.offsetX > dialog.value.clientWidth || event.offsetY < 0 || event.offsetY > dialog.value.clientHeight)) close() }
function go() {
  reachGoal('discount_modal_clicked', { placement: dialog.value?.open ? 'modal' : 'strip' })
  close()
  router.push(state.value.active ? '/tariffs' : '/integrations/wizard')
}
async function copy() {
  try { await navigator.clipboard.writeText(requestText); toaster.success('Текст скопирован') }
  catch { toaster.info('Выделите текст и скопируйте его вручную') }
}
async function refresh() {
  const revision = ++generation
  clearTimeout(expiryTimer)
  let impersonation = false
  try { impersonation = JSON.parse(atob(getToken().split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))).impersonation === true } catch { /* no valid token */ }
  if (!user.value?.id || impersonation) { state.value = {}; close(); return }
  try {
    const { data } = await api.get('billing/signup-discount')
    if (revision !== generation) return
    state.value = data
    if (!data.eligible) { close(); return }
    const remaining = new Date(data.expires_at).getTime() - Date.now()
    if (remaining > 0) expiryTimer = setTimeout(refresh, Math.min(remaining + 100, 2147483647))
    const kind = data.active && !data.toast_seen ? 'toast' : !data.modal_seen && !data.active ? 'modal' : null
    if (!kind) return
    const { data: claim } = await api.post('billing/signup-discount/claim-display', null, { params: { kind } })
    if (revision !== generation || !claim.show) return
    if (kind === 'toast') {
      toaster.success(`Скидка 20% ваша — действует до ${expiry.value}`)
      reachGoal('cabinet_connected_first')
    } else {
      await nextTick(); dialog.value?.showModal()
      reachGoal('discount_modal_shown')
    }
  } catch { /* offer must not block navigation */ }
}
watch([() => user.value, () => route.fullPath], refresh, { immediate: true })
onMounted(() => window.addEventListener('admirra:payment-confirmed', refresh))
onBeforeUnmount(() => { generation++; clearTimeout(expiryTimer); close(); window.removeEventListener('admirra:payment-confirmed', refresh) })
</script>

<style scoped>
.signup-strip { flex-shrink:0; display:grid; grid-template-columns:auto minmax(0,1fr) auto auto; align-items:center; gap:16px; padding:12px 24px; background:#f8faff; color:#263650; border-bottom:1px solid #e3e9f3 }
.signup-strip button, .signup-modal button { color:#2f6bea; font:inherit; cursor:pointer; background:none; border:0 }
.signup-strip__badge { display:grid; place-items:center; min-width:56px; height:40px; padding:0 8px; border:1px solid #dce6fd; border-radius:12px; background:#edf2ff; color:#315fc5; font-size:16px; font-weight:700; letter-spacing:-0.4px }
.signup-strip__copy { display:grid; gap:3px; min-width:0; line-height:1.45; overflow-wrap:anywhere }
.signup-strip__copy strong { font-size:14px; font-weight:600 }
.signup-strip__copy > span { color:#617087; font-size:13px }
.signup-strip .signup-strip__action { display:inline-flex; align-items:center; justify-content:center; gap:10px; min-height:40px; padding:8px 14px; border:1px solid #d7e1f3; border-radius:10px; background:#fff; color:#315fc5; font-size:13px; font-weight:600; line-height:1.4; text-align:left }
.signup-strip__action svg { flex-shrink:0 }
.signup-strip .signup-strip__close { display:grid; place-items:center; width:40px; height:40px; padding:0; border-radius:10px; color:#66758a }
.signup-strip button { transition:background-color .15s ease, border-color .15s ease }
.signup-strip .signup-strip__action:hover { background:#edf2ff; border-color:#b7caf3 }
.signup-strip .signup-strip__close:hover { background:#eaf0f8; color:#263650 }
.signup-strip button:focus-visible { outline:2px solid #315fc5; outline-offset:3px }
.signup-modal { width:min(440px, calc(100vw - 32px)); max-height:calc(100dvh - 48px); overflow:auto; padding:26px; margin:auto; border:0; border-radius:14px; color:#1b2437; background:#fff; box-shadow:0 16px 64px #142b4940 }
.signup-modal::backdrop { background:#13223866 }
.signup-modal h2 { font-size:20px; font-weight:700; line-height:1.35; margin:0 0 12px }
.signup-modal p { font-size:14px; line-height:1.65; color:#5c6b84; margin:0 0 18px }
.signup-actions { display:flex; gap:18px; align-items:center; flex-wrap:wrap }
.signup-modal .signup-primary { border-radius:8px; padding:12px 16px; background:#2f6bea; color:#fff; font-weight:600 }
.signup-modal .signup-help { font-size:13px; margin:20px 0 0 }
.signup-request { user-select:text; white-space:pre-wrap }
:global(.dark .signup-strip) { background:#232b3c; color:#edf2fb; border-color:#354056 }
:global(.dark .signup-strip__copy > span) { color:#b6c4da }
:global(.dark .signup-strip__badge) { background:#2d3c5b; border-color:#415578; color:#cedeff }
:global(.dark .signup-strip .signup-strip__action) { background:#2b3850; border-color:#455573; color:#d3e2ff }
:global(.dark .signup-strip .signup-strip__close) { color:#bdcbe0 }
:global(.dark .signup-strip button:hover) { background:#354660 }
:global(.dark .signup-strip button:focus-visible) { outline-color:#a7c4ff }
:global(.dark .signup-modal) { background:#232637; color:#fff }
:global(.dark .signup-modal p) { color:#bec9dd }
@media(max-width:640px) {
  .signup-strip { grid-template-columns:minmax(0,1fr) 40px; gap:8px 12px; padding:12px 16px }
  .signup-strip__badge { display:none }
  .signup-strip__copy { grid-column:1; grid-row:1 }
  .signup-strip .signup-strip__close { grid-column:2; grid-row:1; align-self:start }
  .signup-strip .signup-strip__action { grid-column:1; grid-row:2; justify-self:start; min-height:44px }
}
@media(prefers-reduced-motion:reduce) { .signup-strip button { transition:none } }
</style>
