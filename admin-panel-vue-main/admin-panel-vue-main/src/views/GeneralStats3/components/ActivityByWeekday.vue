<template>
  <div class="bg-white rounded-[10px] p-6 sm:p-8 border border-gray-100 shadow-sm h-full min-h-[360px] flex flex-col overflow-visible font-[Inter]">
    <h3 class="text-[15px] font-bold text-[#09183F] mb-5">Активность по дням</h3>
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

const WEEKDAY_LABELS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
const WEEKDAY_INDICES = [1, 2, 3, 4, 5, 6, 0]

const updateChart = (data) => {
  if (!chartRef.value) return
  if (chartInstance) chartInstance.destroy()

  const values = WEEKDAY_INDICES.map((i) => data[String(i)] || 0)
  const maxVal = Math.max(...values)
  const maxIdx = maxVal > 0 ? values.indexOf(maxVal) : -1

  chartInstance = new Chart(chartRef.value, {
    type: 'bar',
    data: {
      labels: WEEKDAY_LABELS,
      datasets: [{
        label: 'Активность',
        data: values,
        backgroundColor: values.map((_, i) => (i === maxIdx && maxIdx >= 0 ? '#2563EB' : 'rgba(156, 163, 175, 0.5)')),
        borderRadius: 6,
        barPercentage: 0.65,
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
          font: { size: 13, weight: 'bold' },
          color: '#374151'
        }
      },
      scales: {
        x: {
          display: true,
          grid: { display: false },
          border: { display: false },
          ticks: { color: '#6b7280', font: { size: 12 } }
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
    updateChart(data || {})
  } catch {
    updateChart({})
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.clientId, props.startDate, props.endDate, props.platform, props.campaignIds, props.goalActionIds],
  fetchData,
  { immediate: true }
)

onMounted(fetchData)
onUnmounted(() => {
  if (chartInstance) chartInstance.destroy()
})
</script>
