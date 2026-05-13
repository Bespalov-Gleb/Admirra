<template>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-5 w-full font-[Inter]">

    <!-- Объединённая карточка: Статистика + Итого (2 колонки) -->
    <div class="lg:col-span-2 bg-white dark:bg-[#2A2D3C] rounded-[0.6944rem] shadow-sm border border-gray-100 dark:border-white/10 min-h-[26.3889rem] lg:min-h-[29.1667rem] flex overflow-hidden">

      <!-- Левая часть: Статистика -->
      <div class="flex-1 min-w-0 p-4 sm:p-6 flex flex-col">
        <div class="flex items-center gap-5 mb-5">
          <div class="w-12 h-12 rounded-[0.6944rem] bg-[#EFF6FF] dark:bg-blue-500/20 flex items-center justify-center">
            <ChartBarIcon class="w-7 h-7 text-[#2563EB] dark:text-[#4A7AFF]" />
          </div>
          <div>
            <h3 class="text-[1.3889rem] font-medium text-[#5F5F5F] dark:text-white" style="font-family: Inter, sans-serif; letter-spacing: 0px;">Статистика по ключевым целям</h3>
            <p class="text-[1.0417rem] font-normal mt-0.5 text-[#ABABAB] dark:text-gray-500" style="font-family: 'Open Sans', sans-serif; letter-spacing: 0px;">За период</p>
          </div>
        </div>

        <div v-if="loading || localLoading" class="flex-1 flex flex-col justify-start gap-2">
          <div v-for="i in skeletonCount" :key="i" class="h-8 bg-gray-100 rounded-[0.5556rem] animate-pulse" />
        </div>

        <div v-else-if="topGoals.length === 0" class="flex-1 flex items-center justify-center text-center text-gray-500 text-[0.9722rem] font-medium px-4">
          <span>Нет данных по целям. Возможно, идёт синхронизация — обновите страницу через минуту.</span>
        </div>

        <div v-else class="flex-1 flex flex-col justify-start gap-0.5">
          <div
            v-for="(goal, index) in topGoals"
            :key="goal.id || goal.name"
            class="flex items-center gap-2 py-1.5 border-b border-gray-100 dark:border-white/10 last:border-0"
          >
            <span class="text-[1.0417rem] font-normal text-gray-500 dark:text-white whitespace-nowrap min-w-0 truncate">{{ formatGoalName(goal.name) }}:</span>
            <div class="flex-1 border-b border-dashed border-gray-300 dark:border-gray-600 self-end mb-[0.3472rem]" />
            <div class="flex items-center gap-1.5 flex-shrink-0">
              <span class="text-[1.1111rem] font-bold text-[#09183F] dark:text-white tabular-nums whitespace-nowrap">{{ (goal.count || 0).toLocaleString('ru-RU') }} шт.</span>
              <span
                v-if="goal.trend != null"
                class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-[0.4167rem] text-[0.625rem] font-normal whitespace-nowrap shrink-0"
                :class="goal.trend >= 0 ? 'bg-[#EBFDF2] dark:bg-green-500/20 text-[#38B35A] dark:text-[#66BB6A]' : 'bg-[#FCEBED] dark:bg-red-500/20 text-[#EB5757] dark:text-[#EF5350]'"
              >
                <ArrowTrendingUpIcon v-if="goal.trend >= 0" class="w-2.5 h-2.5 flex-shrink-0" />
                <ArrowTrendingDownIcon v-else class="w-2.5 h-2.5 flex-shrink-0" />
                {{ goal.trend >= 0 ? '+' : '' }}{{ goal.trend }}%
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Правая часть: блок Итого (градиент от #2563EB) -->
      <div
        class="w-[50%] min-w-[11.1111rem] mx-2 lg:mx-3 rounded-[1.3889rem] lg:rounded-[1.5972rem] flex flex-col relative overflow-hidden"
        style="background: linear-gradient(135deg, #2563EB 0%, #2563EB 3%, #1d4ed8 18%, #1e40af 45%, #172554 100%);"
      >
        <!-- Белые точки (как на карточке тарифов) -->
        <div
          class="absolute inset-0"
          style="background-image: radial-gradient(circle, rgba(255,255,255,0.13) 1px, transparent 1px); background-size: 1.1111rem 1.1111rem;"
        ></div>
        <h3 class="text-[1.25rem] lg:text-[1.5972rem] font-normal text-white p-4 lg:p-5 pb-0 relative z-10">Итого:</h3>
        <!-- Число прижато к самому низу, масштаб под ширину экрана -->
        <div class="absolute bottom-0 left-0 right-0 flex items-end justify-center overflow-hidden z-10 px-2">
          <div class="flex items-end" style="transform-origin: bottom center;">
            <span class="text-white tabular-nums" style="font-family: Inter, sans-serif; font-weight: 600; line-height: 0.85; letter-spacing: -0.0771rem; font-size: clamp(5.5556rem, 12vw, 11.1111rem);">{{ totalConversions.toLocaleString('ru-RU') }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Правая: Разбивка по целям (белая карточка) -->
    <div class="bg-white dark:bg-[#2A2D3C] rounded-[0.6944rem] p-4 sm:p-6 shadow-sm border border-gray-100 dark:border-white/10 min-h-[26.3889rem] lg:min-h-[29.1667rem] flex flex-col min-w-0">
      <h3 class="text-[1.3889rem] font-medium text-[#5F5F5F] dark:text-white mb-4" style="font-family: Inter, sans-serif; letter-spacing: 0px;">Разбивка по целям</h3>

      <!-- Диаграмма слева + легенда справа -->
      <div class="flex-1 flex flex-col items-center gap-4 min-w-0 sm:flex-row sm:items-center lg:gap-4">
        <!-- Donut chart — уменьшается на узких экранах -->
        <div ref="chartShellRef" class="relative flex-shrink-0 w-[12.5rem] h-[12.5rem] sm:w-[11.1111rem] sm:h-[11.1111rem] lg:w-[13.8889rem] lg:h-[13.8889rem]">
          <canvas ref="chartCanvas" class="w-full h-full" />
          <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div class="text-center">
              <p class="text-[0.9722rem] sm:text-[1.1111rem] lg:text-[1.25rem] font-bold text-[#09183F] dark:text-white tabular-nums leading-tight">{{ totalConversions.toLocaleString('ru-RU') }} шт.</p>
            </div>
          </div>
        </div>

        <!-- Легенда: полная ширина текста, перенос при необходимости -->
        <div class="flex-1 flex flex-col gap-1.5 min-w-0 overflow-y-auto">
          <div
            v-for="(goal, index) in topGoals"
            :key="goal.id || goal.name"
            class="flex items-start gap-2 px-2.5 py-1.5 rounded-[0.5556rem] bg-gray-50 dark:bg-white/[0.05] min-w-0"
          >
            <div
              class="w-2.5 h-2.5 rounded-full flex-shrink-0 mt-0.5"
              :style="{ backgroundColor: donutColors[index % donutColors.length] }"
            />
            <span class="text-[0.8333rem] sm:text-[0.9028rem] font-normal text-[#09183F] dark:text-white leading-tight" style="word-break: break-word; overflow-wrap: anywhere;">{{ formatGoalName(goal.name) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import { Chart, registerables } from 'chart.js'
import { ArrowTrendingUpIcon, ArrowTrendingDownIcon, ChartBarIcon } from '@heroicons/vue/24/solid'
import api from '../../../api/axios'

Chart.register(...registerables)

const props = defineProps({
  goals: { type: Array, default: () => [] },
  clientId: { type: String, default: '' },
  startDate: { type: String, default: '' },
  endDate: { type: String, default: '' },
  /** yandex | vk | all — при vk запрашиваются цели VK (разбивка по типам ЦД) */
  channel: { type: String, default: 'all' },
  /** Фильтр по кампаниям (для VK — только выбранные кампании) */
  campaignIds: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  /** Общее число лидов (summary.leads) — для центра «Итого» и donut */
  totalLeads: { type: Number, default: null }
})

const chartCanvas = ref(null)
const chartShellRef = ref(null)
let chartInstance = null
let resizeObserver = null

const formatGoalName = (name) => name || 'Цель'

const effectiveGoals = computed(() =>
  props.goals?.length > 0 ? props.goals : localGoals.value
)

/** Число полос скелетона: по количеству целей или 4 по умолчанию */
const skeletonCount = computed(() => {
  const n = effectiveGoals.value?.length ?? 0
  return Math.max(1, n || 4)
})

/** Все цели по количеству конверсий (сортировка: самые результативные сверху) */
const topGoals = computed(() => {
  const goals = [...effectiveGoals.value]
  return goals.sort((a, b) => (b.count || 0) - (a.count || 0))
})

/** Итого: сумма ВСЕХ целей, выбранных пользователем при интеграции (get_goals уже фильтрует по selected_goals) */
const totalConversions = computed(() => {
  return effectiveGoals.value.reduce((sum, g) => sum + (g.count || 0), 0)
})

/** Цвета для диаграммы (поддержка 6+ целей) */
const donutColors = ['#3464F3', '#F0926D', '#C2EECF', '#D38CFF', '#8ADA70', '#EB8525']
const donutColorsPastel = ['#4C78FF', '#FFA582', '#E5FFED', '#E5B8FF', '#A8F08A', '#FFA04D']

const updateChart = () => {
  if (!chartCanvas.value) return
  if (chartInstance) chartInstance.destroy()
  if (!topGoals.value.length || totalConversions.value === 0) return

  const data = topGoals.value.map(g => g.count || 0)
  chartInstance = new Chart(chartCanvas.value, {
    type: 'doughnut',
    data: {
      labels: topGoals.value.map(g => formatGoalName(g.name)),
      datasets: [
        {
          data,
          backgroundColor: topGoals.value.map((_, i) => donutColorsPastel[i % donutColorsPastel.length]),
          borderWidth: 0,
          hoverOffset: 0,
          weight: 4
        },
        {
          data,
          backgroundColor: topGoals.value.map((_, i) => donutColors[i % donutColors.length]),
          borderWidth: 0,
          hoverOffset: 4,
          weight: 2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      resizeDelay: 80,
      cutout: '60%',
      spacing: 0,
      plugins: {
        legend: { display: false },
        datalabels: { display: false }
      },
      layout: { padding: 0 }
    }
  })
}

const fetchGoals = async () => {
  if (!props.clientId || !props.startDate || !props.endDate) return []
  try {
    const params = { client_id: props.clientId, date_from: props.startDate, date_to: props.endDate }
    if (props.channel === 'vk') params.platform = 'vk'
    if (props.campaignIds?.length > 0) params.campaign_ids = props.campaignIds.join(',')
    const { data } = await api.get('dashboard/goals', { params })
    return data || []
  } catch {
    return []
  }
}

const localGoals = ref([])
const localLoading = ref(false)

watch([topGoals, totalConversions], () => {
  if (topGoals.value.length > 0) {
    nextTick(updateChart)
  }
}, { deep: true })

const loadGoals = async () => {
  if (props.goals?.length > 0) return
  if (!props.clientId) {
    localGoals.value = []
    return
  }
  localLoading.value = true
  try {
    localGoals.value = await fetchGoals()
    await nextTick()
    updateChart()
  } finally {
    localLoading.value = false
  }
}

watch(
  () => [props.clientId, props.startDate, props.endDate, props.channel, props.campaignIds],
  loadGoals,
  { immediate: true, deep: true }
)

onMounted(() => {
  resizeObserver = new ResizeObserver(() => {
    if (chartInstance) chartInstance.resize()
  })
  if (chartShellRef.value) resizeObserver.observe(chartShellRef.value)
  if (topGoals.value.length > 0) setTimeout(updateChart, 100)
})

onUnmounted(() => {
  if (chartInstance) chartInstance.destroy()
  if (resizeObserver) resizeObserver.disconnect()
})
</script>
