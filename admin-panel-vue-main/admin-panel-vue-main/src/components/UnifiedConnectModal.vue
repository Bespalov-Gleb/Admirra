<template>
  <div v-if="isOpen" class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-[100] animate-fade-in" @click.self="close">
    <div class="bg-white rounded-[2rem] p-0.5 w-full max-w-2xl shadow-[0_20px_50px_rgba(0,0,0,0.25)] transform transition-all animate-modal-in border border-gray-100 relative overflow-hidden">
      <!-- Decorative Background elements -->
      <div class="absolute top-0 right-0 w-32 h-32 bg-blue-50 rounded-full -mr-16 -mt-16 blur-2xl opacity-60"></div>
      <div class="absolute bottom-0 left-0 w-24 h-24 bg-red-50 rounded-full -ml-12 -mb-12 blur-2xl opacity-50"></div>

      <div class="relative z-10 flex flex-col max-h-[85vh] p-6">
        <!-- Header: Fixed -->
        <div class="flex items-center justify-between mb-2 flex-shrink-0">
          <div class="flex items-center gap-4">
            <div>
              <h3 class="text-xl font-black text-black tracking-tight leading-none uppercase">Добавить интеграцию</h3>
              <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mt-1">Шаг {{ currentStep }} из 5</p>
            </div>

            <!-- Global Date Selector for Preview (Steps 3-4) -->
            <div v-if="currentStep >= 3" class="flex items-center bg-gray-50 border border-gray-100 rounded-xl p-1 shadow-sm ml-4">
              <button 
                v-for="opt in dateRangeOptions" 
                :key="opt.value"
                @click="statsDateRange = opt.value"
                class="px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-tight transition-all"
                :class="statsDateRange === opt.value ? 'bg-white text-blue-600 shadow-sm border border-blue-100' : 'text-gray-400 hover:text-gray-600'"
              >
                {{ opt.label }}
              </button>
            </div>
          </div>

          <div class="flex items-center gap-3">
            <div class="flex flex-col items-end">
              <div class="flex gap-1">
                <div 
                  v-for="i in 5" 
                  :key="i"
                  class="h-1.5 rounded-full transition-all duration-500"
                  :class="[
                    i <= currentStep ? 'bg-blue-600 shadow-[0_0_8px_rgba(37,99,235,0.4)]' : 'bg-gray-100',
                    i === currentStep ? 'w-8' : 'w-4'
                  ]"
                ></div>
              </div>
            </div>
            <button @click="close" class="p-2 bg-gray-100 text-gray-500 hover:text-black hover:rotate-90 hover:bg-gray-200 transition-all rounded-full border border-gray-200 shadow-sm">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
            </button>
          </div>
        </div>

        <!-- Current Step Subtitle -->
        <div class="mb-4 flex-shrink-0 text-center">
           <p class="text-[10px] font-black text-blue-600 uppercase tracking-[0.2em] px-1">{{ stepLabels[currentStep] }}</p>
        </div>

        <!-- Step 1: Configuration (Platform & Project) -->
        <CustomScroll v-if="currentStep === 1" class="flex-grow">
          <IntegrationStep1 
            :modelValue="form"
            @update:modelValue="(newForm) => Object.assign(form, newForm)"
            v-model:isCreatingNewProject="isCreatingNewProject"
            :projects="projects"
            :error="error"
            :showToken="showToken"
            @next="nextStep"
            @openProjectSelector="isProjectSelectorOpen = true"
            @openPlatformSelector="isPlatformSelectorOpen = true"
          />
        </CustomScroll>

        <CustomScroll v-else-if="currentStep === 2" class="flex-grow">
          <IntegrationStep2 
            :profiles="profiles"
            :selectedAccountId="form.account_id"
            :loading="loadingProfiles"
            :platform="form.platform"
            @selectProfile="selectProfile"
            @next="nextStep"
          />
        </CustomScroll>


        <CustomScroll v-else-if="currentStep === 3" class="flex-grow">
          <IntegrationStep3 
            v-if="currentStep === 3" 
            :campaigns="campaigns"
            :selectedIds="selectedCampaignIds"
            :loading="loadingCampaigns"
            :platform="form.platform"
            :allFromProfile="allFromProfile"
            :currency="currentCurrency"
            @toggle="toggleCampaignSelection"
            @toggleAll="toggleAllCampaigns"
            @bulkSelect="bulkSelectCampaigns"
            @bulkDeselect="bulkDeselectCampaigns"
            @next="currentStep++"
          />
        </CustomScroll>

        <!-- Step 4: Goal Selection -->
        <CustomScroll v-else-if="currentStep === 4" class="flex-grow">
          <IntegrationStep4 
            :goals="goals"
            :primaryGoalId="form.primary_goal_id"
            :selectedGoalIds="selectedGoalIds"
            :loading="loadingGoals"
            :platform="form.platform"
            :allFromProfile="allGoalsFromProfile"
            :showValidationError="showValidationError"
            @bulkSelect="(ids) => selectedGoalIds = [...new Set([...selectedGoalIds, ...ids])]"
            @bulkDeselect="(ids) => selectedGoalIds = selectedGoalIds.filter(id => !ids.includes(id))"
            @toggleSecondary="toggleGoal"
            @selectPrimary="selectPrimaryGoal"
          />
        </CustomScroll>

        <!-- Step 5: Final Summary -->
        <CustomScroll v-else-if="currentStep === 5" class="flex-grow">
          <IntegrationStep5 
            :projectName="form.client_name"
            :selectedProfileName="selectedProfile?.name || 'Не выбран'"
            :selectedProfileLogin="form.account_id"
            :currency="currentCurrency"
            :selectedCampaignsList="selectedCampaignsList"
            :primaryGoalName="primaryGoal?.name"
            :secondaryGoalsList="secondaryGoalsList"
            :syncDepth="form.sync_depth"
            :autoSync="form.auto_sync"
          />
        </CustomScroll>

        <!-- Footer: Fixed -->
        <div class="flex gap-3 pt-6 mt-4 border-t border-gray-50 flex-shrink-0 bg-white">
          <button v-if="currentStep === 1" type="button" @click="close" class="flex-1 py-3.5 text-[10px] font-black uppercase tracking-widest border border-gray-200 rounded-2xl text-gray-400 hover:text-gray-700 hover:bg-gray-50 transition-all">
            Отмена
          </button>
          <button v-if="currentStep > 1" type="button" @click="prevStep" class="flex-1 py-3.5 text-[10px] font-black uppercase tracking-widest border border-gray-200 rounded-2xl text-gray-400 hover:text-gray-700 hover:bg-gray-50 transition-all">
            Назад
          </button>
          
          <!-- Step 1 Auth -->
          <button 
            v-if="currentStep === 1 && (form.platform === 'YANDEX_DIRECT' || form.platform === 'VK_ADS')"
            @click="form.platform === 'YANDEX_DIRECT' ? initYandexAuth() : initVKAuth()"
            :disabled="loadingAuth || (isCreatingNewProject && !form.client_name)"
            class="flex-[1.5] py-4 rounded-[1.25rem] text-white font-black text-[11px] uppercase tracking-widest transition-all flex items-center justify-center gap-2 shadow-lg hover:-translate-y-0.5 active:translate-y-0"
            :class="form.platform === 'YANDEX_DIRECT' ? 'bg-[#FF4B21] hover:bg-[#ff3d0d] shadow-[#FF4B21]/20' : 'bg-[#0077FF] hover:bg-[#0066EE] shadow-[#0077FF]/20'"
          >
            <div v-if="loadingAuth" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            <span v-else class="flex items-center gap-2">
              ПОДКЛЮЧИТЬ {{ form.platform === 'YANDEX_DIRECT' ? 'ЯНДЕКС ДИРЕКТ' : 'VK ADS' }}
            </span>
          </button>

          <!-- Step 2, 3 & 4 Next -->
          <button 
            v-else-if="currentStep >= 2 && currentStep <= 4" 
            @click="nextStep" 
            :disabled="isNextDisabled"
            class="flex-[1.5] py-3.5 bg-[#FF4B21] hover:bg-[#ff3d0d] text-white rounded-2xl hover:-translate-y-0.5 active:translate-y-0 font-black text-[10px] uppercase tracking-widest disabled:opacity-50 transition-all shadow-lg"
          >
            ДАЛЕЕ
          </button>
          
          <!-- Step 5 Finish -->
          <button 
            v-else-if="currentStep === 5" 
            @click="finishConnection" 
            :disabled="loadingFinish" 
            class="flex-[1.5] py-3.5 bg-blue-600 text-white rounded-2xl hover:bg-blue-700 hover:-translate-y-0.5 active:translate-y-0 font-black text-[10px] uppercase tracking-widest disabled:opacity-50 transition-all flex items-center justify-center gap-2 shadow-lg"
          >
            <div v-if="loadingFinish" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            <span>{{ loadingFinish ? 'СОХРАНЕНИЕ...' : 'ПОДКЛЮЧИТЬ' }}</span>
          </button>
        </div>

        <!-- Project Selection Modal Overlay -->
        <ProjectSelectionModal 
          :isOpen="isProjectSelectorOpen"
          :projects="projects"
          :selectedId="form.client_id"
          @close="isProjectSelectorOpen = false"
          @select="selectProject"
          @create="selectNewProject"
        />

        <!-- Platform Selection Modal Overlay -->
        <PlatformSelectionModal 
          :isOpen="isPlatformSelectorOpen"
          :selectedKey="form.platform"
          @close="isPlatformSelectorOpen = false"
          @select="selectPlatform"
        />

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api/axios'
import CustomScroll from './ui/CustomScroll.vue'
import { PLATFORMS } from '../constants/platformConfig'
import { useProjects } from '../composables/useProjects'
import { useToaster } from '../composables/useToaster'

const router = useRouter()

// Import Step Components
import IntegrationStep1 from './integration-steps/IntegrationStep1.vue'
import IntegrationStep2 from './integration-steps/IntegrationStep2.vue'
import IntegrationStep3 from './integration-steps/IntegrationStep3.vue'
import IntegrationStep4 from './integration-steps/IntegrationStep4.vue'
import IntegrationStep5 from './integration-steps/IntegrationStep5.vue'
import ProjectSelectionModal from './ProjectSelectionModal.vue'
import PlatformSelectionModal from './PlatformSelectionModal.vue'

const { projects, fetchProjects } = useProjects()
const toaster = useToaster()

const props = defineProps({
  isOpen: Boolean,
  initialClientName: {
    type: String,
    default: ''
  },
  resumeIntegrationId: {
    type: String,
    default: null
  },
  initialStep: {
    type: Number,
    default: 1
  }
})

const emit = defineEmits(['update:isOpen', 'success'])

const loading = ref(false)
const error = ref(null)
const showToken = ref(false)
const isCreatingNewProject = ref(false)
const showValidationError = ref(false)
const isProjectSelectorOpen = ref(false)
const isPlatformSelectorOpen = ref(false)

const isNextDisabled = computed(() => {
  if (currentStep.value === 1) {
    return !form.client_id && (!isCreatingNewProject.value || !form.client_name)
  }
  if (currentStep.value === 2) return !form.account_id || loadingProfiles.value
  if (currentStep.value === 3) return (!allFromProfile.value && selectedCampaignIds.value.length === 0) || loadingCampaigns.value
  if (currentStep.value === 4) return !form.primary_goal_id || loadingGoals.value
  return false
})

const selectedCampaignsList = computed(() => {
  return campaigns.value.filter(c => selectedCampaignIds.value.includes(c.id))
})

const selectedProfile = computed(() => {
  return profiles.value.find(p => p.login === form.account_id)
})

const primaryGoal = computed(() => {
  return goals.value.find(g => g.id === form.primary_goal_id)
})

const searchQuery = ref('')
const lastIntegrationId = ref(props.resumeIntegrationId)

const allFromProfile = computed({
  get: () => campaigns.value.length > 0 && selectedCampaignIds.value.length === campaigns.value.length,
  set: (val) => {
    if (val) {
      selectedCampaignIds.value = campaigns.value.map(c => c.id)
    } else {
      selectedCampaignIds.value = []
    }
  }
})

const allGoalsFromProfile = computed({
  get: () => goals.value.length > 0 && selectedGoalIds.value.length === goals.value.length,
  set: (val) => {
    if (val) {
      selectedGoalIds.value = goals.value.map(g => g.id)
    } else {
      selectedGoalIds.value = []
      // Keep primary goal if it exists? Usually cleaner to leave it or clear it too.
      // Let's keep primary goal if it's manually selected.
      if (form.primary_goal_id) selectedGoalIds.value = [form.primary_goal_id]
    }
  }
})

// Step 2-4 state
const currentStep = ref(props.initialStep || 1)
const statsDateRange = ref('30') // Days: 7, 30, 90, 365
const profiles = ref([])
const campaigns = ref([])
const goals = ref([])
const selectedCampaignIds = ref([])
const selectedGoalIds = ref([])
const loadingProfiles = ref(false)
const loadingCampaigns = ref(false)
const loadingGoals = ref(false)
const loadingFinish = ref(false)

const currentCurrency = computed(() => {
  const p = profiles.value.find(p => p.login === form.account_id)
  return p?.currency || 'RUB'
})

const dateRangeOptions = [
  { label: '7 дней', value: '7' },
  { label: '30 дней', value: '30' },
  { label: '90 дней', value: '90' },
  { label: '1 год', value: '365' }
]

const getDateRangeParams = () => {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - parseInt(statsDateRange.value))
  return {
    date_from: start.toISOString().split('T')[0],
    date_to: end.toISOString().split('T')[0]
  }
}

watch(statsDateRange, () => {
  if (currentStep.value === 3) fetchCampaigns(lastIntegrationId.value)
  if (currentStep.value === 4) fetchGoals(lastIntegrationId.value)
})

const stepLabels = {
  1: 'Настройка канала',
  2: 'Выбор профиля',
  3: 'Выбор кампаний',
  4: 'Настройка целей',
  5: 'Сводка настроек'
}

const sendRemoteLog = async (message, data = null) => {
  try {
    await api.post('integrations/remote-log', { message, data })
  } catch (err) {
    console.warn('Failed to send remote log:', err)
  }
}

const filteredProfiles = computed(() => {
  if (!searchQuery.value) return profiles.value
  const q = searchQuery.value.toLowerCase()
  return profiles.value.filter(p => 
    (p.name && p.name.toLowerCase().includes(q)) || 
    (p.login && p.login.toLowerCase().includes(q))
  )
})

const filteredCampaigns = computed(() => {
  if (!searchQuery.value) return campaigns.value
  const q = searchQuery.value.toLowerCase()
  return campaigns.value.filter(c => 
    (c.name && c.name.toLowerCase().includes(q)) || 
    (c.external_id && c.external_id.toString().includes(q))
  )
})

const form = reactive({
  platform: 'YANDEX_DIRECT',
  client_id: null, // Selected project ID
  client_name: props.initialClientName, // Keep for legacy or if creating new inline
  access_token: '',
  refresh_token: '',
  account_id: '',
  client_id_platform: '', // Rename if needed, but the backend might expect 'client_id' for some platforms
  client_secret: '',
  sync_depth: 90, // Days of history to sync initially
  auto_sync: true
})

const currentPlatform = computed(() => PLATFORMS[form.platform])

watch(() => props.isOpen, async (newVal) => {
  if (newVal) {
    if (props.resumeIntegrationId) {
      lastIntegrationId.value = props.resumeIntegrationId
      currentStep.value = props.initialStep || 2
      // Load integration details (client_id, client_name, platform) first
      await fetchIntegrationDetails(props.resumeIntegrationId)
      if (currentStep.value === 2) fetchProfiles(props.resumeIntegrationId)
      if (currentStep.value === 3) fetchCampaigns(props.resumeIntegrationId)
      if (currentStep.value === 4) fetchGoals(props.resumeIntegrationId)
    } else {
      // Default to picking project first
      form.client_name = props.initialClientName
      form.client_id = null
      isCreatingNewProject.value = false
      error.value = null
      currentStep.value = 1
      campaigns.value = []
      selectedCampaignIds.value = []
      selectedGoalIds.value = []
    }
  }
})

const selectPlatform = (key) => {
  form.platform = key
  isPlatformSelectorOpen.value = false
}

const close = () => {
  sendRemoteLog('Modal Closed')
  emit('update:isOpen', false)
  error.value = null
  showValidationError.value = false
}

const selectProject = (project) => {
  form.client_id = project.id
  form.client_name = project.name
  isCreatingNewProject.value = false
  isProjectSelectorOpen.value = false
}

const selectNewProject = () => {
  form.client_id = null
  form.client_name = ''
  isCreatingNewProject.value = true
  isProjectSelectorOpen.value = false
}

onMounted(() => {
  fetchProjects()
  if (props.resumeIntegrationId && props.isOpen) {
    lastIntegrationId.value = props.resumeIntegrationId
    currentStep.value = props.initialStep || 2
    if (currentStep.value === 2) fetchProfiles(props.resumeIntegrationId)
    if (currentStep.value === 3) fetchCampaigns(props.resumeIntegrationId)
    if (currentStep.value === 4) fetchGoals(props.resumeIntegrationId)
  }
})

const nextStep = async () => {
  searchQuery.value = '' // Reset search on step change
  if (currentStep.value === 1) {
    handleSubmit()
  } else if (currentStep.value === 2) {
    // CRITICAL: Validate profile is selected before moving to campaigns
    if (form.platform === 'YANDEX_DIRECT' && !form.account_id) {
      toaster.error('Пожалуйста, выберите профиль перед переходом к кампаниям')
      return
    }
    currentStep.value = 3
    sendRemoteLog(`Moved to Step 3`)
    await fetchCampaigns(lastIntegrationId.value)
  } else {
    currentStep.value++
    sendRemoteLog(`Moved to Step ${currentStep.value}`)
    if (currentStep.value === 2) fetchProfiles(lastIntegrationId.value)
    if (currentStep.value === 4) fetchGoals(lastIntegrationId.value)
  }
}

const prevStep = () => {
  searchQuery.value = '' // Reset search
  if (currentStep.value > 1) {
    currentStep.value--
    sendRemoteLog(`Moved back to Step ${currentStep.value}`)
  }
}

const fetchIntegrationDetails = async (integrationId) => {
  try {
    const { data } = await api.get(`integrations/${integrationId}`)
    if (data) {
      form.client_id = data.client_id
      form.client_name = data.client_name || 'Не выбран'
      form.platform = data.platform
      form.account_id = data.account_id || ''
      sendRemoteLog('Integration Details Loaded', { 
        client_id: data.client_id, 
        client_name: data.client_name,
        platform: data.platform
      })
    }
  } catch (err) {
    console.error('Failed to fetch integration details:', err)
    toaster.error('Не удалось загрузить данные интеграции.')
  }
}

const fetchProfiles = async (integrationId) => {
  loadingProfiles.value = true
  try {
    const { data } = await api.get(`integrations/${integrationId}/profiles`)
    profiles.value = data
  } catch (err) {
    console.error('Failed to fetch profiles:', err)
    toaster.error('Не удалось загрузить профили. Проверьте соединение.')
  } finally {
    loadingProfiles.value = false
  }
}

const selectProfile = async (profile) => {
  if (form.account_id === profile.login) return // No change
  
  form.account_id = profile.login
  // Reset dependent state
  error.value = null
  campaigns.value = []
  selectedCampaignIds.value = []
  goals.value = []
  selectedGoalIds.value = []
  form.primary_goal_id = null

  try {
    // Update integration with selected sub-account/profile if needed
    // For Yandex Agency, we might need to store agency_client_login
    await api.patch(`integrations/${lastIntegrationId.value}`, { 
      account_id: profile.login,
      agency_client_login: profile.login 
    })
    sendRemoteLog('Profile Selected', { login: profile.login })
    
    // IMPORTANT: Re-fetch campaigns for the newly selected profile
    fetchCampaigns(lastIntegrationId.value)
  } catch (err) {
    toaster.error('Ошибка при выборе профиля. Попробуйте еще раз.')
  }
}

const toggleCampaign = (id) => {
  const index = selectedCampaignIds.value.indexOf(id)
  if (index > -1) {
    selectedCampaignIds.value.splice(index, 1)
  } else {
    selectedCampaignIds.value.push(id)
  }
}

const bulkSelectCampaigns = (ids) => {
  selectedCampaignIds.value = [...new Set([...selectedCampaignIds.value, ...ids])]
}

const bulkDeselectCampaigns = (ids) => {
  selectedCampaignIds.value = selectedCampaignIds.value.filter(id => !ids.includes(id))
}

const fetchGoals = async (integrationId) => {
  loadingGoals.value = true
  try {
    const { date_from, date_to } = getDateRangeParams()
    // We send account_id to help backend find the right counter
    const { data } = await api.get(`integrations/${integrationId}/goals?account_id=${form.account_id}&date_from=${date_from}&date_to=${date_to}`)
    goals.value = data
    
    // Auto-select primary goal if not set
    if (data.length > 0 && !form.primary_goal_id) {
      const bestGoal = [...data].sort((a, b) => (b.conversion_rate || 0) - (a.conversion_rate || 0))[0]
      if (bestGoal) {
        selectPrimaryGoal(bestGoal.id)
      }
    }
  } catch (err) {
    console.error('Failed to fetch goals:', err)
    toaster.warning('Не удалось загрузить статистику целей Метрики.')
  } finally {
    loadingGoals.value = false
  }
}

const selectPrimaryGoal = (goalId) => {
  form.primary_goal_id = goalId
  // Also auto-select it for tracking if not already selected
  if (!selectedGoalIds.value.includes(goalId)) {
    selectedGoalIds.value.push(goalId)
  }
}

const toggleGoal = (id) => {
  const index = selectedGoalIds.value.indexOf(id)
  if (index > -1) {
    selectedGoalIds.value.splice(index, 1)
  } else {
    selectedGoalIds.value.push(id)
  }
}

const toggleAllGoals = () => {
  allGoalsFromProfile.value = !allGoalsFromProfile.value
}

const handleSubmit = async () => {
  if (loading.value) return
  
  // Validation: Ensure project is selected or a new name is provided
  if (!form.client_id && (!isCreatingNewProject.value || !form.client_name)) {
    error.value = 'Пожалуйста, выберите проект или укажите название нового'
    return
  }

  loading.value = true
  error.value = null

  try {
    const { data } = await api.post('integrations/', form)
    lastIntegrationId.value = data.id
    
    // NEW: Update account_id from backend auto-detection
    if (data.account_id) {
      form.account_id = data.account_id
    }
    
    // Transition to step 2
    currentStep.value = 2
    fetchProfiles(data.id) // IMPORTANT: Fetch profiles first
    // NOTE: fetchCampaigns will be called after profile selection in selectProfile function
    
  } catch (err) {
    error.value = err.response?.data?.detail || 'Ошибка подключения'
  } finally {
    loading.value = false
  }
}

const fetchCampaigns = async (integrationId) => {
  loadingCampaigns.value = true
  try {
    const { date_from, date_to } = getDateRangeParams()
    
    // 1. Discover campaigns from platform (creates/updates campaign records)
    const { data: campaignsData } = await api.post(`integrations/${integrationId}/discover-campaigns`)
    
    // 2. Fetch aggregated stats from DB for the date range
    const { data: statsData } = await api.get(
      `integrations/${integrationId}/campaigns-stats?date_from=${date_from}&date_to=${date_to}`
    )
    
    // 3. Merge stats into campaigns
    // IMPORTANT: campaignsData is array of campaign objects with id, name, etc.
    // statsData is array of stats objects with id, impressions, clicks, cost, conversions
    const statsMap = new Map(statsData.map(s => [s.id, s]))
    campaigns.value = campaignsData.map(campaign => {
      const stats = statsMap.get(campaign.id)
      return {
        ...campaign,
        impressions: stats?.impressions || 0,
        clicks: stats?.clicks || 0,
        cost: stats?.cost || 0,
        conversions: stats?.conversions || 0
      }
    })
    
    // Filter out template campaigns on frontend as well (double check)
    campaigns.value = campaigns.value.filter(c => {
      const nameLower = c.name?.toLowerCase().trim() || ''
      const templateNames = ['campaignname', 'test campaign', 'тест', 'test', 'шаблон', 'template']
      return !templateNames.includes(nameLower) && nameLower !== 'campaignname'
    })
    
    // Select active campaigns by default
    selectedCampaignIds.value = campaigns.value.filter(c => c.state === 'ON').map(c => c.id)
    
    // If none are active (newly discovered), select all
    if (selectedCampaignIds.value.length === 0) {
      selectedCampaignIds.value = campaigns.value.map(c => c.id)
    }
  } catch (err) {
    console.error('Failed to fetch campaigns:', err)
    toaster.error(err.response?.data?.detail || 'Не удалось загрузить список кампаний.')
  } finally {
    loadingCampaigns.value = false
  }
}

const toggleAllCampaigns = () => {
  allFromProfile.value = !allFromProfile.value
}

const finishConnection = async () => {
  // Validation: Ensure primary goal is selected if goals exist
  if (goals.value.length > 0 && !form.primary_goal_id) {
    showValidationError.value = true
    return
  }

  loadingFinish.value = true
  error.value = null
  try {
    // 1. Update campaign statuses in bulk (only selected are active)
    const campaignUpdates = campaigns.value.map(c => ({
      id: c.id,
      is_active: selectedCampaignIds.value.includes(c.id)
    }))
    
    // 2. Wrap promises
    const bulkUpdatePromise = api.put('campaigns/bulk-update', campaignUpdates)
    
    const integrationPromise = api.patch(`integrations/${lastIntegrationId.value}`, {
      selected_goals: selectedGoalIds.value,
      primary_goal_id: form.primary_goal_id,
      auto_sync: form.auto_sync,
      sync_interval: 1440 // Daily
    })
    
    await Promise.all([bulkUpdatePromise, integrationPromise])
    
    // 3. Trigger initial sync automatically (sync_depth days)
    try {
      await api.post(`integrations/${lastIntegrationId.value}/sync`, { days: form.sync_depth })
    } catch (syncErr) {
      console.warn('Initial sync failed, but integration was saved:', syncErr)
    }
    
    toaster.success('Интеграция успешно настроена!')
    emit('success', { integration_id: lastIntegrationId.value })
    close()
  } catch (err) {
    console.error('Failed to finalize integration:', err)
    toaster.error('Ошибка при сохранении настроек.')
  } finally {
    loadingFinish.value = false
  }
}

import {
  PlusIcon
} from '@heroicons/vue/24/outline'

const loadingAuth = ref(false)

const initYandexAuth = async () => {
  loadingAuth.value = true
  try {
    // Generate callback URL based on current domain (localhost or admirra.ru)
    const redirectUri = `${window.location.origin}/auth/yandex/callback`
    
    // Save client name to local storage to retrieve it after callback
    if (form.client_name) {
      localStorage.setItem('yandex_auth_client_name', form.client_name)
    }
    
    const { data } = await api.get(`integrations/yandex/auth-url?redirect_uri=${encodeURIComponent(redirectUri)}`)
    if (data.url) {
      window.location.href = data.url
    }
  } catch (err) {
    console.error(err)
    error.value = 'Не удалось инициализировать авторизацию Яндекс'
    loadingAuth.value = false
  }
}

const initVKAuth = async () => {
  loadingAuth.value = true
  try {
    const redirectUri = `${window.location.origin}/auth/vk/callback`
    
    console.log('[initVKAuth] Starting VK ID SDK authorization...')
    console.log('[initVKAuth] Redirect URI:', redirectUri)
    console.log('[initVKAuth] Client name:', form.client_name)
    console.log('[initVKAuth] Client ID:', form.client_id)
    
    if (form.client_name) {
      localStorage.setItem('vk_auth_client_name', form.client_name)
    }
    if (form.client_id) {
      localStorage.setItem('vk_auth_client_id', form.client_id)
    }
    
    // Получаем конфигурацию для VK ID SDK
    const { data } = await api.get(`integrations/vk/auth-url?redirect_uri=${encodeURIComponent(redirectUri)}`)
    console.log('[initVKAuth] Config received:', data)
    
    // Загружаем VK ID SDK если еще не загружен
    if (!window.VKIDSDK) {
      const script = document.createElement('script')
      script.src = data.sdk_url || 'https://unpkg.com/@vkid/sdk@<3.0.0/dist-sdk/umd/index.js'
      script.onload = () => {
        initializeVKIDSDK(data.client_id, redirectUri)
      }
      script.onerror = () => {
        console.error('[initVKAuth] Failed to load VK ID SDK')
        error.value = 'Не удалось загрузить VK ID SDK'
        loadingAuth.value = false
      }
      document.head.appendChild(script)
    } else {
      initializeVKIDSDK(data.client_id, redirectUri)
    }
  } catch (err) {
    console.error('[initVKAuth] Error:', err)
    console.error('[initVKAuth] Error response:', err.response)
    error.value = err.response?.data?.detail || 'Не удалось инициализировать авторизацию VK'
    loadingAuth.value = false
  }
}

const initializeVKIDSDK = (clientId, redirectUri) => {
  try {
    const VKID = window.VKIDSDK
    
    if (!VKID) {
      throw new Error('VK ID SDK not loaded')
    }
    
    // Инициализируем конфигурацию VK ID SDK
    VKID.Config.init({
      app: parseInt(clientId),
      redirectUrl: redirectUri,
      responseMode: VKID.ConfigResponseMode.Callback,
      source: VKID.ConfigSource.LOWCODE,
      scope: '' // Для VK Ads может потребоваться указать scope, но пока оставляем пустым
    })
    
    console.log('[initVKAuth] VK ID SDK initialized')
    
    // Создаем виджет One Tap
    const oneTap = new VKID.OneTap()
    
    // Находим контейнер для виджета (можно создать динамически)
    let container = document.getElementById('vk-id-widget-container')
    if (!container) {
      container = document.createElement('div')
      container.id = 'vk-id-widget-container'
      container.style.position = 'fixed'
      container.style.top = '50%'
      container.style.left = '50%'
      container.style.transform = 'translate(-50%, -50%)'
      container.style.zIndex = '10000'
      container.style.background = 'white'
      container.style.padding = '20px'
      container.style.borderRadius = '12px'
      container.style.boxShadow = '0 4px 20px rgba(0,0,0,0.15)'
      document.body.appendChild(container)
    }
    
    // Рендерим виджет
    oneTap.render({
      container: container,
      showAlternativeLogin: true
    })
    .on(VKID.WidgetEvents.ERROR, (error) => {
      console.error('[initVKAuth] VK ID SDK error:', error)
      error.value = error.message || 'Ошибка авторизации VK ID'
      loadingAuth.value = false
      if (container && container.parentNode) {
        container.parentNode.removeChild(container)
      }
    })
    .on(VKID.OneTapInternalEvents.LOGIN_SUCCESS, async (payload) => {
      console.log('[initVKAuth] VK ID login success:', payload)
      const code = payload.code
      const deviceId = payload.device_id
      
      try {
        // Обмениваем code на токен через бэкенд
        const response = await api.post('integrations/vk/exchange', {
          code,
          device_id: deviceId,
          redirect_uri: redirectUri,
          client_name: form.client_name,
          client_id: form.client_id
        })
        
        console.log('[initVKAuth] Token exchange successful:', response.data)
        
        // Удаляем контейнер виджета
        if (container && container.parentNode) {
          container.parentNode.removeChild(container)
        }
        
        // Переходим к следующему шагу
        const integrationId = response.data.integration_id
        if (integrationId) {
          router.push(`/integrations/wizard?resume_integration_id=${integrationId}&initial_step=2`)
        } else {
          nextStep()
        }
        
        loadingAuth.value = false
      } catch (exchangeErr) {
        console.error('[initVKAuth] Token exchange error:', exchangeErr)
        error.value = exchangeErr.response?.data?.detail || 'Не удалось обменять код на токен'
        loadingAuth.value = false
        if (container && container.parentNode) {
          container.parentNode.removeChild(container)
        }
      }
    })
    
    console.log('[initVKAuth] VK ID One Tap widget rendered')
  } catch (err) {
    console.error('[initVKAuth] Failed to initialize VK ID SDK:', err)
    error.value = 'Не удалось инициализировать VK ID SDK'
    loadingAuth.value = false
  }
}
</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}
.animate-modal-in {
  animation: modalIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.animate-slide-down {
  animation: slideDown 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
.animate-shake {
  animation: shake 0.6s cubic-bezier(.36,.07,.19,.97) both;
}

@keyframes fadeIn {
  from { opacity: 0; backdrop-filter: blur(0); }
  to { opacity: 1; backdrop-filter: blur(4px); }
}

@keyframes modalIn {
  from { opacity: 0; transform: scale(0.95) translateY(20px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

@keyframes slideDown {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes shake {
  10%, 90% { transform: translate3d(-1px, 0, 0); }
  20%, 80% { transform: translate3d(2px, 0, 0); }
  30%, 50%, 70% { transform: translate3d(-4px, 0, 0); }
  40%, 60% { transform: translate3d(4px, 0, 0); }
}
</style>
