import { ref, reactive, computed } from 'vue'
import api from '../api/axios'
import { useToaster } from './useToaster'
import { useRouter } from 'vue-router'

// Global State (persists across page navigations within the SPA)
const currentStep = ref(1)
const lastIntegrationId = ref(null)
const error = ref(null)

const form = reactive({
  platform: 'YANDEX_DIRECT',
  client_id: null,
  client_name: '',
  account_id: null,
  agency_client_login: '',
  primary_goal_id: null
})

const loadingStates = reactive({
  profiles: false,
  campaigns: false,
  counters: false,
  goals: false,
  finish: false
})

const campaigns = ref([])
const selectedCampaignIds = ref([])
const allFromProfile = ref(false)

const counters = ref([])
const selectedCounterIds = ref([])
const allFromCounters = ref(false)

const goals = ref([])
const selectedGoalIds = ref([])
const allFromGoalsFromProfile = ref(false)

const profiles = ref([])

export function useIntegrationWizard() {
  const toaster = useToaster()
  const router = useRouter()

  const resetStore = () => {
    currentStep.value = 1
    lastIntegrationId.value = null
    error.value = null
    form.client_id = null
    form.client_name = ''
    form.account_id = null
    form.agency_client_login = ''
    form.primary_goal_id = null
    campaigns.value = []
    selectedCampaignIds.value = []
    allFromProfile.value = false
    counters.value = []
    selectedCounterIds.value = []
    allFromCounters.value = false
    goals.value = []
    selectedGoalIds.value = []
    profiles.value = []
  }

  const fetchProfiles = async (integrationId) => {
    loadingStates.profiles = true
    try {
      const res = await api.get(`/integrations/${integrationId}/profiles`)
      profiles.value = res.data
    } catch (err) {
      error.value = "Ошибка при загрузке профилей"
    } finally {
      loadingStates.profiles = false
    }
  }

  const getDateRangeParams = () => {
    const now = new Date()
    const sevenDaysAgo = new Date(now)
    sevenDaysAgo.setDate(now.getDate() - 7)
    
    const formatDate = (date) => {
      const year = date.getFullYear()
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')
      return `${year}-${month}-${day}`
    }
    
    return {
      date_from: formatDate(sevenDaysAgo),
      date_to: formatDate(now)
    }
  }

  const fetchCampaigns = async (integrationId) => {
    loadingStates.campaigns = true
    try {
      // OPTIMIZATION: Only fetch campaigns and their status, no statistics
      // Statistics are heavy and slow down the wizard
      const { data: campaignsData } = await api.post(`/integrations/${integrationId}/discover-campaigns`)
      
      campaigns.value = campaignsData
      
      // Select active campaigns by default
      selectedCampaignIds.value = campaigns.value.filter(c => c.state === 'ON').map(c => c.id)
      
      // If none are active (newly discovered), select all
      if (selectedCampaignIds.value.length === 0) {
        selectedCampaignIds.value = campaigns.value.map(c => c.id)
      }
    } catch (err) {
      error.value = err.response?.data?.detail || "Ошибка при загрузке кампаний"
      toaster.error(error.value)
    } finally {
      loadingStates.campaigns = false
    }
  }

  const fetchCounters = async (integrationId) => {
    loadingStates.counters = true
    try {
      const targetAccount = form.agency_client_login || form.account_id
      const accountIdParam = targetAccount ? `&account_id=${targetAccount}` : ''
      
      const campaignIdsParam = selectedCampaignIds.value.length > 0
        ? `&campaign_ids=${selectedCampaignIds.value.join(',')}`
        : ''
      
      const { data } = await api.get(`/integrations/${integrationId}/counters?${accountIdParam}${campaignIdsParam}`)
      
      counters.value = data.counters || []
      
      // Auto-select all counters by default
      selectedCounterIds.value = counters.value.map(c => c.id)
    } catch (err) {
      console.error('Failed to fetch counters:', err)
      toaster.warning('Не удалось загрузить счетчики Метрики.')
      counters.value = []
    } finally {
      loadingStates.counters = false
    }
  }

  const fetchGoals = async (integrationId) => {
    loadingStates.goals = true
    try {
      const { date_from, date_to } = getDateRangeParams()
      // CRITICAL: Use agency_client_login if set, otherwise account_id
      // This ensures we filter Metrika counters by the selected profile
      const targetAccount = form.agency_client_login || form.account_id
      const accountIdParam = targetAccount ? `&account_id=${targetAccount}` : ''
      
      // CRITICAL: Priority 1: If counters are selected, use them
      // Priority 2: Otherwise, use selected campaign IDs
      let goalsUrl = `/integrations/${integrationId}/goals?date_from=${date_from}&date_to=${date_to}${accountIdParam}`
      
      if (selectedCounterIds.value.length > 0) {
        goalsUrl += `&counter_ids=${selectedCounterIds.value.join(',')}`
      } else if (selectedCampaignIds.value.length > 0) {
        goalsUrl += `&campaign_ids=${selectedCampaignIds.value.join(',')}`
      }

      // OPTIMIZATION: Only fetch goal names and types, no statistics
      // Statistics are heavy and slow down the wizard
      const { data } = await api.get(`${goalsUrl}&with_stats=false`)

      // CRITICAL: Handle both formats: array of goals OR object with goals and warning_message
      if (data && typeof data === 'object' && !Array.isArray(data) && data.goals) {
        goals.value = data.goals
        if (data.warning_message) {
          toaster.warning(data.warning_message)
        }
      } else {
        goals.value = Array.isArray(data) ? data : []
      }

      // Автовыбор основной цели по конверсии, если ещё не выбрана
      if (goals.value.length > 0 && !form.primary_goal_id) {
        const bestGoal = [...goals.value].sort((a, b) => (b.conversion_rate || 0) - (a.conversion_rate || 0))[0]
        if (bestGoal) {
          form.primary_goal_id = bestGoal.id
          if (!selectedGoalIds.value.includes(bestGoal.id)) {
            selectedGoalIds.value.push(bestGoal.id)
          }
        }
      }
    } catch (err) {
      console.error('Failed to fetch goals:', err)
      toaster.warning('Не удалось загрузить статистику целей Метрики.')
    } finally {
      loadingStates.goals = false
    }
  }

  const fetchIntegration = async (id) => {
    try {
      const res = await api.get(`/integrations/${id}`)
      const integration = res.data
      form.platform = integration.platform
      form.client_id = integration.client_id
      form.account_id = integration.account_id
      // CRITICAL: agency_client_login is separate from account_id
      // It's set when user selects a profile on step 2
      form.agency_client_login = integration.agency_client_login || integration.account_id
      // CRITICAL: client_name should be returned by backend via IntegrationResponse schema
      // If not present, try to get it from client object
      form.client_name = integration.client_name || (integration.client ? integration.client.name : null)
      if (!form.client_name && integration.client_id) {
        // Fallback: fetch client name separately if not in response
        console.warn('client_name not found in integration response, this should not happen')
      }
    } catch (err) {
      error.value = "Ошибка при загрузке данных интеграции"
    }
  }

  const toggleCampaignSelection = (id) => {
    const idx = selectedCampaignIds.value.indexOf(id)
    if (idx > -1) selectedCampaignIds.value.splice(idx, 1)
    else selectedCampaignIds.value.push(id)
    allFromProfile.value = false
  }

  const bulkSelectCampaigns = (ids) => {
    ids.forEach(id => {
      if (!selectedCampaignIds.value.includes(id)) {
        selectedCampaignIds.value.push(id)
      }
    })
  }

  const bulkDeselectCampaigns = (ids) => {
    selectedCampaignIds.value = selectedCampaignIds.value.filter(id => !ids.includes(id))
    allFromProfile.value = false
  }

  const bulkSelectGoals = (ids) => {
    ids.forEach(id => {
      if (!selectedGoalIds.value.includes(id)) {
        selectedGoalIds.value.push(id)
      }
    })
  }

  const bulkDeselectGoals = (ids) => {
    selectedGoalIds.value = selectedGoalIds.value.filter(id => !ids.includes(id))
  }

  const toggleCounterSelection = (id) => {
    const idx = selectedCounterIds.value.indexOf(id)
    if (idx > -1) selectedCounterIds.value.splice(idx, 1)
    else selectedCounterIds.value.push(id)
    allFromCounters.value = false
  }

  const bulkSelectCounters = (ids) => {
    ids.forEach(id => {
      if (!selectedCounterIds.value.includes(id)) {
        selectedCounterIds.value.push(id)
      }
    })
  }

  const bulkDeselectCounters = (ids) => {
    selectedCounterIds.value = selectedCounterIds.value.filter(id => !ids.includes(id))
    allFromCounters.value = false
  }

  const selectPrimaryGoal = (id) => {
    form.primary_goal_id = id
  }

  const finishConnection = async () => {
    loadingStates.finish = true
    try {
      await api.patch(`/integrations/${lastIntegrationId.value}`, {
        selected_campaign_ids: [...selectedCampaignIds.value],
        all_campaigns: allFromProfile.value,
        selected_counters: [...selectedCounterIds.value],
        primary_goal_id: form.primary_goal_id,
        selected_goals: [...selectedGoalIds.value],
        is_active: true
      })
      toaster.success("Интеграция успешно настроена!")
      resetStore()
      if (router) router.push('/settings')
    } catch (err) {
      error.value = "Ошибка при завершении настройки"
    } finally {
      loadingStates.finish = false
    }
  }

  return {
    // State
    currentStep,
    lastIntegrationId,
    error,
    form,
    loadingStates,
    campaigns,
    selectedCampaignIds,
    allFromProfile,
    counters,
    selectedCounterIds,
    allFromCounters,
    goals,
    selectedGoalIds,
    allFromGoalsFromProfile,
    profiles,

    // Actions
    resetStore,
    fetchProfiles,
    fetchCampaigns,
    fetchCounters,
    fetchGoals,
    fetchIntegration,
    finishConnection,
    toggleCampaignSelection,
    bulkSelectCampaigns,
    bulkDeselectCampaigns,
    toggleCounterSelection,
    bulkSelectCounters,
    bulkDeselectCounters,
    bulkSelectGoals,
    bulkDeselectGoals,
    selectPrimaryGoal
  }
}
