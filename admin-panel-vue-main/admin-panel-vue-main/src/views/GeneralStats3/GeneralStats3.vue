<template>
  <div class="space-y-6 overflow-x-hidden w-full">
    <!-- Заголовок с фильтрами -->
    <div class="space-y-6">
      <div v-if="statsError" class="p-4 bg-red-50 border border-red-200 text-red-600 rounded-xl mb-4 text-sm font-medium">
        {{ statsError }}
      </div>
      <div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-6 mb-8 py-4 px-6 bg-white/50 backdrop-blur-md rounded-[32px] border border-white shadow-sm">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <h1 class="text-2xl sm:text-3xl font-black text-gray-900 tracking-tight">
              {{ dashboardTitle }}
            </h1>
            <button 
              v-if="filters.campaign_ids && filters.campaign_ids.length > 0" 
              @click="filters.campaign_ids = []"
              class="px-3 py-1 bg-blue-100 text-blue-600 text-[10px] font-black uppercase rounded-full hover:bg-blue-200 transition-colors flex items-center gap-1"
            >
              Сбросить 
              <ArrowPathIcon class="w-2.5 h-2.5" />
            </button>
          </div>
          <p class="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em]">Общая аналитика и управление кампаниями</p>
        </div>

        <div class="flex flex-wrap gap-4 items-end">
          <!-- Project Filter -->
          <div class="flex flex-col gap-1.5">
            <label class="text-[9px] font-black text-gray-400 uppercase tracking-widest ml-1">Проект</label>
            <select
              v-model="filters.client_id"
              class="px-4 py-2 border border-gray-100 rounded-xl bg-gray-50/50 text-sm font-bold text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 appearance-none cursor-pointer min-w-[160px] h-[42px] transition-all hover:bg-white hover:border-gray-200 shadow-sm"
            >
              <option value="">Все проекты</option>
              <option v-for="client in clients" :key="client.id" :value="client.id">
                {{ client.name }}
              </option>
            </select>
          </div>

          <!-- Channel Filter -->
          <div class="flex flex-col gap-1.5">
            <label class="text-[9px] font-black text-gray-400 uppercase tracking-widest ml-1">Канал</label>
            <select
              v-model="filters.channel"
              class="px-4 py-2 border border-gray-100 rounded-xl bg-gray-50/50 text-sm font-bold text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 appearance-none cursor-pointer min-w-[140px] h-[42px] transition-all hover:bg-white hover:border-gray-200 shadow-sm"
            >
              <option value="all">Все каналы</option>
              <option value="google" disabled>Google Ads</option>
              <option value="yandex">Яндекс.Директ</option>
              <option value="vk">ВКонтакте</option>
              <option value="telegram" disabled>Telegram Ads</option>
            </select>
          </div>

          <!-- Campaign Filter -->
          <div class="flex flex-col gap-1.5">
            <label class="text-[9px] font-black text-gray-400 uppercase tracking-widest ml-1">Кампания</label>
            <select
              v-model="selectedCampaignId"
              class="px-4 py-2 border border-gray-100 rounded-xl bg-gray-50/50 text-sm font-bold text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 appearance-none cursor-pointer min-w-[180px] h-[42px] transition-all hover:bg-white hover:border-gray-200 shadow-sm"
              :disabled="loadingCampaigns || !filters.client_id || !campaigns.length"
            >
              <template v-if="!filters.client_id">
                <option value="">Выберите проект</option>
              </template>
              <template v-else-if="!campaigns.length && !loadingCampaigns">
                <option value="">Нет кампаний</option>
              </template>
              <template v-else>
                <option value="">Все кампании ({{ campaigns.length }})</option>
                <option v-for="campaign in campaigns" :key="campaign.id" :value="campaign.id">
                  {{ campaign.name }}
                </option>
              </template>
            </select>
          </div>

          <!-- Period Filter -->
          <div class="flex flex-col gap-1.5">
            <label class="text-[9px] font-black text-gray-400 uppercase tracking-widest ml-1">Период</label>
            <select v-model="filters.period" @change="handlePeriodChange" class="px-4 py-2 border border-gray-100 rounded-xl bg-gray-50/50 text-sm font-bold text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 appearance-none cursor-pointer min-w-[120px] h-[42px] transition-all hover:bg-white hover:border-gray-200 shadow-sm pr-8">
              <option value="7">7 дней</option>
              <option value="14">14 дней</option>
              <option value="30">30 дней</option>
              <option value="90">90 дней</option>
              <option value="custom">Период</option>
            </select>
          </div>

          <!-- Custom Date Range -->
          <template v-if="filters.period === 'custom'">
            <input type="date" v-model="filters.start_date" class="px-4 py-2 border border-gray-100 rounded-xl bg-white text-sm font-bold text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 h-[42px]">
            <input type="date" v-model="filters.end_date" class="px-4 py-2 border border-gray-100 rounded-xl bg-white text-sm font-bold text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 h-[42px]">
          </template>

          <!-- Export Button -->
          <button 
            @click="handleExport"
            class="flex items-center gap-2 px-4 py-2 rounded-xl border border-blue-100 bg-blue-50/50 text-blue-600 hover:bg-blue-600 hover:text-white h-[42px] transition-all group shadow-sm shadow-blue-100/50"
            title="Скачать отчет CSV"
          >
            <ArrowDownTrayIcon class="w-4 h-4 group-hover:scale-110 transition-transform" />
            <span class="text-[10px] font-black uppercase tracking-widest">CSV</span>
          </button>
        </div>
      </div>


    <!-- Карточки KPI -->
    <div class="w-full">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-xs font-black text-gray-400 uppercase tracking-[0.2em]">Общая статистика</h2>
      </div>

      <div v-if="loading && !summary.expenses" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6 mb-8">
        <Skeleton v-for="i in 6" :key="i" class="h-32 rounded-3xl shadow-sm" />
      </div>

      <div 
        v-else-if="summary && summary.expenses !== undefined"
        class="w-full overflow-hidden relative group/scroll mb-8"
      >
        <div 
          ref="cardsContainer"
          class="flex gap-4 sm:gap-6 overflow-x-auto pb-4 custom-scrollbar select-none max-w-full"
          @mousedown="handleMouseDown"
          @mousemove="handleMouseMove"
          @mouseup="handleMouseUp"
          @mouseleave="handleMouseUp"
          @wheel.prevent="handleWheel"
          @touchstart="handleTouchStart"
          @touchmove="handleTouchMove"
          @touchend="handleTouchEnd"
        >
          <!-- Расходы -->
          <div class="flex-shrink-0">
            <CardV3
              title="Расходы"
              :value="(summary.expenses || 0).toLocaleString() + ' ₽'"
              :trend="Math.abs(summary.trends?.expenses || 0)"
              :change-positive="(summary.trends?.expenses || 0) <= 0"
              :icon="CurrencyDollarIcon"
              icon-color="orange"
              :is-selected="selectedMetric === 'expenses'"
              @click="toggleMetric('expenses')"
            />
          </div>
          
          <!-- Показы -->
          <div class="flex-shrink-0">
            <CardV3
              title="Показы"
              :value="(summary.impressions || 0).toLocaleString()"
              :trend="summary.trends?.impressions || 0"
              :change-positive="summary.trends?.impressions >= 0"
              :icon="EyeIcon"
              icon-color="blue"
              :is-selected="selectedMetric === 'impressions'"
              @click="toggleMetric('impressions')"
            />
          </div>
          
          <!-- Переходы -->
          <div class="flex-shrink-0">
            <CardV3
              title="Переходы"
              :value="(summary.clicks || 0).toLocaleString()"
              :trend="summary.trends?.clicks || 0"
              :change-positive="summary.trends?.clicks >= 0"
              :icon="ArrowPathIcon"
              icon-color="green"
              :is-selected="selectedMetric === 'clicks'"
              @click="toggleMetric('clicks')"
            />
          </div>
          
          <!-- Лиды -->
          <div class="flex-shrink-0">
            <CardV3
              title="Лиды"
              :value="(summary.leads || 0).toLocaleString()"
              :trend="summary.trends?.leads || 0"
              :change-positive="summary.trends?.leads >= 0"
              :icon="UserGroupIcon"
              icon-color="red"
              :is-selected="selectedMetric === 'leads'"
              @click="toggleMetric('leads')"
            />
          </div>
          
          <!-- CPC -->
          <div class="flex-shrink-0">
            <CardV3
              title="Sр. CPC"
              :value="(summary.cpc || 0).toLocaleString() + ' ₽'"
              :trend="Math.abs(summary.trends?.cpc || 0)"
              :change-positive="(summary.trends?.cpc || 0) <= 0"
              :icon="HandRaisedIcon"
              icon-color="purple"
              :is-selected="selectedMetric === 'cpc'"
              @click="toggleMetric('cpc')"
            />
          </div>
          
          <!-- CPA -->
          <div class="flex-shrink-0">
            <CardV3
              title="Sр. CPA"
              :value="(summary.cpa || 0).toLocaleString() + ' ₽'"
              :trend="Math.abs(summary.trends?.cpa || 0)"
              :change-positive="(summary.trends?.cpa || 0) <= 0"
              :icon="BanknotesIcon"
              icon-color="pink"
              :is-selected="selectedMetric === 'cpa'"
              @click="toggleMetric('cpa')"
            />
          </div>
        </div>
        <!-- Progress Bar for loading -->
        <div v-if="loading" class="absolute bottom-0 left-0 h-0.5 bg-blue-600 animate-progress-fast z-20"></div>
      </div>
    </div>
    


    <!-- График статистики -->
    <div class="w-full relative">
      <div v-if="loading" class="absolute inset-0 bg-white/50 backdrop-blur-[1px] z-10 flex items-center justify-center rounded-[40px]">
        <div class="flex flex-col items-center gap-2">
          <div class="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <span class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Обновление графика...</span>
        </div>
      </div>
      <StatisticsChart 
        :dynamics="dynamics" 
        :selected-metric="selectedMetric"
        :period="filters.period"
        @update:period="(p) => { filters.period = p; handlePeriodChange(); }"
      />
    </div>

    <!-- Эффективность продвижения -->
    <div class="w-full">
      <PromotionEfficiency :summary="summary" />
    </div>


    <!-- Connect Modal for post-callback or manual use -->
    <UnifiedConnectModal
      ref="connectModalRef"
      v-model:is-open="isConnectModalOpen"
      @success="fetchStats"
    />
  </div>
</div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import {
  CurrencyDollarIcon,
  EyeIcon,
  ArrowPathIcon,
  UserGroupIcon,
  HandRaisedIcon,
  BanknotesIcon,
  ArrowDownTrayIcon,
  PlusIcon
} from '@heroicons/vue/24/solid'
import CardV3 from './components/CardV3.vue'
import StatisticsChart from './components/StatisticsChart.vue'
import PromotionEfficiency from './components/PromotionEfficiency.vue'
import UnifiedConnectModal from '../../components/UnifiedConnectModal.vue'
import Skeleton from '../../components/ui/Skeleton.vue'
import { useDashboardStats } from '../../composables/useDashboardStats'
import { useRoute } from 'vue-router'
import api from '../../api/axios'
import { useToaster } from '../../composables/useToaster'
import { useProjects } from '../../composables/useProjects'

// Integrate existing data logic
const {
  summary,
  dynamics,
  clients,
  campaigns,
  loading,
  error: statsError,
  filters,
  handlePeriodChange,
  fetchStats,
  fetchClients,
  loadingCampaigns
} = useDashboardStats()

const selectedCampaignId = computed({
  get: () => (filters.campaign_ids && filters.campaign_ids.length > 0) ? filters.campaign_ids[0] : '',
  set: (val) => {
    filters.campaign_ids = val ? [val] : []
  }
})

const { projects: globalProjects, setCurrentProject, fetchProjects: refreshGlobalProjects } = useProjects()
const toaster = useToaster()
const route = useRoute()

// Modal state
const isConnectModalOpen = ref(false)
const connectModalRef = ref(null)

// React to post-callback redirect
watch(() => route.query.new_integration_id, (id) => {
  if (id) {
    isConnectModalOpen.value = true
    // Need to wait for modal to mount
    setTimeout(() => {
      if (connectModalRef.value) {
        connectModalRef.value.currentStep = 2
        connectModalRef.value.lastIntegrationId = id
        connectModalRef.value.fetchCampaigns(id)
      }
    }, 100)
    
    // Clear query param without recharge
    window.history.replaceState({}, '', window.location.pathname)
  }
}, { immediate: true })

const dashboardTitle = computed(() => {
  if (filters.campaign_ids && filters.campaign_ids.length > 0) {
    const campaignId = filters.campaign_ids[0]
    const campaign = campaigns.value.find(c => c.id === campaignId)
    return campaign ? `Кампания: ${campaign.name}` : `Статистика по кампаниям (${filters.campaign_ids.length})`
  }
  if (filters.client_id) {
    const client = clients.value.find(c => c.id === filters.client_id)
    return client ? `Проект: ${client.name}` : 'Статистика проекта'
  }
  if (filters.channel !== 'all') {
    const channelMap = { yandex: 'Яндекс.Директ', vk: 'VK Ads' }
    return `Статистика: ${channelMap[filters.channel] || filters.channel}`
  }
  return 'Статистика по всем проектам'
})

const creatingProject = ref(false)

const handleCreateProject = async (name) => {
  creatingProject.value = true
  try {
    const { data } = await api.post('clients/', { name })
    toaster.success(`Проект "${name}" успешно создан!`)
    
    // Refresh clients list (for dashboard and header)
    await Promise.all([
      fetchClients(),
      refreshGlobalProjects()
    ])
    
    // Automatically select the new project
    if (data && data.id) {
      setCurrentProject(data.id)
      filters.client_id = data.id
    }
    
    await fetchStats()
  } catch (err) {
    console.error('Error creating project:', err)
    toaster.error('Не удалось создать проект')
  } finally {
    creatingProject.value = false
  }
}

const cardsContainer = ref(null)
const isDragging = ref(false)
const startX = ref(0)
const scrollLeft = ref(0)
const selectedMetric = ref(null) // 'expenses', 'impressions', 'clicks', 'leads', 'cpc', 'cpa' или null для всех

const toggleMetric = (metric) => {
  if (selectedMetric.value === metric) {
    selectedMetric.value = null
  } else {
    selectedMetric.value = metric
  }
}

const handleSelectCampaign = (campaign) => {
  if (campaign && campaign.id) {
    filters.campaign_ids = [campaign.id]
    // Scroll to top to see updated stats
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

const handleExport = async () => {
  try {
    const params = {
      start_date: filters.start_date,
      end_date: filters.end_date,
      platform: filters.channel
    }
    if (filters.client_id) params.client_id = filters.client_id
    if (filters.campaign_ids && filters.campaign_ids.length > 0) {
      params.campaign_ids = filters.campaign_ids
    }

    const response = await api.get('dashboard/export/csv', {
      params,
      responseType: 'blob'
    })
    
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `report_${filters.start_date}_${filters.end_date}.csv`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    
    toaster.success('Отчет успешно сформирован')
  } catch (err) {
    console.error('Export error:', err)
    toaster.error('Не удалось скачать отчет')
  }
}

// Drag to scroll logic (from new design)
const handleMouseDown = (e) => {
  isDragging.value = true
  startX.value = e.pageX - cardsContainer.value.offsetLeft
  scrollLeft.value = cardsContainer.value.scrollLeft
  cardsContainer.value.style.scrollBehavior = 'auto'
}

const handleMouseMove = (e) => {
  if (!isDragging.value) return
  e.preventDefault()
  e.stopPropagation()
  const x = e.pageX - cardsContainer.value.offsetLeft
  const walk = (x - startX.value) * 2 // Скорость прокрутки
  cardsContainer.value.scrollLeft = scrollLeft.value - walk
}

const handleMouseUp = () => {
  isDragging.value = false
  if (cardsContainer.value) {
    cardsContainer.value.style.scrollBehavior = 'smooth'
  }
}

// Прокрутка колесом мыши
const handleWheel = (e) => {
  if (cardsContainer.value) {
    e.preventDefault()
    e.stopPropagation()
    cardsContainer.value.scrollLeft += e.deltaY
  }
}

// Touch события для мобильных устройств
const handleTouchStart = (e) => {
  isDragging.value = true
  startX.value = e.touches[0].pageX - cardsContainer.value.offsetLeft
  scrollLeft.value = cardsContainer.value.scrollLeft
  cardsContainer.value.style.scrollBehavior = 'auto'
}

const handleTouchMove = (e) => {
  if (!isDragging.value) return
  e.preventDefault()
  e.stopPropagation()
  const x = e.touches[0].pageX - cardsContainer.value.offsetLeft
  const walk = (x - startX.value) * 2
  cardsContainer.value.scrollLeft = scrollLeft.value - walk
}

const handleTouchEnd = () => {
  isDragging.value = false
  if (cardsContainer.value) {
    cardsContainer.value.style.scrollBehavior = 'smooth'
  }
}
</script>

<style scoped>
/* Optional: Hide scrollbar but keep functionality */
.custom-scrollbar::-webkit-scrollbar {
  height: 0px;
  background: transparent;
}
.custom-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
