<template>
  <div class="bg-white rounded-[32px] p-6 border border-gray-100 shadow-sm">
    <h3 class="text-base font-bold text-gray-900 mb-4">Возраст аудитории</h3>
    <div v-if="loading" class="h-48 flex items-center justify-center">
      <div class="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
    <div v-else-if="data.length === 0" class="h-48 flex items-center justify-center text-gray-500 text-sm">
      Нет данных (требуется Яндекс.Метрика)
    </div>
    <div v-else class="flex flex-row items-center gap-6">
      <div class="relative w-40 h-40 flex-shrink-0">
        <canvas ref="chartRef" />
      </div>
      <div class="grid grid-cols-2 gap-2 flex-1">
        <div
          v-for="(item, i) in data"
          :key="item.age_interval"
          class="flex items-center gap-2 px-3 py-2 rounded-xl bg-gray-50"
        >
          <span
            class="w-3 h-3 rounded-full flex-shrink-0"
            :style="{ backgroundColor: colors[i % colors.length] }"
          />
          <span class="text-sm text-gray-700">{{ ageLabelRu(item.age_interval) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { Chart, registerables } from 'chart.js'
import DataLabelsPlugin from 'chartjs-plugin-datalabels'
import api from '../../../api/axios'

Chart.register(...registerables, DataLabelsPlugin)

// Маппинг значений Метрики (RU/EN) → русские подписи
const AGE_LABELS_RU = {
  'младше 10 лет': 'Младше 10 лет',
  'младше 18 лет': 'Младше 18 лет',
  'younger than 18': 'Младше 18 лет',
  '10-17 лет': '10–17 лет',
  '18-24 года': '18–24 года',
  '18-25 лет': '18–25 лет',
  'age 18-24': '18–24 года',
  '25-34 года': '25–34 года',
  '25-35 лет': '25–34 года',
  'age 25-34': '25–34 года',
  '35-44 года': '35–44 года',
  'age 35-44': '35–44 года',
  '45-54 года': '45–54 года',
  '44-54 лет': '45–54 года',
  'age 45-54': '45–54 года',
  '55 и старше': '55 и старше',
  'age 55+': '55 и старше',
  'старше 54 лет': '55 и старше'
}

const ageLabelRu = (raw) => {
  const s = String(raw || '').trim()
  const key = s.toLowerCase()
  return AGE_LABELS_RU[key] ?? (s || '—')
}

const props = defineProps({
  clientId: { type: String, default: '' },
  startDate: { type: String, required: true },
  endDate: { type: String, required: true }
})

const chartRef = ref(null)
let chartInstance = null
const loading = ref(false)
const data = ref([])

const colors = ['#3b82f6', '#d4a574', '#8b5cf6', '#22c55e', '#f59e0b', '#10b981']

const total = computed(() => data.value.reduce((s, i) => s + (i.visits || 0), 0))

const percent = (item) => {
  if (total.value === 0) return 0
  return Math.round(((item.visits || 0) / total.value) * 100)
}

const updateChart = () => {
  if (!chartRef.value || data.value.length === 0) return
  if (chartInstance) chartInstance.destroy()

  chartInstance = new Chart(chartRef.value, {
    type: 'pie',
    data: {
      labels: data.value.map((d) => ageLabelRu(d.age_interval)),
      datasets: [{
        data: data.value.map((d) => d.visits || 0),
        backgroundColor: data.value.map((_, i) => colors[i % colors.length]),
        borderWidth: 2,
        borderColor: '#fff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      layout: { padding: 4 },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const p = total.value ? Math.round((ctx.raw / total.value) * 100) : 0
              return `${ageLabelRu(data.value[ctx.dataIndex]?.age_interval)}: ${ctx.raw} (${p}%)`
            }
          }
        },
        datalabels: {
          formatter: (value) => {
            const p = total.value ? Math.round((value / total.value) * 100) : 0
            return p > 0 ? `${p}%` : ''
          },
          color: '#fff',
          font: { size: 12, weight: 'bold' }
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
