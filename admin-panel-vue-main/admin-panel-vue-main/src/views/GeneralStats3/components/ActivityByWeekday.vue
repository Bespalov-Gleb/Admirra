<template>
  <div class="bg-white rounded-[10px] p-6 sm:p-8 border border-gray-100 shadow-sm h-full min-h-[360px] flex flex-col overflow-visible font-[Inter]">
    <div class="flex flex-col gap-1 mb-5">
      <div class="flex items-center justify-between gap-4">
        <h3 class="text-[20px] font-medium text-[#5F5F5F]" style="font-family: Inter, sans-serif;">Активность по дням</h3>
        <!-- Переключатель: Клики / Лиды -->
        <div class="flex rounded-[10px] bg-gray-100 p-0.5">
          <button
            type="button"
            @click="metric = 'clicks'"
            :class="['px-3 py-1.5 text-[12px] font-medium rounded-[8px] transition-colors', metric === 'clicks' ? 'bg-white text-[#2563EB] shadow-sm' : 'text-gray-500 hover:text-gray-700']"
          >
            Клики
          </button>
          <button
            type="button"
            @click="metric = 'leads'"
            :class="['px-3 py-1.5 text-[12px] font-medium rounded-[8px] transition-colors', metric === 'leads' ? 'bg-white text-[#2563EB] shadow-sm' : 'text-gray-500 hover:text-gray-700']"
          >
            Лиды
          </button>
        </div>
      </div>
      <p class="text-[13px] text-[#ABABAB]" style="font-family: 'Open Sans', sans-serif;">Сумма {{ metric === 'clicks' ? 'кликов' : 'лидов' }} по дням недели за период {{ startDate }} — {{ endDate }}</p>
    </div>
    <div v-if="loading" class="flex-1 min-h-[200px] flex items-center justify-center">
      <div class="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
    <div v-else class="flex-1 min-h-[200px] overflow-visible">
      <canvas ref="chartRef" />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
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

const chartRef = ref(null)
let chartInstance = null
const loading = ref(false)
const metric = ref('clicks') // 'clicks' | 'leads'
const chartData = ref({ clicks: {}, leads: {} })

const WEEKDAY_LABELS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
const WEEKDAY_INDICES = [1, 2, 3, 4, 5, 6, 0]

const updateChart = () => {
  if (!chartRef.value) return
  if (chartInstance) chartInstance.destroy()

  const data = chartData.value[metric.value] || chartData.value.clicks || {}
  const values = WEEKDAY_INDICES.map((i) => data[String(i)] || 0)
  const maxVal = Math.max(...values)
  const maxIdx = maxVal > 0 ? values.indexOf(maxVal) : -1

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
          gradient.addColorStop(0, '#2563EB')
          gradient.addColorStop(1, '#4A82FF')
          return values.map((_, i) => i === maxIdx && maxIdx >= 0 ? gradient : '#F5F7F9')
        })(),
        borderRadius: 15,
        barPercentage: 0.9,
        categoryPercentage: 0.85
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: { top: 32 } },
      plugins: {
        legend: { display: false },
        tooltip: { enabled: true },
        datalabels: {
          anchor: 'end',
          align: 'top',
          formatter: (v) => v,
          font: { size: 13, weight: '500', family: 'Inter' },
          color: (ctx) => ctx.dataIndex === maxIdx ? '#2563EB' : '#000000'
        }
      },
      scales: {
        x: {
          display: true,
          grid: { display: false },
          border: { display: false },
          ticks: { color: '#6b7280', font: { size: 13 } }
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
    updateChart()
  } catch {
    chartData.value = { clicks: {}, leads: {} }
    updateChart()
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.clientId, props.startDate, props.endDate, props.platform, props.campaignIds, props.goalActionIds],
  fetchData,
  { immediate: true }
)

watch(metric, () => updateChart())

onMounted(fetchData)
onUnmounted(() => {
  if (chartInstance) chartInstance.destroy()
})
</script>
