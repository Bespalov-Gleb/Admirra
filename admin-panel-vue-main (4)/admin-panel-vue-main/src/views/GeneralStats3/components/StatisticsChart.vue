<template>
  <div class="!bg-white w-full rounded-[40px] px-6 sm:px-10 py-6 sm:py-8 shadow-sm" >
    <!-- Заголовок и селектор дат -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
      <h3 class="text-lg font-semibold text-gray-900">Эффективность кампаний</h3>
      <div class="flex items-center">
        <div class="flex items-center overflow-hidden rounded-lg ">
          <button 
            v-for="(day, index) in [7, 14, 30]" 
            :key="day"
            :class="[
              'px-3 py-1.5 text-sm font-medium transition-colors',
              selectedDays === day 
                ? 'bg-gray-300 text-black' 
                : 'bg-gray-50 text-gray-700 hover:bg-gray-100',
              index > 0 ? '' : ''
            ]"
            @click="selectedDays = day"
          >
            {{ day }}
          </button>
        </div>
        <button class="ml-2 px-3 py-1.5 bg-gray-50 text-gray-700 hover:bg-gray-100 rounded-lg  transition-colors">
          <img :src="calendarIcon" alt="Calendar" class="w-4 h-4" />
        </button>
      </div>
    </div>
    
    <div class="h-64 relative pb-6 w-full overflow-hidden mb-6">
      <Line
        :data="chartData"
        :options="chartOptions"
        :key="chartKey"
      />
    </div>
    
    <!-- Легенда -->
    <div class="flex items-center gap-4 sm:gap-6 flex-wrap">
      <template v-if="!selectedMetric">
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 bg-blue-500 rounded-full"></div>
          <span class="text-sm text-gray-600">Расход</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 bg-orange-500 rounded-full"></div>
          <span class="text-sm text-gray-600">Показы</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 bg-green-500 rounded-full"></div>
          <span class="text-sm text-gray-600">Переходы</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 bg-purple-500 rounded-full"></div>
          <span class="text-sm text-gray-600">Лиды</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 bg-red-500 rounded-full"></div>
          <span class="text-sm text-gray-600">CPC</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 bg-pink-500 rounded-full"></div>
          <span class="text-sm text-gray-600">CPA</span>
        </div>
      </template>
      <template v-else>
        <div v-if="selectedMetric === 'expenses'" class="flex items-center gap-2">
          <div class="w-3 h-3 bg-blue-500 rounded-full"></div>
          <span class="text-sm text-gray-600">Расход</span>
        </div>
        <div v-if="selectedMetric === 'impressions'" class="flex items-center gap-2">
          <div class="w-3 h-3 bg-orange-500 rounded-full"></div>
          <span class="text-sm text-gray-600">Показы</span>
        </div>
        <div v-if="selectedMetric === 'clicks'" class="flex items-center gap-2">
          <div class="w-3 h-3 bg-green-500 rounded-full"></div>
          <span class="text-sm text-gray-600">Переходы</span>
        </div>
        <div v-if="selectedMetric === 'leads'" class="flex items-center gap-2">
          <div class="w-3 h-3 bg-purple-500 rounded-full"></div>
          <span class="text-sm text-gray-600">Лиды</span>
        </div>
        <div v-if="selectedMetric === 'cpc'" class="flex items-center gap-2">
          <div class="w-3 h-3 bg-red-500 rounded-full"></div>
          <span class="text-sm text-gray-600">CPC</span>
        </div>
        <div v-if="selectedMetric === 'cpa'" class="flex items-center gap-2">
          <div class="w-3 h-3 bg-pink-500 rounded-full"></div>
          <span class="text-sm text-gray-600">CPA</span>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  LineController,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import calendarIcon from '../../../assets/dash/calendar.svg'

const props = defineProps({
  selectedMetric: {
    type: String,
    default: null // 'expenses', 'impressions', 'clicks', 'leads', 'cpc', 'cpa' или null
  }
})

const selectedDays = ref(7)

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  LineController,
  Tooltip,
  Legend,
  Filler
)

const isMobile = ref(window.innerWidth < 640)

// Даты с 20 по 26 декабря
const dateLabels = ref(['20 дек. 2025', '21 дек. 2025', '22 дек. 2025', '23 дек. 2025', '24 дек. 2025', '25 дек. 2025', '26 дек. 2025'])

// Реальные данные для tooltip
const realExpensesData = ref([36037, 36150, 37200, 36800, 37500, 37100, 38000])
const realImpressionsData = ref([135200, 136500, 135800, 137200, 136000, 137400, 136800])
const realClicksData = ref([12070, 12300, 12100, 12500, 12200, 12100, 12600])
const realLeadsData = ref([910, 915, 912, 920, 918, 915, 925])
const realCpcData = ref([9.43, 9.5, 9.45, 9.6, 9.55, 9.5, 9.7])
const realCpaData = ref([39.6, 40.0, 39.8, 40.5, 40.2, 40.0, 41.0])

// Нормализованные данные для графика (чтобы все линии были видны)
const expensesData = ref([0.1, 0.12, 0.15, 0.13, 0.16, 0.14, 0.18])
const impressionsData = ref([0.08, 0.1, 0.09, 0.11, 0.1, 0.12, 0.11])
const clicksData = ref([0.06, 0.08, 0.07, 0.09, 0.08, 0.07, 0.1])
const leadsData = ref([0.05, 0.06, 0.055, 0.065, 0.06, 0.055, 0.07])
const cpcData = ref([0.04, 0.045, 0.042, 0.048, 0.046, 0.045, 0.05])
const cpaData = ref([0.02, 0.025, 0.022, 0.028, 0.026, 0.025, 0.03])

const chartKey = ref(0)

const allDatasets = computed(() => [
  {
    label: 'Расход',
    key: 'expenses',
    data: expensesData.value,
    borderColor: '#3b82f6', // blue-500
    backgroundColor: 'transparent',
    borderWidth: isMobile.value ? 2 : 2.5,
    pointRadius: isMobile.value ? 5 : 6,
    pointBackgroundColor: '#3b82f6',
    pointBorderColor: '#ffffff',
    pointBorderWidth: isMobile.value ? 2 : 2.5,
    tension: 0.4,
    fill: false
  },
  {
    label: 'Показы',
    key: 'impressions',
    data: impressionsData.value,
    borderColor: '#f97316', // orange-500
    backgroundColor: 'transparent',
    borderWidth: isMobile.value ? 2 : 2.5,
    pointRadius: isMobile.value ? 3 : 4,
    pointBackgroundColor: '#f97316',
    pointBorderColor: '#ffffff',
    pointBorderWidth: isMobile.value ? 1.5 : 2,
    tension: 0.4,
    fill: false
  },
  {
    label: 'Переходы',
    key: 'clicks',
    data: clicksData.value,
    borderColor: '#22c55e', // green-500
    backgroundColor: 'transparent',
    borderWidth: isMobile.value ? 2 : 2.5,
    pointRadius: isMobile.value ? 3 : 4,
    pointBackgroundColor: '#22c55e',
    pointBorderColor: '#ffffff',
    pointBorderWidth: isMobile.value ? 1.5 : 2,
    tension: 0.4,
    fill: false
  },
  {
    label: 'Лиды',
    key: 'leads',
    data: leadsData.value,
    borderColor: '#a855f7', // purple-500
    backgroundColor: 'transparent',
    borderWidth: isMobile.value ? 2 : 2.5,
    pointRadius: isMobile.value ? 3 : 4,
    pointBackgroundColor: '#a855f7',
    pointBorderColor: '#ffffff',
    pointBorderWidth: isMobile.value ? 1.5 : 2,
    tension: 0.4,
    fill: false
  },
  {
    label: 'CPC',
    key: 'cpc',
    data: cpcData.value,
    borderColor: '#ef4444', // red-500
    backgroundColor: 'transparent',
    borderWidth: isMobile.value ? 2 : 2.5,
    pointRadius: isMobile.value ? 3 : 4,
    pointBackgroundColor: '#ef4444',
    pointBorderColor: '#ffffff',
    pointBorderWidth: isMobile.value ? 1.5 : 2,
    tension: 0.4,
    fill: false
  },
  {
    label: 'CPA',
    key: 'cpa',
    data: cpaData.value,
    borderColor: '#ec4899', // pink-500
    backgroundColor: 'transparent',
    borderWidth: isMobile.value ? 2 : 2.5,
    pointRadius: isMobile.value ? 3 : 4,
    pointBackgroundColor: '#ec4899',
    pointBorderColor: '#ffffff',
    pointBorderWidth: isMobile.value ? 1.5 : 2,
    tension: 0.4,
    fill: false
  }
])

const chartData = computed(() => ({
  labels: dateLabels.value,
  datasets: props.selectedMetric
    ? allDatasets.value.filter(dataset => dataset.key === props.selectedMetric)
    : allDatasets.value
}))

const handleResize = () => {
  isMobile.value = window.innerWidth < 640
  chartKey.value++
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: {
    duration: 1000,
    easing: 'easeInOutQuart'
  },
  plugins: {
    legend: {
      display: false
    },
    tooltip: {
      enabled: true,
      mode: 'index',
      intersect: false,
      usePointStyle: true,
      boxWidth: 12,
      boxHeight: 12,
      boxPadding: 8,
      padding: 16,
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      titleColor: '#ffffff',
      bodyColor: '#ffffff',
      borderColor: 'transparent',
      borderWidth: 0,
      cornerRadius: 10,
      displayColors: true,
      
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      ticks: {
        display: false
      },
      grid: {
        color: '#e5e7eb',
        display: true,
        drawBorder: false,
        lineWidth: 1
      }
    },
    x: {
      grid: {
        display: false
      },
      ticks: {
        display: true,
        font: {
          size: isMobile.value ? 9 : 11
        },
        color: '#6b7280',
        maxRotation: 0,
        minRotation: 0
      }
    }
  }
}))
</script>

<style>
/* Округление квадратиков в tooltip Chart.js */
.chartjs-tooltip-key,
.chartjs-tooltip-key::before,
canvas + div .chartjs-tooltip-key {
  border-radius: 50% !important;
  width: 12px !important;
  height: 12px !important;
}

/* Глобальный стиль для всех tooltip Chart.js */
div[class*="chartjs-tooltip"] .chartjs-tooltip-key {
  border-radius: 50% !important;
  width: 12px !important;
  height: 12px !important;
}

/* Стили для всех элементов tooltip */
div[class*="chartjs-tooltip"] span[style*="background-color"],
div[class*="chartjs-tooltip"] .chartjs-tooltip-color {
  border-radius: 50% !important;
  width: 12px !important;
  height: 12px !important;
  display: inline-block !important;
}

/* Отступы между элементами в tooltip */
div[class*="chartjs-tooltip"] .chartjs-tooltip-body-list-item {
  margin-top: 10px !important;
  margin-bottom: 10px !important;
}

div[class*="chartjs-tooltip"] .chartjs-tooltip-body-list-item:first-child {
  margin-top: 0 !important;
}

div[class*="chartjs-tooltip"] .chartjs-tooltip-body-list-item:last-child {
  margin-bottom: 0 !important;
}
</style>

