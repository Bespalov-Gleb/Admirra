<template>
  <div class="bg-white rounded-[32px] p-6 border border-gray-100 shadow-sm">
    <h3 class="text-base font-bold text-gray-900 mb-4">Активность по дням</h3>
    <div v-if="loading" class="h-48 flex items-center justify-center">
      <div class="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
    <div v-else class="h-48">
      <canvas ref="chartRef" />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { Chart, registerables } from 'chart.js'
import api from '../../../api/axios'

Chart.register(...registerables)

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

const WEEKDAY_LABELS = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']

const updateChart = (data) => {
  if (!chartRef.value) return
  if (chartInstance) chartInstance.destroy()

  const values = WEEKDAY_LABELS.map((_, i) => data[String(i)] || 0)

  chartInstance = new Chart(chartRef.value, {
    type: 'bar',
    data: {
      labels: WEEKDAY_LABELS,
      datasets: [{
        label: 'Активность',
        data: values,
        backgroundColor: values.map((_, i) => (i >= 1 && i <= 5) ? 'rgba(59, 130, 246, 0.7)' : 'rgba(156, 163, 175, 0.6)'),
        borderRadius: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { enabled: true }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { precision: 0 }
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
