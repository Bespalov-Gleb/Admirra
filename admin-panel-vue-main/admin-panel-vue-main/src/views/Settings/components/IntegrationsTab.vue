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
      
      <!-- Список проектов -->
      <div v-if="loading" class="flex justify-center py-12">
        <div class="w-8 h-8 border-3 border-blue-600/20 border-t-blue-600 rounded-full animate-spin"></div>
      </div>
      
      <div v-else-if="groupedClients.length === 0" class="text-center py-16 bg-white rounded-[32px] border border-white/80 shadow-sm animate-fade-in mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-gray-50 rounded-2xl mb-4 border border-gray-100">
           <svg class="w-8 h-8 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
             <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 10V3L4 14h7v7l9-11h-7z" />
           </svg>
        </div>
        <p class="text-[13px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">Ничего не найдено</p>
        <p class="text-[11px] text-gray-400 mb-6">У вас пока нет активных интеграций для ваших проектов</p>
        <button 
          @click="showAddModal = true" 
          class="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-black uppercase tracking-widest rounded-xl transition-all active:scale-95 shadow-lg shadow-blue-500/20"
        >
          Подключить интеграцию
        </button>
      </div>
      
      <div v-else class="grid grid-cols-1 gap-8">
        <div v-for="client in groupedClients" :key="client.id" 
             class="bg-white/60 backdrop-blur-xl rounded-[32px] border border-white/80 shadow-sm overflow-hidden animate-fade-in hover:shadow-md transition-all">
          
          <!-- Шапка лоиҳа (Project Header) -->
          <div class="px-8 py-6 border-b border-gray-50 bg-gradient-to-r from-gray-50/50 to-transparent flex items-center justify-between">
            <div class="flex items-center gap-4">
              <div class="w-10 h-10 bg-white rounded-xl flex items-center justify-center border border-gray-100 shadow-sm">
                <span class="text-xs font-black text-gray-400">{{ client.name.charAt(0).toUpperCase() }}</span>
              </div>
              <div>
                <h3 class="text-[11px] font-black text-gray-400 uppercase tracking-widest leading-none mb-1.5">Проект</h3>
                <p class="text-[15px] font-bold text-[#2d3a5d] tracking-tight">{{ client.name }}</p>
              </div>
            </div>
            <div class="px-4 py-1.5 bg-blue-50/50 border border-blue-100/50 rounded-full">
              <span class="text-[10px] font-black text-blue-600 uppercase tracking-widest">
                {{ client.integrations.length }} {{ getPlural(client.integrations.length, ['Канал', 'Канала', 'Каналов']) }}
              </span>
            </div>
          </div>

          <!-- Список интеграций (Integrations List) -->
          <div class="p-4 space-y-2">
            <div v-for="item in client.integrations" :key="item.id" 
                 class="group pl-4 pr-3 py-3 rounded-2xl border border-transparent hover:border-gray-100 hover:bg-gray-50/50 flex items-center transition-all">
              
              <!-- Платформа и данные -->
              <div class="flex items-center gap-4 flex-1 min-w-0">
                <div class="w-12 h-12 flex-shrink-0 bg-white rounded-xl flex items-center justify-center border border-gray-100 overflow-hidden group-hover:scale-105 transition-transform shadow-sm">
                  <img v-if="item.platform === 'YANDEX_DIRECT' || item.platform === 'YANDEX_METRIKA'" src="https://favicon.yandex.net/favicon/v2/yandex.ru?size=32&stub=1" class="w-8 h-8 object-contain" />
                  <img v-else-if="item.platform === 'VK_ADS'" src="https://vk.com/favicon.ico" class="w-8 h-8 object-contain" />
                  <div v-else class="w-full h-full bg-gray-100 flex items-center justify-center text-[11px] font-black text-gray-400">{{ item.platform.split('_')[0] }}</div>
                </div>
                
                <div class="min-w-0">
                  <div class="flex items-center gap-2 mb-1">
                    <h4 class="text-[13px] font-bold text-[#202939] leading-none">
                      {{ platformLabels[item.platform] || item.platform }}
                    </h4>
                    <span class="text-[9px] font-black text-gray-300 uppercase letter-wider bg-gray-50 px-1.5 py-0.5 rounded border border-gray-100">
                      ID: {{ (item.account_id || '').split('@')[0] }}
                    </span>
                  </div>
                  <div class="flex items-center gap-3">
                    <div class="flex items-center gap-1.5">
                      <div class="w-1.5 h-1.5 rounded-full" :class="item.sync_status === 'SUCCESS' ? 'bg-green-500' : 'bg-red-400'"></div>
                      <span class="text-[10px] font-bold text-gray-400 uppercase tracking-tight">
                        {{ item.sync_status === 'SUCCESS' ? 'Активно' : 'Ошибка' }}
                      </span>
                    </div>
                    <span v-if="item.last_sync_at" class="text-[10px] font-medium text-gray-300">
                      Последняя: {{ formatDate(item.last_sync_at) }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- Настройки и действия (Settings & Actions) -->
              <div class="flex items-center gap-6 pr-2">
                
                <!-- Авто Синхронизация -->
                <div class="flex items-center gap-3 border-r border-gray-100 pr-6 mr-2">
                  <div 
                    @click="openSyncSettings(item)"
                    class="h-8 px-4 bg-[#212121] hover:bg-black text-[10px] font-black text-white uppercase tracking-widest rounded-xl flex items-center gap-2 cursor-pointer transition-all active:scale-95 shadow-sm"
                  >
                    <svg v-if="item.auto_sync" class="w-3 h-3 text-blue-400 animate-spin-slow" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    <span>{{ item.auto_sync ? formatInterval(item.sync_interval) : 'Авто-Синх.' }}</span>
                  </div>
                  
                  <label class="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" :checked="item.auto_sync" @change="toggleAutoSync(item)" class="sr-only peer">
                    <div class="w-8 h-4.5 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-3.5 after:content-[''] after:absolute after:top-[3px] after:left-[3px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>

                <!-- Тугмаи Настройка (Action Menu) -->
                <div class="flex items-center gap-3">
                  <button 
                    @click="openEditModal(item)"
                    class="px-4 py-2 bg-gray-50 hover:bg-gray-100 text-[10px] font-black text-gray-600 uppercase tracking-widest rounded-xl transition-all active:scale-95 border border-gray-100"
                  >
                    Настроить
                  </button>
                  
                  <div class="relative group/menu">
                    <button class="w-9 h-9 flex items-center justify-center rounded-xl bg-white border border-gray-100 hover:border-gray-200 transition-all text-gray-400 hover:text-gray-600">
                      <EllipsisVerticalIcon class="w-5 h-5" />
                    </button>
                    <!-- Floating Actions Menu -->
                    <div class="absolute right-0 top-full mt-2 w-48 bg-white rounded-2xl shadow-2xl border border-gray-100 py-2 hidden group-hover/menu:block z-50 animate-pop-in">
                       <button @click="testConnection(item.id)" class="w-full px-4 py-2.5 text-left text-[11px] font-bold text-gray-600 hover:bg-gray-50 flex items-center gap-2">
                         <div class="w-1.5 h-1.5 rounded-full bg-blue-500"></div> Проверить связь
                       </button>
                       <button @click="handleSync(item.id)" class="w-full px-4 py-2.5 text-left text-[11px] font-bold text-blue-600 hover:bg-blue-50 flex items-center gap-2">
                         <div class="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></div> Синхронизировать
                       </button>
                       <div class="my-1 border-t border-gray-50"></div>
                       <button @click="deleteIntegration(item.id)" class="w-full px-4 py-2.5 text-left text-[11px] font-bold text-red-500 hover:bg-red-50 flex items-center gap-2">
                         <TrashIcon class="w-3.5 h-3.5" /> Удалить
                       </button>
                    </div>
                  </div>
                </div>
              </div>

            </div>
          </div>
        </div>
      </div>

      <!-- Footer Action -->
      <div v-if="!loading" class="flex justify-center mt-12 mb-20">
         <button 
          @click="showAddModal = true"
          class="flex items-center gap-3 px-8 py-4 bg-[#2b3a5d] hover:bg-[#1a253d] text-white rounded-[24px] shadow-xl shadow-blue-900/10 transition-all active:scale-95 border border-white/10 group"
        >
          <div class="w-6 h-6 bg-white/10 rounded-lg flex items-center justify-center group-hover:bg-blue-500 transition-colors">
            <PlusIcon class="w-4 h-4" />
          </div>
          <span class="text-xs font-black uppercase tracking-widest">Подключить новый канал</span>
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
      @success="handleIntegrationSuccess" 
    />
    <AgencyImportModal ref="agencyModalRef" v-model:is-open="isAgencyModalOpen" @success="fetchIntegrations" />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { PlusIcon, EllipsisVerticalIcon, TrashIcon } from '@heroicons/vue/24/outline'
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
  if (min < 60) return `${min} мин`
  if (min === 60) return `1 час`
  if (min < 1440) {
    const hours = min / 60
    return `${hours} ${getPlural(hours, ['час', 'часа', 'часов'])}`
  }
  return `24 часа`
}

const getPlural = (n, forms) => {
  n = Math.abs(n) % 100
  const n1 = n % 10
  if (n > 10 && n < 20) return forms[2]
  if (n1 > 1) {
    if (n1 < 5) return forms[1]
    return forms[2]
  }
  if (n1 === 1) return forms[0]
  return forms[2]
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) + ', ' + 
         date.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short' })
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

const handleIntegrationSuccess = () => {
  toaster.success('Интеграция успешно настроена!')
  fetchIntegrations()
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

const openEditModal = (item) => {
  resumeIntegrationId.value = item.id
  initialStep.value = 2 // Start from Profiles/Campaigns
  showAddModal.value = true
}

onMounted(() => {
  fetchIntegrations()
  
  if (route.query.resume_integration_id) {
    resumeIntegrationId.value = route.query.resume_integration_id
    const isAgency = route.query.is_agency === 'true'
    initialStep.value = 2 // Always show profile selection for consistency
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
