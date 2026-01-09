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
    client_id: null,
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

  // Fetch all dashboard stats (summary, dynamics, top-clients, and filtered campaigns)
  const fetchStats = async () => {
    loading.value = true
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

      // Parallel requests (excluding the full pool)
      const results = await Promise.allSettled([
        api.get('dashboard/summary', { params }),
        api.get('dashboard/dynamics', { params }),
        api.get('dashboard/top-clients'),
        api.get('dashboard/campaigns', { params }) // This one is filtered by campaign_ids
      ])

      // Map results
      if (results[0].status === 'fulfilled') summary.value = results[0].value.data
      if (results[1].status === 'fulfilled') dynamics.value = results[1].value.data
      if (results[2].status === 'fulfilled') topClients.value = results[2].value.data
      if (results[3].status === 'fulfilled') campaigns.value = results[3].value.data

      // If critical summary/dynamics failed, set a general error
      if (results[0].status === 'rejected' && results[1].status === 'rejected') {
        error.value = 'Не удалось загрузить данные статистики'
      }
    } catch (err) {
      console.error('Error fetching stats:', err)
      error.value = 'Произошла непредвиденная ошибка'
    } finally {
      loading.value = false
    }
  }

  // Fetch the total pool of campaigns for the dropdown (unfiltered by campaign_ids)
  const fetchCampaignPool = async () => {
    if (!filters.client_id) {
      allCampaigns.value = []
      return
    }
    
    loadingCampaigns.value = true
    try {
      const params = {
        platform: filters.channel,
        start_date: filters.start_date,
        end_date: filters.end_date
      }
      if (filters.client_id) params.client_id = filters.client_id
      const response = await api.get('dashboard/campaigns', { params })
      allCampaigns.value = response.data
    } catch (err) {
      console.error('Error fetching campaign pool:', err)
    } finally {
      loadingCampaigns.value = false
    }
  }

  // Watchers
  
  // 1. If project or channel changes, reset campaign selection and fetch a new pool
  watch(
    () => [filters.client_id, filters.channel],
    (newVal, oldVal) => {
      if (oldVal && (newVal[0] !== oldVal[0] || newVal[1] !== oldVal[1])) {
        filters.campaign_ids = []
      }
      fetchCampaignPool()
    }
  )

  // 2. Fetch pool if dates change (but keep selection if possible)
  watch(
    () => [filters.start_date, filters.end_date],
    () => {
      fetchCampaignPool()
    }
  )

  // 3. Fetch stats whenever any filter changes
  watch(
    () => [
      filters.start_date, 
      filters.end_date, 
      filters.client_id, 
      filters.channel, 
      JSON.stringify(filters.campaign_ids)
    ],
    () => {
      fetchStats()
    }
  )

  onMounted(() => {
    setInitialDates()
    fetchClients()
    fetchCampaignPool()
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
