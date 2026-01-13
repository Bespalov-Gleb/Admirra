<template>
  <div class="min-h-screen bg-[#f1f4f9] -m-6 p-8 animate-fade-in">
    <div class="max-w-7xl mx-auto space-y-8">
      <div class="flex items-center justify-between">
        <h2 class="text-[15px] font-bold text-[#2d3a5d] tracking-tight">Активные интеграции</h2>
      </div>

      <!-- Список проектов -->
      <div v-if="loading" class="flex justify-center py-12">
        <div class="w-8 h-8 border-3 border-blue-600/20 border-t-blue-600 rounded-full animate-spin"></div>
      </div>
      
      <div v-else-if="groupedClients.length === 0" class="text-center py-16 bg-white rounded-xl border border-gray-100 shadow-sm">
        <p class="text-gray-400 text-sm">У вас пока нет активных интеграций</p>
        <button @click="showAddModal = true" class="mt-4 text-blue-600 text-sm font-bold hover:underline">Добавить интеграцию</button>
      </div>

      <div v-else class="space-y-10">
        <div v-for="client in groupedClients" :key="client.id" class="space-y-4">
          <!-- Заголовок Проекта -->
          <div class="px-2">
            <h3 class="text-[13px] font-bold text-[#4e5d78] tracking-tight">Проект: {{ client.name }}</h3>
          </div>

          <!-- Список интеграций в строку -->
          <div class="space-y-3">
            <div v-for="item in client.integrations" :key="item.id" 
                 class="group bg-white rounded-xl border border-gray-100 p-3.5 flex items-center shadow-sm hover:shadow-md transition-all duration-300">
              
              <!-- Иконка и Инфо -->
              <div class="flex items-center gap-3.5 flex-1 min-w-0">
                <div class="w-10 h-10 flex-shrink-0 bg-white rounded-xl flex items-center justify-center border border-gray-50 overflow-hidden group-hover:scale-105 transition-transform shadow-sm">
                  <img v-if="item.platform === 'YANDEX_DIRECT' || item.platform === 'YANDEX_METRIKA'" src="https://favicon.yandex.net/favicon/v2/yandex.ru?size=32&stub=1" class="w-7 h-7 object-contain" />
                  <img v-else-if="item.platform === 'VK_ADS'" src="https://vk.com/favicon.ico" class="w-7 h-7 object-contain" />
                  <div v-else class="w-full h-full bg-gray-100 flex items-center justify-center text-[10px] font-bold text-gray-400">{{ item.platform.split('_')[0] }}</div>
                </div>
                
                <div class="min-w-0">
                  <h4 class="text-[13px] font-bold text-[#2d3a5d] leading-none mb-1.5">
                    {{ platformLabels[item.platform] || item.platform }}
                  </h4>
                  <p class="text-[10px] font-medium text-gray-400 truncate">ID: {{ item.account_id || 'Не указан' }}</p>
                </div>
              </div>

              <!-- Правая часть: Настройки и Действия -->
              <div class="flex items-center gap-8 pl-4">
                
                <!-- Badge Авто Синхронизация -->
                <div class="hidden sm:flex items-center gap-3">
                  <div 
                    @click="openSyncSettings(item)"
                    class="h-8 px-4 bg-[#2b2d31] hover:bg-[#1a1b1e] rounded-[10px] flex items-center justify-center gap-2.5 cursor-pointer border border-transparent active:scale-95 transition-all shadow-sm"
                  >
                    <div v-if="item.auto_sync" class="flex items-center gap-2">
                       <svg v-if="item.sync_interval <= 60" class="w-3.5 h-3.5 text-white animate-spin-slow" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                         <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                       </svg>
                       <span class="text-[10px] font-bold text-white tracking-wide">
                         Каждые {{ formatInterval(item.sync_interval) }}
                       </span>
                    </div>
                    <span v-else class="text-[10px] font-bold text-white tracking-wide opacity-50">
                      Авто Синхронизация выкл.
                    </span>
                  </div>
                  
                  <!-- Switch (Optional but good for quick toggle) -->
                  <label class="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" :checked="item.auto_sync" @change="toggleAutoSync(item)" class="sr-only peer">
                    <div class="w-7 h-4 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-3 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>

                <!-- Status Badge -->
                <div class="flex flex-col items-end gap-1 px-4 min-w-[100px]">
                  <div 
                    class="px-2.5 py-1 rounded-full text-[9px] font-black uppercase tracking-wider flex items-center gap-1.5 transition-all"
                    :class="{
                      'bg-green-50 text-green-600': item.sync_status === 'SUCCESS',
                      'bg-red-50 text-red-600': item.sync_status === 'FAILED',
                      'bg-gray-50 text-gray-400': item.sync_status === 'NEVER' || item.sync_status === 'PENDING'
                    }"
                  >
                    <div class="w-1.5 h-1.5 rounded-full" :class="{
                      'bg-green-500': item.sync_status === 'SUCCESS',
                      'bg-red-500': item.sync_status === 'FAILED',
                      'bg-gray-300': item.sync_status === 'NEVER' || item.sync_status === 'PENDING'
                    }"></div>
                    {{ statusLabels[item.sync_status] || 'Неизвестно' }}
                  </div>
                  <span v-if="item.error_message" class="text-[9px] text-red-400 font-medium max-w-[150px] truncate" :title="item.error_message">
                    {{ item.error_message }}
                  </span>
                </div>

                <!-- Action Links -->
                <div class="flex items-center gap-6">
                  <button 
                    @click="testConnection(item.id)" 
                    :disabled="testingId === item.id"
                    class="text-[11px] font-bold text-gray-500 hover:text-black transition-colors disabled:opacity-50"
                  >
                    {{ testingId === item.id ? 'Проверка...' : 'Проверить' }}
                  </button>
                  <button 
                    @click="handleSync(item.id)" 
                    :disabled="syncingId === item.id"
                    class="text-[11px] font-bold text-[#4483f8] hover:text-[#2d65d4] transition-colors disabled:opacity-50"
                  >
                    {{ syncingId === item.id ? 'Синхронизация...' : 'Синхронизировать' }}
                  </button>
                  <button 
                    @click="deleteIntegration(item.id)" 
                    class="text-[11px] font-bold text-[#f56c6c] hover:text-[#d9534f] transition-colors"
                  >
                    Удалить
                  </button>
                </div>
              </div>

            </div>
          </div>
        </div>
      </div>

      <!-- Footer Action -->
      <div v-if="!loading" class="flex justify-start">
         <button 
          @click="showAddModal = true"
          class="flex items-center gap-2 text-blue-600 hover:text-blue-700 font-bold text-xs"
        >
          <PlusIcon class="w-4 h-4" />
          Подключить новый канал
        </button>
      </div>
    </div>

    <!-- Модальное окно для выбора интервала -->
    <div v-if="activeSettingsItem" class="fixed inset-0 z-50 flex items-center justify-center px-4 bg-black/20 backdrop-blur-sm" @click.self="activeSettingsItem = null">
      <div class="bg-white rounded-2xl shadow-xl border border-gray-100 p-6 w-full max-w-sm animate-pop-in">
        <h3 class="text-sm font-black text-gray-900 uppercase tracking-widest mb-4">Настройки синхронизации</h3>
        <p class="text-[10px] text-gray-400 uppercase font-black mb-6">Выберите частоту обновления данных</p>
        
        <div class="space-y-2">
          <div v-for="opt in intervals" :key="opt.value" 
               @click="updateSyncInterval(activeSettingsItem, opt.value)"
               class="p-3.5 rounded-xl border border-gray-50 flex items-center justify-between cursor-pointer hover:bg-gray-50 transition-all"
               :class="activeSettingsItem.sync_interval === opt.value ? 'bg-blue-50 border-blue-100' : ''">
             <span class="text-xs font-bold text-gray-700">{{ opt.label }}</span>
             <div v-if="activeSettingsItem.sync_interval === opt.value" class="w-2 h-2 rounded-full bg-blue-600 shadow-[0_0_8px_rgba(37,99,235,0.4)]"></div>
          </div>
        </div>

        <button @click="activeSettingsItem = null" class="w-full mt-6 py-3 bg-gray-900 text-white rounded-xl text-[10px] font-black uppercase tracking-widest">Готово</button>
      </div>
    </div>

    <UnifiedConnectModal 
      v-model:is-open="showAddModal" 
      :resume-integration-id="resumeIntegrationId"
      :initial-step="initialStep"
      @success="fetchIntegrations" 
    />
    <AgencyImportModal ref="agencyModalRef" v-model:is-open="isAgencyModalOpen" @success="fetchIntegrations" />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { PlusIcon } from '@heroicons/vue/24/outline'
import api from '../../../api/axios'
import UnifiedConnectModal from '../../../components/UnifiedConnectModal.vue'
import AgencyImportModal from '../../../components/AgencyImportModal.vue'
import { useToaster } from '../../../composables/useToaster'

const clients = ref([])
const loading = ref(true)
const showAddModal = ref(false)
const activeSettingsItem = ref(null)
const resumeIntegrationId = ref(null)
const initialStep = ref(1)

const platformLabels = {
  'YANDEX_DIRECT': 'Яндекс.Директ',
  'VK_ADS': 'VK Ads',
  'YANDEX_METRIKA': 'Яндекс.Метрика'
}

const statusLabels = {
  'SUCCESS': 'Активно',
  'FAILED': 'Ошибка',
  'PENDING': 'Ожидание',
  'NEVER': 'Не проверено'
}

const syncingId = ref(null)
const testingId = ref(null)

const toaster = useToaster()

const intervals = [
  { label: '15 минут', value: 15 },
  { label: '1 час', value: 60 },
  { label: '6 часов', value: 360 },
  { label: '24 часа', value: 1440 }
]

const formatInterval = (min) => {
  if (min < 60) return `${min} минут`
  if (min === 60) return `1 час`
  if (min < 1440) return `${min / 60} часов`
  return `24 часа`
}

const isAgencyModalOpen = ref(false)
const agencyModalRef = ref(null)
const route = useRoute()

const fetchIntegrations = async () => {
  loading.value = true
  try {
    const response = await api.get('clients/')
    clients.value = response.data
  } catch (error) {
    console.error('Error fetching integrations:', error)
  } finally {
    loading.value = false
  }
}

const groupedClients = computed(() => {
  return clients.value.filter(c => c.integrations && c.integrations.length > 0)
})

const deleteIntegration = async (id) => {
  if (!confirm('Вы уверены, что хотите удалить эту интеграцию?')) return
  try {
    await api.delete(`integrations/${id}`)
    fetchIntegrations()
  } catch (error) {
    console.error('Error deleting integration:', error)
  }
}

const toggleAutoSync = async (integration) => {
  const newValue = !integration.auto_sync
  try {
    await api.patch(`integrations/${integration.id}`, { auto_sync: newValue })
    integration.auto_sync = newValue
    toaster.success(`Авто-синхронизация ${newValue ? 'включена' : 'выключена'}`)
  } catch (err) {
    toaster.error('Не удалось обновить настройки')
  }
}

const openSyncSettings = (item) => {
  activeSettingsItem.value = item
}

const updateSyncInterval = async (integration, value) => {
  try {
    await api.patch(`integrations/${integration.id}`, { sync_interval: value })
    integration.sync_interval = value
    toaster.success('Интервал синхронизации обновлен')
  } catch (err) {
    toaster.error('Не удалось обновить интервал')
  }
}

const testConnection = async (id) => {
  testingId.value = id
  try {
    const { data } = await api.get(`integrations/${id}/test-connection`)
    if (data.status === 'success') {
      toaster.success('Соединение активно: ' + data.details.join(', '))
    } else if (data.status === 'warning') {
      toaster.warning('Соединение частично активно: ' + data.details.join(', '))
    } else {
      toaster.error('Ошибка соединения: ' + data.details.join(', '))
    }
    fetchIntegrations()
  } catch (error) {
    toaster.error('Не удалось проверить соединение: ' + (error.response?.data?.detail || error.message))
  } finally {
    testingId.value = null
  }
}

const handleSync = async (id) => {
  syncingId.value = id
  try {
    await api.post(`integrations/${id}/sync`, { days: 730 })
    toaster.success('Синхронизация завершена успешно!')
    fetchIntegrations() 
  } catch (error) {
    toaster.error('Ошибка при синхронизации: ' + (error.response?.data?.detail || error.message))
  } finally {
    syncingId.value = null
  }
}

onMounted(() => {
  fetchIntegrations()
  
  if (route.query.resume_integration_id) {
    resumeIntegrationId.value = route.query.resume_integration_id
    const isAgency = route.query.is_agency === 'true'
    initialStep.value = isAgency ? 2 : 3 // Skip profile selection for standard accounts
    showAddModal.value = true
    
    // Clean up URL
    window.history.replaceState({}, '', window.location.pathname)
  }

  if (route.query.trigger_agency_import === '1') {
    const token = localStorage.getItem('temp_agency_token')
    if (token) {
      isAgencyModalOpen.value = true
      setTimeout(() => {
        if (agencyModalRef.value) {
          agencyModalRef.value.handleToken(token)
        }
      }, 100)
    }
    window.history.replaceState({}, '', window.location.pathname)
  }
})
</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-pop-in {
  animation: popIn 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.15);
}

@keyframes popIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

.animate-spin-slow {
  animation: spin 3s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
