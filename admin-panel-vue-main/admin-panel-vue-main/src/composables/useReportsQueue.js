/**
 * Общий стор очереди отчётов «ждут одобрения».
 *
 * Одна точка опроса на сессию: бейдж-счётчик в сайдбаре и страница «Отчёты»
 * читают одно и то же состояние. Обновляется по расписанию и по требованию
 * (после утверждения/отправки) через refreshReportsQueue().
 */

import { computed, ref, onMounted, onUnmounted } from 'vue'
import api from '../api/axios'

const pending = ref([])
const isLoading = ref(false)
const pollSubscribers = ref(0)
let pollInterval = null

const pendingCount = computed(() => pending.value.length)

const fetchPending = async () => {
  isLoading.value = true
  try {
    const { data } = await api.get('reports/deliveries', { params: { status: 'pending' } })
    pending.value = Array.isArray(data) ? data : []
  } catch {
    // молча — бейдж не критичен; при 401 интерсептор axios разрулит
  } finally {
    isLoading.value = false
  }
}

// Триггер обновления из любого места (после approve/save)
export const refreshReportsQueue = () => fetchPending()

const startPolling = (intervalMs = 60000) => {
  if (pollInterval) return
  fetchPending()
  pollInterval = setInterval(fetchPending, intervalMs)
}

const stopPolling = ({ force = false } = {}) => {
  if (!force && pollSubscribers.value > 0) return
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

const withPolling = () => {
  pollSubscribers.value += 1
  startPolling()
  return () => {
    pollSubscribers.value = Math.max(0, pollSubscribers.value - 1)
    stopPolling()
  }
}

export function useReportsQueue({ poll = false } = {}) {
  let unsubscribe = null

  onMounted(() => {
    if (poll) unsubscribe = withPolling()
    else fetchPending()
  })

  onUnmounted(() => {
    unsubscribe?.()
    unsubscribe = null
  })

  return {
    pending,
    pendingCount,
    isLoading,
    refresh: fetchPending,
  }
}
