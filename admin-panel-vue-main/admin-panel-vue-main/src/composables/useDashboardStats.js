import { ref, reactive, watch, onMounted, computed } from 'vue'
import api from '../api/axios'

export function useDashboardStats() {
  const summary = ref({
    expenses: 0,
    impressions: 0,
    clicks: 0,
    leads: 0,
    cpc: 0,
    cpa: 0,
    trends: null
  })

  const dynamics = ref({
    labels: [],
    costs: [],
    clicks: [],
    impressions: [],
    leads: [],
    cpc: [],
    cpa: []
  })

  const topClients = ref([])
  const campaigns = ref([])
  const allCampaigns = ref([]) // For dropdown
  const clients = ref([])
  const loading = ref(true)
  const loadingClients = ref(false)
  const loadingCampaigns = ref(false)
  const error = ref(null)

  // Filters state
  const filters = reactive({
    channel: 'all',
    period: '14',
    client_id: '',
    campaign_ids: [],
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
    loadingClients.value = true
    try {
      const response = await api.get('clients/')
      clients.value = response.data
    } catch (err) {
      console.error('Error fetching clients:', err)
    } finally {
      loadingClients.value = false
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
      if (filters.campaign_ids && filters.campaign_ids.length > 0) {
        params.campaign_ids = filters.campaign_ids
      }

      // Parallel requests with error handling
      const results = await Promise.allSettled([
        api.get('dashboard/summary', { params }),
        api.get('dashboard/dynamics', { params }),
        api.get('dashboard/top-clients'),
        api.get('dashboard/campaigns', { params }),
        // Also fetch ALL campaigns for the dropdown if client/channel changed
        api.get('dashboard/campaigns', { 
          params: { 
            client_id: filters.client_id, 
            platform: filters.channel,
            start_date: filters.start_date,
            end_date: filters.end_date
          } 
        })
      ])

      // Map results
      if (results[0].status === 'fulfilled') summary.value = results[0].value.data
      if (results[1].status === 'fulfilled') dynamics.value = results[1].value.data
      if (results[2].status === 'fulfilled') topClients.value = results[2].value.data
      if (results[3].status === 'fulfilled') campaigns.value = results[3].value.data
      if (results[4].status === 'fulfilled') allCampaigns.value = results[4].value.data

      // If all critical failed, set a general error
      if (results.slice(0, 4).every(r => r.status === 'rejected')) {
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
    () => ({
      start_date: filters.start_date,
      end_date: filters.end_date,
      client_id: filters.client_id,
      channel: filters.channel,
      campaign_ids: [...filters.campaign_ids]
    }),
    (newFilters, oldFilters) => {
      // If client or channel changed, reset campaign selection
      if (oldFilters && (newFilters.client_id !== oldFilters.client_id || newFilters.channel !== oldFilters.channel)) {
        filters.campaign_ids = []
      }
      fetchStats()
    },
    { deep: true }
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
    allCampaigns,
    campaigns,
    clients,
    loading: computed(() => loading.value || loadingClients.value),
    loadingCampaigns,
    error,
    filters,
    handlePeriodChange,
    fetchStats,
    fetchClients
  }
}
