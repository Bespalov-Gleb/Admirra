<!-- Layout-level lifecycle only. Offers live in the sidebar and empty states. -->
<template></template>
<script setup>
import { watch, onBeforeUnmount, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import { useToaster } from '@/composables/useToaster'
import { useOnboarding } from '@/composables/useOnboarding'
import { reachGoal } from '@/utils/metrika'
import { trialDate } from '@/utils/onboarding'
import api from '@/api/axios'

const route = useRoute(), router = useRouter(), { user, getToken } = useAuth()
const { state, refresh, reset } = useOnboarding(), toaster = useToaster()
let generation = 0, timer, lastUser = null
async function update(force = false) {
  const revision = ++generation
  clearTimeout(timer)
  const id = user.value?.id
  if (id !== lastUser) { reset(); lastUser = id }
  let impersonation = false
  try { impersonation = JSON.parse(atob(getToken().split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))).impersonation === true } catch { /* no token */ }
  if (!id || impersonation) { reset(); return }
  await refresh(force === true || ['/project-card', '/project-rows'].includes(route.path))
  if (revision !== generation) return
  const data = state.value
  if (data.projects_count === 0 && ['/project-card', '/project-rows'].includes(route.path)) router.replace('/create')
  const deadline = data.active ? Math.min(new Date(data.expires_at).getTime(), new Date(data.trial_ends_at).getTime()) : new Date(data.trial_ends_at).getTime()
  const remaining = deadline - Date.now()
  if (remaining > 0) timer = setTimeout(() => update(true), Math.min(remaining + 100, remaining % 86400000 + 100))
  if (!data.active || data.toast_seen) return
  try {
    const { data: claim } = await api.post('billing/signup-discount/claim-display', null, { params: { kind: 'toast' } })
    if (id !== user.value?.id || !state.value.active || !claim.show) return
    state.value = { ...state.value, toast_seen: true }
    toaster.success(`Скидка 20% закреплена · на первую оплату, до ${trialDate(data.expires_at)}`, 5000)
    reachGoal('cabinet_connected_first')
  } catch { /* optional notification */ }
}
watch([() => user.value?.id, () => route.fullPath], () => update(), { immediate: true })
const invalidate = () => update(true)
const visible = () => { if (document.visibilityState === 'visible') update(true) }
onMounted(() => {
  window.addEventListener('admirra:payment-confirmed', invalidate)
  window.addEventListener('admirra:onboarding-changed', invalidate)
  document.addEventListener('visibilitychange', visible)
})
onBeforeUnmount(() => {
  generation++; clearTimeout(timer); reset()
  window.removeEventListener('admirra:payment-confirmed', invalidate)
  window.removeEventListener('admirra:onboarding-changed', invalidate)
  document.removeEventListener('visibilitychange', visible)
})
</script>
