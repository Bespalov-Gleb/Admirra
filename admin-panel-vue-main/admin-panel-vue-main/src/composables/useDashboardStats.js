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
    console.log('[useDashboardStats] fetchStats: START', { 
      client_id: client_id.value, 
      campaign_ids: JSON.stringify(campaign_ids.value) 
    })
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
    console.log('[useDashboardStats] fetchCampaignPool: START', { client_id: client_id.value })
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
    [client_id, channel],
    (newVal, oldVal) => {
      console.log('[useDashboardStats] WATCH [client_id, channel] triggered', {
        oldProject: oldVal ? oldVal[0] : null,
        newProject: newVal[0],
        oldChannel: oldVal ? oldVal[1] : null,
        newChannel: newVal[1]
      })
      if (oldVal && (newVal[0] !== oldVal[0] || newVal[1] !== oldVal[1])) {
        if (oldVal[0] !== undefined) {
           console.log('[useDashboardStats] RESET campaign_ids due to project/channel change')
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
      console.log('[useDashboardStats] WATCH [dates] triggered', { start: start_date.value, end: end_date.value })
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
