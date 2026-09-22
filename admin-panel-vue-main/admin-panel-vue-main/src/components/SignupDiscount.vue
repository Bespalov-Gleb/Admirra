<template>
  <div v-if="state.eligible" class="signup-strip" role="region" aria-label="Скидка на первую оплату">
    <span v-if="state.active">Пробный период до <b>{{ expiry }}</b> · скидка 20% на первую оплату</span>
    <span v-else>Подключите первый кабинет — получите <b>20% на первую оплату</b></span>
    <button type="button" @click="go">{{ state.active ? 'Выбрать тариф' : 'Подключить кабинет' }} →</button>
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

const route = useRoute(), router = useRouter(), { user, getToken } = useAuth(), toaster = useToaster()
const state = ref({}), dialog = ref(null), showRequest = ref(false)
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
.signup-strip { flex-shrink:0; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px 20px; padding:12px 24px; background:#eaf0fe; color:#334665; font-size:14px; border-bottom:1px solid #dce5f6 }
.signup-strip button, .signup-modal button { color:#2f6bea; font:inherit; cursor:pointer; background:none; border:0 }
.signup-strip button { font-weight:600; white-space:nowrap; min-height:32px }
.signup-modal { width:min(440px, calc(100vw - 32px)); max-height:calc(100dvh - 48px); overflow:auto; padding:26px; margin:auto; border:0; border-radius:14px; color:#1b2437; background:#fff; box-shadow:0 16px 64px #142b4940 }
.signup-modal::backdrop { background:#13223866 }
.signup-modal h2 { font-size:20px; font-weight:700; line-height:1.35; margin:0 0 12px }
.signup-modal p { font-size:14px; line-height:1.65; color:#5c6b84; margin:0 0 18px }
.signup-actions { display:flex; gap:18px; align-items:center; flex-wrap:wrap }
.signup-modal .signup-primary { border-radius:8px; padding:12px 16px; background:#2f6bea; color:#fff; font-weight:600 }
.signup-modal .signup-help { font-size:13px; margin:20px 0 0 }
.signup-request { user-select:text; white-space:pre-wrap }
:global(.dark) .signup-strip { background:#252e46; color:#dce5f6; border-color:#344058 }
:global(.dark) .signup-modal { background:#232637; color:#fff }
:global(.dark) .signup-modal p { color:#bec9dd }
@media(max-width:640px) { .signup-strip { padding:10px 16px; font-size:13px } }
</style>
