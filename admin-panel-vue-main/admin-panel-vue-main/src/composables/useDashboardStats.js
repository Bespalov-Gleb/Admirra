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

  // Individual refs for filters for better reactivity control
  const channel = ref('all')
  const period = ref('14')
  const client_id = ref(null)
  const campaign_ids = ref([])
  const start_date = ref('')
  const end_date = ref(new Date().toISOString().split('T')[0])

  // Computed filters object for backward compatibility if needed, 
  // but we should favor refs for internal logic
  const filters = reactive({
    channel,
    period,
    client_id,
    campaign_ids,
    start_date,
    end_date
  })

  // Set initial dates for "14 days"
  const setInitialDates = () => {
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - parseInt(period.value))
    start_date.value = start.toISOString().split('T')[0]
    end_date.value = end.toISOString().split('T')[0]
  }

  const handlePeriodChange = () => {
    if (period.value === 'custom') return
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - parseInt(period.value))
    start_date.value = start.toISOString().split('T')[0]
    end_date.value = end.toISOString().split('T')[0]
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
        start_date: start_date.value,
        end_date: end_date.value,
        platform: channel.value
      }
      if (client_id.value) params.client_id = client_id.value
      if (campaign_ids.value && campaign_ids.value.length > 0) {
        params.campaign_ids = campaign_ids.value
      }

      // Parallel requests (excluding the full pool)
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
    if (!client_id.value) {
      allCampaigns.value = []
      return
    }
    
    loadingCampaigns.value = true
    try {
      const params = {
        client_id: client_id.value,
        platform: channel.value,
        start_date: start_date.value,
        end_date: end_date.value
      }
      const response = await api.get('dashboard/campaigns', { params })
      allCampaigns.value = response.data
    } catch (err) {
      console.error('Error fetching campaign pool:', err)
    } finally {
      loadingCampaigns.value = false
    }
  }

  // Watchers (Granular control via refs)
  
  // 1. Project or Channel change -> Reset campaign selection and Fetch Pool
  watch(
    [client_id, channel],
    (newVal, oldVal) => {
      if (oldVal && (newVal[0] !== oldVal[0] || newVal[1] !== oldVal[1])) {
        // Only reset if we actually have a change (not initial load from undefined)
        // AND avoid resetting during initial mounting jitter
        if (oldVal[0] !== undefined) {
           campaign_ids.value = []
        }
      }
      fetchCampaignPool()
    }
  )

  // 2. Date range change -> Fetch Pool (keep selection)
  watch(
    [start_date, end_date],
    () => {
      fetchCampaignPool()
    }
  )

  // 3. Any filter change -> Fetch Statistics
  watch(
    () => [
      start_date.value, 
      end_date.value, 
      client_id.value, 
      channel.value, 
      JSON.stringify(campaign_ids.value)
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
