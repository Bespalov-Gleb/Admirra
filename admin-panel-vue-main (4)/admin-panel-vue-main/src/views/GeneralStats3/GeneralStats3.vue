<template>
  <div class="space-y-6 overflow-x-hidden w-full">
    <!-- Заголовок с фильтрами -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6 py-3">
      <h1 class="text-2xl sm:text-3xl font-bold text-gray-900">Статистика по всем проектам</h1>
      <div class="flex flex-wrap gap-2 mr-1">
        <select
          v-model="selectedProject"
          class="px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none cursor-pointer pr-10"
        >
          <option value="">Выбрать проект</option>
          <option value="project1">КСИ СТРОЙ</option>
          <option value="project2">Laptops</option>
          <option value="project3">Phones</option>
          <option value="project4">Проект 4</option>
          <option value="project5">Проект 5</option>
        </select>
        <select
          v-model="selectedChannel"
          class="px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none cursor-pointer pr-10"
        >
          <option value="all">Все каналы</option>
          <option value="google">Google Ads</option>
          <option value="yandex">Яндекс.Директ</option>
          <option value="facebook">Facebook Ads</option>
          <option value="instagram">Instagram</option>
          <option value="vk">ВКонтакте</option>
          <option value="telegram">Telegram</option>
        </select>
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
            value="36 231,29 ₽"
            :trend="15.6"
            change-text="[+1.4k]"
            :change-positive="false"
            :icon="MoneyIcon"
            icon-color="blue"
            :is-selected="selectedMetric === 'expenses'"
            @click="selectedMetric = selectedMetric === 'expenses' ? null : 'expenses'"
          />
        </div>
        
        <!-- Показы -->
        <div class="flex-shrink-0">
          <CardV3
            title="Показы"
            value="136,824"
            :trend="-8.4"
            change-text="[-5.4k]"
            :change-positive="false"
            :icon="DashEyeIcon"
            icon-color="orange"
            :is-selected="selectedMetric === 'impressions'"
            @click="selectedMetric = selectedMetric === 'impressions' ? null : 'impressions'"
          />
        </div>
        
        <!-- Переходы -->
        <div class="flex-shrink-0">
          <CardV3
            title="Переходы"
            value="12,302"
            :trend="12.4"
            change-text="[+1.4k]"
            :change-positive="true"
            :icon="DashArrowIcon"
            icon-color="green"
            :is-selected="selectedMetric === 'clicks'"
            @click="selectedMetric = selectedMetric === 'clicks' ? null : 'clicks'"
          />
        </div>
        
        <!-- Лиды -->
        <div class="flex-shrink-0">
          <CardV3
            title="Лиды"
            value="915"
            :trend="-6.2"
            change-text="[-36]"
            :change-positive="false"
            :icon="UserGroupIcon"
            icon-color="purple"
            :is-selected="selectedMetric === 'leads'"
            @click="selectedMetric = selectedMetric === 'leads' ? null : 'leads'"
          />
        </div>
        
        <!-- CPC -->
        <div class="flex-shrink-0">
          <CardV3
            title="CPC"
            value="9,45"
            :trend="2.8"
            change-text="[+1,42]"
            :change-positive="false"
            :icon="MoneyIcon"
            icon-color="red"
            :is-selected="selectedMetric === 'cpc'"
            @click="selectedMetric = selectedMetric === 'cpc' ? null : 'cpc'"
          />
        </div>
        
        <!-- CPA -->
        <div class="flex-shrink-0">
          <CardV3
            title="CPA"
            value="39,6"
            :trend="2.8"
            change-text="[+8]"
            :change-positive="false"
            :icon="MoneyIcon"
            icon-color="pink"
            :is-selected="selectedMetric === 'cpa'"
            @click="selectedMetric = selectedMetric === 'cpa' ? null : 'cpa'"
          />
        </div>
      </div>
    </div>
    

    <!-- График статистики -->
    <div class="w-full overflow-hidden">
      <StatisticsChart :selected-metric="selectedMetric" />
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
} from '@heroicons/vue/24/outline'
import CardV3 from './components/CardV3.vue'
import StatisticsChart from './components/StatisticsChart.vue'
import MoneyIcon from '../../assets/dash/money.svg'
import DashEyeIcon from '../../assets/dash/dash-eye.svg'
import DashArrowIcon from '../../assets/dash/dash-arrow.svg'

const cardsContainer = ref(null)
const isDragging = ref(false)
const startX = ref(0)
const scrollLeft = ref(0)
const selectedProject = ref('')
const selectedChannel = ref('all')
const selectedMetric = ref(null) // 'expenses', 'impressions', 'clicks', 'leads', 'cpc', 'cpa' или null для всех

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