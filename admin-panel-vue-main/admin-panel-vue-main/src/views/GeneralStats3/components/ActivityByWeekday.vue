<template>
  <div class="bg-white dark:bg-[#2A2D3C] rounded-[0.6944rem] p-6 sm:p-8 border border-gray-100 dark:border-white/10 shadow-sm h-full min-h-[25rem] flex flex-col overflow-visible font-[Inter]">
    <div class="flex items-center justify-between gap-4 mb-5">
      <h3 class="text-[1.3889rem] font-medium text-[#5F5F5F] dark:text-white" style="font-family: Inter, sans-serif;">Активность по дням</h3>
      <!-- Переключатель: Клики / Лиды -->
      <div class="flex rounded-[0.6944rem] bg-gray-100 dark:bg-white/10 p-0.5">
        <button
          type="button"
          @click="metric = 'clicks'"
          :class="['px-3 py-1.5 text-[0.8333rem] font-medium rounded-[0.5556rem] transition-colors', metric === 'clicks' ? 'bg-white dark:bg-[#2A2D3C] text-[#2563EB] dark:text-[#4A7AFF] shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300']"
        >
          Клики
        </button>
        <button
          type="button"
          @click="metric = 'leads'"
          :class="['px-3 py-1.5 text-[0.8333rem] font-medium rounded-[0.5556rem] transition-colors', metric === 'leads' ? 'bg-white dark:bg-[#2A2D3C] text-[#2563EB] dark:text-[#4A7AFF] shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300']"
        >
          Лиды
        </button>
      </div>
    </div>
    <div v-if="loading" class="flex-1 min-h-[13.8889rem] flex items-center justify-center">
      <div class="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
    <div ref="chartShellRef" v-else class="relative h-[18.0556rem] min-h-[16.6667rem] w-full min-w-0 overflow-visible sm:h-[20.8333rem]">
      <canvas ref="chartRef" class="h-full w-full" />
    </div>
  </div>
</template>

<script setup>
import { nextTick, ref, watch, onMounted, onUnmounted } from 'vue'
import { useTheme } from '../../../composables/useTheme'
import { Chart, registerables } from 'chart.js'
import DataLabelsPlugin from 'chartjs-plugin-datalabels'
import api from '../../../api/axios'

Chart.register(...registerables, DataLabelsPlugin)

const props = defineProps({
  clientId: { type: String, default: '' },
  startDate: { type: String, required: true },
  endDate: { type: String, required: true },
  platform: { type: String, default: 'all' },
  campaignIds: { type: Array, default: () => [] },
  goalActionIds: { type: Array, default: () => [] }
})

const { isDarkMode } = useTheme()
const chartRef = ref(null)
const chartShellRef = ref(null)
let chartInstance = null
let resizeObserver = null
const loading = ref(false)
const metric = ref('clicks') // 'clicks' | 'leads'
const chartData = ref({ clicks: {}, leads: {} })

const WEEKDAY_LABELS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
const WEEKDAY_INDICES = [1, 2, 3, 4, 5, 6, 0]

const isDark = () => document.documentElement.classList.contains('dark')

const observeChartShell = () => {
  if (!resizeObserver || !chartShellRef.value) return
  resizeObserver.disconnect()
  resizeObserver.observe(chartShellRef.value)
}

const updateChart = () => {
  if (!chartRef.value) return
  if (chartInstance) chartInstance.destroy()

  const data = chartData.value[metric.value] || chartData.value.clicks || {}
  const values = WEEKDAY_INDICES.map((i) => data[String(i)] || 0)
  const maxVal = Math.max(...values)
  const maxIdx = maxVal > 0 ? values.indexOf(maxVal) : -1
  const dark = isDark()
  const barInactiveColor = dark ? 'rgba(255,255,255,0.18)' : '#F5F7F9'
  const labelColor = dark ? (ctx) => (ctx.dataIndex === maxIdx ? '#4A7AFF' : '#9CA3AF') : (ctx) => (ctx.dataIndex === maxIdx ? '#2563EB' : '#000000')

  chartInstance = new Chart(chartRef.value, {
    type: 'bar',
    data: {
      labels: WEEKDAY_LABELS,
        datasets: [{
        label: metric.value === 'clicks' ? 'Клики' : 'Лиды',
        data: values,
        backgroundColor: (() => {
          const canvas = chartRef.value
          const ctx2d = canvas.getContext('2d')
          const h = canvas.clientHeight || 300
          const gradient = ctx2d.createLinearGradient(0, 0, 0, h)
          gradient.addColorStop(0, dark ? '#2563EB' : '#2563EB')
          gradient.addColorStop(1, dark ? '#4A7AFF' : '#4A82FF')
          return values.map((_, i) => i === maxIdx && maxIdx >= 0 ? gradient : barInactiveColor)
        })(),
        borderRadius: 15,
        barPercentage: 0.9,
        categoryPercentage: 0.85
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      resizeDelay: 80,
      layout: { padding: { top: 32 } },
      plugins: {
        legend: { display: false },
        tooltip: { enabled: true },
        datalabels: {
          anchor: 'end',
          align: 'top',
          formatter: (v) => v,
          font: { size: 13, weight: '500', family: 'Inter' },
          color: labelColor
        }
      },
      scales: {
        x: {
          display: true,
          grid: { display: false },
          border: { display: false },
          ticks: { color: dark ? '#9CA3AF' : '#6b7280', font: { size: 13 } }
        },
        y: {
          display: false,
          beginAtZero: true,
          grid: { display: false },
          border: { display: false }
        }
      }
    }
  })
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      start_date: props.startDate,
      end_date: props.endDate,
      platform: props.platform
    }
    if (props.clientId) params.client_id = props.clientId
    if (props.campaignIds?.length) params.campaign_ids = props.campaignIds
    if (props.goalActionIds?.length) params.goal_action_ids = props.goalActionIds
    const { data } = await api.get('dashboard/activity-by-weekday', { params })
    // Новый формат: { clicks: {...}, leads: {...} }. Старый (кэш): {"0": N, ...} — считаем за clicks
    if (data && data.clicks && data.leads) {
      chartData.value = data
    } else if (data && typeof data === 'object' && !Array.isArray(data) && Object.keys(data).some(k => /^[0-6]$/.test(k))) {
      // Старый формат (clicks+leads): показываем как клики, лиды = 0
      chartData.value = { clicks: { ...data }, leads: { "0": 0, "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0 } }
    } else {
      chartData.value = { clicks: {}, leads: {} }
    }
  } catch {
    chartData.value = { clicks: {}, leads: {} }
  } finally {
    loading.value = false
    await nextTick()
    observeChartShell()
    updateChart()
  }
}

watch(
  () => [props.clientId, props.startDate, props.endDate, props.platform, props.campaignIds, props.goalActionIds],
  fetchData,
  { immediate: true }
)

watch(metric, () => updateChart())
watch(isDarkMode, () => updateChart())

onMounted(() => {
  resizeObserver = new ResizeObserver(() => {
    if (chartInstance) chartInstance.resize()
  })
  if (chartShellRef.value) resizeObserver.observe(chartShellRef.value)
})
onUnmounted(() => {
  if (chartInstance) chartInstance.destroy()
  if (resizeObserver) resizeObserver.disconnect()
})
</script>
