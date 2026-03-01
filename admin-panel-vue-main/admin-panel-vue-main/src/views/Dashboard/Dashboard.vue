<template>
  <!-- Индикатор синхронизации (не блокирует интерфейс) -->
  <SyncStatusBanner :show-dismiss-button="true" />
  
  <div class="space-y-6 overflow-x-hidden w-full">
    <!-- Состояние, если нет проектов -->
    <div v-if="!loading && clients.length === 0" class="flex items-center justify-center min-h-[60vh] px-4">
      <CreateProjectBanner 
        :loading="creatingProject"
        @create="handleCreateProject"
      />
    </div>

    <!-- Сообщение при синхронизации: данные скрыты -->
    <div v-else-if="dataHiddenBySync" class="flex items-center justify-center min-h-[50vh] px-4">
      <div class="max-w-md w-full text-center py-12 px-8 bg-white/80 backdrop-blur-sm rounded-3xl border border-gray-100 shadow-lg">
        <div class="w-14 h-14 mx-auto mb-4 rounded-2xl bg-blue-50 flex items-center justify-center">
          <svg class="w-7 h-7 text-blue-500 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
        <h3 class="text-base font-bold text-gray-800 mb-2">Идёт синхронизация</h3>
        <p class="text-sm text-gray-500">Данные обновляются. Статистика появится через несколько минут.</p>
      </div>
    </div>

    <!-- Заголовок с фильтрами -->
    <div v-else class="space-y-6">
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6 py-3">
      <h1 class="text-2xl sm:text-3xl font-bold text-gray-900">Статистика по всем проектам</h1>
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
            :trend="0"
            change-text="из API"
            :change-positive="true"
            :icon="MoneyIcon"
            icon-color="blue"
            :is-selected="selectedMetric === 'expenses'"
            @click="toggleMetric('expenses')"
          />
        </div>
        
        <!-- Показы -->
        <div class="flex-shrink-0">
          <CardV3
            title="Показы"
            :value="summary.impressions.toLocaleString()"
            :trend="0"
            change-text="из API"
            :change-positive="true"
            :icon="DashEyeIcon"
            icon-color="orange"
            :is-selected="selectedMetric === 'impressions'"
            @click="toggleMetric('impressions')"
          />
        </div>
        
        <!-- Переходы -->
        <div class="flex-shrink-0">
          <CardV3
            title="Переходы"
            :value="summary.clicks.toLocaleString()"
            :trend="0"
            change-text="из API"
            :change-positive="true"
            :icon="DashArrowIcon"
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
            :trend="0"
            change-text="из API"
            :change-positive="true"
            :icon="UserGroupIcon"
            icon-color="purple"
            :is-selected="selectedMetric === 'leads'"
            @click="toggleMetric('leads')"
          />
        </div>
        
        <!-- CPC -->
        <div class="flex-shrink-0">
          <CardV3
            title="CPC"
            :value="summary.cpc.toLocaleString() + ' ₽'"
            :trend="0"
            change-text="ср."
            :change-positive="true"
            :icon="MoneyIcon"
            icon-color="red"
            :is-selected="selectedMetric === 'cpc'"
            @click="toggleMetric('cpc')"
          />
        </div>
        
        <!-- CPA -->
        <div class="flex-shrink-0">
          <CardV3
            title="CPA"
            :value="summary.cpa.toLocaleString() + ' ₽'"
            :trend="0"
            change-text="цель"
            :change-positive="true"
            :icon="MoneyIcon"
            icon-color="pink"
            :is-selected="selectedMetric === 'cpa'"
            @click="toggleMetric('cpa')"
          />
        </div>
      </div>
    </div>
    

    <!-- График статистики -->
    <div class="w-full overflow-hidden">
      <!-- 
        Pass both dynamic data AND selected metric 
      -->
      <StatisticsChart 
        :dynamics="dynamics" 
        :selected-metric="selectedMetric"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import {
  CurrencyDollarIcon,
  EyeIcon,
  ArrowPathIcon,
  UserGroupIcon
} from '@heroicons/vue/24/outline'
import CardV3 from './components/CardV3.vue'
import StatisticsChart from './components/StatisticsChart.vue'
import CreateProjectBanner from './components/CreateProjectBanner.vue'
import SyncStatusBanner from '../../components/SyncStatusBanner.vue'
import MoneyIcon from '../../assets/dash/money.svg'
import DashEyeIcon from '../../assets/dash/dash-eye.svg'
import DashArrowIcon from '../../assets/dash/dash-arrow.svg'
import { useDashboardStats } from '../../composables/useDashboardStats'
import { useSyncStatus } from '../../composables/useSyncStatus'
import { useToaster } from '../../composables/useToaster'
import api from '../../api/axios'

const { isSyncingForProject } = useSyncStatus()

// Integrate existing data logic
const {
  summary,
  dynamics,
  clients,
  loading,
  error,
  filters,
  handlePeriodChange,
  fetchStats,
  fetchClients
} = useDashboardStats()

// Скрываем данные, если идёт синхронизация для текущего вида
const dataHiddenBySync = computed(() => isSyncingForProject(filters.client_id || null))

const toaster = useToaster()
const creatingProject = ref(false)

const handleCreateProject = async (name) => {
  creatingProject.value = true
  try {
    await api.post('clients/', { name })
    toaster.success(`Проект "${name}" успешно создан!`)
    // Refresh clients list and stats
    await fetchClients()
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
