<template>
  <div v-if="operation || error" class="billing-operation" role="status" aria-live="polite">
    <p>{{ error || operation?.message }}</p>
    <small v-if="operation?.command === 'cancel_all'">До подтверждения отмены платёжной системой списание ещё возможно.</small>
    <small v-if="operation && ['uncertain', 'rejected'].includes(operation.status)">Номер для поддержки: {{ operation.id }}</small>
    <button type="button" :disabled="checking" @click="refresh">{{ checking ? 'Проверяем…' : 'Проверить статус' }}</button>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import api from '@/api/axios'

const emit = defineEmits(['settled', 'state'])
const operation = ref(null)
const error = ref('')
const checking = ref(false)
let timer, disposed = false, attempts = 0

async function check() {
  if (checking.value || disposed) return
  clearTimeout(timer)
  checking.value = true
  try {
    const { data } = await api.get('billing/provider-operation')
    if (disposed) return
    const previous = operation.value
    operation.value = data?.operation || null
    emit('state', operation.value)
    error.value = ''
    if (previous && !operation.value) emit('settled')
    if (['queued', 'dispatching'].includes(operation.value?.status)) {
      if (++attempts < 30) timer = setTimeout(check, 10000)
      else error.value = 'Подтверждение занимает больше времени. Проверьте статус позже; повторно отправлять запрос не нужно.'
    }
  } catch {
    if (!disposed) error.value = 'Не удалось проверить результат изменения платежей. Проверьте статус ещё раз — сам запрос не повторится.'
  } finally {
    checking.value = false
  }
}
function refresh() { attempts = 0; return check() }
defineExpose({ refresh })
onMounted(check)
onBeforeUnmount(() => { disposed = true; clearTimeout(timer) })
</script>

<style scoped>
.billing-operation { margin: 12px 0 20px; padding: 14px 18px; border: 1px solid #c9d6ed; border-radius: 12px; background: #f4f7fc; color: #344664; overflow-wrap: anywhere; }
.billing-operation p { margin: 0; line-height: 1.5; }
.billing-operation small { display: block; margin-top: 6px; }
.billing-operation button { margin-top: 10px; padding: 6px 12px; border: 1px solid currentColor; border-radius: 8px; background: transparent; color: inherit; cursor: pointer; }
.billing-operation button:disabled { opacity: .6; cursor: wait; }
:global(.dark) .billing-operation { background: #202b3d; color: #cbd9ee; border-color: #45546b; }
</style>
