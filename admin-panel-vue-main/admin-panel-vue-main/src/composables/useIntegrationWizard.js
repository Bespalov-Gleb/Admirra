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
  goals: false,
  finish: false
})

const campaigns = ref([])
const selectedCampaignIds = ref([])
const allFromProfile = ref(false)

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
      const { date_from, date_to } = getDateRangeParams()
      
      // 1. Discover campaigns from platform (creates/updates campaign records)
      const { data: campaignsData } = await api.post(`/integrations/${integrationId}/discover-campaigns`)
      
      // 2. Fetch aggregated stats from DB for the date range
      const { data: statsData } = await api.get(
        `/integrations/${integrationId}/campaigns-stats?date_from=${date_from}&date_to=${date_to}`
      )
      
      // 3. Merge stats into campaigns
      const statsMap = new Map(statsData.map(s => [s.id, s]))
      campaigns.value = campaignsData.map(campaign => ({
        ...campaign,
        impressions: statsMap.get(campaign.id)?.impressions || 0,
        clicks: statsMap.get(campaign.id)?.clicks || 0,
        cost: statsMap.get(campaign.id)?.cost || 0,
        conversions: statsMap.get(campaign.id)?.conversions || 0
      }))
      
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

  const fetchGoals = async (integrationId) => {
    loadingStates.goals = true
    try {
      const { date_from, date_to } = getDateRangeParams()
      // Send account_id to help backend find the right Metrika counter
      const accountIdParam = form.account_id ? `&account_id=${form.account_id}` : ''
      const { data } = await api.get(
        `/integrations/${integrationId}/goals?date_from=${date_from}&date_to=${date_to}${accountIdParam}`
      )
      goals.value = data
      
      // Auto-select primary goal based on conversion rate if not set
      if (data.length > 0 && !form.primary_goal_id) {
        const bestGoal = [...data].sort((a, b) => (b.conversion_rate || 0) - (a.conversion_rate || 0))[0]
        if (bestGoal) {
          form.primary_goal_id = bestGoal.id
          // Also auto-select it for tracking
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
      form.agency_client_login = integration.agency_client_login || integration.account_id
      if (integration.client) form.client_name = integration.client.name
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

  const selectPrimaryGoal = (id) => {
    form.primary_goal_id = id
  }

  const finishConnection = async () => {
    loadingStates.finish = true
    try {
      await api.patch(`/integrations/${lastIntegrationId.value}`, {
        selected_campaign_ids: [...selectedCampaignIds.value],
        all_campaigns: allFromProfile.value,
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
    goals,
    selectedGoalIds,
    allFromGoalsFromProfile,
    profiles,

    // Actions
    resetStore,
    fetchProfiles,
    fetchCampaigns,
    fetchGoals,
    fetchIntegration,
    finishConnection,
    toggleCampaignSelection,
    bulkSelectCampaigns,
    bulkDeselectCampaigns,
    bulkSelectGoals,
    bulkDeselectGoals,
    selectPrimaryGoal
  }
}
