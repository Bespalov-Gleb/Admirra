<template>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-5 w-full">
    <!-- Левая колонка: Статистика по ключевым целям -->
    <div class="bg-gray-50 rounded-3xl p-6 sm:p-8 border border-gray-100 shadow-md">
      <div class="flex items-center gap-3 mb-5">
        <div class="w-10 h-10 rounded-xl bg-blue-500 flex items-center justify-center shadow-sm">
          <ChartBarIcon class="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 class="text-xs font-black text-gray-800 uppercase tracking-[0.15em]">Статистика по ключевым целям</h3>
          <p class="text-[10px] font-bold text-gray-400 uppercase tracking-[0.2em] mt-0.5">За период</p>
        </div>
      </div>

      <div v-if="loading || localLoading" class="space-y-3">
        <div v-for="i in 3" :key="i" class="h-14 bg-gray-200/50 rounded-2xl animate-pulse" />
      </div>

      <div v-else-if="effectiveGoals.length === 0" class="py-12 text-center text-gray-400 text-sm font-medium">
        Цели не настроены
      </div>

      <div v-else class="space-y-2.5">
        <div
          v-for="(goal, index) in effectiveGoals"
          :key="goal.id || goal.name"
          class="flex items-center justify-between px-4 py-3.5 rounded-2xl bg-blue-50/80 border border-blue-100/80"
        >
          <span class="text-sm font-semibold text-gray-800">{{ formatGoalName(goal.name) }}:</span>
          <div class="flex items-center gap-2.5">
            <span class="text-sm font-bold text-gray-900 tabular-nums">{{ (goal.count || 0).toLocaleString('ru-RU') }} шт.</span>
            <span
              v-if="goal.trend != null"
              :class="[
                'inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[11px] font-bold',
                (goal.trend >= 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700')
              ]"
            >
              <ArrowTrendingUpIcon v-if="goal.trend >= 0" class="w-3.5 h-3.5" />
              <ArrowTrendingDownIcon v-else class="w-3.5 h-3.5" />
              {{ goal.trend >= 0 ? '+' : '' }}{{ goal.trend }}%
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Центр: Итого -->
    <div class="bg-blue-600 rounded-3xl p-6 sm:p-8 flex flex-col justify-center items-center shadow-lg shadow-blue-900/20">
      <h3 class="text-xs font-black text-white/80 uppercase tracking-[0.2em] mb-3">Итого:</h3>
      <p class="text-4xl sm:text-5xl font-black text-white tabular-nums tracking-tight">
        {{ totalConversions.toLocaleString('ru-RU') }} шт.
      </p>
    </div>

    <!-- Правая колонка: Разбивка по целям -->
    <div class="bg-gray-50 rounded-3xl p-6 sm:p-8 border border-gray-100 shadow-md">
      <h3 class="text-xs font-black text-gray-700 uppercase tracking-[0.15em] mb-5">Разбивка по целям</h3>

      <div class="relative w-full aspect-square max-w-[220px] mx-auto mb-5">
        <canvas ref="chartCanvas" class="w-full h-full" />
        <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div class="text-center">
            <p class="text-3xl font-black text-gray-900 tabular-nums">{{ totalConversions.toLocaleString('ru-RU') }}</p>
            <p class="text-[10px] font-bold text-gray-500 uppercase tracking-widest">шт.</p>
          </div>
        </div>
      </div>

      <div class="space-y-2.5 mb-5">
        <div
          v-for="(goal, index) in effectiveGoals"
          :key="goal.id || goal.name"
          class="flex items-center gap-3"
        >
          <div
            class="w-3.5 h-3.5 rounded-full flex-shrink-0 shadow-sm border border-white"
            :style="{ backgroundColor: colors[index % colors.length] }"
          />
          <span class="text-sm font-medium text-gray-700 truncate">{{ formatGoalName(goal.name) }}</span>
        </div>
      </div>

      <select
        class="w-full px-4 py-2.5 text-sm font-medium border border-gray-200 rounded-xl bg-white text-gray-600 shadow-sm focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 cursor-pointer"
        disabled
      >
        <option>Функциональная</option>
      </select>
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
  goals: {
    type: Array,
    default: () => []
  },
  clientId: { type: String, default: '' },
  startDate: { type: String, default: '' },
  endDate: { type: String, default: '' },
  loading: { type: Boolean, default: false }
})

const chartCanvas = ref(null)
let chartInstance = null

const formatGoalName = (name) => name || 'Цель'

const effectiveGoals = computed(() =>
  props.goals?.length > 0 ? props.goals : localGoals.value
)

const totalConversions = computed(() =>
  effectiveGoals.value.reduce((sum, g) => sum + (g.count || 0), 0)
)

const colors = ['#3b82f6', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#ec4899']

const updateChart = () => {
  if (!chartCanvas.value) return
  if (chartInstance) chartInstance.destroy()
  if (!effectiveGoals.value.length || totalConversions.value === 0) return

  chartInstance = new Chart(chartCanvas.value, {
    type: 'doughnut',
    data: {
      labels: effectiveGoals.value.map(g => formatGoalName(g.name)),
      datasets: [{
        data: effectiveGoals.value.map(g => g.count || 0),
        backgroundColor: effectiveGoals.value.map((_, i) => colors[i % colors.length]),
        borderWidth: 2,
        borderColor: '#ffffff',
        hoverOffset: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      cutout: '65%',
      plugins: { legend: { display: false } }
    }
  })
}

const fetchGoals = async () => {
  if (!props.clientId || !props.startDate || !props.endDate) return []
  try {
    const { data } = await api.get('dashboard/goals', {
      params: { client_id: props.clientId, date_from: props.startDate, date_to: props.endDate }
    })
    return (data || []).slice(0, 6)
  } catch {
    return []
  }
}

const localGoals = ref([])
const localLoading = ref(false)

watch(effectiveGoals, () => {
  if (effectiveGoals.value.length > 0) {
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
  if (effectiveGoals.value.length > 0) setTimeout(updateChart, 100)
})

onUnmounted(() => {
  if (chartInstance) chartInstance.destroy()
})
</script>
