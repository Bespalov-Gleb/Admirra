<template>
  <div class="bg-white rounded-[32px] p-6 border border-gray-100 shadow-sm">
    <h3 class="text-base font-bold text-gray-900 mb-4">Возраст аудитории</h3>
    <div v-if="loading" class="h-48 flex items-center justify-center">
      <div class="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
    <div v-else-if="data.length === 0" class="h-48 flex items-center justify-center text-gray-500 text-sm">
      Нет данных (требуется Яндекс.Метрика)
    </div>
    <div v-else class="flex flex-col items-center">
      <div class="relative w-40 h-40">
        <canvas ref="chartRef" />
      </div>
      <div class="mt-4 w-full space-y-1">
        <div
          v-for="(item, i) in data"
          :key="item.age_interval"
          class="flex items-center justify-between text-sm"
        >
          <span class="flex items-center gap-2">
            <span
              class="w-3 h-3 rounded-full flex-shrink-0"
              :style="{ backgroundColor: colors[i % colors.length] }"
            />
            {{ item.age_interval }}
          </span>
          <span class="font-medium">{{ item.visits?.toLocaleString() }} ({{ percent(item) }}%)</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { Chart, registerables } from 'chart.js'
import api from '../../../api/axios'

Chart.register(...registerables)

const props = defineProps({
  clientId: { type: String, default: '' },
  startDate: { type: String, required: true },
  endDate: { type: String, required: true }
})

const chartRef = ref(null)
let chartInstance = null
const loading = ref(false)
const data = ref([])

const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

const total = computed(() => data.value.reduce((s, i) => s + (i.visits || 0), 0))

const percent = (item) => {
  if (total.value === 0) return 0
  return Math.round(((item.visits || 0) / total.value) * 100)
}

const updateChart = () => {
  if (!chartRef.value || data.value.length === 0) return
  if (chartInstance) chartInstance.destroy()

  chartInstance = new Chart(chartRef.value, {
    type: 'doughnut',
    data: {
      labels: data.value.map((d) => d.age_interval),
      datasets: [{
        data: data.value.map((d) => d.visits || 0),
        backgroundColor: data.value.map((_, i) => colors[i % colors.length]),
        borderWidth: 0,
        cutout: '65%'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false },
        tooltip: { enabled: true }
      }
    }
  })
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      start_date: props.startDate,
      end_date: props.endDate
    }
    if (props.clientId) params.client_id = props.clientId
    const { data: res } = await api.get('dashboard/audience-age', { params })
    data.value = res || []
    updateChart()
  } catch {
    data.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.clientId, props.startDate, props.endDate],
  fetchData,
  { immediate: true }
)

onMounted(() => {
  if (data.value.length) updateChart()
})
onUnmounted(() => {
  if (chartInstance) chartInstance.destroy()
})
</script>
