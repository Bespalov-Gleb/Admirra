import { computed, onScopeDispose, ref, watch } from 'vue'
import { createLatestRequest } from '../utils/latestRequest.js'

const emptyStats = () => ({ label: 'Направления', label_key: 'directions', mode: 'cards', total_expenses: 0, items: [] })
const listKey = s => JSON.stringify([s.client_id, s.channel])
const statsKey = s => JSON.stringify([s.client_id, s.channel, s.start_date, s.end_date])

// Definitions are independent of the period and live Metrika statistics.
// Keep only the current scope in memory; never display another project's rows.
export function useDirectionData(api, getScope, onStats = () => {}) {
  const directions = ref([]), directionStats = ref(emptyStats())
  const directionsLoading = ref(false), directionsError = ref('')
  const definitionsScope = ref(null), metricsScope = ref(null)
  const definitions = createLatestRequest(), metrics = createLatestRequest()
  let loadedAt = 0, disposed = false
  const scope = () => ({ ...getScope() })
  const current = (key, keyOf) => !disposed && key === keyOf(scope())

  function fetchDirections({ force = false } = {}) {
    const s = scope(), key = listKey(s)
    if (definitionsScope.value !== key) {
      definitions.cancel()
      directions.value = []
      definitionsScope.value = key
      directionsError.value = ''
      loadedAt = 0
    }
    if (!s.client_id) { directionsLoading.value = false; return Promise.resolve() }
    if (force) { definitions.cancel(); loadedAt = 0 }
    if (loadedAt && Date.now() - loadedAt < 30000) return Promise.resolve()
    directionsLoading.value = true
    return definitions.run(key, async ({ signal, isCurrent }) => {
      if (!current(key, listKey)) return
      try {
        const { data } = await api.get(`clients/${s.client_id}/directions/`, { signal, params: { platform: s.channel } })
        if (!isCurrent() || !current(key, listKey)) return
        if (!Array.isArray(data)) throw new Error('Invalid direction list')
        directions.value = data
        directionsError.value = ''
        loadedAt = Date.now()
      } catch (error) {
        if (isCurrent() && current(key, listKey)) directionsError.value = 'Не удалось загрузить направления'
      } finally {
        if (isCurrent() && current(key, listKey)) directionsLoading.value = false
      }
    })
  }

  function fetchDirectionStats({ force = false } = {}) {
    const s = scope(), key = statsKey(s)
    if (metricsScope.value !== key) {
      metrics.cancel()
      metricsScope.value = key
      directionStats.value = emptyStats()
    }
    if (!s.client_id || !s.start_date || !s.end_date) return Promise.resolve()
    if (force) metrics.cancel()
    return metrics.run(key, async ({ signal, isCurrent }) => {
      if (!current(key, statsKey)) return
      try {
        const { data } = await api.get(`clients/${s.client_id}/directions/stats`, {
          signal, params: { start_date: s.start_date, end_date: s.end_date, platform: s.channel },
        })
        if (!isCurrent() || !current(key, statsKey)) return
        directionStats.value = {
          label: data?.label || 'Направления', label_key: data?.label_key || 'directions',
          mode: data?.mode || 'cards', total_expenses: Number(data?.total_expenses || 0),
          items: Array.isArray(data?.items) ? data.items : [],
        }
        onStats(directionStats.value)
      } catch (error) {
        // A failed statistics read must not erase the fast definitions list.
        if (isCurrent() && current(key, statsKey)) directionStats.value = emptyStats()
      }
    })
  }

  const directionOptions = computed(() => {
    const s = scope()
    const rows = definitionsScope.value === listKey(s) ? directions.value : []
    const stats = metricsScope.value === statsKey(s) ? directionStats.value.items : []
    // The unassigned group is calculated by the server, not guessed from a
    // potentially partial campaign table. Real directions never wait for it.
    return [...rows, ...stats.filter(item => item.is_unassigned)]
  })
  const refreshDirections = () => Promise.all([
    fetchDirections({ force: true }), fetchDirectionStats({ force: true }),
  ])
  watch(() => listKey(scope()), () => fetchDirections(), { immediate: true })
  watch(() => statsKey(scope()), () => fetchDirectionStats(), { immediate: true })
  onScopeDispose(() => { disposed = true; definitions.cancel(); metrics.cancel() })
  return { directions, directionStats, directionOptions, directionsLoading, directionsError, fetchDirections, refreshDirections }
}
