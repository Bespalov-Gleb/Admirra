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
            <h3 class="text-xl font-black text-black tracking-tight leading-tight uppercase">Добавить интеграцию</h3>
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
          <div class="pr-1 pb-4 space-y-5">
            <div v-if="error" class="p-4 bg-red-50 border border-red-100 text-red-600 text-[12px] rounded-xl flex items-start gap-3 animate-shake shadow-sm">
              <svg class="w-5 h-5 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path></svg>
              <span class="font-bold">{{ error }}</span>
            </div>

            <form @submit.prevent="nextStep" class="space-y-5">
              <!-- Platform Selection -->
              <div class="relative">
                <label class="block text-[10px] font-black text-black uppercase tracking-[0.2em] mb-2 px-1">Платформа</label>
                <div class="relative">
                  <button 
                    type="button"
                    @click="dropdownOpen = !dropdownOpen"
                    class="w-full px-4 py-3.5 bg-white border border-gray-300 rounded-2xl focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition-all flex items-center justify-between shadow-sm group hover:border-gray-400"
                  >
                    <div class="flex items-center gap-3">
                      <div class="w-8 h-8 rounded-xl flex items-center justify-center text-[10px] font-black shadow-sm border" :class="currentPlatform.className">
                        {{ currentPlatform.initials }}
                      </div>
                      <div class="text-left">
                        <span class="block text-[13px] font-black text-black leading-none">{{ currentPlatform.label }}</span>
                      </div>
                    </div>
                    <svg class="w-4 h-4 text-gray-400 group-hover:text-black transition-all duration-300" :class="{ 'rotate-180': dropdownOpen }" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                  </button>

                  <div v-if="dropdownOpen" class="absolute z-[110] mt-2 w-full bg-white border border-gray-200 rounded-2xl shadow-xl py-2 overflow-hidden animate-slide-down">
                    <button 
                      v-for="(config, key) in PLATFORMS" 
                      :key="key"
                      type="button"
                      @click="selectPlatform(key)"
                      class="w-full px-4 py-2.5 text-left flex items-center gap-3 hover:bg-gray-50 transition-all border-b border-gray-50 last:border-none"
                      :class="{ 'bg-blue-50/40': form.platform === key }"
                    >
                      <div class="w-7 h-7 rounded-lg flex items-center justify-center text-[9px] font-black shadow-sm" :class="config.className">
                        {{ config.initials }}
                      </div>
                      <span class="text-[12px] font-black" :class="form.platform === key ? 'text-blue-600' : 'text-gray-600 font-bold'">{{ config.label }}</span>
                    </button>
                  </div>
                </div>
              </div>

              <!-- Project Selection -->
              <div class="relative">
                <label class="block text-[10px] font-black text-black uppercase tracking-[0.2em] mb-2 px-1">Проект</label>
                <div class="relative">
                  <button 
                    type="button"
                    @click="projectDropdownOpen = !projectDropdownOpen"
                    class="w-full px-4 py-3.5 bg-white border border-gray-300 rounded-2xl focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition-all flex items-center justify-between shadow-sm group hover:border-gray-400"
                  >
                    <div class="flex items-center gap-3">
                      <div class="text-left">
                        <span class="block text-[13px] font-black text-black leading-none">
                          {{ form.client_id ? projects.find(p => p.id === form.client_id)?.name : 'Выберите проект' }}
                        </span>
                      </div>
                    </div>
                    <svg class="w-4 h-4 text-gray-400 group-hover:text-black transition-all duration-300" :class="{ 'rotate-180': projectDropdownOpen }" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                  </button>

                  <div v-if="projectDropdownOpen" class="absolute z-[110] mt-2 w-full bg-white border border-gray-200 rounded-2xl shadow-xl py-2 overflow-hidden animate-slide-down">
                    <div class="max-h-48 overflow-y-auto">
                      <button 
                        v-for="project in projects" 
                        :key="project.id"
                        type="button"
                        @click="selectProject(project)"
                        class="w-full px-4 py-2.5 text-left flex items-center gap-3 hover:bg-gray-50 transition-all border-b border-gray-50 last:border-none"
                        :class="{ 'bg-blue-50/40': form.client_id === project.id }"
                      >
                        <span class="text-[12px] font-black" :class="form.client_id === project.id ? 'text-blue-600' : 'text-gray-600 font-bold'">{{ project.name }}</span>
                      </button>

                      <button 
                        type="button"
                        @click="selectNewProject"
                        class="w-full px-4 py-2.5 text-left flex items-center gap-3 hover:bg-blue-50 transition-all border-t border-gray-100"
                        :class="{ 'bg-blue-50': isCreatingNewProject }"
                      >
                        <div class="w-5 h-5 rounded-lg bg-blue-100 flex items-center justify-center text-blue-600">
                          <PlusIcon class="w-4 h-4" />
                        </div>
                        <span class="text-[12px] font-black text-blue-600">СОЗДАТЬ НОВЫЙ ПРОЕКТ</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- New Project Name Input -->
              <div v-if="isCreatingNewProject" class="animate-modal-in">
                <Input
                  v-model="form.client_name"
                  label="Название проекта"
                  labelClass="text-[10px] font-black text-black uppercase tracking-[0.2em] mb-2 px-1"
                  inputClass="rounded-2xl font-black text-black shadow-sm"
                  placeholder="Нанапример: Проект Альфа"
                  required
                />
              </div>

              <!-- Yandex Auth Button (Step 1 footer alternative) -->
              <div v-if="form.platform === 'YANDEX_DIRECT' && currentStep === 1" class="py-2">
                <!-- This button is handled by nextStep logic indirectly or explicitly here -->
              </div>

              <!-- VK Auth Button (Step 1 footer alternative) -->
              <div v-else-if="form.platform === 'VK_ADS' && !currentPlatform.isDynamic && currentStep === 1" class="py-2">
                <!-- Handled in footer -->
              </div>

              <!-- Standard Token Input -->
              <Input
                v-else-if="!currentPlatform.isDynamic"
                v-model="form.access_token"
                :type="showToken ? 'text' : 'password'"
                label="Access Token"
                labelClass="text-[10px] font-black text-black uppercase tracking-[0.2em] mb-1 px-1"
                inputClass="rounded-2xl font-mono text-[13px] tracking-widest text-black shadow-sm hover:border-gray-400"
                placeholder="••••••••••••••••••••"
                required
              />
            </form>
          </div>
        </CustomScroll>

        <!-- Step 2: Profile Selection -->
        <CustomScroll v-else-if="currentStep === 2" class="flex-grow">
          <div class="pr-1 pb-4 space-y-4">
            <div class="relative mb-4">
              <label class="block text-[10px] font-black text-black uppercase tracking-[0.2em] mb-2 px-1">Профиль рекламной кампании</label>
              
              <!-- Search Profiles -->
              <div class="mb-4">
                <input 
                  v-model="searchQuery" 
                  type="text" 
                  placeholder="Поиск профиля..." 
                  class="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-xs font-bold outline-none focus:border-blue-500 transition-all"
                >
              </div>

              <div v-if="loadingProfiles" class="py-12 flex flex-col items-center justify-center gap-4">
                <div class="w-10 h-10 border-4 border-gray-100 border-t-blue-600 rounded-full animate-spin"></div>
                <span class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Загрузка профилей...</span>
              </div>
              <div v-else-if="filteredProfiles.length > 0" class="space-y-2">
                <button 
                  v-for="profile in filteredProfiles" 
                  :key="profile.login"
                  @click="selectProfile(profile)"
                  class="w-full px-5 py-4 bg-white border rounded-2xl transition-all flex items-center justify-between group"
                  :class="form.account_id === profile.login ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-50' : 'border-gray-100 hover:border-gray-300'"
                >
                  <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-[10px] font-black text-gray-500 uppercase">
                      {{ profile.login.substring(0, 2) }}
                    </div>
                    <div class="text-left">
                      <span class="block text-[13px] font-black transition-all" :class="form.account_id === profile.login ? 'text-blue-700' : 'text-black'">{{ profile.name || profile.login }}</span>
                      <span class="block text-[10px] text-gray-400 font-bold uppercase tracking-wider">{{ profile.login }}</span>
                    </div>
                  </div>
                  <ChevronRightIcon class="w-5 h-5 text-gray-300 group-hover:text-black transition-all" />
                </button>
              </div>
              <div v-else class="py-12 flex flex-col items-center justify-center text-center px-4">
                <div class="w-12 h-12 bg-gray-50 text-gray-300 rounded-full flex items-center justify-center mb-3">
                  <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                </div>
                <p class="text-[11px] font-black text-gray-400 uppercase tracking-widest">Профили не найдены</p>
                <p class="text-[10px] text-gray-300 mt-1 font-bold">Попробуйте изменить поисковый запрос</p>
              </div>
            </div>
          </div>
        </CustomScroll>

        <!-- Step 3: Campaign Selection -->
        <CustomScroll v-else-if="currentStep === 3" class="flex-grow">
          <div class="pr-1 pb-4 space-y-4">
            <label class="block text-[10px] font-black text-black uppercase tracking-[0.2em] mb-2 px-1">Рекламная кампания</label>
            
            <!-- Search Campaigns -->
            <div class="mb-4">
              <input 
                v-model="searchQuery" 
                type="text" 
                placeholder="Поиск кампании..." 
                class="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-xs font-bold outline-none focus:border-blue-500 transition-all"
              >
            </div>

            <div v-if="loadingCampaigns" class="py-12 flex flex-col items-center justify-center gap-4">
              <div class="w-10 h-10 border-4 border-gray-100 border-t-blue-600 rounded-full animate-spin"></div>
              <span class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Получение кампаний...</span>
            </div>
            <div v-else class="space-y-2">
              <button 
                v-for="campaign in filteredCampaigns" 
                :key="campaign.id"
                @click="toggleCampaign(campaign.id)"
                class="w-full p-4 rounded-2xl border transition-all flex items-center justify-between group"
                :class="selectedCampaignIds.includes(campaign.id) ? 'bg-blue-50 border-blue-200 ring-2 ring-blue-50' : 'bg-white border-gray-100 hover:border-gray-300'"
              >
                <div class="flex items-center gap-3">
                  <div class="w-5 h-5 rounded-lg border-2 flex items-center justify-center transition-all" :class="selectedCampaignIds.includes(campaign.id) ? 'bg-blue-600 border-blue-600' : 'border-gray-200 group-hover:border-gray-400'">
                    <svg v-if="selectedCampaignIds.includes(campaign.id)" class="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path></svg>
                  </div>
                  <div class="text-left">
                    <span class="block text-[12px] font-black transition-all" :class="selectedCampaignIds.includes(campaign.id) ? 'text-blue-700' : 'text-gray-700 font-bold'">{{ campaign.name }}</span>
                    <span class="block text-[9px] text-gray-400 font-bold uppercase tracking-widest mt-0.5">ID: {{ campaign.external_id }}</span>
                  </div>
                </div>
              </button>
            </div>
          </div>
        </CustomScroll>

        <!-- Step 4: Goal Selection -->
        <CustomScroll v-else-if="currentStep === 4" class="flex-grow">
          <div class="pr-1 pb-4 space-y-6">
            <div>
              <label class="block text-[10px] font-black text-black uppercase tracking-[0.2em] mb-3 px-1">Основная цель:</label>
              <div class="relative">
                <button 
                  @click="goalDropdownOpen = !goalDropdownOpen"
                  class="w-full px-4 py-4 bg-gray-50 border border-gray-200 rounded-2xl flex items-center justify-between hover:bg-gray-100 transition-all"
                >
                  <span class="text-[12px] font-black text-black text-left">
                    {{ form.primary_goal_id ? goals.find(g => g.id === form.primary_goal_id)?.name || form.primary_goal_id : 'Выберите основную цель' }}
                  </span>
                  <ChevronDownIcon class="w-5 h-5 text-gray-400" />
                </button>
                <div v-if="goalDropdownOpen" class="absolute z-[120] mt-2 w-full bg-white border border-gray-200 rounded-2xl shadow-xl py-2 max-h-48 overflow-y-auto animate-slide-down">
                  <button 
                    v-for="goal in goals" 
                    :key="goal.id"
                    @click="selectPrimaryGoal(goal)"
                    class="w-full px-4 py-2.5 text-left text-[11px] font-bold text-gray-600 hover:bg-blue-50 hover:text-blue-600 transition-all border-b border-gray-50 last:border-none"
                  >
                    {{ goal.name }} ({{ goal.id }})
                  </button>
                </div>
              </div>
            </div>

            <div>
              <label class="block text-[10px] font-black text-black uppercase tracking-[0.2em] mb-3 px-1">Цели для блока с конверсиями:</label>
              <div class="space-y-2">
                <button 
                  v-for="goal in goals" 
                  :key="goal.id"
                  @click="toggleGoal(goal.id)"
                  class="w-full p-4 rounded-2xl border transition-all flex items-center justify-between group"
                  :class="selectedGoalIds.includes(goal.id) ? 'bg-blue-50 border-blue-200' : 'bg-white border-gray-100 hover:border-gray-300'"
                >
                  <div class="flex items-center gap-3">
                    <div class="w-4 h-4 rounded border flex items-center justify-center transition-all" :class="selectedGoalIds.includes(goal.id) ? 'bg-blue-600 border-blue-600' : 'border-gray-200 group-hover:border-gray-400'">
                      <svg v-if="selectedGoalIds.includes(goal.id)" class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path></svg>
                    </div>
                    <div class="text-left">
                      <span class="block text-[11px] font-black transition-all" :class="selectedGoalIds.includes(goal.id) ? 'text-blue-700' : 'text-gray-700 font-bold'">{{ goal.name }}</span>
                      <span class="block text-[9px] text-gray-400 font-bold uppercase tracking-widest mt-0.5">{{ goal.id }}</span>
                    </div>
                  </div>
                </button>
              </div>
            </div>
          </div>
        </CustomScroll>

        <!-- Footer: Fixed -->
        <div class="flex gap-3 pt-6 mt-4 border-t border-gray-50 flex-shrink-0 bg-white">
          <button v-if="currentStep === 1" type="button" @click="close" class="flex-1 py-3.5 text-[10px] font-black uppercase tracking-widest border border-gray-200 rounded-2xl text-gray-400 hover:text-gray-700 hover:bg-gray-50 transition-all">Отмена</button>
          <button v-else type="button" @click="prevStep" class="flex-1 py-3.5 text-[10px] font-black uppercase tracking-widest border border-gray-200 rounded-2xl text-gray-400 hover:text-gray-700 hover:bg-gray-50 transition-all">Назад</button>
          
          <button 
            v-if="currentStep === 1 && (form.platform === 'YANDEX_DIRECT' || form.platform === 'VK_ADS')"
            @click="form.platform === 'YANDEX_DIRECT' ? initYandexAuth() : initVKAuth()"
            :disabled="loadingAuth || (isCreatingNewProject && !form.client_name)"
            class="flex-[1.5] py-3.5 rounded-2xl text-white font-black text-[10px] uppercase tracking-widest transition-all flex items-center justify-center gap-2 shadow-lg hover:-translate-y-0.5 active:translate-y-0"
            :class="form.platform === 'YANDEX_DIRECT' ? 'bg-[#FC3F1D] hover:bg-[#e63212]' : 'bg-[#0077FF] hover:bg-[#0066EE]'"
          >
            <div v-if="loadingAuth" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            <span v-else class="flex items-center gap-2">
              <svg v-if="form.platform === 'YANDEX_DIRECT'" class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12.923 15.686L8.683 5H5v14h3.04V9.695l4.577 9.305h3.336l-5.603-9.52 5.09-4.48h-3.32l-3.2 3.11V15.686z"/></svg>
              <svg v-else class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M13.162 18.994c-6.098 0-9.57-4.172-9.714-11.104h3.047c.1 5.093 2.344 7.25 4.125 7.696V7.89H13.5v4.39c1.703-.187 3.562-2.188 4.172-4.39h2.89c-.531 2.766-2.563 4.766-3.734 5.438 1.171.547 3.5 2.25 4.406 5.664h-3.14c-.703-2.203-2.454-3.906-4.22-4.08v4.08h-2.1c-.015.002-.015.002 0 .006z"/></svg>
              ПОДКЛЮЧИТЬ {{ form.platform === 'YANDEX_DIRECT' ? 'ЯНДЕКС' : 'VK ADS' }}
            </span>
          </button>

          <button v-else-if="currentStep < 4" @click="nextStep" :disabled="loading || loadingProfiles || loadingCampaigns" class="flex-[1.5] py-3.5 bg-gray-900 text-white rounded-2xl hover:bg-black hover:-translate-y-0.5 active:translate-y-0 font-black text-[10px] uppercase tracking-widest disabled:opacity-50 transition-all flex items-center justify-center gap-2 shadow-lg">
            <div v-if="loading || loadingProfiles || loadingCampaigns" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            <span>{{ loading || loadingProfiles || loadingCampaigns ? 'ЗАГРУЗКА...' : 'ДАЛЕЕ' }}</span>
          </button>
          
          <button v-else @click="finishConnection" :disabled="loadingFinish" class="flex-[1.5] py-3.5 bg-blue-600 text-white rounded-2xl hover:bg-blue-700 hover:-translate-y-0.5 active:translate-y-0 font-black text-[10px] uppercase tracking-widest disabled:opacity-50 transition-all flex items-center justify-center gap-2 shadow-lg">
            <div v-if="loadingFinish" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            <span>{{ loadingFinish ? 'СОХРАНЕНИЕ...' : 'ПОДКЛЮЧИТЬ' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, computed, onMounted } from 'vue'
import api from '../api/axios'
import CustomScroll from './ui/CustomScroll.vue'
import Input from '../views/Settings/components/Input.vue'
import { PLATFORMS, getPlatformProperty } from '../constants/platformConfig'
import { useProjects } from '../composables/useProjects'

const { projects, fetchProjects } = useProjects()
const projectDropdownOpen = ref(false)

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
const dropdownOpen = ref(false)
const showToken = ref(false)
const isCreatingNewProject = ref(false)

// Step 2 state
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
const goalDropdownOpen = ref(false)
const searchQuery = ref('')
const lastIntegrationId = ref(props.resumeIntegrationId)

const stepLabels = {
  1: 'Настройка канала',
  2: 'Выбор профиля',
  3: 'Выбор кампаний',
  4: 'Настройка целей'
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
  dropdownOpen.value = false
}

const close = () => {
  emit('update:isOpen', false)
  error.value = null
  dropdownOpen.value = false
  projectDropdownOpen.value = false
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
    if (currentStep.value === 2) fetchProfiles(lastIntegrationId.value)
    if (currentStep.value === 3) fetchCampaigns(lastIntegrationId.value)
    if (currentStep.value === 4) fetchGoals(lastIntegrationId.value)
  }
}

const prevStep = () => {
  searchQuery.value = '' // Reset search
  if (currentStep.value > 1) {
    currentStep.value--
  }
}

const fetchProfiles = async (integrationId) => {
  loadingProfiles.value = true
  try {
    const { data } = await api.get(`integrations/${integrationId}/profiles`)
    profiles.value = data
    
    // AUTO-SKIP: If only one profile, select it automatically
    if (data.length === 1) {
      console.log('Auto-selecting single profile:', data[0].login)
      selectProfile(data[0])
    }
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
    nextStep()
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

const selectPrimaryGoal = (goal) => {
  form.primary_goal_id = goal.id
  goalDropdownOpen.value = false
}

const toggleGoal = (id) => {
  const index = selectedGoalIds.value.indexOf(id)
  if (index > -1) {
    selectedGoalIds.value.splice(index, 1)
  } else {
    selectedGoalIds.value.push(id)
  }
}

const handleSubmit = async () => {
  if (loading.value) return
  loading.value = true
  error.value = null

  try {
    const { data } = await api.post('integrations/', form)
    lastIntegrationId.value = data.id
    
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
}

const finishConnection = async () => {
  loadingFinish.value = true
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
