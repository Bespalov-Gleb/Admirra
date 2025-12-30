<template>
  <div class="space-y-6 overflow-x-hidden w-full">
    <!-- Заголовок с фильтрами -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
      <h1 class="text-2xl sm:text-3xl font-bold text-gray-900">Статистика по всем проектам</h1>
      <div class="flex flex-wrap gap-2">
        <select v-model="filters.channel" class="px-4 py-2.5 border border-gray-300 rounded-xl bg-white text-sm font-bold text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none cursor-pointer pr-10 shadow-sm hover:border-gray-400 transition-all">
          <option value="all">Все каналы</option>
          <option value="google" disabled>Google Ads</option>
          <option value="yandex">Яндекс.Директ</option>
          <option value="facebook" disabled>Facebook Ads</option>
          <option value="instagram" disabled>Instagram</option>
          <option value="vk">ВКонтакте</option>
          <option value="telegram" disabled>Telegram</option>
        </select>

        <select v-model="filters.period" @change="handlePeriodChange" class="px-4 py-2.5 border border-gray-300 rounded-xl bg-white text-sm font-bold text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none cursor-pointer pr-10 shadow-sm hover:border-gray-400 transition-all">
          <option value="7">Последние 7 дней</option>
          <option value="14">Последние 14 дней</option>
          <option value="30">Последние 30 дней</option>
          <option value="90">Последние 90 дней</option>
          <option value="custom">Произвольно</option>
        </select>
        
        <!-- Custom Date Range -->
        <template v-if="filters.period === 'custom'">
          <input 
            type="date" 
            v-model="filters.start_date"
            class="px-4 py-2.5 border border-gray-300 rounded-xl bg-white text-sm font-bold text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm hover:border-gray-400 transition-all"
          >
          <input 
            type="date" 
            v-model="filters.end_date"
            class="px-4 py-2.5 border border-gray-300 rounded-xl bg-white text-sm font-bold text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm hover:border-gray-400 transition-all"
          >
        </template>

        <select v-model="filters.client_id" class="px-4 py-2.5 border border-gray-300 rounded-xl bg-white text-sm font-bold text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none cursor-pointer pr-10 shadow-sm hover:border-gray-400 transition-all">
          <option value="">Все проекты</option>
          <option v-for="client in clients" :key="client.id" :value="client.id">
            {{ client.name }}
          </option>
        </select>
      </div>
    </div>

    <!-- Error Alert -->
    <div v-if="error" class="p-4 bg-red-50 border border-red-100 text-red-600 rounded-2xl flex items-center gap-3">
      <span class="text-sm font-bold">{{ error }}</span>
      <button @click="fetchStats" class="ml-auto text-xs bg-red-100 px-3 py-1 rounded-lg hover:bg-red-200 transition-all font-black uppercase tracking-widest">Повторить</button>
    </div>


    <!-- Карточки KPI -->
    <div class="space-y-4">
      <div class="flex items-center justify-between px-1">
        <h2 class="text-lg font-bold text-gray-800">Статистика по картам</h2>
        <div class="flex gap-2">
          <button 
            @click="scrollCards('left')"
            class="p-2 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 transition-all shadow-sm group"
          >
            <ChevronLeftIcon class="w-5 h-5 text-gray-400 group-hover:text-gray-600" />
          </button>
          <button 
            @click="scrollCards('right')"
            class="p-2 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 transition-all shadow-sm group"
          >
            <ChevronRightIcon class="w-5 h-5 text-gray-400 group-hover:text-gray-600" />
          </button>
        </div>
      </div>

      <div class="w-full overflow-hidden">
        <div 
          ref="cardsContainer"
          class="flex gap-4 sm:gap-6 overflow-x-auto pb-2 scrollbar-hide select-none max-w-full scroll-smooth"
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
            icon-color="orange"
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
            icon-color="blue"
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
            icon-color="red"
          />
        </div>
        
        <!-- CPC -->
        <div class="flex-shrink-0">
          <CardV3
            title="CPC"
            :value="summary.cpc.toLocaleString() + ' ₽'"
            :trend="0"
            change-text="среднее"
            :change-positive="true"
            :icon="MoneyIcon"
            icon-color="orange"
          />
        </div>
        
        <!-- CPA -->
        <div class="flex-shrink-0">
          <CardV3
            title="CPA"
            :value="summary.cpa.toLocaleString() + ' ₽'"
            :trend="0"
            change-text="целевое"
            :change-positive="true"
            :icon="MoneyIcon"
            icon-color="orange"
          />
        </div>
      </div>
    </div>
    

    <!-- График статистики -->
    <div class="w-full overflow-hidden">
      <StatisticsChart :dynamics="dynamics" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import {
  UserGroupIcon,
  ChevronLeftIcon,
  ChevronRightIcon
} from '@heroicons/vue/24/outline'
import CardV3 from './components/CardV3.vue'
import StatisticsChart from './components/StatisticsChart.vue'
import MoneyIcon from '../../assets/dash/money.svg'
import DashEyeIcon from '../../assets/dash/dash-eye.svg'
import DashArrowIcon from '../../assets/dash/dash-arrow.svg'
import { useDashboardStats } from '../../composables/useDashboardStats'

const {
  summary,
  dynamics,
  clients,
  loading,
  error,
  filters,
  handlePeriodChange,
  fetchStats
} = useDashboardStats()

const cardsContainer = ref(null)
const isDragging = ref(false)
const startX = ref(0)
const scrollLeft = ref(0)

const scrollCards = (direction) => {
  if (!cardsContainer.value) return
  const scrollAmount = 350
  if (direction === 'left') {
    cardsContainer.value.scrollLeft -= scrollAmount
  } else {
    cardsContainer.value.scrollLeft += scrollAmount
  }
}

// Drag to scroll
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

// Автоматическая прокрутка отключена
</script>

