<template>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-5 w-full">
    <!-- Левая колонка: Статистика по ключевым целям (синяя вся по шаблону) -->
    <div class="bg-[#1e3a8a] rounded-3xl p-6 sm:p-8 shadow-lg relative overflow-hidden">
      <!-- Декоративный паттерн -->
      <div class="absolute inset-0 opacity-[0.06]" style="background-image: radial-gradient(circle at 1px 1px, white 1px, transparent 0); background-size: 20px 20px" />
      <div class="relative z-10">
        <div class="flex items-center gap-3 mb-6">
          <div class="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center">
            <ChartBarIcon class="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 class="text-sm font-black text-white">Статистика по ключевым целям</h3>
            <p class="text-[10px] font-semibold text-white/70 uppercase tracking-wider mt-0.5">За период</p>
          </div>
        </div>

        <div v-if="loading || localLoading" class="space-y-4">
          <div v-for="i in 3" :key="i" class="h-16 bg-white/10 rounded-2xl animate-pulse" />
        </div>

        <div v-else-if="topGoals.length === 0" class="py-12 text-center text-white/60 text-sm font-medium">
          Цели не настроены
        </div>

        <div v-else class="space-y-4">
          <div
            v-for="(goal, index) in topGoals"
            :key="goal.id || goal.name"
            class="flex items-center justify-between"
          >
            <span class="text-base font-semibold text-white">{{ formatGoalName(goal.name) }}:</span>
            <div class="flex items-center gap-2">
              <span class="text-lg font-bold text-white tabular-nums">{{ (goal.count || 0).toLocaleString('ru-RU') }} шт.</span>
              <span
                v-if="goal.trend != null"
                :class="[
                  'inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold',
                  (goal.trend >= 0 ? 'bg-green-400/90 text-white' : 'bg-red-400/90 text-white')
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

    <!-- Центр: Итого (темнее левой по шаблону) -->
    <div class="bg-[#1e40af] rounded-3xl p-6 sm:p-8 flex flex-col justify-center items-center shadow-lg">
      <h3 class="text-xs font-black text-white/80 uppercase tracking-[0.2em] mb-4">Итого:</h3>
      <p class="text-5xl sm:text-6xl font-black text-white tabular-nums tracking-tight leading-none">
        {{ totalConversions.toLocaleString('ru-RU') }} шт.
      </p>
    </div>

    <!-- Правая колонка: Разбивка по целям (белый фон, минималистичная диаграмма) -->
    <div class="bg-white rounded-3xl p-6 sm:p-8 border border-gray-100 shadow-md">
      <h3 class="text-xs font-black text-gray-700 uppercase tracking-[0.15em] mb-5">Разбивка по целям</h3>

      <div class="relative w-full aspect-square max-w-[200px] mx-auto mb-5">
        <canvas ref="chartCanvas" class="w-full h-full" />
        <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div class="text-center">
            <p class="text-2xl font-black text-gray-800 tabular-nums">{{ totalConversions.toLocaleString('ru-RU') }}</p>
            <p class="text-[10px] font-bold text-gray-500 uppercase tracking-widest">шт.</p>
          </div>
        </div>
      </div>

      <div class="space-y-2.5">
        <div
          v-for="(goal, index) in topGoals"
          :key="goal.id || goal.name"
          class="flex items-center gap-3"
        >
          <div
            class="w-3 h-3 rounded-full flex-shrink-0"
            :style="{ backgroundColor: donutColors[index] }"
          />
          <span class="text-sm font-medium text-gray-700 truncate">{{ formatGoalName(goal.name) }}</span>
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

/** Цвета для 3 сегментов: синий, оранжевый, зелёный (по шаблону) */
const donutColors = ['#3b82f6', '#f59e0b', '#10b981']

const updateChart = () => {
  if (!chartCanvas.value) return
  if (chartInstance) chartInstance.destroy()
  if (!topGoals.value.length || totalConversions.value === 0) return

  chartInstance = new Chart(chartCanvas.value, {
    type: 'doughnut',
    data: {
      labels: topGoals.value.map(g => formatGoalName(g.name)),
      datasets: [{
        data: topGoals.value.map(g => g.count || 0),
        backgroundColor: topGoals.value.map((_, i) => donutColors[i]),
        borderWidth: 3,
        borderColor: '#ffffff',
        hoverOffset: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      cutout: '70%',
      plugins: { legend: { display: false } },
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
