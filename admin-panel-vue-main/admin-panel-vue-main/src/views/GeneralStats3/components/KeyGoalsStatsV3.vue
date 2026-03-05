<template>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-5 w-full">
    <!-- Левая + центр: одна синяя таблица, почти равные блоки (по шаблону) -->
    <div class="lg:col-span-2 flex rounded-3xl overflow-hidden shadow-lg">
      <!-- Левая зона: цели (#3B82F6) -->
      <div class="flex-1 min-w-0 bg-[#3B82F6] p-6 sm:p-8 relative overflow-hidden flex flex-col min-h-[280px]">
        <div class="absolute inset-0 opacity-[0.06]" style="background-image: radial-gradient(circle at 1px 1px, white 1px, transparent 0); background-size: 20px 20px" />
        <div class="relative z-10 flex flex-col flex-1">
          <div class="flex items-center gap-3 mb-6">
            <div class="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center">
              <ChartBarIcon class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-sm font-black text-white">Статистика по ключевым целям</h3>
              <p class="text-[10px] font-semibold text-white/70 uppercase tracking-wider mt-0.5">За период</p>
            </div>
          </div>

          <div v-if="loading || localLoading" class="flex-1 flex flex-col justify-evenly">
            <div v-for="i in 3" :key="i" class="h-16 bg-white/10 rounded-2xl animate-pulse" />
          </div>

          <div v-else-if="topGoals.length === 0" class="flex-1 flex items-center justify-center text-white/60 text-base font-medium">
            Цели не настроены
          </div>

          <div v-else class="flex-1 flex flex-col justify-evenly">
            <div
              v-for="(goal, index) in topGoals"
              :key="goal.id || goal.name"
              class="flex items-center gap-3 py-2"
            >
              <span class="text-xl font-bold text-white flex-1 min-w-0 border-b border-dotted border-white/40 pb-0.5">{{ formatGoalName(goal.name) }}:</span>
              <div class="flex items-center gap-2 flex-shrink-0">
                <span class="text-2xl font-black text-white tabular-nums">{{ (goal.count || 0).toLocaleString('ru-RU') }} шт.</span>
                <span
                  v-if="goal.trend != null"
                  :class="[
                    'inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-sm font-bold',
                    (goal.trend >= 0 ? 'bg-[#10B981] text-white' : 'bg-red-400/90 text-white')
                  ]"
                >
                  <ArrowTrendingUpIcon v-if="goal.trend >= 0" class="w-4 h-4" />
                  <ArrowTrendingDownIcon v-else class="w-4 h-4" />
                  {{ goal.trend >= 0 ? '+' : '' }}{{ goal.trend }}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Правая зона: Итого (#2563EB, темнее левой), почти равная ширина -->
      <div class="flex-1 min-w-0 bg-[#2563EB] p-8 sm:p-10 relative overflow-hidden flex flex-col min-h-[280px]">
        <div class="absolute inset-0 opacity-[0.05]" style="background-image: linear-gradient(white 1px, transparent 1px), linear-gradient(90deg, white 1px, transparent 1px); background-size: 16px 16px" />
        <div class="relative z-10 flex flex-col flex-1">
          <h3 class="text-xs font-semibold text-white/80 uppercase tracking-wider mb-0">Итого:</h3>
          <div class="flex-1 flex items-end justify-center pb-4">
            <p class="flex items-baseline justify-center gap-1">
              <span class="text-7xl sm:text-8xl lg:text-9xl font-black text-white tabular-nums tracking-tight leading-none">{{ totalConversions.toLocaleString('ru-RU') }}</span>
              <span class="text-2xl sm:text-3xl font-bold text-white">шт.</span>
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Правая колонка: Разбивка по целям (белый фон, отдельная карточка) -->
    <div class="bg-white rounded-2xl p-6 sm:p-8 border border-gray-100 shadow-md">
      <h3 class="text-xs font-black text-gray-700 uppercase tracking-[0.15em] mb-5">Разбивка по целям</h3>

      <div class="relative w-full aspect-square max-w-[200px] mx-auto mb-5">
        <canvas ref="chartCanvas" class="w-full h-full" />
        <!-- Число в центре, без фона -->
        <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div class="text-center">
            <p class="text-2xl font-black text-gray-900 tabular-nums">{{ totalConversions.toLocaleString('ru-RU') }}</p>
            <p class="text-[10px] font-bold text-gray-600 uppercase tracking-widest">шт.</p>
          </div>
        </div>
      </div>

      <div class="space-y-2">
        <div
          v-for="(goal, index) in topGoals"
          :key="goal.id || goal.name"
          class="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-gray-100/80"
        >
          <div
            class="w-3.5 h-3.5 rounded-full flex-shrink-0 shadow-sm border border-white"
            :style="{ backgroundColor: donutColors[index] }"
          />
          <span class="text-sm font-semibold text-gray-800 truncate">{{ formatGoalName(goal.name) }}</span>
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

/** Итого: summary.leads если передан, иначе сумма топ-3 целей */
const totalConversions = computed(() => {
  if (props.totalLeads != null && !isNaN(props.totalLeads)) {
    return props.totalLeads
  }
  return topGoals.value.reduce((sum, g) => sum + (g.count || 0), 0)
})

/** Цвета: внешнее кольцо (светлее) и внутреннее (темнее того же цвета) */
const donutColors = ['#3b82f6', '#f59e0b', '#10b981']  // синий, оранжевый, зелёный
const donutColorsDark = ['#1d4ed8', '#d97706', '#059669']  // тёмно-синий, тёмно-оранжевый, тёмно-зелёный

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
          weight: 1.5
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
