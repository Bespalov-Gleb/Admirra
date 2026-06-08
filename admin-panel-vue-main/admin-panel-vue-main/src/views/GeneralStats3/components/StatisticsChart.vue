<template>
  <div class="bg-white dark:bg-[#2A2D3C] w-full rounded-[1.3889rem] px-6 sm:px-8 py-6 shadow-sm flex flex-col min-h-0 font-[Inter] dark:border dark:border-white/10">
    <!-- Заголовок + чекбокс НДС (без селектора метрики — выбор через клик по карточкам) -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6 flex-shrink-0">
      <h3 class="text-[1.3889rem] font-medium text-gray-500 dark:text-white leading-[1] tracking-normal">Эффективность кампаний</h3>
      <div class="flex items-center gap-3">
        <label class="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            :checked="includeVat"
            @change="$emit('update:includeVat', ($event.target).checked)"
            class="w-4 h-4 rounded border-gray-300 text-[#2563EB] focus:ring-[#2563EB]"
          />
          <span class="text-[0.8333rem] font-medium text-gray-700 dark:text-gray-300">НДС</span>
        </label>
      </div>
    </div>

    <div data-statistics-chart-shell class="relative h-[22.2222rem] w-full min-w-0 overflow-hidden sm:h-[29.1667rem] xl:h-[33.3333rem]">
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
    default: () => ['expenses']
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

/** Цвета как в круговых диаграммах (KeyGoalsStatsV3) */
const METRIC_COLORS = {
  expenses: '#3464F3',
  impressions: '#F0926D',
  clicks: '#C2EECF',
  cpc: '#D38CFF',
  leads: '#8ADA70',
  cpa: '#EB8525'
}

const METRIC_LABELS = {
  expenses: 'Расход',
  impressions: 'Показы',
  clicks: 'Переходы',
  leads: 'Лиды',
  cpc: 'CPC',
  cpa: 'CPA'
}

const METRIC_KEYS = ['expenses', 'impressions', 'clicks', 'cpc', 'leads', 'cpa']
const Y_AXIS_IDS = ['y', 'y1', 'y2', 'y3', 'y4', 'y5']

const chartKey = ref(0)
let resizeObserver = null

const getDataByMetric = (key) => {
  const d = props.dynamics
  const vatFactor = props.includeVat ? 1.22 : 1
  const map = {
    expenses: (d.costs || []).map((v) => (Number(v) || 0) * vatFactor),
    impressions: d.impressions || [],
    clicks: d.clicks || [],
    leads: d.leads || [],
    cpc: (d.cpc || []).map((v) => (Number(v) || 0) * vatFactor),
    cpa: (d.cpa || []).map((v) => (Number(v) || 0) * vatFactor)
  }
  return (map[key] || []).map((v) => Number(v) || 0)
}

const isCurrencyMetric = (key) => ['expenses', 'cpc', 'cpa'].includes(key)

const chartData = computed(() => {
  const labels = props.dynamics.labels || []
  const active = props.selectedMetrics?.length ? props.selectedMetrics : ['expenses'] // fallback когда всё снято

  const datasets = active.map((metricKey, idx) => {
    const data = getDataByMetric(metricKey)
    const points = labels.map((label, i) => ({ x: label, y: data[i] ?? 0 }))
    const color = METRIC_COLORS[metricKey] || '#3464F3'
    return {
      label: METRIC_LABELS[metricKey] || metricKey,
      data: points,
      borderColor: color,
      backgroundColor: 'transparent',
      borderWidth: 2.5,
      pointRadius: 4,
      pointHoverRadius: 6,
      pointBackgroundColor: color,
      pointBorderColor: '#ffffff',
      pointBorderWidth: 1,
      fill: false,
      cubicInterpolationMode: 'monotone',
      yAxisID: Y_AXIS_IDS[METRIC_KEYS.indexOf(metricKey)] || 'y'
    }
  })

  return { labels, datasets }
})

const chartOptions = computed(() => {
  const active = props.selectedMetrics?.length ? props.selectedMetrics : ['expenses']
  const scales = {
    x: {
      grid: { display: false },
      ticks: {
        font: { size: 11, family: 'Inter' },
        color: '#9ca3af',
        maxRotation: 0,
        minRotation: 0
      }
    }
  }

  METRIC_KEYS.forEach((key, idx) => {
    const axisId = Y_AXIS_IDS[idx]
    scales[axisId] = {
      type: 'linear',
      position: 'left',
      display: false,
      beginAtZero: true,
      min: 0,
      grid: { display: false, drawBorder: false },
      ticks: { display: false }
    }
  })

  return {
    responsive: true,
    maintainAspectRatio: false,
    resizeDelay: 80,
    interaction: { mode: 'index', intersect: false },
    animation: { duration: 0 },
    plugins: {
      legend: { display: false },
      datalabels: { display: false },
      tooltip: {
        enabled: true,
        mode: 'index',
        intersect: false,
        displayColors: true,
        backgroundColor: 'rgba(30, 58, 138, 0.95)',
        titleColor: '#ffffff',
        bodyColor: '#ffffff',
        titleFont: { family: 'Inter' },
        bodyFont: { family: 'Inter' },
        padding: 10,
        cornerRadius: 6,
        callbacks: {
          label: (context) => {
            const val = context.parsed.y
            const key = active[context.datasetIndex]
            if (isCurrencyMetric(key)) {
              return `${context.dataset.label}: ${new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(val)}`
            }
            return `${context.dataset.label}: ${new Intl.NumberFormat('ru-RU').format(Math.round(val))}`
          }
        }
      }
    },
    scales
  }
})

watch(
  [() => props.dynamics, () => props.selectedMetrics, () => props.includeVat],
  () => {
    chartKey.value++
  },
  { deep: true }
)

onMounted(() => {
  chartKey.value++
  resizeObserver = new ResizeObserver(() => {
    chartKey.value++
  })
  const el = document.querySelector('[data-statistics-chart-shell]')
  if (el) resizeObserver.observe(el)
})

onUnmounted(() => {
  if (resizeObserver) resizeObserver.disconnect()
})
</script>
