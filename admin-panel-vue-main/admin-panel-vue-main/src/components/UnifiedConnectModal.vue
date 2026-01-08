<template>
  <div v-if="isOpen" class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-[100] animate-fade-in" @click.self="close">
    <div class="bg-white rounded-[2rem] p-0.5 w-full max-w-md shadow-[0_20px_50px_rgba(0,0,0,0.25)] transform transition-all animate-modal-in border border-gray-100 relative overflow-hidden">
      <!-- Decorative Background elements -->
      <div class="absolute top-0 right-0 w-32 h-32 bg-blue-50 rounded-full -mr-16 -mt-16 blur-2xl opacity-60"></div>
      <div class="absolute bottom-0 left-0 w-24 h-24 bg-red-50 rounded-full -ml-12 -mb-12 blur-2xl opacity-50"></div>

      <div class="relative z-10 flex flex-col max-h-[85vh] p-6">
        <!-- Header: Fixed -->
        <div class="flex items-center justify-between mb-6 flex-shrink-0">
          <div>
            <h3 class="text-xl font-black text-black tracking-tight leading-tight uppercase">Добавить интеграцию</h3>
            <p class="text-[11px] text-gray-500 mt-1 font-bold uppercase tracking-wider">Новый рекламный канал</p>
          </div>
          <button @click="close" class="p-2 bg-gray-50 text-gray-500 hover:text-black hover:rotate-90 hover:bg-gray-100 transition-all rounded-full border border-gray-100 shadow-sm">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
          </button>
        </div>

        <!-- Scrollable Content using CustomScroll -->
        <CustomScroll class="flex-grow">
          <div class="pr-1 pb-4 space-y-5">
            <div v-if="error" class="p-4 bg-red-50 border border-red-100 text-red-600 text-[12px] rounded-xl flex items-start gap-3 animate-shake shadow-sm">
              <svg class="w-5 h-5 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path></svg>
              <span class="font-bold">{{ error }}</span>
            </div>

            <form @submit.prevent="handleSubmit" class="space-y-5">
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

              <!-- Platform Description -->
              <div v-if="currentPlatform.description" class="p-4 bg-gray-50/80 border border-gray-100 rounded-2xl">
                <p v-html="currentPlatform.description" class="text-[11px] text-gray-600 font-bold leading-relaxed uppercase tracking-tight italic"></p>
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
                    </div>
                  </div>
                </div>
              </div>

              <!-- Yandex Auth Button -->
              <div v-if="form.platform === 'YANDEX_DIRECT'" class="py-2">
                <button
                  type="button"
                  @click="initYandexAuth"
                  :disabled="loadingAuth"
                  class="w-full py-4 bg-[#FC3F1D] text-white rounded-2xl hover:bg-[#e63212] transition-all flex items-center justify-center gap-3 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 active:translate-y-0"
                >
                  <div v-if="loadingAuth" class="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  <span v-else class="font-black text-[12px] uppercase tracking-widest flex items-center gap-2">
                    <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M12.923 15.686L8.683 5H5v14h3.04V9.695l4.577 9.305h3.336l-5.603-9.52 5.09-4.48h-3.32l-3.2 3.11V15.686z"/></svg>
                    Подключить Яндекс Директ
                  </span>
                </button>
                <p class="text-[10px] text-gray-400 text-center mt-3 font-medium">
                  Вы будете перенаправлены на страницу авторизации Яндекс
                </p>
              </div>

              <!-- VK Auth Button -->
              <div v-else-if="form.platform === 'VK_ADS' && !currentPlatform.isDynamic" class="py-2">
                <button
                  type="button"
                  @click="initVKAuth"
                  :disabled="loadingAuth"
                  class="w-full py-4 bg-[#0077FF] text-white rounded-2xl hover:bg-[#0066EE] transition-all flex items-center justify-center gap-3 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 active:translate-y-0"
                >
                  <div v-if="loadingAuth" class="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  <span v-else class="font-black text-[12px] uppercase tracking-widest flex items-center gap-2">
                    <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M13.162 18.994c-6.098 0-9.57-4.172-9.714-11.104h3.047c.1 5.093 2.344 7.25 4.125 7.696V7.89H13.5v4.39c1.703-.187 3.562-2.188 4.172-4.39h2.89c-.531 2.766-2.563 4.766-3.734 5.438 1.171.547 3.5 2.25 4.406 5.664h-3.14c-.703-2.203-2.454-3.906-4.22-4.08v4.08h-2.1c-.015.002-.015.002 0 .006z"/></svg>
                    Подключить VK Ads
                  </span>
                </button>
                <p class="text-[10px] text-gray-400 text-center mt-3 font-medium">
                  Вы будете перенаправлены на страницу авторизации VK
                </p>
              </div>

              <!-- Standard Token Input (Show for other non-dynamic platforms) -->
              <Input
                v-else-if="!currentPlatform.isDynamic"
                v-model="form.access_token"
                :type="showToken ? 'text' : 'password'"
                label="Access Token"
                labelClass="text-[10px] font-black text-black uppercase tracking-[0.2em] mb-1 px-1"
                inputClass="rounded-2xl font-mono text-[13px] tracking-widest text-black shadow-sm hover:border-gray-400"
                placeholder="••••••••••••••••••••"
                required
              >
                <template #label-right>
                  <a 
                    v-if="currentPlatform.tokenLink"
                    :href="currentPlatform.tokenLink"
                    target="_blank"
                    class="text-[9px] text-blue-500 hover:text-blue-600 font-black flex items-center gap-1.5 bg-blue-50/50 px-2 py-1 rounded-lg transition-all"
                  >
                    <span>ПОЛУЧИТЬ</span>
                    <svg class="w-3 h-3 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                  </a>
                </template>
                <button 
                  type="button"
                  @click="showToken = !showToken"
                  class="absolute right-4 top-1/2 -translate-y-1/2 text-gray-300 hover:text-black transition-colors p-1"
                >
                  <svg v-if="!showToken" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path></svg>
                  <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.542-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18"></path></svg>
                </button>
              </Input>

              <!-- Dynamic Fields (e.g., VK Ads Client ID/Secret) -->
              <template v-if="currentPlatform.isDynamic">
                <Input
                  v-for="field in currentPlatform.dynamicFields"
                  :key="field.key"
                  v-model="form[field.key]"
                  :type="field.type"
                  :label="field.label"
                  labelClass="text-[10px] font-black text-black uppercase tracking-[0.2em] mb-1 px-1"
                  inputClass="rounded-2xl text-black text-[13px] shadow-sm hover:border-gray-400"
                  :input-style="field.type === 'password' ? 'font-mono tracking-widest' : 'font-bold'"
                  :placeholder="field.placeholder"
                  :required="field.required"
                >
                  <template v-if="field.helpLink" #label-right>
                    <a 
                      :href="field.helpLink"
                      target="_blank"
                      class="text-[9px] text-blue-500 hover:text-blue-600 font-black flex items-center gap-1.5 bg-blue-50/50 px-2 py-1 rounded-lg transition-all"
                    >
                      <span>ГДЕ ВЗЯТЬ?</span>
                      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                    </a>
                  </template>
                </Input>
              </template>

              <!-- Account/Cabinet ID (Hidden for Yandex and VK as it's not needed for auth initially) -->
              <Input 
                v-if="form.platform !== 'YANDEX_DIRECT' && form.platform !== 'VK_ADS'"
                v-model="form.account_id" 
                :label="currentPlatform.accountIdLabel || 'Account ID'"
                labelClass="text-[10px] font-black text-black uppercase tracking-[0.2em] mb-1 px-1"
                inputClass="rounded-2xl font-bold text-black text-[13px] shadow-sm hover:border-gray-400"
                :hint="form.platform === 'YANDEX_DIRECT' ? '(необязательно)' : '(обязательно)'"
                :placeholder="currentPlatform.accountIdPlaceholder || 'Введите ID'" 
              />
            </form>
          </div>
        </CustomScroll>
        
        <!-- Footer: Fixed -->
        <div class="flex gap-3 pt-6 mt-4 border-t border-gray-50 flex-shrink-0 bg-white">
          <button type="button" @click="close" class="flex-1 py-3.5 text-[10px] font-black uppercase tracking-widest border border-gray-200 rounded-2xl text-gray-400 hover:text-gray-700 hover:bg-gray-50 transition-all">Отмена</button>
          <button @click="handleSubmit" :disabled="loading" class="flex-[1.5] py-3.5 bg-gray-900 text-white rounded-2xl hover:bg-black hover:-translate-y-0.5 active:translate-y-0 font-black text-[10px] uppercase tracking-widest disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 shadow-lg">
            <div v-if="loading" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            <span>{{ loading ? 'ЗАГРУЗКА...' : 'ПОДКЛЮЧИТЬ' }}</span>
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
  }
})

const emit = defineEmits(['update:isOpen', 'success'])

const loading = ref(false)
const error = ref(null)
const dropdownOpen = ref(false)
const showToken = ref(false)

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
    form.client_name = props.initialClientName
    error.value = null
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
  projectDropdownOpen.value = false
}

onMounted(() => {
  fetchProjects()
})

const handleSubmit = async () => {
  if (loading.value) return
  loading.value = true
  error.value = null

  try {
    const response = await api.post('integrations/', form)
    emit('success', response.data)
    form.access_token = ''
    form.account_id = ''
    form.client_id = ''
    form.client_secret = ''
    close()
  } catch (err) {
    error.value = err.response?.data?.detail || 'Ошибка подключения'
  } finally {
    loading.value = false
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
