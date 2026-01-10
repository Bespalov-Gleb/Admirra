<template>
  <div class="!bg-white w-full rounded-[40px] px-6 sm:px-10 pt-4 pb-6 sm:pb-8 shadow-sm border border-gray-50 relative">
    <div class="h-80 relative w-full overflow-hidden mt-2">
      <!-- Кнопка скачивания -->
      <button 
        @click="downloadChart"
        class="absolute top-0 right-0 z-10 p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-all"
        title="Скачать график как изображение"
      >
        <ArrowDownTrayIcon class="w-5 h-5" />
      </button>

      <Line
        ref="chartRef"
        :data="chartData"
        :options="chartOptions"
        :key="chartKey"
      />
    </div>
    
    <!-- Легенда -->
    <div class="flex items-center gap-6 flex-wrap justify-center sm:justify-start">
      <template v-for="dataset in allDatasets" :key="dataset.key">
        <div 
          v-if="!selectedMetrics.length || selectedMetrics.includes(dataset.key)"
          class="flex items-center gap-2 cursor-pointer select-none transition-opacity"
          :class="{ 'opacity-30': hiddenDatasets.has(dataset.key) }"
          @click="toggleDataset(dataset.key)"
        >
          <div :style="{ backgroundColor: dataset.borderColor }" class="w-2.5 h-2.5 rounded-full"></div>
          <span class="text-sm font-bold text-gray-500">{{ dataset.label }}</span>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { 
  CalendarIcon,
  ArrowDownTrayIcon
} from '@heroicons/vue/24/outline'
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
  selectedMetrics: {
    type: Array,
    default: () => []
  },
  period: {
    type: [String, Number],
    default: 7
  }
})

const emit = defineEmits(['update:period'])

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
const chartRef = ref(null)
const hiddenDatasets = ref(new Set())

const selectedDays = computed({
  get: () => Number(props.period) || 7,
  set: (val) => emit('update:period', val)
})

const toggleDataset = (key) => {
  if (hiddenDatasets.value.has(key)) {
    hiddenDatasets.value.delete(key)
  } else {
    hiddenDatasets.value.add(key)
  }
}

const downloadChart = () => {
  if (!chartRef.value || !chartRef.value.chart) return
  const link = document.createElement('a')
  link.download = `statistics_${new Date().toISOString().split('T')[0]}.png`
  link.href = chartRef.value.chart.toBase64Image()
  link.click()
}

// Compute all datasets from props - matching image colors and using REAL values
const allDatasets = computed(() => {
  if (!props.dynamics || !props.dynamics.labels) return []

  const d = props.dynamics
  const datasets = [
    {
      label: 'Показы',
      key: 'impressions',
      data: d.impressions || [],
      borderColor: '#818cf8',
      yAxisID: 'yLeft',
      backgroundColor: 'transparent',
      borderWidth: 2,
      pointRadius: 4,
      pointBackgroundColor: '#818cf8',
      pointBorderColor: '#ffffff',
      pointBorderWidth: 2,
      tension: 0.4,
      fill: false
    },
    {
      label: 'Клики',
      key: 'clicks',
      data: d.clicks || [],
      borderColor: '#fbbf24',
      yAxisID: 'yRight',
      backgroundColor: 'transparent',
      borderWidth: 2,
      pointRadius: 4,
      pointBackgroundColor: '#fbbf24',
      pointBorderColor: '#ffffff',
      pointBorderWidth: 2,
      tension: 0.4,
      fill: false
    },
    {
      label: 'Конверсии',
      key: 'leads',
      data: d.leads || [],
      borderColor: '#3b82f6',
      yAxisID: 'yRight',
      backgroundColor: 'transparent',
      borderWidth: 2,
      pointRadius: 4,
      pointBackgroundColor: '#3b82f6',
      pointBorderColor: '#ffffff',
      pointBorderWidth: 2,
      tension: 0.4,
      fill: false
    },
    {
      label: 'Цена конверсии',
      key: 'cpa',
      data: d.cpa || [],
      borderColor: '#991b1b',
      yAxisID: 'yRight',
      backgroundColor: 'transparent',
      borderWidth: 2,
      pointRadius: 4,
      pointBackgroundColor: '#991b1b',
      pointBorderColor: '#ffffff',
      pointBorderWidth: 2,
      tension: 0.4,
      fill: false
    },
    {
      label: 'Расход',
      key: 'expenses',
      data: d.costs || [],
      borderColor: '#f43f5e',
      yAxisID: 'yLeft',
      backgroundColor: 'transparent',
      borderWidth: 2,
      pointRadius: 4,
      pointBackgroundColor: '#f43f5e',
      pointBorderColor: '#ffffff',
      pointBorderWidth: 2,
      tension: 0.4,
      fill: false
    }
  ]

  return datasets
})

const chartData = computed(() => ({
  labels: props.dynamics.labels || [],
  datasets: allDatasets.value.filter(dataset => {
    // Priority 1: Check selectedMetrics from parent (Cards selection)
    if (props.selectedMetrics.length > 0 && !props.selectedMetrics.includes(dataset.key)) return false
    // Priority 2: Check hiddenDatasets (Interactive legend selection)
    if (hiddenDatasets.value.has(dataset.key)) return false
    return true
  })
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
      backgroundColor: '#111827',
      padding: 16,
      cornerRadius: 12,
      titleFont: {
        size: 13,
        weight: 'bold'
      },
      bodyFont: {
        size: 12
      },
      callbacks: {
        label: function(context) {
          let label = context.dataset.label || '';
          if (label) {
            label += ': ';
          }
          const val = context.raw;
          if (val !== undefined) {
             if (['Расход', 'Цена конверсии', 'CPC'].includes(context.dataset.label)) {
              label += new Intl.NumberFormat('ru-RU').format(val) + ' ₽'
            } else {
              label += new Intl.NumberFormat('ru-RU').format(val)
            }
          }
          return label;
        }
      }
    }
  },
  scales: {
    yLeft: {
      type: 'linear',
      display: false, // Keep image look (clean)
      position: 'left',
      beginAtZero: true,
      grid: {
        color: '#f3f4f6',
        display: true,
        drawBorder: false
      }
    },
    yRight: {
      type: 'linear',
      display: false,
      position: 'right',
      beginAtZero: true,
      grid: {
        drawOnChartArea: false // Only show grid for left axis
      }
    },
    x: {
      grid: {
        display: false
      },
      ticks: {
        display: true,
        color: '#9ca3af',
        font: {
          size: 11
        }
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
