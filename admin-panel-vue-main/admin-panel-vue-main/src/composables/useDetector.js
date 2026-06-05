import { ref, readonly } from 'vue'
import api from '@/api/axios'

// Demo mode is kept only for local visual checks. Production must read real detector API data.
const DEMO_MODE = false

const DEMO_ALERTS = [
  {
    id: 'demo-1',
    metric: 'expenses',
    detection_level: 'project',
    entity_id: null,
    channel: null,
    mode: 'baseline',
    severity: 'problem',
    deviation_pct: -42.3,
    baseline_value: 85000,
    actual_value: 49065,
    consecutive_days: 4,
    pattern_key: 'budget_exhausted',
    hypothesis_text: 'Закончился бюджет или остановилась кампания',
    status: 'open',
    opened_at: new Date().toISOString(),
  },
  {
    id: 'demo-2',
    metric: 'clicks',
    detection_level: 'project',
    entity_id: null,
    channel: null,
    mode: 'baseline',
    severity: 'warning',
    deviation_pct: -31.5,
    baseline_value: 1240,
    actual_value: 849,
    consecutive_days: 2,
    pattern_key: 'reach_down',
    hypothesis_text: 'Сужение охвата — проверьте настройки таргетинга',
    status: 'open',
    opened_at: new Date().toISOString(),
  },
  {
    id: 'demo-3',
    metric: 'cpa',
    detection_level: 'project',
    entity_id: null,
    channel: null,
    mode: 'plan_cpa',
    severity: 'warning',
    deviation_pct: 48.7,
    baseline_value: 1200,
    actual_value: 1784,
    consecutive_days: 3,
    pattern_key: 'conversion_drop',
    hypothesis_text: 'Просела конверсия сайта — CPA вырос при стабильном трафике',
    status: 'open',
    opened_at: new Date().toISOString(),
  },
  {
    id: 'demo-4',
    metric: 'impressions',
    detection_level: 'project',
    entity_id: null,
    channel: null,
    mode: 'baseline',
    severity: 'problem',
    deviation_pct: -55.2,
    baseline_value: 48000,
    actual_value: 21504,
    consecutive_days: 3,
    pattern_key: 'reach_down',
    hypothesis_text: 'Резкое снижение показов — возможна проблема с модерацией',
    status: 'open',
    opened_at: new Date().toISOString(),
  },
]

const DEMO_SUMMARY = {
  warning_count: 2,
  problem_count: 2,
  max_severity: 'problem',
  warmup_status: null,
  warmup_days_left: null,
  alerts: DEMO_ALERTS,
}
// <<< END DEMO MODE >>>

const crossProjectData = ref({})
const crossProjectLoading = ref(false)

export function useDetector() {
  const summary = ref(null)
  const loading = ref(false)

  async function fetchSummary(clientId) {
    if (!clientId) return
    if (DEMO_MODE) {
      summary.value = JSON.parse(JSON.stringify(DEMO_SUMMARY))
      return
    }
    loading.value = true
    try {
      const { data } = await api.get(`detector/${clientId}/summary`)
      summary.value = data
    } catch {
      summary.value = null
    } finally {
      loading.value = false
    }
  }

  async function dismissAlert(alertId) {
    try {
      await api.post(`detector/alerts/${alertId}/dismiss`)
      if (summary.value?.alerts) {
        summary.value.alerts = summary.value.alerts.filter(a => a.id !== alertId)
        summary.value.warning_count = summary.value.alerts.filter(a => a.severity === 'warning').length
        summary.value.problem_count = summary.value.alerts.filter(a => a.severity === 'problem').length
        summary.value.max_severity = summary.value.problem_count > 0
          ? 'problem'
          : summary.value.warning_count > 0 ? 'warning' : null
      }
      return true
    } catch {
      return false
    }
  }

  function getAlertForMetric(metricKey) {
    if (!summary.value?.alerts) return null
    const metricMap = {
      expenses: 'expenses',
      impressions: 'impressions',
      clicks: 'clicks',
      cpc: 'cpc',
      leads: 'conversions',
      cpa: 'cpa',
    }
    const dbKey = metricMap[metricKey] || metricKey
    return summary.value.alerts.find(a => a.metric === dbKey) || null
  }

  function getAlertForEntity(level, entityId) {
    if (!summary.value?.alerts || !level || entityId === null || entityId === undefined) return null
    return summary.value.alerts.find(a =>
      a.detection_level === level &&
      String(a.entity_id ?? '') === String(entityId)
    ) || null
  }

  return {
    summary: readonly(summary),
    loading: readonly(loading),
    fetchSummary,
    dismissAlert,
    getAlertForMetric,
    getAlertForEntity,
  }
}

export function useDetectorCrossProject() {
  async function fetchCrossProject() {
    if (DEMO_MODE) {
      crossProjectLoading.value = false
      return
    }
    crossProjectLoading.value = true
    try {
      const { data } = await api.get('detector/cross-project')
      const map = {}
      for (const item of data) {
        map[item.project_id] = item
      }
      crossProjectData.value = map
    } catch {
      crossProjectData.value = {}
    } finally {
      crossProjectLoading.value = false
    }
  }

  function getProjectStatus(projectId) {
    if (DEMO_MODE) {
      const demoStatuses = [
        { warning_count: 2, problem_count: 1, max_severity: 'problem', warmup_status: null },
        { warning_count: 1, problem_count: 0, max_severity: 'warning', warmup_status: null },
        { warning_count: 0, problem_count: 0, max_severity: null, warmup_status: 'warming_up' },
      ]
      const hash = String(projectId).charCodeAt(0) % 3
      return demoStatuses[hash]
    }
    return crossProjectData.value[projectId] || null
  }

  return {
    crossProjectData: readonly(crossProjectData),
    loading: readonly(crossProjectLoading),
    fetchCrossProject,
    getProjectStatus,
  }
}
