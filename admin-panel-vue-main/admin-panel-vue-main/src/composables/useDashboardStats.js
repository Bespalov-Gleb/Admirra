import { ref, reactive, watch, onMounted } from 'vue'
import api from '../api/axios'

export function useDashboardStats() {
  const summary = ref({
    expenses: 0,
    impressions: 0,
    clicks: 0,
    leads: 0,
    cpc: 0,
    cpa: 0
  })

  const dynamics = ref({
    labels: [],
    costs: [],
    clicks: []
  })

  const topClients = ref([])
  const campaigns = ref([])
  const clients = ref([])
  const loading = ref(true)
  const loadingCampaigns = ref(false)
  const error = ref(null)

  // Filters state
  const filters = reactive({
    channel: 'all',
    period: '14',
    client_id: '',
    start_date: '',
    end_date: new Date().toISOString().split('T')[0]
  })

  // Set initial dates for "14 days"
  const setInitialDates = () => {
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - parseInt(filters.period))
    filters.start_date = start.toISOString().split('T')[0]
    filters.end_date = end.toISOString().split('T')[0]
  }

  const handlePeriodChange = () => {
    if (filters.period === 'custom') return
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - parseInt(filters.period))
    filters.start_date = start.toISOString().split('T')[0]
    filters.end_date = end.toISOString().split('T')[0]
  }

  // Fetch clients list
  const fetchClients = async () => {
    try {
      const response = await api.get('clients/')
      clients.value = response.data
    } catch (err) {
      console.error('Error fetching clients:', err)
    }
  }

  // Fetch all dashboard stats
  const fetchStats = async () => {
    loading.value = true
    loadingCampaigns.value = true
    error.value = null

    try {
      const params = {
        start_date: filters.start_date,
        end_date: filters.end_date,
        platform: filters.channel
      }
      if (filters.client_id) params.client_id = filters.client_id

      // Parallel requests with error handling
      const results = await Promise.allSettled([
        api.get('dashboard/summary', { params }),
        api.get('dashboard/dynamics', { params }),
        api.get('dashboard/top-clients'),
        api.get('dashboard/campaigns', { params })
      ])

      // Map results
      if (results[0].status === 'fulfilled') summary.value = results[0].value.data
      if (results[1].status === 'fulfilled') dynamics.value = results[1].value.data
      if (results[2].status === 'fulfilled') topClients.value = results[2].value.data
      if (results[3].status === 'fulfilled') campaigns.value = results[3].value.data

      // If all failed, set a general error
      if (results.every(r => r.status === 'rejected')) {
        error.value = 'Не удалось загрузить данные статистики'
      }
    } catch (err) {
      console.error('Error fetching stats:', err)
      error.value = 'Произошла непредвиденная ошибка'
    } finally {
      loading.value = false
      loadingCampaigns.value = false
    }
  }

  // Watch filters and trigger fetch
  watch(
    () => [filters.start_date, filters.end_date, filters.client_id, filters.channel],
    () => fetchStats()
  )

  onMounted(() => {
    setInitialDates()
    fetchClients()
    fetchStats()
  })

  return {
    summary,
    dynamics,
    topClients,
    campaigns,
    clients,
    loading,
    loadingCampaigns,
    error,
    filters,
    handlePeriodChange,
    fetchStats
  }
}
