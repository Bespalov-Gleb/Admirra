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
                      <div class="w-8 h-8 rounded-xl flex items-center justify-center text-[10px] font-black shadow-sm border" :class="platformClasses[form.platform]">
                        {{ platformInitials[form.platform] }}
                      </div>
                      <div class="text-left">
                        <span class="block text-[13px] font-black text-black leading-none">{{ platformLabels[form.platform] }}</span>
                      </div>
                    </div>
                    <svg class="w-4 h-4 text-gray-400 group-hover:text-black transition-all duration-300" :class="{ 'rotate-180': dropdownOpen }" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                  </button>

                  <div v-if="dropdownOpen" class="absolute z-[110] mt-2 w-full bg-white border border-gray-200 rounded-2xl shadow-xl py-2 overflow-hidden animate-slide-down">
                    <button 
                      v-for="(label, key) in platformLabels" 
                      :key="key"
                      type="button"
                      @click="selectPlatform(key)"
                      class="w-full px-4 py-2.5 text-left flex items-center gap-3 hover:bg-gray-50 transition-all border-b border-gray-50 last:border-none"
                      :class="{ 'bg-blue-50/40': form.platform === key }"
                    >
                      <div class="w-7 h-7 rounded-lg flex items-center justify-center text-[9px] font-black shadow-sm" :class="platformClasses[key]">
                        {{ platformInitials[key] }}
                      </div>
                      <span class="text-[12px] font-black" :class="form.platform === key ? 'text-blue-600' : 'text-gray-600 font-bold'">{{ label }}</span>
                    </button>
                  </div>
                </div>
              </div>

              <!-- Client Name -->
              <Input
                v-model="form.client_name"
                label="Название проекта"
                labelClass="text-[10px] font-black text-black uppercase tracking-[0.2em] mb-1 px-1"
                inputClass="rounded-2xl font-bold text-black text-[13px] shadow-sm hover:border-gray-400"
                placeholder="Напр: ТРАФИК АГЕНТСТВО"
                required
              />

              <!-- Token Input -->
              <Input
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
                    v-if="tokenLinks[form.platform]"
                    :href="tokenLinks[form.platform]"
                    target="_blank"
                    class="text-[9px] text-blue-500 hover:text-blue-600 font-black flex items-center gap-1.5 bg-blue-50/50 px-2 py-1 rounded-lg transition-all"
                  >
                    <span>ПОЛУЧИТЬ</span>
                    <svg class="w-3 h-3 group-hover/link:translate-x-0.5 group-hover/link:-translate-y-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
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

              <!-- Account ID -->
              <Input 
                v-model="form.account_id" 
                :label="form.platform === 'VK_ADS' ? 'ID Кабинета' : (form.platform === 'YANDEX_METRIKA' ? 'ID Счетчика' : 'Account ID')"
                labelClass="text-[10px] font-black text-black uppercase tracking-[0.2em] mb-1 px-1"
                inputClass="rounded-2xl font-bold text-black text-[13px] shadow-sm hover:border-gray-400"
                :hint="form.platform === 'YANDEX_DIRECT' ? '(необязательно)' : '(обязательно)'"
                :placeholder="form.platform === 'VK_ADS' ? 'Напр: 1234567' : (form.platform === 'YANDEX_METRIKA' ? 'Напр: 98765432' : 'Пусто для Яндекс.Директ')" 
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
import { ref, reactive, watch } from 'vue'
import api from '../api/axios'
import CustomScroll from './ui/CustomScroll.vue'
import Input from '../views/Settings/components/Input.vue'

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
  client_name: props.initialClientName,
  access_token: '',
  refresh_token: '',
  account_id: ''
})

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    form.client_name = props.initialClientName
    error.value = null
  }
})

const platformLabels = {
  'YANDEX_DIRECT': 'Яндекс.Директ',
  'VK_ADS': 'VK Ads',
  'YANDEX_METRIKA': 'Яндекс.Метрика'
}

const platformInitials = {
  'YANDEX_DIRECT': 'ЯD',
  'VK_ADS': 'VK',
  'YANDEX_METRIKA': 'YM'
}

const platformClasses = {
  'YANDEX_DIRECT': 'bg-red-500 text-white border-red-600',
  'VK_ADS': 'bg-blue-600 text-white border-blue-700',
  'YANDEX_METRIKA': 'bg-yellow-400 text-black border-yellow-500'
}

const tokenLinks = {
  'YANDEX_DIRECT': 'https://oauth.yandex.ru/authorize?response_type=token&client_id=3febb68881204d9380089f718e5251b1',
  'VK_ADS': 'https://ads.vk.com/hq/settings/access',
  'YANDEX_METRIKA': 'https://oauth.yandex.ru/authorize?response_type=token&client_id=3febb68881204d9380089f718e5251b1'
}

const selectPlatform = (key) => {
  form.platform = key
  dropdownOpen.value = false
}

const close = () => {
  emit('update:isOpen', false)
  error.value = null
  dropdownOpen.value = false
}

const handleSubmit = async () => {
  if (loading.value) return
  loading.value = true
  error.value = null

  try {
    const response = await api.post('integrations/', form)
    emit('success', response.data)
    form.access_token = ''
    form.account_id = ''
    close()
  } catch (err) {
    error.value = err.response?.data?.detail || 'Ошибка подключения'
  } finally {
    loading.value = false
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
