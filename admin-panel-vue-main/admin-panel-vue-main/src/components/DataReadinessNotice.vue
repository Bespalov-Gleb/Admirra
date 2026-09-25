<template>
  <div v-if="state && !(quietWaiting && state.status === 'waiting' && !pollError)" class="data-readiness" :class="{ 'data-readiness--inline': inline }" role="status" aria-live="polite">
    <p>{{ message }}</p>
    <small v-if="state.status === 'waiting' && context !== 'detector'">Запрос к ИИ и отправка отчёта автоматически не запускаются.</small>
    <button v-if="pollError" type="button" :disabled="busy" @click="poll">Проверить статус</button>
    <button v-else-if="state.status === 'ready'" type="button" :disabled="busy" @click="$emit('ready-action')">{{ actionLabel }}</button>
    <button v-else-if="state.status === 'held' && state.can_retry && state.id" type="button" :disabled="busy" @click="retry">Повторить подготовку данных</button>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import api from '@/api/axios'
import { consumerReadiness, createReadinessCompletion, readinessMessage } from '@/utils/consumerReadiness'

const props = defineProps({
  readiness: { default: null },
  actionLabel: { type: String, default: 'Повторить действие' },
  context: { type: String, default: 'action' },
  inline: { type: Boolean, default: false },
  quietWaiting: { type: Boolean, default: false },
})
const emit = defineEmits(['ready-action', 'ready', 'state-change'])
const firstCompletion = createReadinessCompletion()
const state = ref(null)
const pollError = ref(false)
const busy = ref(false)
let timer, generation = 0, controller
const message = computed(() => readinessMessage(state.value, props.context, pollError.value))
const presentationState = computed(() => state.value ? { ...state.value, poll_error: pollError.value } : null)
watch(presentationState, value => {
  emit('state-change', value)
  if (firstCompletion(value)) emit('ready', value)
})
function stop() { clearTimeout(timer); controller?.abort(); generation++ }
function schedule() {
  clearTimeout(timer)
  state.value = consumerReadiness(state.value)
  if (state.value?.status !== 'waiting' || !state.value.id) return
  if (document.hidden) return
  const remaining = Date.parse(state.value.deadline) - Date.now()
  if (!Number.isFinite(remaining) || remaining <= 0) {
    state.value = { ...state.value, status: 'held', can_retry: true, message: 'Время ожидания истекло. Можно повторить подготовку данных.' }
    return
  }
  timer = setTimeout(poll, Math.min(30000, remaining))
}
async function load(retry = false) {
  if (busy.value || !state.value?.id) return
  const token = generation
  busy.value = true
  pollError.value = false
  controller = new AbortController()
  try {
    const url = `data-refresh/${state.value.id}${retry ? '/retry' : ''}`
    const { data } = retry
      ? await api.post(url, null, { signal: controller.signal, timeout: 20000 })
      : await api.get(url, { signal: controller.signal, timeout: 20000 })
    if (token !== generation) return
    state.value = consumerReadiness(data)
    schedule()
  } catch {
    if (token === generation) pollError.value = true
  } finally {
    if (token === generation) busy.value = false
  }
}
function poll() { return load() }
function retry() { return load(true) }
function resume() {
  if (!document.hidden && state.value?.status === 'waiting') {
    clearTimeout(timer)
    poll()
  } else if (document.hidden) clearTimeout(timer)
}
watch(() => props.readiness, value => {
  stop()
  busy.value = false
  pollError.value = false
  state.value = consumerReadiness(value)
  schedule()
}, { immediate: true })
onMounted(() => document.addEventListener('visibilitychange', resume))
onBeforeUnmount(() => {
  stop()
  document.removeEventListener('visibilitychange', resume)
})
</script>

<style scoped>
.data-readiness { padding: 12px 16px; margin: 12px 0; border: 1px solid #dbe4f0; border-radius: 12px; background: #f5f8fc; color: #41516b; font-size: 14px; overflow-wrap: anywhere; }
.data-readiness p { margin: 0; }
.data-readiness small { display: block; margin-top: 4px; }
.data-readiness button { display: block; margin-top: 10px; padding: 8px 12px; border-radius: 8px; border: 1px solid #ccd8eb; color: inherit; background: transparent; }
.data-readiness button:disabled { opacity: .55; }
:global(.dark .data-readiness) { background: #202a39; color: #d0dcee; border-color: #3b4960; }
.data-readiness.data-readiness--inline { padding: 0; margin: 0; border: 0; border-radius: 0; background: transparent; color: inherit; font-size: inherit; line-height: 1.5; }
.data-readiness--inline button { margin-top: 8px; font-size: 13px; }
</style>
