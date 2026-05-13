<template>
  <div class="bg-white dark:bg-[#2A2D3C] rounded-[0.6944rem] p-6 sm:p-8 border border-gray-100 dark:border-white/10 shadow-sm h-full min-h-[25rem] flex flex-col font-[Inter]">
    <h3 class="text-[1.3889rem] font-medium text-[#5F5F5F] dark:text-white mb-5" style="font-family: Inter, sans-serif;">Возраст аудитории</h3>
    <div v-if="loading" class="flex-1 min-h-[16.6667rem] flex items-center justify-center">
      <div class="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
    <div v-else-if="data.length === 0" class="flex-1 min-h-[16.6667rem] flex items-center justify-center text-gray-500 dark:text-gray-400 text-sm">
      Нет данных (требуется Яндекс.Метрика)
    </div>
    <div v-else class="flex flex-col items-stretch gap-6 flex-1 min-h-0 lg:flex-row lg:gap-8">
      <div ref="chartWrapRef" class="relative mx-auto flex h-[15.2778rem] w-[15.2778rem] flex-shrink-0 cursor-pointer items-center justify-center sm:h-[16.6667rem] sm:w-[16.6667rem] lg:mx-0">
        <canvas ref="chartRef" class="h-full w-full" />
      </div>
      <div ref="legendRef" class="grid grid-cols-1 sm:grid-cols-2 flex-1 min-w-0 self-stretch" style="gap: 0.9028rem; align-content: space-between;">
        <div
          v-for="(item, i) in data"
          :key="item.age_interval"
          class="flex items-center rounded-[0.6944rem] bg-[#F5F7F9] dark:bg-white/5"
          style="padding: 1.25rem 1.1111rem; gap: 0.9028rem; min-height: 5rem;"
        >
          <span
            class="w-3 h-3 rounded-full flex-shrink-0"
            :style="{ backgroundColor: colors[i % colors.length] }"
          />
          <span class="text-[0.9722rem] font-medium text-[#2C2C2C] dark:text-gray-200" style="font-family: Inter, sans-serif;">{{ ageLabelRu(item.age_interval) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useTheme } from '../../../composables/useTheme'
import { Chart, registerables } from 'chart.js'
import DataLabelsPlugin from 'chartjs-plugin-datalabels'
import api from '../../../api/axios'

Chart.register(...registerables, DataLabelsPlugin)

// Маппинг значений Метрики (RU/EN) → русские подписи
const AGE_LABELS_RU = {
  // Русские варианты
  'младше 10 лет': 'Младше 10 лет',
  'младше 18 лет': 'Младше 18 лет',
  '10-17 лет': '10–17 лет',
  '18-24 года': '18–24 года',
  '18-25 лет': '18–25 лет',
  '25-34 года': '25–34 года',
  '25-35 лет': '25–35 лет',
  '35-44 года': '35–44 года',
  '45-54 года': '45–54 года',
  '44-54 лет': '44–54 лет',
  '55 и старше': '55 и старше',
  'старше 54 лет': '55 и старше',
  // Английские варианты (Яндекс Метрика EN)
  'younger than 18': 'Младше 18 лет',
  'age 18-24': '18–24 года',
  'age 25-34': '25–34 года',
  'age 35-44': '35–44 года',
  'age 45-54': '45–54 года',
  'age 55+': '55 и старше',
  // С дефисом и без пробела
  'age18-24': '18–24 года',
  'age25-34': '25–34 года',
  'age35-44': '35–44 года',
  'age45-54': '45–54 года',
  'age55+': '55 и старше',
  // Числовые диапазоны без "age"
  '18-24': '18–24 года',
  '25-34': '25–34 года',
  '35-44': '35–44 года',
  '45-54': '45–54 года',
  '55+': '55 и старше',
  // С нижним подчёркиванием
  'age_18_24': '18–24 года',
  'age_25_34': '25–34 года',
  'age_35_44': '35–44 года',
  'age_45_54': '45–54 года',
  'age_55_': '55 и старше',
  // С неразрывным дефисом U+2011
  'age 18\u2011-24': '18–24 года',
  'age 25\u2011-34': '25–34 года',
  'age 35\u2011-44': '35–44 года',
  'age 45\u2011-54': '45–54 года',
  'age 18\u201124': '18–24 года',
  'age 25\u201134': '25–34 года',
  'age 35\u201144': '35–44 года',
  'age 45\u201154': '45–54 года',
}

const ageLabelRu = (raw) => {
  const s = String(raw || '').trim()
  const key = s.toLowerCase()

  // Прямое совпадение в словаре
  if (AGE_LABELS_RU[key]) return AGE_LABELS_RU[key]

  // Fallback: "55+" или "55 и старше"
  if (/55\s*\+/.test(key) || key.includes('55+') || key.includes('55 и старше') || key.includes('старше 54')) {
    return '55 и старше'
  }

  // Fallback: "younger than" / "младше"
  if (key.includes('younger') || key.includes('младше')) {
    return 'Младше 18 лет'
  }

  // Fallback: диапазон вида "18-24", "Age 18-24", "18–24", "18‑24" (U+2011) и т.д.
  const rangeMatch = s.match(/(\d+)\s*[-\u2011–—]\s*(\d+)/)
  if (rangeMatch) {
    const from = parseInt(rangeMatch[1])
    const to = parseInt(rangeMatch[2])
    const directKey = `${from}-${to}`
    if (AGE_LABELS_RU[directKey]) return AGE_LABELS_RU[directKey]
    // Подбираем ближайший известный диапазон
    if (from <= 18 && to <= 25) return '18–24 года'
    if (from <= 25 && to <= 35) return '25–34 года'
    if (from <= 35 && to <= 44) return '35–44 года'
    if (from <= 45 && to <= 54) return '45–54 года'
    return `${from}–${to} лет`
  }

  return s || '—'
}

const props = defineProps({
  clientId: { type: String, default: '' },
  startDate: { type: String, required: true },
  endDate: { type: String, required: true }
})

const { isDarkMode } = useTheme()
const chartRef = ref(null)
const chartWrapRef = ref(null)
let chartInstance = null
let resizeObserver = null
const loading = ref(false)
const data = ref([])

const colors = ['#2B68EE', '#D1957C', '#D38CFF', '#8ADA70', '#EB8525BA', '#BAE8C8']

const total = computed(() => data.value.reduce((s, i) => s + (i.visits || 0), 0))

const percent = (item) => {
  if (total.value === 0) return 0
  return Math.round(((item.visits || 0) / total.value) * 100)
}

const isDark = () => document.documentElement.classList.contains('dark')

const updateChart = () => {
  if (!chartRef.value || data.value.length === 0) return
  if (chartInstance) chartInstance.destroy()

  const dark = isDark()
  const borderColor = dark ? '#2A2D3C' : '#fff'

  chartInstance = new Chart(chartRef.value, {
    type: 'pie',
    data: {
      labels: data.value.map((d) => ageLabelRu(d.age_interval)),
      datasets: [{
        data: data.value.map((d) => d.visits || 0),
        backgroundColor: data.value.map((_, i) => colors[i % colors.length]),
        borderWidth: 2,
        borderColor,
        spacing: 4,
        hoverOffset: 14,
        hoverBorderWidth: 2,
        hoverBorderColor: borderColor
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      resizeDelay: 80,
      layout: { padding: 8 },
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
          color: '#FFFFFF',
          font: { size: 14, weight: 'bold', family: 'Inter' }
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
  } catch {
    data.value = []
  } finally {
    loading.value = false
    await nextTick()
    observeChartWrap()
    updateChart()
  }
}

watch(
  () => [props.clientId, props.startDate, props.endDate],
  fetchData,
  { immediate: true }
)
watch(isDarkMode, () => updateChart())

const observeChartWrap = () => {
  if (!resizeObserver || !chartWrapRef.value) return
  resizeObserver.disconnect()
  resizeObserver.observe(chartWrapRef.value)
}

onMounted(() => {
  resizeObserver = new ResizeObserver(() => {
    if (chartInstance) chartInstance.resize()
  })
  if (data.value.length) {
    nextTick(() => {
      observeChartWrap()
      updateChart()
    })
  }
})
onUnmounted(() => {
  if (chartInstance) chartInstance.destroy()
  if (resizeObserver) resizeObserver.disconnect()
})
</script>
