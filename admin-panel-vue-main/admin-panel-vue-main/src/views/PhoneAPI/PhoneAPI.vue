<template>
  <div class="min-h-screen bg-gray-50 p-8">
    <div class="max-w-6xl mx-auto">
      <!-- Header -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900 mb-2">Квалификатор лидов</h1>
        <p class="text-gray-500">Тестирование валидации лидов и настройка webhook интеграций</p>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <!-- Left Column: Test Form -->
        <div class="space-y-6">
          <!-- Test Lead Form Card -->
          <div class="bg-white rounded-3xl p-8 shadow-sm border border-gray-100">
            <h2 class="text-xl font-bold text-gray-900 mb-6 flex items-center gap-3">
              <div class="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center">
                <svg class="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
              Тестовая проверка лида
            </h2>

            <form @submit.prevent="validateLead" class="space-y-4">
              <!-- Phone -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Телефон <span class="text-red-500">*</span>
                </label>
                <input 
                  v-model="form.phone"
                  type="tel"
                  placeholder="+7 (999) 123-45-67"
                  class="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                  required
                />
              </div>

              <!-- Email -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input 
                  v-model="form.email"
                  type="email"
                  placeholder="example@mail.ru"
                  class="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                />
              </div>

              <!-- Name -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Имя</label>
                <input 
                  v-model="form.name"
                  type="text"
                  placeholder="Иван Петров"
                  class="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                />
              </div>

              <!-- UTM Toggle -->
              <div class="pt-2">
                <button 
                  type="button"
                  @click="showUtm = !showUtm"
                  class="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
                >
                  <svg :class="['w-4 h-4 transition-transform', showUtm ? 'rotate-90' : '']" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                  UTM параметры
                </button>
              </div>

              <!-- UTM Fields -->
              <div v-if="showUtm" class="space-y-3 pl-4 border-l-2 border-blue-100">
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="block text-xs font-medium text-gray-500 mb-1">utm_source</label>
                    <input v-model="form.utm_source" type="text" placeholder="yandex" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" />
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-gray-500 mb-1">utm_medium</label>
                    <input v-model="form.utm_medium" type="text" placeholder="cpc" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" />
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-gray-500 mb-1">utm_campaign</label>
                    <input v-model="form.utm_campaign" type="text" placeholder="campaign123" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" />
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-gray-500 mb-1">utm_content</label>
                    <input v-model="form.utm_content" type="text" placeholder="banner1" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" />
                  </div>
                </div>
              </div>

              <!-- Test Mode Toggle -->
              <div class="pt-2 flex items-center gap-3">
                <label class="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" v-model="testMode" class="sr-only peer" />
                  <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-500"></div>
                </label>
                <span class="text-sm font-medium" :class="testMode ? 'text-green-600' : 'text-gray-500'">
                  {{ testMode ? '✓ Тестовый режим (без CAPTCHA)' : 'Продакшен режим (с CAPTCHA)' }}
                </span>
              </div>

              <!-- Submit Button -->
              <button
                type="submit"
                :disabled="loading"
                class="w-full py-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-semibold rounded-xl transition flex items-center justify-center gap-2"
              >
                <svg v-if="loading" class="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {{ loading ? 'Проверка...' : 'Проверить лид' }}
              </button>
            </form>
          </div>

          <!-- Result Card -->
          <div v-if="result" :class="['rounded-3xl p-6 shadow-sm border transition-all', result.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200']">
            <div class="flex items-start gap-4">
              <div :class="['w-12 h-12 rounded-xl flex items-center justify-center', result.success ? 'bg-green-100' : 'bg-red-100']">
                <svg v-if="result.success" class="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                <svg v-else class="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <div class="flex-1">
                <h3 :class="['font-bold text-lg', result.success ? 'text-green-800' : 'text-red-800']">
                  {{ result.success ? 'Лид прошёл валидацию' : 'Лид отклонён' }}
                </h3>
                <p v-if="result.rejection_reason" class="text-red-600 text-sm mt-1">
                  Причина: {{ formatReason(result.rejection_reason) }}
                </p>
                <div class="mt-3 grid grid-cols-2 gap-2 text-sm">
                  <div v-if="result.phone_type" class="flex items-center gap-2">
                    <span class="text-gray-500">Тип:</span>
                    <span class="font-medium">{{ result.phone_type }}</span>
                  </div>
                  <div v-if="result.phone_provider" class="flex items-center gap-2">
                    <span class="text-gray-500">Оператор:</span>
                    <span class="font-medium">{{ result.phone_provider }}</span>
                  </div>
                  <div v-if="result.phone_region" class="flex items-center gap-2">
                    <span class="text-gray-500">Регион:</span>
                    <span class="font-medium">{{ result.phone_region }}</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <span class="text-gray-500">Время:</span>
                    <span class="font-medium">{{ result.execution_time_ms?.toFixed(0) }} мс</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Column: Webhook Info & History -->
        <div class="space-y-6">
          <!-- Webhook URLs Card -->
          <div class="bg-white rounded-3xl p-8 shadow-sm border border-gray-100">
            <h2 class="text-xl font-bold text-gray-900 mb-6 flex items-center gap-3">
              <div class="w-10 h-10 bg-purple-100 rounded-xl flex items-center justify-center">
                <svg class="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                </svg>
              </div>
              Webhook интеграции
            </h2>

            <div class="space-y-4">
              <!-- Tilda -->
              <div class="p-4 bg-gray-50 rounded-xl">
                <div class="flex items-center justify-between mb-2">
                  <span class="font-semibold text-gray-900">Tilda</span>
                  <button @click="copyToClipboard(webhookUrls.tilda)" class="text-blue-600 hover:text-blue-800 text-sm flex items-center gap-1">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    Копировать
                  </button>
                </div>
                <code class="text-sm text-gray-600 break-all">{{ webhookUrls.tilda }}</code>
              </div>

              <!-- Marquiz -->
              <div class="p-4 bg-gray-50 rounded-xl">
                <div class="flex items-center justify-between mb-2">
                  <span class="font-semibold text-gray-900">Marquiz</span>
                  <button @click="copyToClipboard(webhookUrls.marquiz)" class="text-blue-600 hover:text-blue-800 text-sm flex items-center gap-1">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    Копировать
                  </button>
                </div>
                <code class="text-sm text-gray-600 break-all">{{ webhookUrls.marquiz }}</code>
              </div>

              <p class="text-xs text-gray-500">
                Укажите эти URL в настройках форм Tilda и Marquiz для автоматической валидации лидов.
              </p>
            </div>
          </div>

          <!-- History Card -->
          <div class="bg-white rounded-3xl p-8 shadow-sm border border-gray-100">
            <div class="flex items-center justify-between mb-6">
              <h2 class="text-xl font-bold text-gray-900 flex items-center gap-3">
                <div class="w-10 h-10 bg-orange-100 rounded-xl flex items-center justify-center">
                  <svg class="w-5 h-5 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                История проверок
              </h2>
              <button v-if="history.length > 0" @click="clearHistory" class="text-sm text-gray-500 hover:text-red-600">
                Очистить
              </button>
            </div>

            <div v-if="history.length === 0" class="text-center py-8 text-gray-400">
              <svg class="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              <p>Пока нет проверок</p>
            </div>

            <div v-else class="space-y-3 max-h-80 overflow-y-auto">
              <div 
                v-for="(item, index) in history" 
                :key="index"
                :class="['p-3 rounded-xl border', item.success ? 'bg-green-50 border-green-100' : 'bg-red-50 border-red-100']"
              >
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <span :class="['w-2 h-2 rounded-full', item.success ? 'bg-green-500' : 'bg-red-500']"></span>
                    <span class="font-medium text-sm">{{ item.phone }}</span>
                  </div>
                  <span class="text-xs text-gray-500">{{ item.time }}</span>
                </div>
                <p v-if="item.rejection_reason" class="text-xs text-red-600 mt-1 pl-4">
                  {{ formatReason(item.rejection_reason) }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../../api/axios'

// API base URL для webhook (полный URL, так как используется вне приложения)
const API_BASE = window.location.origin

// Form state
const form = ref({
  phone: '',
  email: '',
  name: '',
  utm_source: '',
  utm_medium: '',
  utm_campaign: '',
  utm_content: ''
})

const showUtm = ref(false)
const loading = ref(false)
const result = ref(null)
const history = ref([])
const testMode = ref(true) // По умолчанию тестовый режим

// Webhook URLs
const webhookUrls = ref({
  tilda: `${API_BASE}/api/webhook/tilda/`,
  marquiz: `${API_BASE}/api/webhook/marquiz/`
})

// Load history from localStorage
onMounted(() => {
  const saved = localStorage.getItem('leadQualifierHistory')
  if (saved) {
    try {
      history.value = JSON.parse(saved)
    } catch (e) {
      console.error('Failed to load history:', e)
    }
  }
})

// Validate lead
async function validateLead() {
  loading.value = true
  result.value = null

  try {
    const payload = {
      phone: form.value.phone,
      email: form.value.email || undefined,
      name: form.value.name || undefined,
      utm_source: form.value.utm_source || undefined,
      utm_medium: form.value.utm_medium || undefined,
      utm_campaign: form.value.utm_campaign || undefined,
      utm_content: form.value.utm_content || undefined
    }

    // Выбираем эндпоинт в зависимости от режима
    let data
    
    if (testMode.value) {
      // test-validate ожидает phone в query params
      const params = { phone: form.value.phone }
      if (form.value.email) params.email = form.value.email
      if (form.value.name) params.name = form.value.name
      
      const response = await api.post('lead/test-validate', null, { params })
      data = response.data
    } else {
      const response = await api.post('lead/', payload)
      data = response.data
    }
    
    // Преобразуем ответ test-validate в формат обычного результата
    if (testMode.value && data.overall_valid !== undefined) {
      result.value = {
        success: data.overall_valid,
        rejection_reason: data.overall_valid ? null : Object.entries(data.checks)
          .filter(([_, v]) => !v.passed)
          .map(([k, v]) => `${k}: ${v.reason || v.error || 'failed'}`)
          .join(', '),
        phone_type: data.checks?.dadata?.type,
        phone_provider: data.checks?.dadata?.provider,
        phone_region: data.checks?.dadata?.region,
        execution_time_ms: 0
      }
    } else {
      result.value = data
    }

    // Add to history
    const historyItem = {
      phone: form.value.phone,
      success: result.value.success,
      rejection_reason: result.value.rejection_reason,
      time: new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
    }
    history.value.unshift(historyItem)
    
    // Keep only last 10 items
    if (history.value.length > 10) {
      history.value = history.value.slice(0, 10)
    }

    // Save to localStorage
    localStorage.setItem('leadQualifierHistory', JSON.stringify(history.value))

  } catch (error) {
    console.error('Validation error:', error)
    result.value = {
      success: false,
      rejection_reason: `network_error: ${error.message}`
    }
  } finally {
    loading.value = false
  }
}

// Format rejection reason for display
function formatReason(reason) {
  const reasonMap = {
    'captcha_failed': 'Не пройдена CAPTCHA',
    'honeypot_filled': 'Обнаружен бот',
    'form_filled_too_fast': 'Форма заполнена слишком быстро',
    'stale_timestamp': 'Устаревшая метка времени',
    'empty_or_short_phone': 'Пустой или короткий телефон',
    'phone_too_few_digits': 'Слишком мало цифр в телефоне',
    'phone_too_many_digits': 'Слишком много цифр в телефоне',
    'rate_limit_exceeded': 'Превышен лимит запросов',
    'duplicate_phone': 'Дубликат телефона',
    'duplicate_email': 'Дубликат email',
    'invalid_phone_qc_1': 'Телефон с допущениями',
    'invalid_phone_qc_2': 'Невалидный телефон',
    'dadata_unavailable': 'Сервис валидации недоступен'
  }

  // Check for prefix match
  for (const [key, label] of Object.entries(reasonMap)) {
    if (reason && reason.startsWith(key)) {
      return label
    }
  }

  return reason
}

// Copy to clipboard
async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text)
    // Could add toast notification here
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}

// Clear history
function clearHistory() {
  history.value = []
  localStorage.removeItem('leadQualifierHistory')
}
</script>
