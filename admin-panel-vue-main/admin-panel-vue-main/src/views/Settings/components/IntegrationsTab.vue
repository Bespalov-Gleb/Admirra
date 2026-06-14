<template>
  <div class="min-h-screen bg-[#f1f4f9] -m-6 p-8 animate-fade-in">
    <div class="max-w-7xl mx-auto space-y-8">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h2 class="text-[1.0417rem] font-bold text-[#2d3a5d] tracking-tight">Активные интеграции</h2>
        <div class="relative w-full sm:w-72">
          <MagnifyingGlassIcon class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Поиск по интеграциям"
            class="w-full pl-9 pr-4 py-2.5 text-[0.9028rem] rounded-xl border border-gray-200 bg-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all"
          />
          <button
            v-if="searchQuery"
            @click="searchQuery = ''"
            class="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <XMarkIcon class="w-4 h-4" />
          </button>
        </div>
      </div>

      <!-- Список проектов -->
      <div v-if="loading" class="flex justify-center py-12">
        <div class="w-8 h-8 border-3 border-blue-600/20 border-t-blue-600 rounded-full animate-spin"></div>
      </div>
      
      <div v-else-if="filteredGroupedClients.length === 0" class="text-center py-16 bg-white rounded-[2.2222rem] border border-white/80 shadow-sm animate-fade-in mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-gray-50 rounded-2xl mb-4 border border-gray-100">
           <MagnifyingGlassIcon v-if="searchQuery" class="w-8 h-8 text-gray-300" />
           <svg v-else class="w-8 h-8 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
             <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 10V3L4 14h7v7l9-11h-7z" />
           </svg>
        </div>
        <p class="text-[0.9028rem] font-bold text-gray-500 uppercase tracking-widest mb-1.5">Ничего не найдено</p>
        <p class="text-[0.7639rem] text-gray-400 mb-6">
          {{ searchQuery ? `По запросу «${searchQuery}» ничего не найдено` : 'У вас пока нет активных интеграций для ваших проектов' }}
        </p>
        <button 
          v-if="!searchQuery"
          @click="$router.push('/integrations/wizard')" 
          class="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-[0.7639rem] font-black uppercase tracking-widest rounded-xl transition-all active:scale-95 shadow-lg shadow-blue-500/20"
        >
          Подключить интеграцию
        </button>
        <button 
          v-else
          @click="searchQuery = ''" 
          class="px-6 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-[0.7639rem] font-black uppercase tracking-widest rounded-xl transition-all"
        >
          Очистить поиск
        </button>
      </div>
      
      <div v-else class="grid grid-cols-1 gap-8">
        <div v-for="client in filteredGroupedClients" :key="client.id" 
             class="bg-[#f7f6ed] rounded-[1.7361rem] border border-[#e2dfd0] shadow-sm animate-fade-in transition-all relative z-10 hover:z-50 overflow-hidden">
          
          <!-- Шапка проекта (Project Header) -->
          <div class="px-8 py-6 flex items-start justify-between gap-4">
            <div class="flex items-center gap-4 min-w-0">
              <div class="w-12 h-12 bg-white/80 rounded-full flex items-center justify-center border border-white/80 shadow-sm shrink-0">
                <span class="text-[0.9028rem] font-bold text-[#3b3b36]">{{ projectInitials(client.name) }}</span>
              </div>
              <div class="min-w-0">
                <h3 class="text-[0.9028rem] font-semibold text-[#7d7c73] leading-none mb-1.5">Проект</h3>
                <p class="text-[1.3889rem] font-bold text-[#1f2024] tracking-tight truncate">{{ client.name }}</p>
              </div>
            </div>
            <div class="px-4 py-2 bg-white/35 border border-blue-500/70 rounded-[0.9028rem] shrink-0">
              <span class="text-[0.9722rem] font-semibold text-blue-600">
                {{ client.integrations.length }} {{ getPlural(client.integrations.length, ['канал', 'канала', 'каналов']) }}
              </span>
            </div>
          </div>

          <!-- Список интеграций (Integrations List) -->
          <div class="px-8 pb-8 space-y-4">
            <div v-for="item in client.integrations" :key="item.id" 
                 class="group rounded-[1.3889rem] border border-[#d5d2c6] bg-white px-8 py-7 shadow-sm hover:shadow-md transition-all">
              
              <!-- Платформа и данные -->
              <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
                <div class="flex items-start gap-6 min-w-0">
                  <div class="w-16 h-16 flex-shrink-0 bg-white rounded-full flex items-center justify-center overflow-hidden shadow-sm">
                    <img :src="platformIcon(item.platform)" :alt="platformLabels[item.platform] || item.platform" class="w-full h-full object-contain" />
                  </div>

                  <div class="min-w-0">
                    <div class="flex flex-wrap items-center gap-3 mb-4">
                      <h4 class="text-[1.5278rem] font-bold text-[#1f2024] leading-none">
                        {{ platformLabels[item.platform] || item.platform }}
                      </h4>
                      <span
                        class="px-4 py-1.5 rounded-full text-[0.9722rem] font-semibold"
                        :class="statusBadgeClass(item)"
                        :title="item.error_message || ''"
                      >
                        {{ displayStatus(item) }}
                      </span>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-10 gap-y-4 mb-4">
                      <div>
                        <div class="text-[0.9722rem] font-semibold text-[#777973] mb-1">Последняя синхронизация</div>
                        <div class="text-[1.0417rem] font-semibold text-[#1f2024]">{{ formatSyncDate(item.last_sync_at) }}</div>
                      </div>
                      <div>
                        <div class="text-[0.9722rem] font-semibold text-[#777973] mb-1">Следующая</div>
                        <div class="text-[1.0417rem] font-semibold text-[#1f2024]">{{ formatNextSync(item) }}</div>
                      </div>
                    </div>

                    <div class="flex flex-wrap items-center gap-3 text-[1.0417rem] font-semibold text-[#777973] mb-3">
                      <span class="inline-flex items-center gap-2">
                        <svg class="w-4 h-4 text-[#777973]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6l4 2m6-2a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z" />
                        </svg>
                        {{ formatAutoSyncText(item) }}
                      </span>
                    </div>

                    <div class="flex items-center gap-2 text-[0.9722rem] font-semibold text-[#777973]">
                      <span>ID: {{ item.id }}</span>
                      <button
                        type="button"
                        class="w-5 h-5 inline-flex items-center justify-center rounded-md text-[#777973] hover:bg-gray-100 hover:text-blue-600 transition-colors"
                        title="Скопировать ID"
                        @click="copyIntegrationId(item.id)"
                      >
                        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M8 8h10a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V10a2 2 0 0 1 2-2Z" />
                          <path stroke-linecap="round" stroke-linejoin="round" d="M16 8V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h2" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>

                <!-- Настройки и действия (Settings & Actions) -->
                <div class="flex flex-col items-stretch sm:items-end gap-3 lg:min-w-[21.5278rem]">
                  <button
                    @click="handleSync(item.id)"
                    :disabled="syncingId === item.id"
                    class="h-12 px-6 inline-flex items-center justify-center gap-3 rounded-[0.9028rem] border border-[#c9c9c9] bg-white text-[#1f2024] text-[1.0417rem] font-semibold hover:border-blue-400 hover:text-blue-600 hover:bg-blue-50/40 disabled:opacity-60 disabled:cursor-not-allowed transition-all"
                  >
                    <svg class="w-5 h-5" :class="{ 'animate-spin': syncingId === item.id || isSyncRunning(item) }" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h5M20 20v-5h-5M6.5 17.5a8 8 0 0 0 12-2.5M17.5 6.5a8 8 0 0 0-12 2.5" />
                    </svg>
                    <span>{{ isSyncRunning(item) ? `Синхронизация ${syncProgressById[item.id]?.progress || 0}%` : 'Синхронизировать сейчас' }}</span>
                  </button>

                  <button
                    @click="openEditWizard(item)"
                    class="h-12 px-6 inline-flex items-center justify-center rounded-[0.9028rem] border border-blue-500 bg-blue-50 text-blue-700 text-[1.0417rem] font-semibold hover:bg-blue-100 transition-all"
                  >
                    Настроить
                  </button>

                  <div class="flex items-center justify-end gap-3 pt-1">
                    <label class="inline-flex items-center gap-3 text-[0.9028rem] font-semibold text-[#777973] cursor-pointer select-none">
                      <span>Авто</span>
                      <span class="relative inline-flex items-center">
                        <input type="checkbox" :checked="item.auto_sync" @change="toggleAutoSync(item)" class="sr-only peer">
                        <span class="w-10 h-5 bg-gray-200 rounded-full peer-checked:bg-blue-600 transition-colors"></span>
                        <span class="absolute left-0.5 top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform peer-checked:translate-x-5"></span>
                      </span>
                    </label>

                    <button
                      @click="openSyncSettings(item)"
                      class="text-[0.9028rem] font-semibold text-blue-600 hover:text-blue-700 transition-colors"
                    >
                      Интервал
                    </button>

                    <div class="relative group/menu">
                      <button class="w-9 h-9 flex items-center justify-center rounded-xl bg-white border border-gray-200 hover:border-gray-300 transition-all text-gray-400 hover:text-gray-600">
                        <EllipsisVerticalIcon class="w-5 h-5" />
                      </button>
                      <div class="absolute right-0 top-full pt-2 w-48 bg-white rounded-2xl shadow-2xl border border-gray-100 py-2 hidden group-hover/menu:block z-50 animate-pop-in">
                        <button @click="testConnection(item.id)" class="w-full px-4 py-2.5 text-left text-[0.7639rem] font-bold text-gray-600 hover:bg-gray-50 flex items-center gap-2">
                          <div class="w-1.5 h-1.5 rounded-full bg-blue-500"></div> Проверить связь
                        </button>
                        <div class="my-1 border-t border-gray-50"></div>
                        <button @click="deleteIntegration(item.id)" class="w-full px-4 py-2.5 text-left text-[0.7639rem] font-bold text-red-500 hover:bg-red-50 flex items-center gap-2">
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
      </div>

    </div>

    <!-- Модальное окно для выбора интервала -->
    <div v-if="activeSettingsItem" class="fixed inset-0 z-50 flex items-center justify-center px-4 bg-black/20 backdrop-blur-sm" @click.self="activeSettingsItem = null">
      <div class="bg-white rounded-2xl shadow-xl border border-gray-100 p-6 w-full max-w-sm animate-pop-in">
        <h3 class="text-sm font-black text-gray-900 uppercase tracking-widest mb-4">Настройки синхронизации</h3>
        <p class="text-[0.6944rem] text-gray-400 uppercase font-black mb-6">Выберите частоту обновления данных</p>
        
        <div class="space-y-2">
          <div v-for="opt in intervals" :key="opt.value" 
               @click="updateSyncInterval(activeSettingsItem, opt.value)"
               class="p-3.5 rounded-xl border border-gray-50 flex items-center justify-between cursor-pointer hover:bg-gray-50 transition-all"
               :class="activeSettingsItem.sync_interval === opt.value ? 'bg-blue-50 border-blue-100' : ''">
             <span class="text-xs font-bold text-gray-700">{{ opt.label }}</span>
             <div v-if="activeSettingsItem.sync_interval === opt.value" class="w-2 h-2 rounded-full bg-blue-600 shadow-[0_0_8px_rgba(37,99,235,0.4)]"></div>
          </div>
        </div>

        <button @click="activeSettingsItem = null" class="w-full mt-6 py-3 bg-gray-900 text-white rounded-xl text-[0.6944rem] font-black uppercase tracking-widest">Готово</button>
      </div>
    </div>

  </div>

  <!-- Confirm delete modal -->
  <Teleport to="body">
    <div v-if="deleteConfirm.open" class="fixed inset-0 bg-black/45 flex items-center justify-center z-[9999] p-4" @click.self="deleteConfirm.open = false">
      <div class="bg-white dark:bg-[#2C2F3D] rounded-[1.1111rem] p-8 w-full max-w-sm shadow-2xl flex flex-col gap-4">
        <h4 class="text-[1.1111rem] font-semibold text-gray-900 dark:text-white">Удалить интеграцию?</h4>
        <p class="text-[0.9028rem] text-gray-500 dark:text-white/55">Это действие нельзя отменить. Все данные синхронизации будут удалены.</p>
        <div class="flex gap-3 justify-end mt-2">
          <button class="px-5 py-2.5 rounded-[0.6944rem] bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-white/70 text-[0.9028rem] font-medium" @click="deleteConfirm.open = false">Отмена</button>
          <button class="px-5 py-2.5 rounded-[0.6944rem] bg-red-500 hover:bg-red-600 text-white text-[0.9028rem] font-medium transition-colors" @click="confirmDelete">Удалить</button>
        </div>
      </div>
    </div>
  </Teleport>

</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { EllipsisVerticalIcon, TrashIcon, MagnifyingGlassIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import api from '../../../api/axios'
import { useToaster } from '../../../composables/useToaster'
import { useProjects } from '../../../composables/useProjects'
import avitoIcon from '@/assets/icons/avito.svg'
import vkAdsIcon from '@/assets/icons/vk-ads.png'
import yandexDirectIcon from '@/assets/icons/yandex-direct.svg'

const { currentProjectId } = useProjects()

const clients = ref([])
const loading = ref(true)
const activeSettingsItem = ref(null)
const searchQuery = ref('')

const platformLabels = {
  'YANDEX_DIRECT': 'Яндекс.Директ',
  'VK_ADS': 'VK Ads',
  'AVITO_ADS': 'Avito Ads',
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
const syncProgressById = ref({})

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

const projectInitials = (name = '') => {
  const parts = String(name || '').trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return '—'
  return parts.slice(0, 2).map((part) => part[0]).join('').toUpperCase()
}

const platformIcon = (platform) => {
  if (platform === 'VK_ADS') return vkAdsIcon
  if (platform === 'AVITO_ADS') return avitoIcon
  return yandexDirectIcon
}

const isSyncRunning = (item) => {
  const status = syncProgressById.value[item.id]?.status
  return status === 'QUEUED' || status === 'RUNNING'
}

const displayStatus = (item) => {
  if (isSyncRunning(item)) return 'Синхронизация'
  return statusLabels[item.sync_status] || 'Неизвестно'
}

const statusBadgeClass = (item) => {
  if (isSyncRunning(item)) return 'bg-blue-50 text-blue-700'
  if (item.sync_status === 'SUCCESS') return 'bg-green-50 text-green-700'
  if (item.sync_status === 'FAILED') return 'bg-red-50 text-red-700'
  if (item.sync_status === 'PENDING') return 'bg-amber-50 text-amber-700'
  return 'bg-gray-100 text-gray-500'
}

const formatSyncDate = (dateStr) => {
  if (!dateStr) return 'ещё не было'
  const date = new Date(dateStr)
  if (Number.isNaN(date.getTime())) return '—'
  const day = date.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short' }).replace('.', '')
  const time = date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
  return `${day}, ${time} МСК`
}

const formatNextSync = (item) => {
  if (!item.auto_sync) return 'авто выключено'
  if (!item.last_sync_at) return 'после первой синхронизации'

  const interval = Number(item.sync_interval || 1440)
  const lastSync = new Date(item.last_sync_at)
  if (Number.isNaN(lastSync.getTime())) return '—'

  const nextSync = new Date(lastSync.getTime() + interval * 60 * 1000)
  const now = new Date()
  const todayKey = now.toDateString()
  const tomorrow = new Date(now)
  tomorrow.setDate(now.getDate() + 1)
  const nextKey = nextSync.toDateString()
  const time = nextSync.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })

  if (nextKey === todayKey) return `сегодня ~${time} МСК`
  if (nextKey === tomorrow.toDateString()) return `завтра ~${time} МСК`
  const day = nextSync.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short' }).replace('.', '')
  return `${day} ~${time} МСК`
}

const formatAutoSyncText = (item) => {
  if (!item.auto_sync) return 'Автоматическая синхронизация выключена'
  const interval = Number(item.sync_interval || 1440)
  if (interval === 1440) return 'Обновляется автоматически раз в сутки'
  if (interval < 60) return `Обновляется автоматически раз в ${interval} ${getPlural(interval, ['минуту', 'минуты', 'минут'])}`
  const hours = Math.round(interval / 60)
  return `Обновляется автоматически раз в ${hours} ${getPlural(hours, ['час', 'часа', 'часов'])}`
}

const copyIntegrationId = async (id) => {
  try {
    await navigator.clipboard.writeText(String(id))
    toaster.success('ID интеграции скопирован')
  } catch {
    toaster.error('Не удалось скопировать ID')
  }
}

const route = useRoute()
const router = useRouter()

const fetchIntegrations = async () => {
  loading.value = true
  try {
    const response = await api.get('clients/')
    clients.value = response.data
    await refreshSyncStatuses()
  } catch (error) {
    console.error('Error fetching integrations:', error)
  } finally {
    loading.value = false
  }
}

const refreshSyncStatuses = async () => {
  const integrations = clients.value.flatMap(c => c.integrations || [])
  await Promise.all(integrations.map(async (item) => {
    try {
      const { data } = await api.get(`integrations/${item.id}/sync-status`)
      if (data?.job) {
        syncProgressById.value[item.id] = data.job
      }
    } catch {
      // ignore
    }
  }))
}

const pollSyncJob = (integrationId, jobId) => {
  const pollInterval = setInterval(async () => {
    try {
      const { data } = await api.get(`integrations/sync/jobs/${jobId}`)
      syncProgressById.value[integrationId] = data
      if (data.status === 'SUCCESS') {
        clearInterval(pollInterval)
        toaster.success('Синхронизация завершена успешно!')
        await fetchIntegrations()
      } else if (data.status === 'FAILED' || data.status === 'CANCELLED') {
        clearInterval(pollInterval)
        toaster.error('Ошибка при синхронизации: ' + (data.error || 'Неизвестная ошибка'))
        await fetchIntegrations()
      }
    } catch {
      clearInterval(pollInterval)
    }
  }, 3000)
  setTimeout(() => clearInterval(pollInterval), 10 * 60 * 1000)
}

const handleIntegrationSuccess = () => {
  toaster.success('Интеграция успешно настроена!')
  fetchIntegrations()
}

const groupedClients = computed(() => {
  const withIntegrations = clients.value.filter(c => c.integrations && c.integrations.length > 0)
  // Фильтруем по выбранному проекту в хедере: показываем только интеграции этого проекта
  if (currentProjectId.value) {
    return withIntegrations.filter(c => String(c.id) === String(currentProjectId.value))
  }
  return withIntegrations
})

const filteredGroupedClients = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return groupedClients.value

  return groupedClients.value
    .map(client => {
      const clientMatches = client.name.toLowerCase().includes(q)
      const matchedIntegrations = client.integrations.filter(item => {
        const platformText = (platformLabels[item.platform] || item.platform || '').toLowerCase()
        const accountId = (item.account_id || '').toLowerCase()
        const accountName = (item.account_name || '').toLowerCase()
        return platformText.includes(q) || accountId.includes(q) || accountName.includes(q)
      })
      if (clientMatches) return { ...client, integrations: client.integrations }
      if (matchedIntegrations.length > 0) return { ...client, integrations: matchedIntegrations }
      return null
    })
    .filter(Boolean)
})

const deleteConfirm = ref({ open: false, id: null })

const deleteIntegration = (id) => {
  deleteConfirm.value = { open: true, id }
}

const confirmDelete = async () => {
  const id = deleteConfirm.value.id
  deleteConfirm.value.open = false
  try {
    await api.delete(`integrations/${id}`)
    toaster.success('Интеграция удалена')
    fetchIntegrations()
  } catch (error) {
    toaster.error('Не удалось удалить интеграцию')
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
    const { data } = await api.post(`integrations/${id}/sync`, { days: 90, force_full: false })
    toaster.info('Синхронизация запущена. Данные появятся через несколько минут.')
    fetchIntegrations()
    if (data?.job_id) {
      pollSyncJob(id, data.job_id)
    }
  } catch (error) {
    toaster.error('Ошибка при синхронизации: ' + (error.response?.data?.detail || error.message))
  } finally {
    syncingId.value = null
  }
}

const openEditWizard = (item) => {
  router.push({
    path: '/integrations/wizard',
    query: { 
      resume_integration_id: item.id,
      initial_step: 2 
    }
  })
}

watch(currentProjectId, () => {
  fetchIntegrations()
})

onMounted(() => {
  fetchIntegrations()
  
  // If there's a resume_integration_id, redirect to wizard page
  if (route.query.resume_integration_id) {
    router.push({
      path: '/integrations/wizard',
      query: {
        resume_integration_id: route.query.resume_integration_id,
        initial_step: 2
      }
    })
    return
  }

  // SIMPLIFIED ARCHITECTURE: Removed agency import logic
  // All integrations are now one token = one account
})
</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(0.5556rem); }
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
