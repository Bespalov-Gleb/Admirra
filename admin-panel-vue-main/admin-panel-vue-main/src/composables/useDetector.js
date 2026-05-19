import { ref, readonly } from 'vue'
import api from '@/api/axios'

const crossProjectData = ref({})
const crossProjectLoading = ref(false)

export function useDetector() {
  const summary = ref(null)
  const loading = ref(false)

  async function fetchSummary(clientId) {
    if (!clientId) return
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

  return {
    summary: readonly(summary),
    loading: readonly(loading),
    fetchSummary,
    dismissAlert,
    getAlertForMetric,
  }
}

export function useDetectorCrossProject() {
  async function fetchCrossProject() {
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
    return crossProjectData.value[projectId] || null
  }

  return {
    crossProjectData: readonly(crossProjectData),
    loading: readonly(crossProjectLoading),
    fetchCrossProject,
    getProjectStatus,
  }
}
