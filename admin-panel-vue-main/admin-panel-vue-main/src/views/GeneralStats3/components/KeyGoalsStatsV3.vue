<template>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 w-full">
    <!-- Левая колонка: Статистика по ключевым целям (светло-синий фон по макету) -->
    <div class="bg-blue-50 rounded-2xl p-6 border border-blue-100 shadow-sm">
      <h3 class="text-sm font-black text-gray-900 uppercase tracking-wider mb-1">Статистика по ключевым целям</h3>
      <p class="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-6">За период</p>

      <div v-if="loading || localLoading" class="space-y-4">
        <div v-for="i in 3" :key="i" class="h-12 bg-blue-100/50 rounded-xl animate-pulse" />
      </div>

      <div v-else-if="effectiveGoals.length === 0" class="py-8 text-center text-gray-500 text-sm font-medium">
        Цели не настроены
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="(goal, index) in effectiveGoals"
          :key="goal.id || goal.name"
          class="flex items-center justify-between px-4 py-3 rounded-xl bg-blue-100/60 border border-blue-200/60"
        >
          <span class="text-sm font-semibold text-gray-800">{{ formatGoalName(goal.name) }}:</span>
          <div class="flex items-center gap-2">
            <span class="text-sm font-bold text-gray-900">{{ (goal.count || 0).toLocaleString() }} шт.</span>
            <span v-if="goal.trend != null" class="inline-flex items-center gap-0.5 text-xs font-bold text-green-600">
              <ArrowTrendingUpIcon class="w-3.5 h-3.5" />
              +{{ goal.trend }}%
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Центр: Итого (тёмно-синий по макету) -->
    <div class="bg-blue-800 rounded-2xl p-6 flex flex-col justify-center items-center shadow-lg">
      <h3 class="text-sm font-black text-white/90 uppercase tracking-wider mb-2">Итого:</h3>
      <p class="text-3xl sm:text-4xl font-black text-white">
        {{ totalConversions.toLocaleString() }} шт.
      </p>
    </div>

    <!-- Правая колонка: Разбивка по целям -->
    <div class="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
      <h3 class="text-sm font-black text-gray-500 uppercase tracking-wider mb-4">Разбивка по целям</h3>

      <div class="relative w-full aspect-square max-w-[200px] mx-auto mb-4">
        <canvas ref="chartCanvas" class="w-full h-full" />
        <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div class="text-center">
            <p class="text-2xl font-black text-gray-900">{{ totalConversions.toLocaleString() }}</p>
            <p class="text-[10px] font-bold text-gray-400 uppercase">шт.</p>
          </div>
        </div>
      </div>

      <div class="space-y-2 mb-4">
        <div
          v-for="(goal, index) in effectiveGoals"
          :key="goal.id || goal.name"
          class="flex items-center gap-2"
        >
          <div
            class="w-3 h-3 rounded-full flex-shrink-0"
            :style="{ backgroundColor: colors[index % colors.length] }"
          />
          <span class="text-xs font-semibold text-gray-700 truncate">{{ formatGoalName(goal.name) }}</span>
        </div>
      </div>

      <select
        class="w-full px-3 py-2 text-xs font-medium border border-gray-200 rounded-xl bg-gray-50 text-gray-700 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
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
import { ArrowTrendingUpIcon } from '@heroicons/vue/24/solid'
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
