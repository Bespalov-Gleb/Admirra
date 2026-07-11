/**
 * Общий стор очереди отчётов «ждут одобрения».
 *
 * Одна точка опроса на сессию: бейдж-счётчик в сайдбаре и страница «Отчёты»
 * читают одно и то же состояние. Обновляется по расписанию и по требованию
 * (после утверждения/отправки) через refreshReportsQueue().
 */

import { ref, onMounted, onUnmounted } from 'vue'
import api from '../api/axios'

const pendingCount = ref(0)
const isLoading = ref(false)
const pollSubscribers = ref(0)
let pollInterval = null

const fetchPending = async () => {
  isLoading.value = true
  try {
    const { data } = await api.get('reports/deliveries/pending-count')
    pendingCount.value = Number(data?.count || 0)
  } catch {
    pendingCount.value = 0
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
    pendingCount,
    isLoading,
    refresh: fetchPending,
  }
}
