<template>
  <div class="!bg-white w-full rounded-[40px] px-6 sm:px-10 py-6 sm:py-8 shadow-sm">
    <!-- Заголовок и селектор дат -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
      <h3 class="text-lg font-semibold text-gray-900">Эффективность кампаний</h3>
      <div class="flex items-center">
        <!-- Фейковые кнопки периода (для дизайна), реальный фильтр в GeneralStats3.vue -->
        <div class="flex items-center overflow-hidden rounded-lg">
          <button 
            v-for="(day, index) in [7, 14, 30]" 
            :key="day"
            class="px-3 py-1.5 text-sm font-medium transition-colors bg-gray-50 text-gray-700 hover:bg-gray-100 cursor-default"
          >
            {{ day }}
          </button>
        </div>
        <button class="ml-2 px-3 py-1.5 bg-gray-50 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors cursor-default">
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
        <!-- Dynamic Legend based on selection -->
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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
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
  dynamics: {
    type: Object,
    required: true,
    default: () => ({
      labels: [],
      costs: [],
      clicks: [],
      impressions: [],
      leads: [],
      cpc: [],
      cpa: []
    })
  },
  selectedMetric: {
    type: String,
    default: null // 'expenses', 'impressions', 'clicks', 'leads', 'cpc', 'cpa' or null
  }
})

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
const chartKey = ref(0)
const selectedDays = ref(7) // Local ref, technically controlled by parent but kept for UI state

// Helper to normalize data for visual display (scale 0-1)
const normalizeDataset = (data, label, offset = 0) => {
  const cleanData = Array.isArray(data) ? data.map(v => Number(v) || 0) : []
  
  if (cleanData.length === 0) return []

  const max = Math.max(...cleanData, 0)
  const safeMax = max === 0 ? 1 : max
  
  return cleanData.map((val, index) => ({
    x: props.dynamics.labels[index],
    y: (val / safeMax) * 0.4 + offset, // Scale down and add offset
    realValue: val
  }))
}

// Compute all datasets from props
const allDatasets = computed(() => {
  if (!props.dynamics || !props.dynamics.labels) return []

  const d = props.dynamics
  
  return [
    {
      label: 'Расход',
      key: 'expenses',
      data: normalizeDataset(d.costs, 'Расход', 0.5),
      borderColor: '#3b82f6',
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
      data: normalizeDataset(d.impressions, 'Показы', 0.4),
      borderColor: '#f97316',
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
      data: normalizeDataset(d.clicks, 'Переходы', 0.3),
      borderColor: '#22c55e',
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
      data: normalizeDataset(d.leads, 'Лиды', 0.2),
      borderColor: '#a855f7',
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
      data: normalizeDataset(d.cpc, 'CPC', 0.1),
      borderColor: '#ef4444',
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
      data: normalizeDataset(d.cpa, 'CPA', 0),
      borderColor: '#ec4899',
      backgroundColor: 'transparent',
      borderWidth: isMobile.value ? 2 : 2.5,
      pointRadius: isMobile.value ? 3 : 4,
      pointBackgroundColor: '#ec4899',
      pointBorderColor: '#ffffff',
      pointBorderWidth: isMobile.value ? 1.5 : 2,
      tension: 0.4,
      fill: false
    }
  ]
})

const chartData = computed(() => ({
  labels: props.dynamics.labels || [],
  datasets: props.selectedMetric
    ? allDatasets.value.filter(dataset => dataset.key === props.selectedMetric)
    : allDatasets.value
}))

const handleResize = () => {
  isMobile.value = window.innerWidth < 640
  chartKey.value++
}

watch(() => props.dynamics, () => {
  chartKey.value++
}, { deep: true })

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index',
    intersect: false,
  },
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
      callbacks: {
        label: function(context) {
          let label = context.dataset.label || '';
          if (label) {
            label += ': ';
          }
          const realValue = context.raw.realValue;
          if (realValue !== undefined) {
             if (['Расход', 'CPC', 'CPA'].includes(context.dataset.label)) {
              label += new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', minimumFractionDigits: 2 }).format(realValue);
            } else {
              label += new Intl.NumberFormat('ru-RU').format(realValue);
            }
          }
          return label;
        }
      }
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      max: 1.1, // Headroom for offsets
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
/* Custom Tooltip Styles */
.chartjs-tooltip-key {
  border-radius: 50% !important;
  width: 12px !important;
  height: 12px !important;
}
</style>
