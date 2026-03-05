<template>
  <div class="bg-white w-full rounded-2xl px-6 sm:px-8 py-6 shadow-md border border-gray-100">
    <!-- Заголовок + селектор метрики -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
      <h3 class="text-xl font-bold text-gray-900">Эффективность кампаний</h3>
      <select
        v-model="chartMetric"
        class="h-9 px-3 rounded-xl border border-gray-200 text-sm font-medium text-gray-700 bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      >
        <option v-for="opt in metricOptions" :key="opt.key" :value="opt.key">{{ opt.label }}</option>
      </select>
    </div>
    
    <div class="h-72 relative w-full overflow-hidden">
      <Line
        :data="chartData"
        :options="chartOptions"
        :key="chartKey"
      />
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

const chartKey = ref(0)
const chartMetric = ref('expenses')

const metricOptions = [
  { key: 'expenses', label: 'Расход' },
  { key: 'impressions', label: 'Показы' },
  { key: 'clicks', label: 'Переходы' },
  { key: 'leads', label: 'Лиды' },
  { key: 'cpc', label: 'CPC' },
  { key: 'cpa', label: 'CPA' }
]

const getDataByMetric = (key) => {
  const d = props.dynamics
  const map = {
    expenses: d.costs || [],
    impressions: d.impressions || [],
    clicks: d.clicks || [],
    leads: d.leads || [],
    cpc: d.cpc || [],
    cpa: d.cpa || []
  }
  return (map[key] || []).map(v => Number(v) || 0)
}

const getLabelByMetric = (key) => {
  return metricOptions.find(o => o.key === key)?.label || key
}

const isCurrencyMetric = (key) => ['expenses', 'cpc', 'cpa'].includes(key)

const chartData = computed(() => {
  const labels = props.dynamics.labels || []
  const data = getDataByMetric(chartMetric.value)
  const points = labels.map((label, i) => ({ x: label, y: data[i] ?? 0 }))
  const maxVal = Math.max(...data, 1)
  
  return {
    labels,
    datasets: [{
      label: getLabelByMetric(chartMetric.value),
      data: points,
      borderColor: '#3b82f6',
      backgroundColor: 'rgba(59, 130, 246, 0.25)',
      borderWidth: 2,
      pointRadius: 4,
      pointBackgroundColor: '#3b82f6',
      pointBorderColor: '#ffffff',
      pointBorderWidth: 2,
      fill: true,
      tension: 0.3
    }]
  }
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  animation: { duration: 0 },
  plugins: {
    legend: { display: false },
    datalabels: { display: false },
    tooltip: {
      enabled: true,
      mode: 'index',
      intersect: false,
      displayColors: false,
      backgroundColor: 'rgba(30, 58, 138, 0.95)',
      titleColor: '#ffffff',
      bodyColor: '#ffffff',
      padding: 12,
      cornerRadius: 8,
      callbacks: {
        label: (context) => {
          const val = context.parsed.y
          if (isCurrencyMetric(chartMetric.value)) {
            return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(val)
          }
          return new Intl.NumberFormat('ru-RU').format(Math.round(val))
        }
      }
    }
  },
  scales: {
    y: {
      type: 'linear',
      position: 'left',
      beginAtZero: true,
      max: (() => {
        const data = getDataByMetric(chartMetric.value)
        const max = Math.max(...data, 1)
        return max * 1.1
      })(),
      ticks: {
        font: { size: 11 },
        color: '#6b7280',
        callback: (value) => {
          if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M'
          if (value >= 1000) return (value / 1000).toFixed(1) + 'K'
          return value
        }
      },
      grid: { color: '#e5e7eb', drawBorder: false }
    },
    x: {
      grid: { display: false },
      ticks: {
        font: { size: 11 },
        color: '#6b7280',
        maxRotation: 0,
        minRotation: 0
      }
    }
  }
}))

watch([() => props.dynamics, chartMetric], () => {
  chartKey.value++
}, { deep: true })

onMounted(() => {
  chartKey.value++
})
</script>
