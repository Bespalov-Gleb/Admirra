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
import { pollSyncJobsUntilDone } from '../utils/syncJobPolling'

const SYNC_ACTIVE_STATUSES = new Set(['PENDING', 'QUEUED', 'RUNNING'])

const integrations = ref([])
const isLoading = ref(true)
const error = ref(null)
const pollSubscribers = ref(0)
let pollInterval = null
let backgroundPollInFlight = false

const normalizeStatus = (status) => String(status || '').trim().toUpperCase()

const fetchSyncStatus = async (params = {}) => {
  try {
    const response = await api.get('/integrations/', { params, timeout: 10000 })
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
  const tick = async () => {
    if (backgroundPollInFlight) return
    backgroundPollInFlight = true
    try { await fetchSyncStatus() } finally { backgroundPollInFlight = false }
  }
  tick()
  pollInterval = setInterval(tick, intervalMs)
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

const startIntegrationSync = async (integrationId, { days = 90, forceFull = false } = {}) => {
  const { data } = await api.post(`integrations/${integrationId}/sync`, { days, force_full: forceFull })
  await fetchSyncStatus()
  return data
}

const waitForSyncJobs = (jobIds, options = {}) => pollSyncJobsUntilDone(jobIds, {
  ...options,
  getJob: async (id, config) => (await api.get(`integrations/sync/jobs/${id}`, config)).data,
  afterPoll: fetchSyncStatus,
})

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
