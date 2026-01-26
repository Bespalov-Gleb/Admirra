<template>
  <div class="!bg-white w-full rounded-[40px] px-6 sm:px-10 py-6 sm:py-8 shadow-sm border border-gray-50">
    <!-- Заголовок -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-10">
      <h3 class="text-xl font-bold text-gray-900">Эффективность кампаний</h3>
    </div>
    
    <div class="h-80 relative pb-10 w-full overflow-hidden">
      <Line
        :data="chartData"
        :options="chartOptions"
        :key="chartKey"
      />
    </div>
    
    <!-- Легенда -->
    <div class="flex items-center gap-6 flex-wrap justify-center sm:justify-start">
      <template v-for="dataset in allDatasets" :key="dataset.key">
        <div 
          v-if="selectedMetrics.length === 0 || selectedMetrics.includes(dataset.key)"
          class="flex items-center gap-2"
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
  CalendarIcon
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
  selectedMetrics: {
    type: Array,
    default: () => [] // Array of selected metric keys: ['expenses', 'impressions', etc.]
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
const selectedDays = computed({
  get: () => Number(props.period) || 7,
  set: (val) => emit('update:period', val)
})

// Helper to prepare data - use real values without normalization
const prepareDataset = (data, label) => {
  const cleanData = Array.isArray(data) ? data.map(v => Number(v) || 0) : []
  
  if (cleanData.length === 0) return []
  
  return cleanData.map((val, index) => ({
    x: props.dynamics.labels[index],
    y: val, // Use real value directly
    realValue: val
  }))
}

// Compute all datasets from props
const allDatasets = computed(() => {
  if (!props.dynamics || !props.dynamics.labels) return []

  const d = props.dynamics
  const datasets = [
    {
      label: 'Расход',
      key: 'expenses',
      data: prepareDataset(d.costs, 'Расход'),
      borderColor: '#f97316', // Orange - matches card color
      backgroundColor: 'transparent',
      borderWidth: isMobile.value ? 2 : 2.5,
      pointRadius: isMobile.value ? 5 : 6,
      pointBackgroundColor: '#f97316',
      pointBorderColor: '#ffffff',
      pointBorderWidth: isMobile.value ? 2 : 2.5,
      tension: 0, // No smoothing - sharp lines
      stepped: false,
      fill: false
    },
    {
      label: 'Показы',
      key: 'impressions',
      data: prepareDataset(d.impressions, 'Показы'),
      borderColor: '#3b82f6', // Blue - matches card color
      backgroundColor: 'transparent',
      borderWidth: isMobile.value ? 2 : 2.5,
      pointRadius: isMobile.value ? 3 : 4,
      pointBackgroundColor: '#3b82f6',
      pointBorderColor: '#ffffff',
      pointBorderWidth: isMobile.value ? 1.5 : 2,
      tension: 0, // No smoothing - sharp lines
      stepped: false,
      fill: false
    },
    {
      label: 'Переходы',
      key: 'clicks',
      data: prepareDataset(d.clicks, 'Переходы'),
      borderColor: '#22c55e', // Green - matches card color
      backgroundColor: 'transparent',
      borderWidth: isMobile.value ? 2 : 2.5,
      pointRadius: isMobile.value ? 3 : 4,
      pointBackgroundColor: '#22c55e',
      pointBorderColor: '#ffffff',
      pointBorderWidth: isMobile.value ? 1.5 : 2,
      tension: 0, // No smoothing - sharp lines
      stepped: false,
      fill: false
    },
    {
      label: 'Лиды',
      key: 'leads',
      data: prepareDataset(d.leads, 'Лиды'),
      borderColor: '#ef4444', // Red - matches card color
      backgroundColor: 'transparent',
      borderWidth: isMobile.value ? 2 : 2.5,
      pointRadius: isMobile.value ? 3 : 4,
      pointBackgroundColor: '#ef4444',
      pointBorderColor: '#ffffff',
      pointBorderWidth: isMobile.value ? 1.5 : 2,
      tension: 0, // No smoothing - sharp lines
      stepped: false,
      fill: false
    },
    {
      label: 'CPC',
      key: 'cpc',
      data: prepareDataset(d.cpc, 'CPC'),
      borderColor: '#a855f7', // Purple - matches card color
      backgroundColor: 'transparent',
      borderWidth: isMobile.value ? 2 : 2.5,
      pointRadius: isMobile.value ? 3 : 4,
      pointBackgroundColor: '#a855f7',
      pointBorderColor: '#ffffff',
      pointBorderWidth: isMobile.value ? 1.5 : 2,
      tension: 0, // No smoothing - sharp lines
      stepped: false,
      fill: false
    },
    {
      label: 'CPA',
      key: 'cpa',
      data: prepareDataset(d.cpa, 'CPA'),
      borderColor: '#ec4899', // Pink - matches card color
      backgroundColor: 'transparent',
      borderWidth: isMobile.value ? 2 : 2.5,
      pointRadius: isMobile.value ? 3 : 4,
      pointBackgroundColor: '#ec4899',
      pointBorderColor: '#ffffff',
      pointBorderWidth: isMobile.value ? 1.5 : 2,
      tension: 0, // No smoothing - sharp lines
      stepped: false,
      fill: false
    }
  ]

  return datasets
})

const chartData = computed(() => ({
  labels: props.dynamics.labels || [],
  datasets: props.selectedMetrics.length > 0
    ? allDatasets.value.filter(dataset => props.selectedMetrics.includes(dataset.key))
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
    duration: 0 // Disable animation for immediate rendering
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
          // Use the actual y value (which is now the real value)
          const realValue = context.parsed.y !== undefined ? context.parsed.y : (context.raw.realValue || context.raw.y || 0);
          if (realValue !== undefined && realValue !== null) {
             if (['Расход', 'CPC', 'CPA'].includes(context.dataset.label)) {
              label += new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(realValue);
            } else {
              label += new Intl.NumberFormat('ru-RU').format(Math.round(realValue));
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
      ticks: {
        display: true,
        font: {
          size: isMobile.value ? 9 : 11
        },
        color: '#6b7280',
        callback: function(value) {
          // Format large numbers
          if (value >= 1000000) {
            return (value / 1000000).toFixed(1) + 'M'
          }
          if (value >= 1000) {
            return (value / 1000).toFixed(1) + 'K'
          }
          return value
        }
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
