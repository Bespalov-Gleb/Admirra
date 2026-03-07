<template>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-5 w-full font-[Inter]">
    <!-- Левая: Статистика по ключевым целям (белая карточка) -->
    <div class="bg-white rounded-[10px] p-6 shadow-sm border border-gray-100 min-h-[280px] flex flex-col">
      <div class="flex items-center gap-3 mb-5">
        <div class="w-10 h-10 rounded-[10px] bg-[#EFF6FF] flex items-center justify-center">
          <ChartBarIcon class="w-5 h-5 text-[#2563EB]" />
        </div>
        <div>
          <h3 class="text-[20px] font-bold text-[#09183F]">Статистика по ключевым целям</h3>
          <p class="text-[15px] font-normal text-gray-500 mt-0.5">За период</p>
        </div>
      </div>

      <div v-if="loading || localLoading" class="flex-1 flex flex-col justify-evenly gap-3">
        <div v-for="i in 3" :key="i" class="h-12 bg-gray-100 rounded-[10px] animate-pulse" />
      </div>

      <div v-else-if="topGoals.length === 0" class="flex-1 flex items-center justify-center text-gray-500 text-[14px] font-medium">
        Цели не настроены
      </div>

      <div v-else class="flex-1 flex flex-col justify-evenly">
        <div
          v-for="(goal, index) in topGoals"
          :key="goal.id || goal.name"
          class="flex items-center gap-2 py-2 border-b border-gray-100 last:border-0"
        >
          <span class="text-[20px] font-normal text-gray-500 whitespace-nowrap">{{ formatGoalName(goal.name) }}:</span>
          <div class="flex-1 border-b border-dashed border-gray-300 self-end mb-[7px]" />
          <div class="flex items-center gap-1.5 flex-shrink-0">
            <span class="text-[21px] font-bold text-[#09183F] tabular-nums whitespace-nowrap">{{ (goal.count || 0).toLocaleString('ru-RU') }} шт.</span>
            <span
              v-if="goal.trend != null"
              class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[11px] font-semibold whitespace-nowrap"
              :class="goal.trend >= 0 ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-500'"
            >
              <ArrowTrendingUpIcon v-if="goal.trend >= 0" class="w-3 h-3 flex-shrink-0" />
              <ArrowTrendingDownIcon v-else class="w-3 h-3 flex-shrink-0" />
              {{ goal.trend >= 0 ? '+' : '' }}{{ goal.trend }}%
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Центр: Итого (светло-голубая карточка с точечным паттерном) -->
    <div
      class="rounded-[10px] p-6 border border-blue-200 shadow-sm min-h-[280px] flex flex-col relative overflow-hidden"
      style="background-color: #BFDBFE; background-image: radial-gradient(circle, rgba(255,255,255,0.55) 1.5px, transparent 1.5px); background-size: 14px 14px;"
    >
      <h3 class="text-[23px] font-normal text-white">Итого:</h3>
      <div class="flex-1 flex items-end justify-center min-h-0 overflow-visible">
        <p class="flex items-baseline gap-2" style="margin-bottom: -4px;">
          <span class="text-[96px] font-black text-white tabular-nums tracking-tight" style="line-height: 1;">{{ totalConversions.toLocaleString('ru-RU') }}</span>
          <span class="text-[36px] font-bold text-white" style="line-height: 1; padding-bottom: 8px;">шт.</span>
        </p>
      </div>
    </div>

    <!-- Правая: Разбивка по целям (белая карточка) -->
    <div class="bg-white rounded-[10px] p-6 shadow-sm border border-gray-100 min-h-[280px] flex flex-col">
      <h3 class="text-[15px] font-bold text-[#09183F] mb-4">Разбивка по целям</h3>

      <div class="relative w-full aspect-square max-w-[180px] mx-auto mb-4">
        <canvas ref="chartCanvas" class="w-full h-full" />
        <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div class="text-center">
            <p class="text-[16px] font-bold text-[#09183F] tabular-nums">{{ totalConversions.toLocaleString('ru-RU') }}</p>
            <p class="text-[10px] font-semibold text-gray-500">шт.</p>
          </div>
        </div>
      </div>

      <div class="space-y-2 mb-4">
        <div
          v-for="(goal, index) in topGoals"
          :key="goal.id || goal.name"
          class="flex items-center gap-2.5"
        >
          <div
            class="w-3 h-3 rounded-full flex-shrink-0"
            :style="{ backgroundColor: donutColors[index] }"
          />
          <span class="text-[12px] font-medium text-[#09183F] truncate">{{ formatGoalName(goal.name) }}</span>
        </div>
      </div>

      <!-- Dropdown как на скрине -->
      <div class="mt-auto">
        <select class="w-full h-9 pl-3 pr-8 bg-white border border-gray-200 rounded-[10px] text-[12px] font-medium text-gray-700 outline-none appearance-none focus:border-[#2563EB]">
          <option>Функциональная</option>
        </select>
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
  loading: { type: Boolean, default: false },
  /** Общее число лидов (summary.leads) — для центра «Итого» и donut */
  totalLeads: { type: Number, default: null }
})

const chartCanvas = ref(null)
let chartInstance = null

const formatGoalName = (name) => name || 'Цель'

const effectiveGoals = computed(() =>
  props.goals?.length > 0 ? props.goals : localGoals.value
)

/** Топ-3 цели по количеству конверсий (самые результативные) */
const topGoals = computed(() => {
  const goals = [...effectiveGoals.value]
  return goals
    .sort((a, b) => (b.count || 0) - (a.count || 0))
    .slice(0, 3)
})

/** Итого: сумма ВСЕХ целей, выбранных пользователем при интеграции (get_goals уже фильтрует по selected_goals) */
const totalConversions = computed(() => {
  return effectiveGoals.value.reduce((sum, g) => sum + (g.count || 0), 0)
})

/** Цвета по скрину: синий, оранжевый, зелёный */
const donutColors = ['#2563EB', '#FB923C', '#86EFAC']
const donutColorsDark = ['#1d4ed8', '#ea580c', '#22c55e']

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
          backgroundColor: topGoals.value.map((_, i) => donutColors[i]),
          borderWidth: 0,
          hoverOffset: 0,
          weight: 3
        },
        {
          data,
          backgroundColor: topGoals.value.map((_, i) => donutColorsDark[i]),
          borderWidth: 0,
          hoverOffset: 2,
          weight: 2.25
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
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
    const { data } = await api.get('dashboard/goals', {
      params: { client_id: props.clientId, date_from: props.startDate, date_to: props.endDate }
    })
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
  () => [props.clientId, props.startDate, props.endDate],
  loadGoals,
  { immediate: true }
)

onMounted(() => {
  if (topGoals.value.length > 0) setTimeout(updateChart, 100)
})

onUnmounted(() => {
  if (chartInstance) chartInstance.destroy()
})
</script>
