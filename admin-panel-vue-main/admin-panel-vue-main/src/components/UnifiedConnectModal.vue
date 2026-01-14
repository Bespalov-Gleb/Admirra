<template>
  <div v-if="isOpen" class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-[100] animate-fade-in" @click.self="close">
    <div class="bg-white rounded-[2rem] p-0.5 w-full max-w-md shadow-[0_20px_50px_rgba(0,0,0,0.25)] transform transition-all animate-modal-in border border-gray-100 relative overflow-hidden">
      <!-- Decorative Background elements -->
      <div class="absolute top-0 right-0 w-32 h-32 bg-blue-50 rounded-full -mr-16 -mt-16 blur-2xl opacity-60"></div>
      <div class="absolute bottom-0 left-0 w-24 h-24 bg-red-50 rounded-full -ml-12 -mb-12 blur-2xl opacity-50"></div>

      <div class="relative z-10 flex flex-col max-h-[85vh] p-6">
        <!-- Header: Fixed -->
        <div class="flex items-center justify-between mb-2 flex-shrink-0">
          <div>
            <h3 class="text-xl font-black text-black tracking-tight leading-none uppercase">Добавить интеграцию</h3>
            <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mt-1">Новый рекламный канал</p>
          </div>
          <button @click="close" class="p-2 bg-gray-50 text-gray-500 hover:text-black hover:rotate-90 hover:bg-gray-100 transition-all rounded-full border border-gray-100 shadow-sm">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
          </button>
        </div>

        <!-- Visual Stepper: Dots and Lines -->
        <div class="flex items-center justify-between px-4 mb-8 flex-shrink-0">
          <div v-for="step in 4" :key="step" class="flex items-center flex-1 last:flex-none">
            <!-- Circle -->
            <div 
              class="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-black transition-all duration-300"
              :class="[
                currentStep >= step ? 'bg-blue-600 text-white shadow-lg shadow-blue-200' : 'bg-gray-100 text-gray-400',
                currentStep === step ? 'ring-4 ring-blue-50 scale-110' : ''
              ]"
            >
              {{ step }}
            </div>
            <!-- Line -->
            <div 
              v-if="step < 4" 
              class="flex-1 h-0.5 mx-2 rounded-full transition-all duration-500"
              :class="currentStep > step ? 'bg-blue-600' : 'bg-gray-100'"
            ></div>
          </div>
        </div>

        <!-- Current Step Subtitle -->
        <div class="mb-4 flex-shrink-0">
           <p class="text-[10px] font-black text-blue-600 uppercase tracking-[0.2em] px-1">{{ stepLabels[currentStep] }}</p>
        </div>

        <!-- Step 1: Configuration (Platform & Project) -->
        <CustomScroll v-if="currentStep === 1" class="flex-grow">
          <IntegrationStep1 
            v-model="form"
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
            @openProfileSelector="isProfileSelectorOpen = true"
            @next="nextStep"
          />
        </CustomScroll>


        <CustomScroll v-else-if="currentStep === 3" class="flex-grow">
          <IntegrationStep3 
            :campaigns="campaigns"
            :selectedIds="selectedCampaignIds"
            :loading="loadingCampaigns"
            :platform="form.platform"
            :allFromProfile="allFromProfile"
            @openCampaignSelector="isCampaignSelectorOpen = true"
            @toggleAll="toggleAllCampaigns"
            @next="nextStep"
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
            @openGoalSelector="isGoalSelectorOpen = true"
            @toggleAll="toggleAllGoals"
            @toggleSecondary="toggleGoal"
            @selectPrimary="selectPrimaryGoal"
            @finish="finishConnection"
          />
        </CustomScroll>

        <!-- Footer: Fixed -->
        <div class="flex gap-3 pt-6 mt-4 border-t border-gray-50 flex-shrink-0 bg-white">
          <button v-if="currentStep <= 3" type="button" @click="close" class="flex-1 py-3.5 text-[10px] font-black uppercase tracking-widest border border-gray-200 rounded-2xl text-gray-400 hover:text-gray-700 hover:bg-gray-50 transition-all">
            Отмена
          </button>
          <button v-else type="button" @click="prevStep" class="flex-1 py-3.5 text-[10px] font-black uppercase tracking-widest border border-gray-200 rounded-2xl text-gray-400 hover:text-gray-700 hover:bg-gray-50 transition-all">Назад</button>
          
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

          <!-- No right button for step 2 & 3 in footer, use the content button -->
          
          <button v-else-if="currentStep === 4" @click="finishConnection" :disabled="loadingFinish" class="flex-[1.5] py-3.5 bg-blue-600 text-white rounded-2xl hover:bg-blue-700 hover:-translate-y-0.5 active:translate-y-0 font-black text-[10px] uppercase tracking-widest disabled:opacity-50 transition-all flex items-center justify-center gap-2 shadow-lg">
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

        <!-- Profile Selection Modal Overlay -->
        <ProfileSelectionModal 
          :isOpen="isProfileSelectorOpen"
          :profiles="profiles"
          :selectedAccountId="form.account_id"
          :loading="loadingProfiles"
          @close="isProfileSelectorOpen = false"
          @select="selectProfile"
        />

        <!-- Campaign Selection Modal Overlay -->
        <CampaignSelectionModal 
          :isOpen="isCampaignSelectorOpen"
          :campaigns="campaigns"
          :selectedIds="selectedCampaignIds"
          :loading="loadingCampaigns"
          @close="isCampaignSelectorOpen = false"
          @toggle="toggleCampaign"
        />

        <!-- Goal Selection Modal Overlay -->
        <GoalSelectionModal 
          :isOpen="isGoalSelectorOpen"
          :goals="goals"
          :selectedId="form.primary_goal_id"
          :loading="loadingGoals"
          @close="isGoalSelectorOpen = false"
          @select="selectPrimaryGoal"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, computed, onMounted } from 'vue'
import api from '../api/axios'
import CustomScroll from './ui/CustomScroll.vue'
import { PLATFORMS } from '../constants/platformConfig'
import { useProjects } from '../composables/useProjects'

// Import Step Components
import IntegrationStep1 from './integration-steps/IntegrationStep1.vue'
import IntegrationStep2 from './integration-steps/IntegrationStep2.vue'
import IntegrationStep3 from './integration-steps/IntegrationStep3.vue'
import IntegrationStep4 from './integration-steps/IntegrationStep4.vue'
import ProjectSelectionModal from './ProjectSelectionModal.vue'
import PlatformSelectionModal from './PlatformSelectionModal.vue'
import ProfileSelectionModal from './ProfileSelectionModal.vue'
import CampaignSelectionModal from './CampaignSelectionModal.vue'
import GoalSelectionModal from './GoalSelectionModal.vue'

const { projects, fetchProjects } = useProjects()

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
const isProfileSelectorOpen = ref(false)
const isCampaignSelectorOpen = ref(false)
const isGoalSelectorOpen = ref(false)
const allFromProfile = ref(false)
const allGoalsFromProfile = ref(false)

// Step 2-4 state
const currentStep = ref(props.initialStep || 1)
const profiles = ref([])
const campaigns = ref([])
const goals = ref([])
const selectedCampaignIds = ref([])
const selectedGoalIds = ref([])
const loadingProfiles = ref(false)
const loadingCampaigns = ref(false)
const loadingGoals = ref(false)
const loadingFinish = ref(false)
const searchQuery = ref('')
const lastIntegrationId = ref(props.resumeIntegrationId)

const stepLabels = {
  1: 'Настройка канала',
  2: 'Выбор профиля',
  3: 'Выбор кампаний',
  4: 'Настройка целей'
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
    (c.external_id && c.external_id.toLowerCase().includes(q))
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
  client_secret: ''
})

const currentPlatform = computed(() => PLATFORMS[form.platform])

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    if (props.resumeIntegrationId) {
      lastIntegrationId.value = props.resumeIntegrationId
      currentStep.value = props.initialStep || 2
      if (currentStep.value === 2) fetchProfiles(props.resumeIntegrationId)
      if (currentStep.value === 3) fetchCampaigns(props.resumeIntegrationId)
      if (currentStep.value === 4) fetchGoals(props.resumeIntegrationId)
    } else {
      form.client_name = props.initialClientName
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
  projectDropdownOpen.value = false
}

const selectNewProject = () => {
  form.client_id = null
  form.client_name = ''
  isCreatingNewProject.value = true
  projectDropdownOpen.value = false
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

const nextStep = () => {
  searchQuery.value = '' // Reset search on step change
  if (currentStep.value === 1) {
    handleSubmit()
  } else {
    currentStep.value++
    sendRemoteLog(`Moved to Step ${currentStep.value}`)
    if (currentStep.value === 2) fetchProfiles(lastIntegrationId.value)
    if (currentStep.value === 3) fetchCampaigns(lastIntegrationId.value)
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

const fetchProfiles = async (integrationId) => {
  loadingProfiles.value = true
  try {
    const { data } = await api.get(`integrations/${integrationId}/profiles`)
    profiles.value = data
  } catch (err) {
    console.error('Failed to fetch profiles:', err)
    error.value = 'Не удалось загрузить профили'
  } finally {
    loadingProfiles.value = false
  }
}

const selectProfile = async (profile) => {
  form.account_id = profile.login
  try {
    // Update integration with selected sub-account/profile if needed
    // For Yandex Agency, we might need to store agency_client_login
    await api.patch(`integrations/${lastIntegrationId.value}`, { 
      account_id: profile.login,
      agency_client_login: profile.login 
    })
    sendRemoteLog('Profile Selected', { login: profile.login })
  } catch (err) {
    error.value = 'Ошибка при выборе профиля'
  }
}

const fetchGoals = async (integrationId) => {
  loadingGoals.value = true
  try {
    // We send account_id to help backend find the right counter
    const { data } = await api.get(`integrations/${integrationId}/goals?account_id=${form.account_id}`)
    goals.value = data
  } catch (err) {
    console.error('Failed to fetch goals:', err)
  } finally {
    loadingGoals.value = false
  }
}

const selectPrimaryGoal = (goalId) => {
  form.primary_goal_id = goalId
}

const toggleGoal = (id) => {
  const index = selectedGoalIds.value.indexOf(id)
  if (index > -1) {
    selectedGoalIds.value.splice(index, 1)
  } else {
    selectedGoalIds.value.push(id)
  }
  if (selectedGoalIds.value.length < goals.value.length) {
    allGoalsFromProfile.value = false
  }
}

const toggleAllGoals = () => {
  allGoalsFromProfile.value = !allGoalsFromProfile.value
  if (allGoalsFromProfile.value) {
    selectedGoalIds.value = goals.value.map(g => g.id)
  }
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
    fetchCampaigns(data.id)
    
  } catch (err) {
    error.value = err.response?.data?.detail || 'Ошибка подключения'
  } finally {
    loading.value = false
  }
}

const fetchCampaigns = async (integrationId) => {
  loadingCampaigns.value = true
  try {
    // Use the discovery endpoint which fetches fresh data from platform
    const { data } = await api.post(`integrations/${integrationId}/discover-campaigns`)
    campaigns.value = data
    // Select active campaigns by default
    selectedCampaignIds.value = data.filter(c => c.is_active).map(c => c.id)
    
    // If none are active (newly discovered), select all
    if (selectedCampaignIds.value.length === 0) {
      selectedCampaignIds.value = data.map(c => c.id)
    }
  } catch (err) {
    console.error('Failed to fetch campaigns:', err)
    error.value = 'Не удалось загрузить список кампаний'
  } finally {
    loadingCampaigns.value = false
  }
}

const toggleCampaign = (id) => {
  const index = selectedCampaignIds.value.indexOf(id)
  if (index > -1) {
    selectedCampaignIds.value.splice(index, 1)
  } else {
    selectedCampaignIds.value.push(id)
  }
  // If user manually toggles, they are no longer in "All" mode if they deselected something
  if (selectedCampaignIds.value.length < campaigns.value.length) {
    allFromProfile.value = false
  }
}

const toggleAllCampaigns = () => {
  allFromProfile.value = !allFromProfile.value
  if (allFromProfile.value) {
    selectedCampaignIds.value = campaigns.value.map(c => c.id)
  } else {
    // Keep current or clear? Usually better to keep current but let them select specific ones
    // But for the checkbox UX, checking it should select all.
  }
}

const finishConnection = async () => {
  // Validation: Ensure primary goal is selected
  if (!form.primary_goal_id) {
    showValidationError.value = true
    return
  }

  loadingFinish.value = true
  error.value = null
  try {
    // 1. Update campaign statuses (only selected are active)
    const campaignPromises = campaigns.value.map(c => {
      const isActive = selectedCampaignIds.value.includes(c.id)
      return api.patch(`campaigns/${c.id}`, { is_active: isActive })
    })
    
    // 2. Update integration goals
    const integrationPromise = api.patch(`integrations/${lastIntegrationId.value}`, {
      selected_goals: selectedGoalIds.value,
      primary_goal_id: form.primary_goal_id
    })
    
    await Promise.all([...campaignPromises, integrationPromise])
    
    emit('success', { integration_id: lastIntegrationId.value })
    close()
  } catch (err) {
    console.error('Failed to finalize integration:', err)
    error.value = 'Ошибка при сохранении настроек'
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
    
    if (form.client_name) {
      localStorage.setItem('vk_auth_client_name', form.client_name)
    }
    
    const { data } = await api.get(`integrations/vk/auth-url?redirect_uri=${encodeURIComponent(redirectUri)}`)
    if (data.url) {
      window.location.href = data.url
    }
  } catch (err) {
    console.error(err)
    error.value = 'Не удалось инициализировать авторизацию VK'
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
