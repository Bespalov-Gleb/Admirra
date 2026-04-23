/**
 * Composable для отслеживания статуса синхронизации интеграций
 * Автоматически опрашивает API и определяет, идёт ли синхронизация
 */

import { ref, onMounted, onUnmounted, computed } from 'vue'
import api from '../api/axios'

export function useSyncStatus() {
  const integrations = ref([])
  const isLoading = ref(true)
  const error = ref(null)
  let pollInterval = null

  // Computed: есть ли интеграции в процессе синхронизации
  const isSyncing = computed(() => {
    return integrations.value.some(
      (integration) => integration.sync_status === 'PENDING'
    )
  })

  // Computed: список интеграций в процессе синхронизации
  const syncingIntegrations = computed(() => {
    return integrations.value.filter(
      (integration) => integration.sync_status === 'PENDING'
    )
  })

  /**
   * Идёт ли синхронизация для текущего вида дашборда.
   * @param {string|null} clientId - ID проекта или null для «все проекты»
   * @returns {boolean}
   */
  const isSyncingForProject = (clientId) => {
    const pending = syncingIntegrations.value
    if (pending.length === 0) return false
    if (!clientId) return true // «Все проекты» — любая синхронизация релевантна
    return pending.some((i) => String(i.client_id) === String(clientId))
  }

  // Computed: есть ли хотя бы одна интеграция
  const hasIntegrations = computed(() => {
    return integrations.value.length > 0
  })

  // Computed: есть ли интеграции, которые никогда не синхронизировались
  const hasNeverSyncedIntegrations = computed(() => {
    return integrations.value.some(
      (integration) => integration.sync_status === 'NEVER'
    )
  })

  // Функция для загрузки статуса интеграций
  const fetchSyncStatus = async () => {
    try {
      const response = await api.get('/integrations/')
      integrations.value = response.data
      error.value = null
    } catch (err) {
      if (err.response?.status === 401) {
        error.value = 'Unauthorized'
      } else {
        error.value = err.message || 'Unknown error'
      }
      console.error('Error fetching sync status:', err)
    } finally {
      isLoading.value = false
    }
  }

  // Начать опрос
  const startPolling = (intervalMs = 5000) => {
    // Первая загрузка сразу
    fetchSyncStatus()

    // Затем опрашиваем с интервалом
    pollInterval = setInterval(() => {
      fetchSyncStatus()
    }, intervalMs)
  }

  // Остановить опрос
  const stopPolling = () => {
    if (pollInterval !== null) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  }

  // Автоматически начинаем опрос при монтировании
  onMounted(() => {
    startPolling()
  })

  // Останавливаем опрос при размонтировании
  onUnmounted(() => {
    stopPolling()
  })

  return {
    integrations,
    isLoading,
    error,
    isSyncing,
    syncingIntegrations,
    isSyncingForProject,
    hasIntegrations,
    hasNeverSyncedIntegrations,
    fetchSyncStatus,
    startPolling,
    stopPolling
  }
}
