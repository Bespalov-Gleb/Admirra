import { ref, reactive, watch, onMounted, computed } from 'vue'
import api from '../api/axios'
import { getAccessToken } from '@/utils/authToken'
import { getProjectPeriodRange } from '@/utils/projectPeriods'

const DEVICE_STATS_MOCK = [
  { name: 'Мобильные', value: '—', width: '0%', icon: 'mobile' },
  { name: 'Десктоп',   value: '—', width: '0%', icon: 'desktop' },
  { name: 'Планшеты',  value: '—', width: '0%', icon: 'desktop' }
]

const PLACEMENTS_MOCK = [
  { name: 'Поиск', value: '—', width: '0%' },
  { name: 'РСЯ',   value: '—', width: '0%' }
]

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
  const allCampaigns = ref([])
  const allCampaignsForGoalsTab = ref([])
  const clients = ref([])
  const deviceStats = ref([...DEVICE_STATS_MOCK])
  const placements = ref([...PLACEMENTS_MOCK])
  const loading = ref(true)
  const loadingClients = ref(false)
  const loadingCampaigns = ref(false)
  const loadingVkGoalActions = ref(false)
  const error = ref(null)
  const vkGoalActions = ref([])

  const STORAGE_KEY = 'trafic_agent_dashboard_filters'
  const validChannels = ['all', 'yandex', 'vk', 'avito']

  const loadFiltersFromStorage = () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return null
      const parsed = JSON.parse(raw)
      if (!parsed || typeof parsed !== 'object') return null
      if (typeof parsed.period !== 'string') return null
      return parsed
      return null
    } catch {
      return null
    }
  }

  const saveFiltersToStorage = () => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        channel: filters.channel,
        period: filters.period,
        client_id: filters.client_id || null,
        campaign_ids: Array.isArray(filters.campaign_ids) ? filters.campaign_ids : [],
        vk_goal_action_ids: Array.isArray(filters.vk_goal_action_ids) ? filters.vk_goal_action_ids : [],
        start_date: filters.start_date || '',
        end_date: filters.end_date || ''
      }))
    } catch {
      // ignore
    }
  }

  const saved = loadFiltersFromStorage()
  const projectPeriodValues = [
    'today',
    'yesterday',
    'last_week',
    'last_month',
    'this_week',
    'this_month',
    'last_7_days',
    'last_30_days',
    'last_90_days',
    'last_365_days',
  ]
  const periodDaysMap = {
    '7': 7,
    '14': 14,
    '30': 30,
    '90': 90,
    '180': 180,
    '365': 365,
  }
  const validPeriods = [...Object.keys(periodDaysMap), ...projectPeriodValues, 'custom']
  const getCurrentPeriodRange = () => {
    if (projectPeriodValues.includes(filters.period)) {
      return getProjectPeriodRange(filters.period)
    }

    const end = new Date()
    const start = new Date()
    const periodDays = periodDaysMap[filters.period] || 7
    start.setTime(end.getTime() - (periodDays - 1) * 24 * 60 * 60 * 1000)
    return {
      startDate: start.toISOString().split('T')[0],
      endDate: end.toISOString().split('T')[0],
    }
  }

  // Filters state — инициализация из localStorage
  const filters = reactive({
    channel: (saved && validChannels.includes(saved.channel)) ? saved.channel : 'all',
    period: (saved && validPeriods.includes(saved.period)) ? saved.period : 'last_7_days',
    client_id: (saved && typeof saved.client_id === 'string' && saved.client_id.trim())
      ? saved.client_id
      : null,
    campaign_ids: Array.isArray(saved?.campaign_ids)
      ? saved.campaign_ids.filter(Boolean)
      : [],
    vk_goal_action_ids: Array.isArray(saved?.vk_goal_action_ids)
      ? saved.vk_goal_action_ids.filter(Boolean)
      : [],
    start_date: (saved?.period === 'custom' && saved?.start_date) ? saved.start_date : '',
    end_date: (saved?.period === 'custom' && saved?.end_date) ? saved.end_date : new Date().toISOString().split('T')[0]
  })

  // --- Logic Helpers ---

  const setInitialDates = () => {
    if (filters.period === 'custom' && filters.start_date && filters.end_date) {
      return // сохраняем выбранные даты для своего периода
    }
    const { startDate, endDate } = getCurrentPeriodRange()
    filters.start_date = startDate
    filters.end_date = endDate
  }

  const handlePeriodChange = async () => {
    if (filters.period === 'custom') {
      if (filters.start_date && filters.end_date) {
        fetchStats()
      }
      return
    }
    const { startDate: newStartDate, endDate: newEndDate } = getCurrentPeriodRange()
    
    // Only update if dates actually changed to avoid unnecessary API calls
    if (filters.start_date !== newStartDate || filters.end_date !== newEndDate) {
      filters.start_date = newStartDate
      filters.end_date = newEndDate
      
      // Explicitly fetch stats after period change
      fetchStats()
    }
  }

  // --- API Calls ---

  const fetchClients = async () => {
    // Проверяем наличие токена перед запросом
    const token = getAccessToken()
    if (!token) {
      console.log('[DashboardStats] No auth token, skipping clients fetch')
      return
    }

    loadingClients.value = true
    try {
      const { data } = await api.get('clients/')
      clients.value = data
    } catch (err) {
      // Игнорируем 401 ошибки (неавторизованный пользователь)
      if (err.response?.status === 401) {
        console.log('[DashboardStats] Unauthorized, skipping clients fetch')
        return
      }
      console.error('[DashboardStats] Error fetching clients:', err)
    } finally {
      loadingClients.value = false
    }
  }

  const fetchStats = async () => {
    // Проверяем наличие токена перед запросом
    const token = getAccessToken()
    if (!token) {
      console.log('[DashboardStats] No auth token, skipping stats fetch')
      loading.value = false
      return
    }

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
        campaign_ids: filters.campaign_ids.length > 0 ? filters.campaign_ids : undefined,
        goal_action_ids: (filters.channel === 'vk' && shouldFilterVkGoals())
          ? filters.vk_goal_action_ids
          : undefined
      }

      const [summaryRes, dynamicsRes, topClientsRes, campaignsRes, deviceStatsRes, placementsRes] = await Promise.allSettled([
        api.get('dashboard/summary', { params }),
        api.get('dashboard/dynamics', { params }),
        api.get('dashboard/top-clients'),
        api.get('dashboard/campaigns', { params }),
        api.get('dashboard/devices', { params }),
        api.get('dashboard/placements', { params })
      ])

      if (summaryRes.status === 'fulfilled') {
        const summaryData = summaryRes.value.data
        console.log('[DashboardStats] Summary data received:', summaryData)
        console.log('[DashboardStats] Balance:', summaryData.balance, 'Currency:', summaryData.currency)
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

      const devData = deviceStatsRes.status === 'fulfilled' ? deviceStatsRes.value.data : null
      deviceStats.value = Array.isArray(devData) && devData.length ? devData : [...DEVICE_STATS_MOCK]

      const plData = placementsRes.status === 'fulfilled' ? placementsRes.value.data : null
      placements.value = Array.isArray(plData) && plData.length ? plData : [...PLACEMENTS_MOCK]

      if (summaryRes.status === 'rejected' && dynamicsRes.status === 'rejected') {
        // Проверяем, не 401 ли это (неавторизованный пользователь)
        const isUnauthorized = summaryRes.reason?.response?.status === 401 || 
                              dynamicsRes.reason?.response?.status === 401
        if (!isUnauthorized) {
          error.value = 'Failed to load statistics'
        }
      }
    } catch (err) {
      // Игнорируем 401 ошибки (неавторизованный пользователь)
      if (err.response?.status === 401) {
        console.log('[DashboardStats] Unauthorized, skipping stats fetch')
        return
      }
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

      if (filters.channel === 'vk' && shouldFilterVkGoals()) {
        params.goal_action_ids = filters.vk_goal_action_ids
      }
      
      const { data } = await api.get('campaigns/', { params })
      
      // Format for dashboard: { id, name, external_id } (external_id для поиска)
      // Если name = "Campaign {id}" — показываем "Кампания (ID: X)" в списке
      const fmt = (c) => {
        let name = c.name || (c.external_id ? `Campaign ${c.external_id}` : null) || `Campaign ${c.id}`
        const extId = c.external_id || ''
        const m = name.match(/^Campaign\s+(\d+)$/i)
        if (m && extId) name = `Кампания (ID: ${extId})`
        else if (m && !extId) name = `Кампания (ID: ${m[1]})`
        return {
          id: c.id,
          name,
          external_id: extId,
          vk_goal_action_id: c.vk_goal_action_id,
          is_active: c.is_active !== false,
          // Реальный статус площадки — для цветных точек в дропдауне
          display_status: c.display_status || null,
        }
      }
      allCampaigns.value = data.map(fmt)
    } catch (err) {
      console.error('[DashboardStats] Error fetching campaign pool:', err)
      allCampaigns.value = []
    } finally {
      loadingCampaigns.value = false
    }
  }

  /** Для вкладки «По целям» в модалке — все VK кампании без фильтра по целям */
  const fetchAllCampaignsForGoalsTab = async () => {
    if (filters.channel !== 'vk' || !filters.client_id) {
      allCampaignsForGoalsTab.value = []
      return
    }
    try {
      const params = {
        client_id: filters.client_id,
        platform: 'vk',
        only_active: true
      }
      const { data } = await api.get('campaigns/', { params })
      const fmt = (c) => {
        let name = c.name || (c.external_id ? `Campaign ${c.external_id}` : null) || `Campaign ${c.id}`
        const extId = c.external_id || ''
        const m = name.match(/^Campaign\s+(\d+)$/i)
        if (m && extId) name = `Кампания (ID: ${extId})`
        else if (m && !extId) name = `Кампания (ID: ${m[1]})`
        return { id: c.id, name, external_id: extId, vk_goal_action_id: c.vk_goal_action_id }
      }
      allCampaignsForGoalsTab.value = data.map(fmt)
    } catch {
      allCampaignsForGoalsTab.value = []
    }
  }

  const shouldFilterVkGoals = () => {
    if (filters.channel !== 'vk') return false
    if (!vkGoalActions.value.length) return false
    if (!filters.vk_goal_action_ids || filters.vk_goal_action_ids.length === 0) return false
    // ИСПРАВЛЕНО: Всегда применять фильтр, если выбран VK и есть целевые действия
    // Даже если выбраны "Все действия", нужно фильтровать, чтобы показать ТОЛЬКО кампании с целями
    return true
  }

  const fetchVkGoalActions = async () => {
    if (filters.channel !== 'vk' || !filters.client_id) {
      vkGoalActions.value = []
      filters.vk_goal_action_ids = []
      return
    }
    loadingVkGoalActions.value = true
    try {
      const { data } = await api.get('campaigns/vk-goal-actions', {
        params: { client_id: filters.client_id }
      })
      vkGoalActions.value = Array.isArray(data) ? data : []
      const allIds = vkGoalActions.value.map(g => g.id).filter(Boolean)
      // НЕ подставляем все цели по умолчанию — иначе фильтр исключает кампании без vk_goal_action_id
      // и данные идут в ноль. Цели применяются только при явном выборе во вкладке «По целям».
      if (filters.vk_goal_action_ids && filters.vk_goal_action_ids.length > 0) {
        const normalized = filters.vk_goal_action_ids.filter(id => allIds.includes(id))
        filters.vk_goal_action_ids = normalized.length > 0 ? normalized : []
      }
    } catch (err) {
      console.error('[DashboardStats] Error fetching VK goal actions:', err)
      vkGoalActions.value = []
      filters.vk_goal_action_ids = []
    } finally {
      loadingVkGoalActions.value = false
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
      fetchVkGoalActions()
    }
  )

  // 2. Any relevant filter change -> Fetch Statistics
  watch(
    () => [
      filters.start_date, 
      filters.end_date, 
      filters.client_id, 
      filters.channel, 
      filters.campaign_ids,
      filters.vk_goal_action_ids
    ],
    (newVal, oldVal) => {
      // Only fetch if dates are actually set (not empty strings)
      if (filters.start_date && filters.end_date) {
        fetchStats()
      }
    },
    { deep: true }
  )

  // 3. VK goal actions change -> Refresh campaign pool
  watch(
    () => filters.vk_goal_action_ids,
    () => {
      if (filters.channel === 'vk' && filters.client_id) {
        filters.campaign_ids = []
        fetchCampaignPool()
      }
    },
    { deep: true }
  )

  // 4. Сохранять фильтры дашборда в localStorage при изменении
  watch(
    () => [
      filters.channel,
      filters.period,
      filters.client_id,
      filters.start_date,
      filters.end_date,
      filters.campaign_ids,
      filters.vk_goal_action_ids
    ],
    () => saveFiltersToStorage(),
    { deep: true }
  )

  onMounted(() => {
    setInitialDates()
    fetchClients()
    fetchCampaignPool()
    fetchVkGoalActions()
    fetchStats()
  })

  return {
    summary,
    dynamics,
    topClients,
    allCampaigns,
    allCampaignsForGoalsTab,
    campaigns,
    clients,
    deviceStats,
    placements,
    loading: computed(() => loading.value || loadingClients.value),
    loadingCampaigns,
    loadingVkGoalActions,
    vkGoalActions,
    error,
    filters,
    handlePeriodChange,
    fetchStats,
    fetchClients,
    fetchCampaignPool,
    fetchAllCampaignsForGoalsTab
  }
}
