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

  // Filters state - single reactive object for consistency
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
    console.log('[useDashboardStats] fetchStats: START', JSON.parse(JSON.stringify(filters)))
    loading.value = true
    error.value = null

    try {
      const params = {
        start_date: filters.start_date,
        end_date: filters.end_date,
        platform: filters.channel
      }
      
      console.log('[useDashboardStats] fetchStats: current filters.campaign_ids =', filters.campaign_ids)
      
      if (filters.client_id) params.client_id = filters.client_id
      
      // Explicitly check for campaign_ids and log the decision
      if (Array.isArray(filters.campaign_ids) && filters.campaign_ids.length > 0) {
        console.log('[useDashboardStats] fetchStats: ADDING campaign_ids to params:', filters.campaign_ids)
        params.campaign_ids = filters.campaign_ids
      } else {
        console.log('[useDashboardStats] fetchStats: NO campaigns selected (empty array)')
        params.campaign_ids = [] // Send empty array instead of nothing
      }

      console.log('[useDashboardStats] fetchStats: FINAL PARAMS for Axios ->', JSON.stringify(params))

      const results = await Promise.allSettled([
        api.get('dashboard/summary', { params }),
        api.get('dashboard/dynamics', { params }),
        api.get('dashboard/top-clients'),
        api.get('dashboard/campaigns', { params })
      ])

      if (results[0].status === 'fulfilled') summary.value = results[0].value.data
      if (results[1].status === 'fulfilled') dynamics.value = results[1].value.data
      if (results[2].status === 'fulfilled') topClients.value = results[2].value.data
      if (results[3].status === 'fulfilled') campaigns.value = results[3].value.data
      
      console.log('[useDashboardStats] fetchStats: SUCCESS', { 
        campaignsCount: campaigns.value.length 
      })

      if (results[0].status === 'rejected' && results[1].status === 'rejected') {
        error.value = 'Не удалось загрузить данные статистики'
      }
    } catch (err) {
      console.error('[useDashboardStats] fetchStats: ERROR', err)
      error.value = 'Произошла непредвиденная ошибка'
    } finally {
      loading.value = false
    }
  }

  // Fetch the total pool of campaigns for the dropdown (unfiltered by campaign_ids)
  const fetchCampaignPool = async () => {
    console.log('[useDashboardStats] fetchCampaignPool: START', { client_id: filters.client_id })
    if (!filters.client_id) {
      allCampaigns.value = []
      return
    }
    
    loadingCampaigns.value = true
    try {
      const params = {
        client_id: filters.client_id,
        platform: filters.channel,
        start_date: filters.start_date,
        end_date: filters.end_date
      }
      const response = await api.get('dashboard/campaigns', { params })
      allCampaigns.value = response.data
      console.log('[useDashboardStats] fetchCampaignPool: SUCCESS', { poolCount: allCampaigns.value.length })
    } catch (err) {
      console.error('[useDashboardStats] fetchCampaignPool: ERROR', err)
    } finally {
      loadingCampaigns.value = false
    }
  }

  // Watchers (Granular control via refs)
  
  // 1. Project or Channel change -> Reset campaign selection and Fetch Pool
  watch(
    () => [filters.client_id, filters.channel],
    (newVal, oldVal) => {
      console.log('[useDashboardStats] WATCH [client_id, channel] triggered', {
        oldProject: oldVal ? oldVal[0] : null,
        newProject: newVal[0]
      })
      if (oldVal && (newVal[0] !== oldVal[0] || newVal[1] !== oldVal[1])) {
        // Only reset if this is a REAL change
        if (oldVal[0] !== null && oldVal[0] !== undefined) {
           console.log('[useDashboardStats] RESET campaign_ids: Project changed')
           filters.campaign_ids = []
        }
      }
      fetchCampaignPool()
    }
  )

  // 2. Date range change -> Fetch Pool (keep selection)
  watch(
    () => [filters.start_date, filters.end_date],
    () => {
      console.log('[useDashboardStats] WATCH [dates] triggered')
      fetchCampaignPool()
    }
  )

  // 3. Any filter change -> Fetch Statistics
  watch(
    () => [
      filters.start_date, 
      filters.end_date, 
      filters.client_id, 
      filters.channel, 
      JSON.stringify(filters.campaign_ids)
    ],
    (newVal) => {
      console.log('[useDashboardStats] WATCH [all filters] triggered -> fetchStats', {
        campaign_ids: newVal[4]
      })
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
