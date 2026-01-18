<template>
  <div class="max-w-6xl mx-auto p-4 md:p-8">
    <!-- Header -->
    <div class="flex items-center justify-between mb-8">
      <div class="flex items-center gap-4">
        <button 
          @click="$router.push('/settings')" 
          class="p-2.5 hover:bg-white rounded-2xl transition-all border border-transparent hover:border-gray-100 shadow-sm group"
        >
          <ArrowLeftIcon class="w-5 h-5 text-gray-400 group-hover:text-black" />
        </button>
        <div>
          <h1 class="text-2xl font-black text-black tracking-tight uppercase leading-none">Новая интеграция</h1>
          <div class="flex items-center gap-2 mt-2">
            <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest leading-none">Добавление рекламного канала</p>
            <template v-if="currentStep > 1 && form.client_name">
              <span class="text-[8px] text-gray-300">•</span>
              <span class="px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full text-[9px] font-black uppercase tracking-wider border border-blue-100/50">
                {{ form.client_name }}
              </span>
            </template>
          </div>
        </div>
      </div>
      
      <!-- Quick Status -->
      <div v-if="currentStep > 1" class="flex items-center gap-3 px-4 py-2 bg-white rounded-2xl border border-gray-100 shadow-sm animate-fade-in">
        <PlatformIcon :platform="form.platform" size="sm" />
        <span class="text-[11px] font-black text-black uppercase tracking-wider">{{ form.platform }}</span>
      </div>
    </div>

    <!-- Wizard Interface -->
    <div class="bg-white rounded-[2.5rem] border border-gray-100 shadow-[0_20px_60px_-15px_rgba(0,0,0,0.05)] overflow-hidden flex flex-col min-h-[600px]">
      <!-- Stepper Header -->
      <div class="px-8 py-10 border-b border-gray-50 bg-gray-50/30">
        <div class="max-w-2xl mx-auto flex items-center justify-between relative">
          <!-- Background Line -->
          <div class="absolute top-1/2 left-0 w-full h-0.5 bg-gray-100 -translate-y-1/2 z-0"></div>
          <div 
            class="absolute top-1/2 left-0 h-0.5 bg-blue-600 transition-all duration-500 -translate-y-1/2 z-0"
            :style="{ width: `${((currentStep - 1) / 3) * 100}%` }"
          ></div>

          <!-- Steps -->
          <div 
            v-for="step in 4" 
            :key="step"
            class="relative z-10 flex flex-col items-center gap-3"
          >
            <div 
              class="w-10 h-10 rounded-full flex items-center justify-center text-[12px] font-black transition-all duration-500 border-4"
              :class="[
                currentStep >= step ? 'bg-blue-600 text-white border-blue-100 shadow-lg scale-110' : 'bg-white text-gray-400 border-gray-50',
                currentStep === step ? 'ring-4 ring-blue-50' : ''
              ]"
            >
              {{ step }}
            </div>
            <span 
              class="absolute -bottom-7 whitespace-nowrap text-[9px] font-black uppercase tracking-widest transition-all duration-300"
              :class="currentStep >= step ? 'text-blue-600' : 'text-gray-300'"
            >
              {{ stepLabels[step] }}
            </span>
          </div>
        </div>
      </div>

      <!-- Step Content Area -->
      <div class="flex-grow p-8 md:p-12">
        <div class="max-w-3xl mx-auto">
          <Transition name="fade-slide" mode="out-in">
            <div :key="currentStep">
              <IntegrationStep1 
                v-if="currentStep === 1"
                :modelValue="form"
                @update:modelValue="updateFormData"
                v-model:isCreatingNewProject="isCreatingNewProject"
                :projects="projects"
                :error="error"
                @next="nextStep"
              />

              <IntegrationStep2 
                v-else-if="currentStep === 2"
                :profiles="profiles"
                :selectedAccountId="form.account_id"
                :loading="loadingProfiles"
                :platform="form.platform"
                @selectProfile="selectProfile"
                @next="nextStep"
              />

              <IntegrationStep3 
                v-else-if="currentStep === 3"
                :campaigns="campaigns"
                :selectedIds="selectedCampaignIds"
                :loading="loadingCampaigns"
                :platform="form.platform"
                @toggle="toggleCampaignSelection"
                @bulkSelect="bulkSelectCampaigns"
                @bulkDeselect="bulkDeselectCampaigns"
                @next="nextStep"
              />

              <IntegrationStep4 
                v-else-if="currentStep === 4"
                :goals="goals"
                :primaryGoalId="form.primary_goal_id"
                :selectedGoalIds="selectedGoalIds"
                :loading="loadingGoals"
                :platform="form.platform"
                @selectPrimary="selectPrimaryGoal"
                @toggleSecondary="toggleGoalSelection"
                @bulkSelect="bulkSelectGoals"
                @bulkDeselect="bulkDeselectGoals"
              />
            </div>
          </Transition>
        </div>
      </div>

      <!-- Action Footer -->
      <div class="px-8 py-6 border-t border-gray-50 flex items-center justify-between bg-white sticky bottom-0 z-20">
        <button 
          @click="prevStep"
          :disabled="currentStep === 1"
          class="px-8 py-3.5 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all flex items-center gap-2 group border border-gray-100 hover:border-gray-200 disabled:opacity-0"
        >
          <ArrowLeftIcon class="w-4 h-4 text-gray-400 group-hover:-translate-x-1 transition-transform" />
          Назад
        </button>

        <div class="flex items-center gap-4">
          <button 
            @click="$router.push('/settings')"
            class="px-6 py-3.5 text-gray-400 hover:text-black text-[10px] font-black uppercase tracking-widest transition-colors"
          >
            Отмена
          </button>
          
          <!-- Step 1: OAuth Auth for Yandex/VK -->
          <button 
            v-if="currentStep === 1 && (form.platform === 'YANDEX_DIRECT' || form.platform === 'VK_ADS')"
            @click="form.platform === 'YANDEX_DIRECT' ? initYandexAuth() : initVKAuth()"
            :disabled="loadingAuth || (isCreatingNewProject && !form.client_name)"
            class="px-10 py-3.5 rounded-2xl text-white font-black text-[10px] uppercase tracking-widest transition-all flex items-center justify-center gap-2 shadow-xl hover:-translate-y-0.5 active:translate-y-0"
            :class="form.platform === 'YANDEX_DIRECT' ? 'bg-[#FF4B21] hover:bg-[#ff3d0d] shadow-[#FF4B21]/20' : 'bg-[#0077FF] hover:bg-[#0066EE] shadow-[#0077FF]/20'"
          >
            <div v-if="loadingAuth" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            <span v-else>ПОДКЛЮЧИТЬ {{ form.platform === 'YANDEX_DIRECT' ? 'ЯНДЕКС ДИРЕКТ' : 'VK ADS' }}</span>
          </button>

          <!-- Step 2-3: Regular Next -->
          <button 
            v-else-if="currentStep >= 2 && currentStep < 4"
            @click="nextStep"
            :disabled="isNextDisabled"
            class="px-10 py-3.5 bg-black text-white rounded-2xl hover:bg-blue-600 hover:-translate-y-0.5 active:translate-y-0 font-black text-[10px] uppercase tracking-widest disabled:opacity-50 disabled:translate-y-0 transition-all flex items-center gap-2 shadow-xl shadow-gray-200 hover:shadow-blue-200"
          >
            Далее
            <ArrowRightIcon class="w-4 h-4" />
          </button>

          <button 
            v-else
            @click="finishConnection"
            :disabled="isNextDisabled || loadingFinish"
            class="px-10 py-3.5 bg-blue-600 text-white rounded-2xl hover:bg-blue-700 hover:-translate-y-0.5 active:translate-y-0 font-black text-[10px] uppercase tracking-widest disabled:opacity-50 disabled:translate-y-0 transition-all flex items-center gap-2 shadow-xl shadow-blue-200"
          >
            <div v-if="loadingFinish" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            <span>{{ loadingFinish ? 'СОХРАНЕНИЕ...' : 'ПОДКЛЮЧИТЬ' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Selectors (Remain as compact modals for now) -->





  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { 
  ArrowLeftIcon, 
  ArrowRightIcon, 
  CheckIcon 
} from '@heroicons/vue/24/outline'

// Unified components
import PlatformIcon from '../../components/ui/PlatformIcon.vue'
import Skeleton from '../../components/ui/Skeleton.vue'

// Step Components
import IntegrationStep1 from '../../components/integration-steps/IntegrationStep1.vue'
import IntegrationStep2 from '../../components/integration-steps/IntegrationStep2.vue'
import IntegrationStep3 from '../../components/integration-steps/IntegrationStep3.vue'
import IntegrationStep4 from '../../components/integration-steps/IntegrationStep4.vue'

// Composables & API
import { useProjects } from '../../composables/useProjects'
import api from '../../api/axios'
import { useToaster } from '../../composables/useToaster'
import { useIntegrationWizard } from '../../composables/useIntegrationWizard'

const router = useRouter()
const { projects, fetchProjects } = useProjects()
const {
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
  fetchProfiles,
  fetchCampaigns,
  fetchGoals,
  fetchIntegration,
  finishConnection,
  resetStore,
  toggleCampaignSelection,
  bulkSelectCampaigns,
  bulkDeselectCampaigns,
  bulkSelectGoals,
  bulkDeselectGoals,
  selectPrimaryGoal
} = useIntegrationWizard()

const isCreatingNewProject = ref(false)
const isProfileSelectorOpen = ref(false)

const stepLabels = {
  1: 'Платформа и проект',
  2: 'Выбор профиля',
  3: 'Рекламные кампании',
  4: 'Цели и конверсии'
}

// Selectors Presence (Moved inline)

// Validation
const isNextDisabled = computed(() => {
  if (currentStep.value === 1) {
    // For Yandex/VK, we need OAuth first (button will be different)
    // For other platforms, we need project selection
    if (form.platform === 'YANDEX_DIRECT' || form.platform === 'VK_ADS') {
      // Just need project selection or new project name
      return !form.client_id && (!isCreatingNewProject.value || !form.client_name)
    }
    return !form.client_id && (!isCreatingNewProject.value || !form.client_name)
  }
  if (currentStep.value === 2) return !form.account_id || loadingStates.profiles
  if (currentStep.value === 3) return (!allFromProfile.value && selectedCampaignIds.value.length === 0) || loadingStates.campaigns
  if (currentStep.value === 4) return !form.primary_goal_id || loadingStates.finish
  return false
})

// Navigation Actions
const nextStep = async () => {
  if (currentStep.value === 1) {
    // Create or find integration
    try {
      const payload = {
        platform: form.platform,
        client_id: form.client_id,
        new_client_name: isCreatingNewProject.value ? form.client_name : null
      }
      const res = await api.post('/integrations/', payload)
      lastIntegrationId.value = res.data.id
      form.client_id = res.data.client_id
      if (res.data.client) form.client_name = res.data.client.name
      
      currentStep.value = 2
      fetchProfiles(lastIntegrationId.value)
    } catch (err) {
      error.value = err.response?.data?.detail || "Ошибка при создании интеграции"
    }
  } else if (currentStep.value === 2) {
    currentStep.value = 3
    fetchCampaigns(lastIntegrationId.value)
  } else if (currentStep.value === 3) {
    currentStep.value = 4
    fetchGoals(lastIntegrationId.value)
  }
}

const prevStep = () => {
  if (currentStep.value > 1) currentStep.value--
}

// Update form data (handle reactive updates)
const updateFormData = (updates) => {
  Object.assign(form, updates)
}

// Selection Handlers (Step 1 handled inline now)
const selectProfile = async (profile) => {
  form.account_id = profile.login
  form.agency_client_login = profile.login
  isProfileSelectorOpen.value = false
  
  // Patch integration with profile
  try {
    await api.patch(`/integrations/${lastIntegrationId.value}`, {
      account_id: profile.login,
      agency_client_login: profile.login
    })
  } catch (err) {
    error.value = "Ошибка при сохранении профиля"
  }
}

// Selection Handlers (Step 3 handled via composable now)
// Selection Handlers (All handled via composable now)
const toggleGoalSelection = (id) => {
  const idx = selectedGoalIds.value.indexOf(id)
  if (idx > -1) selectedGoalIds.value.splice(idx, 1)
  else selectedGoalIds.value.push(id)
}

// OAuth Authentication
const loadingAuth = ref(false)

const initYandexAuth = async () => {
  loadingAuth.value = true
  try {
    const redirectUri = `${window.location.origin}/auth/yandex/callback`
    
    // Save form state to localStorage
    if (form.client_id) localStorage.setItem('yandex_auth_client_id', form.client_id)
    if (form.client_name) localStorage.setItem('yandex_auth_client_name', form.client_name)
    if (isCreatingNewProject.value) localStorage.setItem('yandex_auth_is_new_project', 'true')
    
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
    
    // Save form state to localStorage
    if (form.client_id) localStorage.setItem('vk_auth_client_id', form.client_id)
    if (form.client_name) localStorage.setItem('vk_auth_client_name', form.client_name)
    if (isCreatingNewProject.value) localStorage.setItem('vk_auth_is_new_project', 'true')
    
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

onMounted(() => {
  fetchProjects()
  
  const resumeId = router.currentRoute.value.query.resume_integration_id
  const startStep = router.currentRoute.value.query.initial_step
  
  if (resumeId) {
    lastIntegrationId.value = resumeId
    currentStep.value = parseInt(startStep) || 2
    fetchIntegration(resumeId)
    
    if (currentStep.value === 2) fetchProfiles(resumeId)
    if (currentStep.value === 3) fetchCampaigns(resumeId)
    if (currentStep.value === 4) fetchGoals(resumeId)
  }
})
</script>

<style scoped>
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s ease-out;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
