<template>
  <div class="space-y-6 overflow-x-hidden w-full">
    <!-- Заголовок с фильтрами -->
    <div class="space-y-6">
      <div v-if="statsError" class="p-4 bg-red-50 border border-red-200 text-red-600 rounded-xl mb-4 text-sm font-medium">
        {{ statsError }}
      </div>
      
      <div class="flex flex-col xl:flex-row xl:items-center justify-between gap-6 mb-8 py-5 px-6 sm:px-8 bg-white/60 backdrop-blur-xl rounded-[32px] border border-white/80 shadow-sm transition-all hover:shadow-md">
        <div class="min-w-0 flex-shrink-0">
          <StatsHeader 
            :label="filters.client_id ? 'Выбранный проект' : 'Общий дашборд'"
            :title="dashboardTitle"
            :subtitle="dynamicSubtitle"
            :show-reset="filters.campaign_ids && filters.campaign_ids.length > 0"
            @reset="filters.campaign_ids = []"
          />
        </div>

        <div class="flex-grow xl:flex xl:justify-end min-w-0">
          <StatsFilters 
            :filters="filters"
            :clients="clients"
            :all-campaigns="allCampaigns"
            :loading-campaigns="loadingCampaigns"
            @period-change="handlePeriodChange"
            @export="handleExport"
            @update:campaign-ids="(ids) => filters.campaign_ids = ids"
          />
        </div>
      </div>

    <!-- Карточки KPI -->
    <div class="w-full">
      <div v-if="loading && !summary.expenses" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6 mb-8">
        <Skeleton v-for="i in 6" :key="i" class="h-32 rounded-3xl shadow-sm" />
      </div>

      <KPIOverview
        v-else-if="summary && summary.expenses !== undefined"
        :summary="summary"
        :selected-metric="selectedMetric"
        :loading="loading"
        @toggle-metric="toggleMetric"
        class="mb-8"
      />
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
      <PromotionEfficiency :summary="summary" :campaigns="campaigns" />
    </div>

  </div>
</div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import {
  ArrowPathIcon,
} from '@heroicons/vue/24/solid'

// Components
import StatisticsChart from './components/StatisticsChart.vue'
import PromotionEfficiency from './components/PromotionEfficiency.vue'
import KPIOverview from './components/KPIOverview.vue'
import StatsFilters from './components/StatsFilters.vue'
import StatsHeader from './components/StatsHeader.vue'
import Skeleton from '../../components/ui/Skeleton.vue'

// Logic
import { useDashboardStats } from '../../composables/useDashboardStats'
import { useRoute, useRouter } from 'vue-router'
import { useToaster } from '../../composables/useToaster'
import { useProjects } from '../../composables/useProjects'
import api from '../../api/axios'

const {
  summary,
  dynamics,
  clients,
  allCampaigns,
  loading,
  error: statsError,
  filters,
  handlePeriodChange,
  fetchStats,
  loadingCampaigns
} = useDashboardStats()

const { currentProjectId, setCurrentProject } = useProjects()
const toaster = useToaster()
const route = useRoute()
const router = useRouter()

// --- Project Synchronization ---

// Sync Global -> Local
watch(currentProjectId, (newId) => {
  if (filters.client_id !== newId) {
    filters.client_id = newId
  }
}, { immediate: true })

// Sync Local -> Global
watch(() => filters.client_id, (newId) => {
  if (currentProjectId.value !== newId) {
    setCurrentProject(newId)
  }
})

// --- State & UI Logic ---

const selectedMetric = ref(null)

const toggleMetric = (metric) => {
  selectedMetric.value = selectedMetric.value === metric ? null : metric
}

const dynamicSubtitle = computed(() => {
  if (filters.campaign_ids?.length > 0) {
    return 'Детальная статистика выбранной кампании'
  }
  if (filters.client_id) {
    return 'Аналитика и показатели эффективности проекта'
  }
  if (filters.channel !== 'all') {
    return 'Статистика по конкретному рекламному каналу'
  }
  return 'Общая аналитика по всем активным проектам'
})

const dashboardTitle = computed(() => {
  if (filters.campaign_ids?.length > 0) {
    const campaignId = filters.campaign_ids[0]
    const campaign = allCampaigns.value.find(c => c.id === campaignId)
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

// --- Handlers ---

const handleExport = async () => {
  try {
    const params = {
      start_date: filters.start_date,
      end_date: filters.end_date,
      platform: filters.channel,
      client_id: filters.client_id || undefined,
      campaign_ids: filters.campaign_ids.length > 0 ? filters.campaign_ids : undefined
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

// React to post-callback redirect (integrations)
watch(() => route.query.new_integration_id, (id) => {
  if (id) {
    router.push({
      path: '/integrations/wizard',
      query: {
        resume_integration_id: id,
        initial_step: 2
        connectModalRef.value.lastIntegrationId = id
        connectModalRef.value.fetchCampaigns(id)
      }
    }, 100)
    window.history.replaceState({}, '', window.location.pathname)
  }
}, { immediate: true })

</script>
