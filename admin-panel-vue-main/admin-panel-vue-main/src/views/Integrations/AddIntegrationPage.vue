<template>
  <div class="flex flex-col h-full min-h-[calc(100vh-160px)]">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 md:px-8 py-6 bg-white border-b border-gray-100 flex-shrink-0">
      <div class="flex items-center gap-4">
        <button 
          @click="$router.push('/settings')" 
          class="p-2.5 hover:bg-white rounded-2xl transition-all border border-transparent hover:border-gray-100 shadow-sm group"
        >
          <ArrowLeftIcon class="w-5 h-5 text-gray-400 group-hover:text-black" />
        </button>
        <div>
          <h1 class="text-2xl font-black text-black tracking-tight uppercase leading-none">НОВАЯ ИНТЕГРАЦИЯ</h1>
          <div class="flex items-center gap-2 mt-2">
            <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest leading-none">ДОБАВЛЕНИЕ РЕКЛАМНОГО КАНАЛА</p>
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
    <div class="max-w-7xl mx-auto px-4 md:px-8 py-8 flex-1 flex flex-col">
      <div class="bg-white rounded-3xl border border-gray-100/50 shadow-2xl shadow-blue-100/20 overflow-hidden flex flex-col flex-1">
      <!-- Stepper Header -->
      <div class="px-8 py-10 border-b border-gray-50 bg-gray-50/30">
        <div class="max-w-2xl mx-auto flex items-center justify-between relative">
          <!-- Background Line -->
          <div class="absolute top-1/2 left-0 w-full h-0.5 bg-gray-100 -translate-y-1/2 z-0"></div>
          <div 
            class="absolute top-1/2 left-0 h-0.5 bg-blue-600 transition-all duration-500 -translate-y-1/2 z-0"
            :style="{ width: `${((currentStep - 1) / 4) * 100}%` }"
          ></div>

          <!-- Steps -->
          <div 
            v-for="step in 5" 
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

              <!-- Step 2: Profile selection -->
              <IntegrationStep2 
                v-else-if="currentStep === 2"
                :profiles="profiles"
                :loading="loadingProfiles"
                :selectedProfile="form.account_id"
                :platform="form.platform"
                @select="selectProfile"
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

              <!-- Step 5: Summary -->
              <div v-else-if="currentStep === 5" class="space-y-6">
                <div class="text-center py-6">
                  <h3 class="text-2xl font-black text-gray-900 mb-2">Сводка настроек</h3>
                  <p class="text-[11px] font-bold text-gray-400 uppercase tracking-widest">Проверьте выбранные параметры перед подключением</p>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <!-- Проект -->
                  <div class="bg-white border-2 border-gray-100 rounded-[1.5rem] p-6 shadow-sm">
                    <div class="flex items-center gap-3 mb-4">
                      <div class="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center">
                        <svg class="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                        </svg>
                      </div>
                      <div>
                        <p class="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-1">Проект</p>
                        <p class="text-[15px] font-black text-gray-900">{{ form.client_name || 'Не выбран' }}</p>
                      </div>
                    </div>
                  </div>

                  <!-- Профиль -->
                  <div class="bg-white border-2 border-gray-100 rounded-[1.5rem] p-6 shadow-sm">
                    <div class="flex items-center gap-3 mb-4">
                      <div class="w-10 h-10 rounded-xl bg-purple-50 flex items-center justify-center">
                        <svg class="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                      </div>
                      <div>
                        <p class="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-1">Профиль</p>
                        <p class="text-[15px] font-black text-gray-900">{{ form.account_id || 'Не выбран' }}</p>
                      </div>
                    </div>
                  </div>

                  <!-- Рекламные кампании -->
                  <div class="bg-white border-2 border-gray-100 rounded-[1.5rem] p-6 shadow-sm">
                    <div class="flex items-center gap-3 mb-4">
                      <div class="w-10 h-10 rounded-xl bg-orange-50 flex items-center justify-center">
                        <svg class="w-5 h-5 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                        </svg>
                      </div>
                      <div class="flex-1">
                        <p class="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-1">Рекламные кампании</p>
                        <p class="text-[11px] font-bold text-gray-500 mb-2">{{ selectedCampaignIds.length }} {{ selectedCampaignIds.length === 1 ? 'кампания' : selectedCampaignIds.length < 5 ? 'кампании' : 'кампаний' }}</p>
                      </div>
                    </div>
                    <div class="space-y-2 max-h-32 overflow-y-auto custom-scrollbar">
                      <template v-if="selectedCampaignIds.length > 0">
                        <div 
                          v-for="campaignId in selectedCampaignIds" 
                          :key="campaignId"
                          class="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-xl"
                        >
                          <div class="w-1.5 h-1.5 rounded-full bg-blue-600"></div>
                          <span class="text-[12px] font-bold text-gray-700 flex-1">
                            {{ campaigns.find(c => c.id === campaignId)?.name || `Кампания #${campaignId}` }}
                          </span>
                        </div>
                      </template>
                      <p v-else class="text-[11px] text-gray-400 italic">Кампании не выбраны</p>
                    </div>
                  </div>

                  <!-- Метрики (цели) -->
                  <div class="bg-white border-2 border-gray-100 rounded-[1.5rem] p-6 shadow-sm">
                    <div class="flex items-center gap-3 mb-4">
                      <div class="w-10 h-10 rounded-xl bg-green-50 flex items-center justify-center">
                        <svg class="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                        </svg>
                      </div>
                      <div class="flex-1">
                        <p class="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-1">Метрики</p>
                        <p class="text-[11px] font-bold text-gray-500 mb-2">
                          {{ (selectedGoalIds.length + (form.primary_goal_id ? 1 : 0)) }} 
                          {{ (selectedGoalIds.length + (form.primary_goal_id ? 1 : 0)) === 1 ? 'метрика' : (selectedGoalIds.length + (form.primary_goal_id ? 1 : 0)) < 5 ? 'метрики' : 'метрик' }}
                        </p>
                      </div>
                    </div>
                    <div class="space-y-2 max-h-32 overflow-y-auto custom-scrollbar">
                      <template v-if="form.primary_goal_id">
                        <div class="flex items-center gap-2 px-3 py-2 bg-blue-50 rounded-xl border border-blue-100">
                          <div class="w-1.5 h-1.5 rounded-full bg-blue-600"></div>
                          <span class="text-[11px] font-black text-blue-600 uppercase tracking-tight mr-1">Основная:</span>
                          <span class="text-[12px] font-bold text-gray-700 flex-1">
                            {{ goals.find(g => g.id === form.primary_goal_id)?.name || `Цель #${form.primary_goal_id}` }}
                          </span>
                        </div>
                      </template>
                      <template v-if="selectedGoalIds.length > 0">
                        <div 
                          v-for="goalId in selectedGoalIds" 
                          :key="goalId"
                          class="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-xl"
                        >
                          <div class="w-1.5 h-1.5 rounded-full bg-gray-400"></div>
                          <span class="text-[12px] font-bold text-gray-700 flex-1">
                            {{ goals.find(g => g.id === goalId)?.name || `Цель #${goalId}` }}
                          </span>
                        </div>
                      </template>
                      <p v-if="!form.primary_goal_id && selectedGoalIds.length === 0" class="text-[11px] text-gray-400 italic">Метрики не выбраны</p>
                    </div>
                  </div>
                </div>
              </div>
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
            @click="handleCancel"
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

          <!-- Step 2: Regular Next (profile selection) -->
          <button 
            v-else-if="currentStep === 2"
            @click="nextStep"
            :disabled="isNextDisabled"
            class="px-10 py-3.5 bg-black text-white rounded-2xl hover:bg-blue-600 hover:-translate-y-0.5 active:translate-y-0 font-black text-[10px] uppercase tracking-widest disabled:opacity-50 disabled:translate-y-0 transition-all flex items-center gap-2 shadow-xl shadow-gray-200 hover:shadow-blue-200"
          >
            Далее
            <ArrowRightIcon class="w-4 h-4" />
          </button>

          <!-- Step 3: Regular Next (campaigns) -->
          <button 
            v-else-if="currentStep === 3"
            @click="nextStep"
            :disabled="isNextDisabled"
            class="px-10 py-3.5 bg-black text-white rounded-2xl hover:bg-blue-600 hover:-translate-y-0.5 active:translate-y-0 font-black text-[10px] uppercase tracking-widest disabled:opacity-50 disabled:translate-y-0 transition-all flex items-center gap-2 shadow-xl shadow-gray-200 hover:shadow-blue-200"
          >
            Далее
            <ArrowRightIcon class="w-4 h-4" />
          </button>

          <!-- Step 4: Next button (goals -> summary) -->
          <button 
            v-else-if="currentStep === 4"
            @click="nextStep"
            :disabled="isNextDisabled"
            class="px-10 py-3.5 bg-black text-white rounded-2xl hover:bg-blue-600 hover:-translate-y-0.5 active:translate-y-0 font-black text-[10px] uppercase tracking-widest disabled:opacity-50 disabled:translate-y-0 transition-all flex items-center gap-2 shadow-xl shadow-gray-200 hover:shadow-blue-200"
          >
            Далее
            <ArrowRightIcon class="w-4 h-4" />
          </button>

          <!-- Step 5: Finish button (summary) -->
          <button 
            v-else-if="currentStep === 5"
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
    </div>
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
import { PLATFORMS } from '../../constants/platformConfig'

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
const isSyncingData = ref(false)

const stepLabels = {
  1: 'Платформа и проект',
  2: 'Выбор профиля',
  3: 'Рекламные кампании',
  4: 'Цели и конверсии',
  5: 'Сводка настроек'
}

// Loading state computed properties
const loadingProfiles = computed(() => loadingStates.profiles)
const loadingCampaigns = computed(() => loadingStates.campaigns || isSyncingData.value)
const loadingGoals = computed(() => loadingStates.goals || isSyncingData.value)
const loadingFinish = computed(() => loadingStates.finish)

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
  if (currentStep.value === 4) return !form.primary_goal_id || loadingStates.goals
  if (currentStep.value === 5) return false // Summary step - no validation needed
  return false
})

// Cancel integration flow
const handleCancel = async () => {
  try {
    // Если интеграция уже создана (на любом шаге),
    // по нажатию "Отмена" удаляем её целиком.
    if (lastIntegrationId.value) {
      try {
        await api.delete(`/integrations/${lastIntegrationId.value}`)
      } catch (err) {
        console.error('Failed to delete integration on cancel:', err)
        // Даже если удаление на бэкенде не удалось, всё равно сбрасываем локальное состояние
      }
    }
  } finally {
    // В любом случае сбрасываем локальный стор и уходим со страницы интеграции
    resetStore()
    router.push('/settings')
  }
}

// Navigation Actions
const nextStep = async () => {
  if (currentStep.value === 1) {
    // Step 1 -> 2: OAuth completed, now load profiles
    // Integration is already created by OAuth callback
    currentStep.value = 2
    if (lastIntegrationId.value) {
      fetchProfiles(lastIntegrationId.value)
    }
  } else if (currentStep.value === 2) {
    // Step 2 -> 3: Profile selected, validate and load campaigns
    if (!form.account_id) {
      toaster.error('Пожалуйста, выберите профиль перед переходом к кампаниям')
      return
    }
    // CRITICAL: Update integration with selected profile (both account_id and agency_client_login)
    // This ensures the backend uses the correct profile when fetching campaigns
    try {
      await api.patch(`/integrations/${lastIntegrationId.value}`, {
        account_id: form.account_id,
        agency_client_login: form.agency_client_login || form.account_id
      })
      // Wait a bit to ensure DB commit is complete
      await new Promise(resolve => setTimeout(resolve, 100))
    } catch (err) {
      console.error('Failed to update integration with profile:', err)
      toaster.error('Ошибка при сохранении профиля')
      return
    }
    currentStep.value = 3
    fetchCampaigns(lastIntegrationId.value)
  } else if (currentStep.value === 3) {
    // Step 3 -> 4: Campaigns selected, load goals
    currentStep.value = 4
    fetchGoals(lastIntegrationId.value)
  } else if (currentStep.value === 4) {
    // Step 4 -> 5: Goals selected, show summary
    currentStep.value = 5
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
    const step = parseInt(startStep) || 2
    currentStep.value = step
    fetchIntegration(resumeId)
    
    // Load data for the current step
    if (step === 2) {
      fetchProfiles(resumeId)
    } else if (step === 3) {
      fetchCampaigns(resumeId)
    } else if (step === 4) {
      fetchGoals(resumeId)
    }
    
    // Step 2 = campaigns, Step 3 = goals (profile selection removed)
    if (currentStep.value === 2) fetchCampaigns(resumeId)
    if (currentStep.value === 3) fetchGoals(resumeId)
  }
})
</script>

<style scoped>
/* Custom scrollbar styling */
.custom-scrollbar {
  scrollbar-width: thin;
  scrollbar-color: #e5e7eb #f9fafb;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: #f9fafb;
  border-radius: 10px;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #e5e7eb;
  border-radius: 10px;
  transition: background 0.2s;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #d1d5db;
}
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
