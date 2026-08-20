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
  avito_client_id: '',
  avito_client_secret: '',
  avito_account_id: '',
  account_id: null,
  account_name: '',
  agency_client_login: '',
  is_agency: false,
  utm_source: 'avito-ads',
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
const countersFetched = ref(false) // была ли завершена загрузка счётчиков (чтобы не показывать «нет счётчиков» до первой загрузки)
const selectedCounterIds = ref([])
const allFromCounters = ref(false)

const goals = ref([])
const selectedGoalIds = ref([])
const allFromGoalsFromProfile = ref(false)

const profiles = ref([])

// №5: VK — шаг «что считать CPL». Какие типы событий VK считаем лидом для расчёта
// CPL. codes — канонические коды ЦД, уходят в integration.selected_goals; бэкенд
// по ним считает лид/CPL (см. stats.py /goals summable). По умолчанию — лид-типы.
const VK_CPL_OPTIONS = [
  { key: 'lead_forms', label: 'Лид-формы', codes: ['leadads', 'lead_forms', 'leadforms', 'leadgen', 'evt_51_lead_forms'], def: true },
  { key: 'site_conversions', label: 'Конверсии на сайте', codes: ['engagement', 'conversions', 'site_conversions', 'siteconversions', 'site_conversion'], def: true },
  { key: 'messages', label: 'Сообщения', codes: ['messages', 'vkmessages'], def: true },
  { key: 'purchases', label: 'Покупки / каталог', codes: ['storeproductssales', 'store_products_sales', 'catalogue_sales'], def: true },
  { key: 'community', label: 'Подписки в сообществе', codes: ['community', 'group_join', 'socialengagement', 'social_engagement', 'evt_41_community_actions'], def: false },
  { key: 'installs', label: 'Установки приложений', codes: ['appinstalls', 'app_install', 'app_installs', 'reengagement', 'playersengagement', 'mini_app', 'evt_43_miniapp_events'], def: false },
  { key: 'traffic', label: 'Трафик', codes: ['traffic'], def: false },
  { key: 'reach', label: 'Охват', codes: ['reach', 'premium_reach', 'premium_reach_network', 'general_ttm', 'branding', 'audiolistening', 'audio_listening'], def: false },
  { key: 'views', label: 'Просмотры', codes: ['videoviews', 'video_views', 'articleviews', 'article_views', 'storevisits', 'store_visits', 'dzen'], def: false },
]
const vkCplDefaultKeys = () => VK_CPL_OPTIONS.filter(o => o.def).map(o => o.key)
const vkCplSelected = ref(vkCplDefaultKeys())

export function useIntegrationWizard() {
  const toaster = useToaster()
  const router = useRouter()

  const resetStore = () => {
    currentStep.value = 1
    lastIntegrationId.value = null
    try {
      localStorage.removeItem('wizard_integration_id')
      localStorage.removeItem('metrika_integration_id')
    } catch (e) {}
    error.value = null
    form.platform = 'YANDEX_DIRECT'
    form.client_id = null
    form.client_name = ''
    form.avito_client_id = ''
    form.avito_client_secret = ''
    form.avito_account_id = ''
    form.account_id = null
    form.account_name = ''
    form.agency_client_login = ''
    form.is_agency = false
    form.utm_source = 'avito-ads'
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
    vkCplSelected.value = vkCplDefaultKeys()
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

  const metrikaAccountParam = () => {
    if (form.platform === 'AVITO_ADS') return ''
    const targetAccount = form.agency_client_login || form.account_id
    const normalizedAccount = String(targetAccount || '').trim()
    if (!normalizedAccount || normalizedAccount.toLowerCase().startsWith('porg-')) return ''
    return `&account_id=${encodeURIComponent(normalizedAccount)}`
  }

  const fetchCounters = async (integrationId) => {
    loadingStates.counters = true
    try {
      const accountIdParam = metrikaAccountParam()
      
      const campaignIdsParam = selectedCampaignIds.value.length > 0
        ? `&campaign_ids=${selectedCampaignIds.value.join(',')}`
        : ''
      
      const { data } = await api.get(`/integrations/${integrationId}/counters?${accountIdParam}${campaignIdsParam}`)
      
      counters.value = data.counters || []

      // Авто-выбор всех счётчиков — только когда их немного. При большом числе
      // (например Avito с сотней счётчиков) НЕ грузим тысячи целей сразу: пользователь
      // сам выбирает счётчик, и под него подгружаются цели (каскад, как в Яндексе).
      const AUTO_SELECT_COUNTER_LIMIT = 5
      if (counters.value.length <= AUTO_SELECT_COUNTER_LIMIT && selectedCounterIds.value.length === 0) {
        selectedCounterIds.value = counters.value.map(c => c.id)
      } else if (counters.value.length > AUTO_SELECT_COUNTER_LIMIT) {
        selectedCounterIds.value = []
      }
    } catch (err) {
      console.error('Failed to fetch counters:', err)
      toaster.warning('Не удалось загрузить счетчики Метрики.')
      counters.value = []
    } finally {
      loadingStates.counters = false
      countersFetched.value = true
    }
  }

  const fetchGoals = async (integrationId) => {
    loadingStates.goals = true
    try {
      if (form.platform === 'AVITO_ADS' && selectedCounterIds.value.length === 0) {
        goals.value = []
        selectedGoalIds.value = []
        form.primary_goal_id = null
        return
      }

      const { date_from, date_to } = getDateRangeParams()
      const accountIdParam = metrikaAccountParam()

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

      const goalIdSet = new Set(goals.value.map((g) => g.id))
      selectedGoalIds.value = selectedGoalIds.value.filter((id) => goalIdSet.has(id))
      if (form.primary_goal_id != null && !goalIdSet.has(form.primary_goal_id)) {
        form.primary_goal_id = null
      }

      // Автовыбор основной цели по конверсии, если ещё не выбрана
      if (goals.value.length > 0 && !form.primary_goal_id) {
        const bestGoal = [...goals.value].sort((a, b) => (b.conversion_rate || 0) - (a.conversion_rate || 0))[0]
        if (bestGoal) {
          form.primary_goal_id = bestGoal.id
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
      form.account_name = integration.account_name || ''
      form.utm_source = integration.utm_source || 'avito-ads'
      selectedCounterIds.value = Array.isArray(integration.selected_counters)
        ? integration.selected_counters.map(String)
        : []
      selectedGoalIds.value = Array.isArray(integration.selected_goals)
        ? integration.selected_goals.map(String)
        : []
      // CRITICAL: agency_client_login is separate from account_id
      // It's set when user selects a profile on step 2
      form.agency_client_login = integration.agency_client_login || integration.account_id
      if (integration.platform === 'AVITO_ADS' && integration.account_id) {
        form.avito_account_id = integration.account_id
      }
      // CRITICAL: client_name should be returned by backend via IntegrationResponse schema
      // If not present, try to get it from client object
      form.client_name = integration.client_name || (integration.client ? integration.client.name : null)
      if (!form.client_name && integration.client_id) {
        // Fallback: fetch client name separately if not in response
        console.warn('client_name not found in integration response, this should not happen')
      }
      return integration
    } catch (err) {
      error.value = "Ошибка при загрузке данных интеграции"
      return null
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
    if (form.primary_goal_id === id) {
      form.primary_goal_id = null
    } else {
      form.primary_goal_id = id
    }
  }

  // №5: VK CPL helpers
  const vkCplCodes = computed(() =>
    VK_CPL_OPTIONS.filter(o => vkCplSelected.value.includes(o.key)).flatMap(o => o.codes)
  )
  const vkCplSelectedLabels = computed(() =>
    VK_CPL_OPTIONS.filter(o => vkCplSelected.value.includes(o.key)).map(o => o.label)
  )
  const toggleVkCpl = (key) => {
    const i = vkCplSelected.value.indexOf(key)
    if (i > -1) vkCplSelected.value.splice(i, 1)
    else vkCplSelected.value.push(key)
  }

  const finishConnection = async () => {
    loadingStates.finish = true
    try {
      const isVk = form.platform === 'VK_ADS'
      await api.patch(`/integrations/${lastIntegrationId.value}`, {
        // VK: РК не выбираем — активируем все кампании кабинета.
        selected_campaign_ids: [...selectedCampaignIds.value],
        all_campaigns: isVk ? true : allFromProfile.value,
        selected_counters: [...selectedCounterIds.value],
        // VK: целей Метрики нет; primary_goal не используем.
        primary_goal_id: isVk ? null : form.primary_goal_id,
        // VK: selected_goals хранит выбор «что считать лидом для CPL».
        selected_goals: isVk ? [...vkCplCodes.value] : [...selectedGoalIds.value],
        account_name: form.account_name || null,
        ...(form.platform === 'AVITO_ADS' && { utm_source: form.utm_source || 'avito-ads' }),
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
    countersFetched,
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
    // №5: VK CPL step
    VK_CPL_OPTIONS,
    vkCplSelected,
    vkCplCodes,
    vkCplSelectedLabels,
    toggleVkCpl,
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
