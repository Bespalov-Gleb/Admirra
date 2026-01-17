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

  const fetchCampaigns = async (integrationId) => {
    loadingStates.campaigns = true
    try {
      const res = await api.post(`/integrations/${integrationId}/discover-campaigns`)
      campaigns.value = res.data
      // Keep existing selection if matching
      selectedCampaignIds.value = campaigns.value.filter(c => c.is_active).map(c => c.id)
    } catch (err) {
      error.value = "Ошибка при загрузке кампаний"
    } finally {
      loadingStates.campaigns = false
    }
  }

  const fetchGoals = async (integrationId) => {
    loadingStates.goals = true
    try {
      const res = await api.get(`/integrations/${integrationId}/goals`)
      goals.value = res.data
    } catch (err) {
      error.value = "Ошибка при загрузке целей"
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
      form.agency_client_login = integration.account_id
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
