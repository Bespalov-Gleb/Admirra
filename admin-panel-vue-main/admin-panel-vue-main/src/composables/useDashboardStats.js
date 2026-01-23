import { ref, reactive, watch, onMounted, computed } from 'vue'
import api from '../api/axios'

/**
 * Composable for managing dashboard statistics and filters.
 */
export function useDashboardStats() {
  const summary = ref({
    expenses: 0,
    impressions: 0,
    clicks: 0,
    leads: 0,
    cpc: 0,
    cpa: 0,
    balance: 0,
    currency: 'RUB',
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
  const allCampaigns = ref([]) // For dropdown pool
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

  // --- Logic Helpers ---

  const setInitialDates = () => {
    const end = new Date()
    const start = new Date()
    // CRITICAL: If period is "14 days", we want 14 days total (including today)
    // So we subtract (period - 1) days to get the correct start date
    const periodDays = parseInt(filters.period)
    start.setDate(end.getDate() - (periodDays - 1))
    filters.start_date = start.toISOString().split('T')[0]
    filters.end_date = end.toISOString().split('T')[0]
  }

  const handlePeriodChange = async () => {
    if (filters.period === 'custom') return
    const end = new Date()
    const start = new Date()
    // CRITICAL: If period is "14 days", we want 14 days total (including today)
    // So we subtract (period - 1) days to get the correct start date
    const periodDays = parseInt(filters.period)
    start.setDate(end.getDate() - (periodDays - 1))
    const newStartDate = start.toISOString().split('T')[0]
    const newEndDate = end.toISOString().split('T')[0]
    
    // Only update if dates actually changed to avoid unnecessary API calls
    if (filters.start_date !== newStartDate || filters.end_date !== newEndDate) {
      filters.start_date = newStartDate
      filters.end_date = newEndDate
      
      // Автоматический пересинхрон при смене периода
      if (filters.client_id) {
        try {
          // Получаем список интеграций для текущего проекта
          const { data: integrations } = await api.get('integrations/')
          const projectIntegrations = integrations.filter(integration => 
            integration.client_id === filters.client_id
          )
          
          // Запускаем синхронизацию для всех интеграций проекта в фоне
          const syncPromises = projectIntegrations.map(integration => 
            api.post(`integrations/${integration.id}/sync`, { 
              days: periodDays 
            }).catch(err => {
              console.warn(`[DashboardStats] Sync failed for integration ${integration.id}:`, err)
              return null
            })
          )
          
          // Запускаем синхронизацию параллельно, но не ждем завершения
          Promise.allSettled(syncPromises).then(() => {
            console.log('[DashboardStats] Background sync completed')
          })
        } catch (err) {
          console.warn('[DashboardStats] Failed to trigger auto-sync:', err)
          // Не блокируем загрузку статистики, если синхронизация не удалась
        }
      }
      
      // Explicitly fetch stats after period change
      fetchStats()
    }
  }

  // --- API Calls ---

  const fetchClients = async () => {
    loadingClients.value = true
    try {
      const { data } = await api.get('clients/')
      clients.value = data
    } catch (err) {
      console.error('[DashboardStats] Error fetching clients:', err)
    } finally {
      loadingClients.value = false
    }
  }

  const fetchStats = async () => {
    loading.value = true
    error.value = null

    try {
      const params = {
        start_date: filters.start_date,
        end_date: filters.end_date,
        platform: filters.channel,
        client_id: filters.client_id || undefined,
        // CRITICAL: Only send campaign_ids if there are any selected
        // Empty array should not be sent (backend treats it as "no filter")
        campaign_ids: filters.campaign_ids.length > 0 ? filters.campaign_ids : undefined
      }

      const [summaryRes, dynamicsRes, topClientsRes, campaignsRes] = await Promise.allSettled([
        api.get('dashboard/summary', { params }),
        api.get('dashboard/dynamics', { params }),
        api.get('dashboard/top-clients'),
        api.get('dashboard/campaigns', { params })
      ])

      if (summaryRes.status === 'fulfilled') {
        const summaryData = summaryRes.value.data
        console.log('[DashboardStats] Summary data received:', summaryData)
        console.log('[DashboardStats] Balance:', summaryData.balance, 'Currency:', summaryData.currency)
        // CRITICAL: Ensure balance and currency are always set, even if backend returns undefined
        summary.value = {
          ...summaryData,
          balance: summaryData.balance ?? 0,
          currency: summaryData.currency ?? 'RUB'
        }
      } else {
        console.error('[DashboardStats] Failed to fetch summary:', summaryRes.reason)
      }
      
      if (dynamicsRes.status === 'fulfilled') dynamics.value = dynamicsRes.value.data
      if (topClientsRes.status === 'fulfilled') topClients.value = topClientsRes.value.data
      if (campaignsRes.status === 'fulfilled') campaigns.value = campaignsRes.value.data

      if (summaryRes.status === 'rejected' && dynamicsRes.status === 'rejected') {
        error.value = 'Failed to load statistics'
      }
    } catch (err) {
      console.error('[DashboardStats] Unexpected error:', err)
      error.value = 'An unexpected error occurred'
    } finally {
      loading.value = false
    }
  }

  const fetchCampaignPool = async () => {
    if (!filters.client_id) {
      allCampaigns.value = []
      return
    }
    
    loadingCampaigns.value = true
    try {
      // CRITICAL: Use /campaigns/ endpoint to get ALL campaigns for the project
      // /dashboard/campaigns only returns campaigns with stats (JOIN with stats tables)
      // For dropdown, we need ALL campaigns, even those without stats
      const params = {
        client_id: filters.client_id,
        // В выпадающем списке кампаний на дашборде должны быть только кампании,
        // которые пользователь выбрал при настройке интеграции (is_active = true)
        only_active: true
      }
      
      // Add platform filter if not "all"
      if (filters.channel !== 'all') {
        params.platform = filters.channel
      }
      
      const { data } = await api.get('campaigns/', { params })
      
      // Format for dropdown: { id, name }
      allCampaigns.value = data.map(c => ({
        id: c.id,
        name: c.name
      }))
    } catch (err) {
      console.error('[DashboardStats] Error fetching campaign pool:', err)
      allCampaigns.value = []
    } finally {
      loadingCampaigns.value = false
    }
  }

  // --- Watchers ---
  
  // 1. Project or Channel change -> Reset campaign selection and Fetch Pool
  watch(
    () => [filters.client_id, filters.channel],
    (newVal, oldVal) => {
      // If project changed, reset campaign selection
      if (oldVal && newVal[0] !== oldVal[0]) {
        filters.campaign_ids = []
      }
      fetchCampaignPool()
    }
  )

  // 2. Any relevant filter change -> Fetch Statistics
  watch(
    () => [
      filters.start_date, 
      filters.end_date, 
      filters.client_id, 
      filters.channel, 
      filters.campaign_ids
    ],
    (newVal, oldVal) => {
      // Only fetch if dates are actually set (not empty strings)
      if (filters.start_date && filters.end_date) {
        fetchStats()
      }
    },
    { deep: true }
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
    fetchClients,
    fetchCampaignPool
  }
}
