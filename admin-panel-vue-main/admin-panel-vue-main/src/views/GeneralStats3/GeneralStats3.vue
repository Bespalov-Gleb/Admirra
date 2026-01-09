<template>
  <div class="space-y-6 overflow-x-hidden w-full">
    <!-- Состояние, если включен превью баннера -->
    <div v-if="showBannerPreview" class="flex items-center justify-center min-h-[calc(100vh-144px)] px-4">
      <CreateProjectBanner 
        :loading="creatingProject"
        @create="handleCreateProject"
      />
    </div>

    <!-- Заголовок с фильтрами -->
    <div v-else class="space-y-6">
      <div v-if="statsError" class="p-4 bg-red-50 border border-red-200 text-red-600 rounded-xl mb-4 text-sm font-medium">
        {{ statsError }}
      </div>
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6 py-3">
      <h1 @click="showBannerPreview = !showBannerPreview" class="text-2xl sm:text-3xl font-bold text-gray-900 cursor-pointer hover:text-blue-600 transition-colors">Статистика по всем проектам</h1>
      <div class="flex flex-wrap gap-2 mr-1">
        <!-- Project Filter -->
        <select
          v-model="filters.client_id"
          class="px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none cursor-pointer pr-10"
        >
          <option value="">Все проекты</option>
          <option v-for="client in clients" :key="client.id" :value="client.id">
            {{ client.name }}
          </option>
        </select>

        <!-- Channel Filter -->
        <select
          v-model="filters.channel"
          class="px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none cursor-pointer pr-10"
        >
          <option value="all">Все каналы</option>
          <option value="google" disabled>Google Ads</option>
          <option value="yandex">Яндекс.Директ</option>
          <option value="facebook" disabled>Facebook Ads</option>
          <option value="instagram" disabled>Instagram</option>
          <option value="vk">ВКонтакте</option>
        </select>

         <!-- Period Filter (Added from old logic to keep functionality) -->
        <select v-model="filters.period" @change="handlePeriodChange" class="px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none cursor-pointer pr-10">
          <option value="7">7 дней</option>
          <option value="14">14 дней</option>
          <option value="30">30 дней</option>
          <option value="90">90 дней</option>
          <option value="custom">Произвольно</option>
        </select>
        
        <!-- Custom Date Range -->
        <template v-if="filters.period === 'custom'">
          <input 
            type="date" 
            v-model="filters.start_date"
            class="px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 shadow-sm transition-all"
          >
          <input 
            type="date" 
            v-model="filters.end_date"
            class="px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 shadow-sm transition-all"
          >
        </template>
      </div>
    </div>


    <!-- Карточки KPI -->
    <div class="w-full overflow-hidden">
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
            :value="summary.expenses.toLocaleString() + ' ₽'"
            :trend="summary.trends?.expenses || 0"
            :change-positive="summary.trends?.expenses >= 0"
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
            :value="summary.impressions.toLocaleString()"
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
            :value="summary.clicks.toLocaleString()"
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
            :value="summary.leads.toLocaleString()"
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
            title="CPC"
            :value="summary.cpc.toLocaleString() + ' ₽'"
            :trend="summary.trends?.cpc || 0"
            :change-positive="summary.trends?.cpc <= 0"
            :icon="CurrencyDollarIcon"
            icon-color="orange"
            :is-selected="selectedMetric === 'cpc'"
            @click="toggleMetric('cpc')"
          />
        </div>
        
        <!-- CPA -->
        <div class="flex-shrink-0">
          <CardV3
            title="CPA"
            :value="summary.cpa.toLocaleString() + ' ₽'"
            :trend="summary.trends?.cpa || 0"
            :change-positive="summary.trends?.cpa <= 0"
            :icon="CurrencyDollarIcon"
            icon-color="blue"
            :is-selected="selectedMetric === 'cpa'"
            @click="toggleMetric('cpa')"
          />
        </div>
      </div>
    </div>
    

    <!-- График статистики -->
    <div class="w-full">
      <StatisticsChart 
        :dynamics="dynamics" 
        :selected-metric="selectedMetric"
      />
    </div>

    <!-- Эффективность продвижения -->
    <div class="w-full">
      <PromotionEfficiency :summary="summary" />
    </div>
  </div>
</div>
</template>

<script setup>
import { ref } from 'vue'
import {
  CurrencyDollarIcon,
  EyeIcon,
  ArrowPathIcon,
  UserGroupIcon
} from '@heroicons/vue/24/solid'
import CardV3 from './components/CardV3.vue'
import StatisticsChart from './components/StatisticsChart.vue'
import PromotionEfficiency from './components/PromotionEfficiency.vue'
import CreateProjectBanner from '../Dashboard/components/CreateProjectBanner.vue'
import { useDashboardStats } from '../../composables/useDashboardStats'
import api from '../../api/axios'
import { useToaster } from '../../composables/useToaster'
import { useProjects } from '../../composables/useProjects'

// Integrate existing data logic
const {
  summary,
  dynamics,
  clients,
  loading,
  error: statsError,
  filters,
  handlePeriodChange,
  fetchStats,
  fetchClients
} = useDashboardStats()

const { projects: globalProjects, setCurrentProject, fetchProjects: refreshGlobalProjects } = useProjects()
const toaster = useToaster()

const creatingProject = ref(false)
const showBannerPreview = ref(false) // Toggle for user review

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
