<template>
  <div class="bg-white w-full rounded-[20px] px-6 sm:px-8 py-6 shadow-md border border-gray-100 flex flex-col min-h-0">
    <!-- Заголовок + чекбокс НДС + селектор метрики -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6 flex-shrink-0">
      <h3 class="text-[20px] font-medium text-[#09183F] leading-[1] tracking-normal">Эффективность кампаний</h3>
      <div class="flex items-center gap-3">
        <label class="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            :checked="includeVat"
            @change="$emit('update:includeVat', ($event.target).checked)"
            class="w-4 h-4 rounded border-gray-300 text-[#2563EB] focus:ring-[#2563EB]"
          />
          <span class="text-[12px] font-medium text-gray-700">НДС</span>
        </label>
        <select
          v-model="chartMetric"
          class="h-[38px] px-3 rounded-[10px] border border-gray-200 text-[12px] font-medium text-gray-700 bg-white focus:ring-2 focus:ring-[#2563EB] focus:border-[#2563EB]"
        >
          <option v-for="opt in metricOptions" :key="opt.key" :value="opt.key">{{ opt.label }}</option>
        </select>
      </div>
    </div>
    
    <div class="flex-1 min-h-[200px] relative w-full overflow-hidden">
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
  },
  includeVat: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['update:period', 'update:includeVat'])

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
  const vatFactor = props.includeVat ? 1.22 : 1
  const map = {
    expenses: (d.costs || []).map(v => (Number(v) || 0) * vatFactor),
    impressions: d.impressions || [],
    clicks: d.clicks || [],
    leads: d.leads || [],
    cpc: (d.cpc || []).map(v => (Number(v) || 0) * vatFactor),
    cpa: (d.cpa || []).map(v => (Number(v) || 0) * vatFactor)
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
  const totalPoints = points.length

  return {
    labels,
    datasets: [{
      label: getLabelByMetric(chartMetric.value),
      data: points,
      borderColor: '#48A0FF',
      backgroundColor: (context) => {
        const chart = context.chart
        const { ctx, chartArea } = chart
        if (!chartArea) return 'rgba(77, 178, 255, 0.25)'
        const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom)
        gradient.addColorStop(0, 'rgba(72, 160, 255, 0.45)')
        gradient.addColorStop(0.5, 'rgba(72, 160, 255, 0.2)')
        gradient.addColorStop(1, 'rgba(72, 160, 255, 0.02)')
        return gradient
      },
      borderWidth: 2,
      pointRadius: (ctx) => {
        const idx = ctx.dataIndex
        const step = Math.max(1, Math.floor(totalPoints / 8))
        return idx % step === 0 ? 4 : 0
      },
      pointHoverRadius: 6,
      pointBackgroundColor: '#48A0FF',
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

watch([() => props.dynamics, chartMetric, () => props.includeVat], () => {
  chartKey.value++
}, { deep: true })

onMounted(() => {
  chartKey.value++
})
</script>
