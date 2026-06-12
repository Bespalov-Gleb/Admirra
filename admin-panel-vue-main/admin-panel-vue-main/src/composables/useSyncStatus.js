/**
 * Shared integration sync status store.
 *
 * Sync is asynchronous on the backend: POST /integrations/:id/sync creates a
 * SyncJob, while the Integration row keeps the user-visible status and
 * last_sync_at. Keep one polling loop per app session so dashboard, projects
 * and integrations read the same state.
 */

import { computed, ref, onMounted, onUnmounted } from 'vue'
import api from '../api/axios'

const SYNC_ACTIVE_STATUSES = new Set(['PENDING', 'QUEUED', 'RUNNING'])
const SYNC_TERMINAL_JOB_STATUSES = new Set(['SUCCESS', 'FAILED', 'CANCELLED'])

const integrations = ref([])
const isLoading = ref(true)
const error = ref(null)
const pollSubscribers = ref(0)
let pollInterval = null

const normalizeStatus = (status) => String(status || '').trim().toUpperCase()

const fetchSyncStatus = async (params = {}) => {
  try {
    const response = await api.get('/integrations/', { params })
    integrations.value = Array.isArray(response.data) ? response.data : []
    error.value = null
    return integrations.value
  } catch (err) {
    error.value = err.response?.status === 401 ? 'Unauthorized' : (err.message || 'Unknown error')
    console.error('Error fetching sync status:', err)
    return integrations.value
  } finally {
    isLoading.value = false
  }
}

const startPolling = (intervalMs = 5000) => {
  if (pollInterval) return
  fetchSyncStatus()
  pollInterval = setInterval(() => {
    fetchSyncStatus()
  }, intervalMs)
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

const isSyncing = computed(() => integrations.value.some((integration) => (
  SYNC_ACTIVE_STATUSES.has(normalizeStatus(integration.sync_status))
)))

const syncingIntegrations = computed(() => integrations.value.filter((integration) => (
  SYNC_ACTIVE_STATUSES.has(normalizeStatus(integration.sync_status))
)))

const hasIntegrations = computed(() => integrations.value.length > 0)

const hasNeverSyncedIntegrations = computed(() => integrations.value.some(
  (integration) => normalizeStatus(integration.sync_status) === 'NEVER'
))

const isSyncingForProject = (clientId) => {
  const pending = syncingIntegrations.value
  if (pending.length === 0) return false
  if (!clientId) return true
  return pending.some((integration) => String(integration.client_id) === String(clientId))
}

const isSyncingIntegration = (integrationId) => {
  if (!integrationId) return false
  return integrations.value.some((integration) => (
    String(integration.id) === String(integrationId)
    && SYNC_ACTIVE_STATUSES.has(normalizeStatus(integration.sync_status))
  ))
}

const startIntegrationSync = async (integrationId, { days = 90, forceFull = true } = {}) => {
  const { data } = await api.post(`integrations/${integrationId}/sync`, { days, force_full: forceFull })
  await fetchSyncStatus()
  return data
}

const waitForSyncJobs = async (jobIds, {
  intervalMs = 4000,
  timeoutMs = 20 * 60 * 1000,
  onTick = null,
} = {}) => {
  const ids = [...new Set((jobIds || []).filter(Boolean).map(String))]
  if (!ids.length) return { finished: [], failed: [] }

  const startedAt = Date.now()
  const statuses = {}

  while (Date.now() - startedAt < timeoutMs) {
    const results = await Promise.allSettled(ids.map((jobId) => api.get(`integrations/sync/jobs/${jobId}`)))
    results.forEach((result, index) => {
      const jobId = ids[index]
      if (result.status === 'fulfilled') statuses[jobId] = result.value.data || {}
      else statuses[jobId] = { status: 'FAILED', error: result.reason?.response?.data?.detail || result.reason?.message }
    })

    await fetchSyncStatus()
    if (typeof onTick === 'function') onTick({ ...statuses })

    const normalized = ids.map((jobId) => normalizeStatus(statuses[jobId]?.status))
    if (normalized.every((status) => SYNC_TERMINAL_JOB_STATUSES.has(status))) {
      return {
        finished: ids,
        failed: ids.filter((jobId) => normalizeStatus(statuses[jobId]?.status) !== 'SUCCESS'),
        statuses,
      }
    }

    await new Promise((resolve) => setTimeout(resolve, intervalMs))
  }

  return {
    finished: ids.filter((jobId) => SYNC_TERMINAL_JOB_STATUSES.has(normalizeStatus(statuses[jobId]?.status))),
    failed: ids.filter((jobId) => normalizeStatus(statuses[jobId]?.status) !== 'SUCCESS'),
    timedOut: true,
    statuses,
  }
}

export function useSyncStatus() {
  let unsubscribe = null

  onMounted(() => {
    unsubscribe = withPolling()
  })

  onUnmounted(() => {
    unsubscribe?.()
    unsubscribe = null
  })

  return {
    integrations,
    isLoading,
    error,
    isSyncing,
    syncingIntegrations,
    isSyncingForProject,
    isSyncingIntegration,
    hasIntegrations,
    hasNeverSyncedIntegrations,
    normalizeStatus,
    fetchSyncStatus,
    startPolling,
    stopPolling,
    startIntegrationSync,
    waitForSyncJobs,
  }
}
